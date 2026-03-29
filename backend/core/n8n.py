import threading
import requests
import datetime
import uuid
import os

# Central Automation Controller for N8n
class AutomationAgent:
    def __init__(self):
        self._dynamic_url = None

    def set_url(self, url):
        """Update the webhook URL dynamically from the UI."""
        self._dynamic_url = url

    @property
    def webhook_url(self):
        return self._dynamic_url or os.environ.get("N8N_WEBHOOK_URL")

    def emit(self, event_type: str, payload: dict):
        """Fire-and-forget event emission to N8n."""
        # Priority: Dynamic UI URL > Environment Variable
        url = self._dynamic_url or os.environ.get("N8N_WEBHOOK_URL")
        if not url:
            return

        event_data = {
            "event": event_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": str(uuid.uuid4()), # Generates a new ID per event, or should this be persistent? 
                                             # "Session IDs" usually imply a user session. 
                                             # For backend statelessness, we might just generate one or rely on payload.
                                             # Requirement says "session IDs". I'll generate a unique ID for the *event* 
                                             # or try to grab a global one if available. 
                                             # Safe default: unique event ID if no context passed.
            "payload": payload
        }

        def _send():
            try:
                requests.post(url, json=event_data, timeout=5)
            except Exception:
                # Failure must NEVER impact core execution
                pass

        thread = threading.Thread(target=_send)
        thread.daemon = True
        thread.start()

# Global instance
agent = AutomationAgent()
