"""
WhatsApp Adapter — Phase 9
Provider-agnostic WhatsApp messaging through HTTP API.
Supports: send, draft, template messages, recipient validation, delivery tracking.
"""

import os
import re
import json
import requests
from typing import Optional, Dict, Any
from datetime import datetime


class WhatsAppAdapter:
    """
    WhatsApp Business API adapter.
    Supports Meta Cloud API or any provider with HTTP send endpoint.
    """

    def __init__(self):
        self.api_url = os.getenv("WHATSAPP_API_URL", "")
        self.api_token = os.getenv("WHATSAPP_API_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self._contacts: Dict[str, str] = {}  # name → phone cache
        self._load_contacts()

    def is_configured(self) -> bool:
        return bool(self.api_url and self.api_token)

    def send_message(self, to: str, message: str,
                     template_name: str = None,
                     template_vars: dict = None) -> dict:
        """Send a WhatsApp message."""
        if not self.is_configured():
            raise WhatsAppNotConfiguredError(
                "WhatsApp is not configured. Set WHATSAPP_API_URL, "
                "WHATSAPP_API_TOKEN in .env"
            )

        phone = self._resolve_recipient(to)
        if not phone:
            raise ValueError(
                f"Could not resolve recipient '{to}'. "
                "Please provide a valid phone number with country code."
            )

        # Template message (required for first-contact in some providers)
        if template_name:
            return self._send_template(phone, template_name, template_vars or {})

        # Regular text message
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message},
        }

        response = requests.post(
            f"{self.api_url}/{self.phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        if response.status_code not in (200, 201):
            raise WhatsAppSendError(
                f"Failed to send: {response.status_code} — {response.text}"
            )

        result = response.json()
        msg_id = None
        if result.get("messages"):
            msg_id = result["messages"][0].get("id")

        return {
            "message_id": msg_id,
            "to": phone,
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat(),
            "provider_response": result,
        }

    def draft_message(self, to: str, message: str) -> dict:
        """Create a draft (stored locally, not sent)."""
        phone = self._resolve_recipient(to)
        return {
            "to": phone or to,
            "message": message,
            "status": "drafted",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _send_template(self, phone: str, template_name: str,
                       template_vars: dict) -> dict:
        """Send a template message."""
        components = []
        if template_vars:
            params = [{"type": "text", "text": v} for v in template_vars.values()]
            components.append({
                "type": "body",
                "parameters": params,
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": components,
            },
        }

        response = requests.post(
            f"{self.api_url}/{self.phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        if response.status_code not in (200, 201):
            raise WhatsAppSendError(
                f"Template send failed: {response.status_code} — {response.text}"
            )

        result = response.json()
        return {
            "message_id": result.get("messages", [{}])[0].get("id"),
            "to": phone,
            "template": template_name,
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ── Recipient Resolution ──────────────────────────────────────

    def _resolve_recipient(self, to: str) -> Optional[str]:
        """Resolve a name or number to a valid phone number."""
        # Already a phone number?
        cleaned = re.sub(r"[\s\-\(\)]", "", to)
        if re.match(r"^\+?\d{10,15}$", cleaned):
            return cleaned

        # Contact name lookup
        name_lower = to.lower().strip()
        if name_lower in self._contacts:
            return self._contacts[name_lower]

        return None

    def _load_contacts(self):
        """Load contact name→phone mapping from contacts.json."""
        contacts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "whatsapp_contacts.json"
        )
        if os.path.exists(contacts_file):
            try:
                with open(contacts_file, "r") as f:
                    data = json.load(f)
                self._contacts = {
                    k.lower(): v for k, v in data.items()
                }
            except Exception:
                self._contacts = {}

    def add_contact(self, name: str, phone: str):
        """Add a contact to the local mapping."""
        self._contacts[name.lower()] = phone
        contacts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "whatsapp_contacts.json"
        )
        os.makedirs(os.path.dirname(contacts_file), exist_ok=True)
        with open(contacts_file, "w") as f:
            json.dump(self._contacts, f, indent=2)


class WhatsAppNotConfiguredError(Exception):
    pass


class WhatsAppSendError(Exception):
    pass
