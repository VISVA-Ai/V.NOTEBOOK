"""
Google Calendar Adapter — Phase 8
Create/update/delete/list events with strict time handling.
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


TOKEN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "calendar_token.json"
)
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_root_dir = os.path.dirname(_backend_dir)

# Support credentials.json in either backend/ or project root
if os.path.exists(os.path.join(_root_dir, "credentials.json")):
    CREDENTIALS_FILE = os.path.join(_root_dir, "credentials.json")
else:
    CREDENTIALS_FILE = os.path.join(_backend_dir, "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarAdapter:
    """Google Calendar API adapter."""

    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service

        if not os.path.exists(CREDENTIALS_FILE):
            raise CalendarNotConfiguredError(
                "Google Calendar is not configured. Place credentials.json in project root."
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

                os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
                with open(TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())

            self._service = build("calendar", "v3", credentials=creds)
            return self._service

        except ImportError:
            raise CalendarNotConfiguredError(
                "Google API packages not installed. Run: "
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

    def is_configured(self) -> bool:
        try:
            self._get_service()
            return True
        except Exception:
            return False

    def create_event(self, title: str, datetime_str: str,
                     attendees: list = None, location: str = None,
                     end_datetime: str = None) -> dict:
        """Create a calendar event. datetime_str must be explicit."""
        service = self._get_service()

        start = self._parse_datetime(datetime_str)
        if not start:
            raise ValueError(
                f"Could not parse datetime: '{datetime_str}'. "
                "Please provide an explicit date and time."
            )

        end = self._parse_datetime(end_datetime) if end_datetime else start + timedelta(hours=1)

        # Detect timezone from the datetime string, default to Asia/Kolkata
        tz_name = "Asia/Kolkata"

        event = {
            "summary": title,
            "start": {"dateTime": start.isoformat(), "timeZone": tz_name},
            "end": {"dateTime": end.isoformat(), "timeZone": tz_name},
        }

        if location:
            event["location"] = location

        if attendees:
            event["attendees"] = [{"email": a} for a in attendees]

        result = service.events().insert(
            calendarId="primary", body=event
        ).execute()

        return {
            "event_id": result.get("id"),
            "html_link": result.get("htmlLink"),
            "status": "created",
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }

    def update_event(self, event_id: str, patch: dict) -> dict:
        """Update an existing event."""
        service = self._get_service()

        # Get existing event
        event = service.events().get(
            calendarId="primary", eventId=event_id
        ).execute()

        # Apply patch
        for key, value in patch.items():
            if key == "title":
                event["summary"] = value
            elif key == "location":
                event["location"] = value
            elif key == "datetime":
                dt = self._parse_datetime(value)
                if dt:
                    event["start"] = {"dateTime": dt.isoformat(), "timeZone": "Asia/Kolkata"}
            elif key == "end_datetime":
                dt = self._parse_datetime(value)
                if dt:
                    event["end"] = {"dateTime": dt.isoformat(), "timeZone": "Asia/Kolkata"}
            elif key == "attendees":
                event["attendees"] = [{"email": a} for a in value]

        result = service.events().update(
            calendarId="primary", eventId=event_id, body=event
        ).execute()

        return {
            "event_id": result.get("id"),
            "status": "updated",
            "html_link": result.get("htmlLink"),
        }

    def delete_event(self, event_id: str) -> dict:
        """Delete an event."""
        service = self._get_service()
        service.events().delete(
            calendarId="primary", eventId=event_id
        ).execute()
        return {"event_id": event_id, "status": "deleted"}

    def list_events(self, start: str = None, end: str = None,
                    max_results: int = 10) -> dict:
        """List upcoming events."""
        service = self._get_service()

        time_min = start or datetime.utcnow().isoformat() + "Z"
        params = {
            "calendarId": "primary",
            "timeMin": time_min,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if end:
            params["timeMax"] = end

        result = service.events().list(**params).execute()

        events = []
        for event in result.get("items", []):
            events.append({
                "event_id": event.get("id"),
                "title": event.get("summary", "Untitled"),
                "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
                "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date")),
                "location": event.get("location"),
                "html_link": event.get("htmlLink"),
                "attendees": [a.get("email") for a in event.get("attendees", [])],
            })

        return {"count": len(events), "events": events}

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse datetime string — strict, no guessing."""
        if not dt_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_str.strip(), fmt)
            except ValueError:
                continue

        # Try ISO format
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00").replace("+00:00", ""))
        except Exception:
            pass

        return None


class CalendarNotConfiguredError(Exception):
    pass
