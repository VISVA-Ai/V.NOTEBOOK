"""
Gmail Adapter — Phase 7: Google Gmail API Integration
OAuth flow, token persistence, send/read/search/draft.
Falls back gracefully when credentials are not configured.
"""

import os
import re
import html
import base64
import json
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_root_dir = os.path.dirname(_backend_dir)

if os.path.exists(os.path.join(_root_dir, "credentials.json")):
    CREDENTIALS_FILE = os.path.join(_root_dir, "credentials.json")
else:
    CREDENTIALS_FILE = os.path.join(_backend_dir, "credentials.json")
TOKEN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "gmail_token.json"
)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailAdapter:
    """Gmail API adapter with OAuth flow and graceful degradation."""

    def __init__(self):
        self._service = None
        self._initialized = False

    def _get_service(self):
        """Lazy initialization of Gmail API service."""
        if self._service:
            return self._service

        if not os.path.exists(CREDENTIALS_FILE):
            raise GmailNotConfiguredError(
                "Gmail is not configured. Place your Google OAuth credentials.json "
                "in the project root. See README for setup instructions."
            )

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            creds = None
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_FILE, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save token
                os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
                with open(TOKEN_FILE, "w") as token:
                    token.write(creds.to_json())

            self._service = build("gmail", "v1", credentials=creds)
            self._initialized = True
            return self._service

        except ImportError:
            raise GmailNotConfiguredError(
                "Google API packages not installed. Run: "
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

    def is_configured(self) -> bool:
        """Check if Gmail is ready to use."""
        try:
            self._get_service()
            return True
        except Exception:
            return False

    # ── Core Operations ───────────────────────────────────────────

    def send_email(self, to: str, subject: str, body: str,
                   attachments: list = None) -> dict:
        """Send an email via Gmail API."""
        service = self._get_service()

        message = MIMEMultipart() if attachments else MIMEText(body)
        if attachments:
            message.attach(MIMEText(body))

        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        return {
            "message_id": result.get("id"),
            "thread_id": result.get("threadId"),
            "status": "sent",
            "to": to,
            "subject": subject,
        }

    def draft_email(self, to: str, subject: str, body: str,
                   thread_id: str = None, message_id: str = None) -> dict:
        """Create a draft in Gmail, optionally threaded under an existing conversation."""
        service = self._get_service()

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        # Thread the draft under the original conversation
        if message_id:
            message["In-Reply-To"] = message_id
            message["References"] = message_id

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft_body = {"message": {"raw": raw}}
        if thread_id:
            draft_body["message"]["threadId"] = thread_id

        result = service.users().drafts().create(
            userId="me",
            body=draft_body
        ).execute()

        return {
            "draft_id": result.get("id"),
            "message_id": result.get("message", {}).get("id"),
            "thread_id": thread_id,
            "status": "drafted",
            "to": to,
            "subject": subject,
        }

    def reply_to_email(self, thread_id: str, to: str, body: str,
                       subject: str = "", message_id: str = None) -> dict:
        """Send a reply within an existing Gmail thread.
        GAP 1: Subject fallback threading
        GAP 2: Reply-To header priority
        GAP 3: Quoted original message context
        """
        service = self._get_service()

        # Fetch the original thread to get headers
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["From", "To", "Reply-To", "Subject", "Message-ID", "Date"]
        ).execute()

        last_msg = thread.get("messages", [{}])[-1]
        orig_headers = {h["name"].lower(): h["value"]
                        for h in last_msg.get("payload", {}).get("headers", [])}

        # Get our own email to avoid replying to ourselves
        try:
            my_email = service.users().getProfile(userId='me').execute().get('emailAddress', '').lower()
        except:
            my_email = ""

        orig_from = orig_headers.get("from", "")
        
        # If the NLP engine explicitly passed our own email as 'to', ignore it 
        # so the smart header fallback picks the right person.
        if to and my_email and my_email in to.lower():
            to = ""

        # GAP 2 + Fix: If we sent the last message, we want to follow up with the 'To' person.
        # Otherwise, reply to 'Reply-To' or 'From'.
        if my_email and my_email in orig_from.lower():
            reply_to = to or orig_headers.get("to", "")
        else:
            reply_to = to or orig_headers.get("reply-to") or orig_from

        # GAP 1: Subject fallback with Re: prefix
        orig_subject = subject or orig_headers.get("subject", "")
        if not orig_subject.lower().startswith("re:"):
            orig_subject = f"Re: {orig_subject}"

        # Get the original Message-ID for threading headers
        orig_msg_id = message_id or orig_headers.get("message-id", "")

        # GAP 3: Quoted original message context
        orig_snippet = last_msg.get("snippet", "")
        orig_from = orig_headers.get("from", "")
        orig_date = orig_headers.get("date", "")
        quoted_body = (
            f"{body}\n\n"
            f"---\n"
            f"On {orig_date}, {orig_from} wrote:\n"
            f"> {orig_snippet}"
        )

        # Build MIME message with threading headers
        message = MIMEText(quoted_body)
        message["to"] = reply_to
        message["subject"] = orig_subject
        if orig_msg_id:
            message["In-Reply-To"] = orig_msg_id
            message["References"] = orig_msg_id

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": thread_id}
        ).execute()

        return {
            "message_id": result.get("id"),
            "thread_id": result.get("threadId"),
            "status": "sent",
            "to": reply_to,
            "subject": orig_subject,
        }

    def read_emails(self, query: str = None, max_results: int = 10) -> dict:
        """Read recent emails from inbox."""
        service = self._get_service()

        q = "in:inbox"
        if query:
            if "in:" in query or "is:sent" in query or "label:" in query:
                q = query
            else:
                q = f"in:inbox {query}"
        results = service.users().messages().list(
            userId="me", q=q, maxResults=max_results
        ).execute()

        messages = []
        for msg_meta in results.get("messages", []):
            msg = service.users().messages().get(
                userId="me", id=msg_meta["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            messages.append({
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": self._clean_snippet(msg.get("snippet", "")),
            })

        return {
            "count": len(messages),
            "messages": messages,
            "query": q,
        }

    def search_emails(self, query: str, max_results: int = 10) -> dict:
        """Search emails with Gmail query syntax — independent of read_emails.
        Does NOT inject in:inbox, allowing is:sent and other scopes."""
        service = self._get_service()

        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = []
        for msg_meta in results.get("messages", []):
            msg = service.users().messages().get(
                userId="me", id=msg_meta["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            messages.append({
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": self._clean_snippet(msg.get("snippet", "")),
            })

        return {
            "count": len(messages),
            "messages": messages,
            "query": query,
        }

    def get_thread(self, thread_id: str) -> dict:
        """Get full email thread for context."""
        service = self._get_service()

        thread = service.users().threads().get(
            userId="me", id=thread_id, format="full"
        ).execute()

        messages = []
        for msg in thread.get("messages", []):
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

            # Extract body
            body = ""
            payload = msg.get("payload", {})
            if payload.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
            elif payload.get("parts"):
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                        break

            messages.append({
                "id": msg["id"],
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "subject": headers.get("Subject", ""),
                "body": body[:2000],
                "snippet": msg.get("snippet", ""),
            })

        return {
            "thread_id": thread_id,
            "message_count": len(messages),
            "messages": messages,
        }

    @staticmethod
    def _clean_snippet(text: str) -> str:
        """GAP 5: Decode HTML entities AND strip HTML tags from snippets."""
        text = html.unescape(text)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    @staticmethod
    def _rank_results(query: str, messages: list) -> list:
        """GAP 4: Lightweight relevance ranking by keyword match score."""
        keywords = query.lower().split()
        # Remove Gmail operators from scoring
        keywords = [k for k in keywords if ':' not in k and k not in ('and', 'or', 'not')]
        if not keywords:
            return messages

        def score(msg):
            text = f"{msg.get('from', '')} {msg.get('subject', '')} {msg.get('snippet', '')}".lower()
            return sum(1 for kw in keywords if kw in text)

        return sorted(messages, key=score, reverse=True)


class GmailNotConfiguredError(Exception):
    """Raised when Gmail credentials are not available."""
    pass
