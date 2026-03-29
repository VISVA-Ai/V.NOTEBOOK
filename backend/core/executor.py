"""
Executor — Phase 6: Provider-neutral execution layer.
Dispatches approved actions to the correct adapter, captures results,
handles errors, and updates action status.
"""

from typing import Dict, Any, Optional
from core.actions import ActionQueue
from core.adapters.gmail_adapter import GmailAdapter
from core.adapters.calendar_adapter import CalendarAdapter
from core.adapters.whatsapp_adapter import WhatsAppAdapter
from models.assistant import ActionStatus, ExecutionResult


# Rate limiter: max actions per minute
MAX_ACTIONS_PER_MINUTE = 10
_recent_executions = []


class Executor:
    """
    Provider-neutral executor. Routes approved actions to the
    correct adapter and captures structured results.
    """

    def __init__(self, action_queue: ActionQueue):
        self.actions = action_queue
        self.gmail = GmailAdapter()
        self.calendar = CalendarAdapter()
        self.whatsapp = WhatsAppAdapter()

        # Intent → handler mapping
        self._handlers = {
            "send_email": self._exec_send_email,
            "draft_email": self._exec_draft_email,
            "reply_email": self._exec_reply_email,
            "read_email": self._exec_read_email,
            "search_email": self._exec_search_email,
            "create_event": self._exec_create_event,
            "update_event": self._exec_update_event,
            "delete_event": self._exec_delete_event,
            "list_events": self._exec_list_events,
            "send_whatsapp_message": self._exec_send_whatsapp,
            "draft_whatsapp_message": self._exec_draft_whatsapp,
        }

    def execute(self, action_id: str) -> ExecutionResult:
        """Execute an approved action. Returns structured result."""
        action = self.actions.get_action(action_id)

        if not action:
            return ExecutionResult(
                success=False, action_id=action_id, intent="unknown",
                error="Action not found"
            )

        if action.status != ActionStatus.APPROVED:
            return ExecutionResult(
                success=False, action_id=action_id, intent=action.intent,
                error=f"Action is not approved. Current status: {action.status}"
            )

        # Rate limit check
        if not self._check_rate_limit():
            return ExecutionResult(
                success=False, action_id=action_id, intent=action.intent,
                error="Rate limit exceeded. Please wait before executing more actions."
            )

        # Get handler
        handler = self._handlers.get(action.intent)
        if not handler:
            self.actions.update_status(
                action_id, ActionStatus.FAILED,
                error_message=f"No executor handler for intent: {action.intent}"
            )
            return ExecutionResult(
                success=False, action_id=action_id, intent=action.intent,
                error=f"Unsupported action intent: {action.intent}"
            )

        # Execute with exception safety
        try:
            self.actions.append_audit_log(action_id, "execution_started")
            provider_response = handler(action.parameters)

            self.actions.update_status(
                action_id, ActionStatus.EXECUTED,
                execution_result=provider_response
            )
            self._track_execution()

            return ExecutionResult(
                success=True,
                action_id=action_id,
                intent=action.intent,
                provider_response=provider_response,
                message=f"Successfully executed: {action.intent.replace('_', ' ')}"
            )

        except Exception as e:
            error_msg = str(e)
            self.actions.update_status(
                action_id, ActionStatus.FAILED,
                error_message=error_msg
            )
            return ExecutionResult(
                success=False,
                action_id=action_id,
                intent=action.intent,
                error=error_msg,
                message=f"Execution failed: {error_msg}"
            )

    # ── Gmail Handlers ────────────────────────────────────────────

    def _exec_send_email(self, params: dict) -> dict:
        return self.gmail.send_email(
            to=params["to"],
            subject=params.get("subject", ""),
            body=params.get("body", ""),
            attachments=params.get("attachments"),
        )

    def _exec_draft_email(self, params: dict) -> dict:
        return self.gmail.draft_email(
            to=params["to"],
            subject=params.get("subject", ""),
            body=params.get("body", ""),
            thread_id=params.get("thread_id"),
            message_id=params.get("message_id"),
        )

    def _exec_reply_email(self, params: dict) -> dict:
        return self.gmail.reply_to_email(
            thread_id=params["thread_id"],
            to=params.get("to", ""),
            body=params.get("body", ""),
            subject=params.get("subject", ""),
            message_id=params.get("message_id"),
        )

    def _exec_read_email(self, params: dict) -> dict:
        return self.gmail.read_emails(query=params.get("query"))

    def _exec_search_email(self, params: dict) -> dict:
        return self.gmail.search_emails(query=params["query"])

    # ── Calendar Handlers ─────────────────────────────────────────

    def _exec_create_event(self, params: dict) -> dict:
        return self.calendar.create_event(
            title=params["title"],
            datetime_str=params.get("datetime", params.get("datetime_str", "")),
            attendees=params.get("attendees"),
            location=params.get("location"),
            end_datetime=params.get("end_datetime"),
        )

    def _exec_update_event(self, params: dict) -> dict:
        return self.calendar.update_event(
            event_id=params["event_id"],
            patch=params.get("patch", {}),
        )

    def _exec_delete_event(self, params: dict) -> dict:
        return self.calendar.delete_event(event_id=params["event_id"])

    def _exec_list_events(self, params: dict) -> dict:
        return self.calendar.list_events(
            start=params.get("start"),
            end=params.get("end"),
        )

    # ── WhatsApp Handlers ─────────────────────────────────────────

    def _exec_send_whatsapp(self, params: dict) -> dict:
        return self.whatsapp.send_message(
            to=params["to"],
            message=params["message"],
            template_name=params.get("template_name"),
            template_vars=params.get("template_vars"),
        )

    def _exec_draft_whatsapp(self, params: dict) -> dict:
        return self.whatsapp.draft_message(
            to=params["to"],
            message=params["message"],
        )

    # ── Rate Limiting ─────────────────────────────────────────────

    def _check_rate_limit(self) -> bool:
        """Simple rate limiter: max N executions per minute."""
        import time
        now = time.time()
        global _recent_executions
        _recent_executions = [t for t in _recent_executions if now - t < 60]
        return len(_recent_executions) < MAX_ACTIONS_PER_MINUTE

    def _track_execution(self):
        import time
        _recent_executions.append(time.time())
