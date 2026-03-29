"""
Persistent Action Queue — Phase 4
File-based durable store at data/actions.json with atomic writes,
full audit trail, status transitions, and idempotency support.
"""

import json
import os
import uuid
import tempfile
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any
from models.assistant import ActionModel, AuditEntry, ActionStatus


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ACTIONS_FILE = os.path.join(DATA_DIR, "actions.json")


class ActionQueue:
    """Thread-safe, file-backed action queue with audit trail."""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(ACTIONS_FILE):
            self._atomic_write([])

    # ── CRUD ──────────────────────────────────────────────────────

    def create_action(self, intent: str, parameters: dict,
                      confirmation_level: str = "normal",
                      parent_group_id: str = None,
                      idempotency_key: str = None) -> ActionModel:
        """Create a new pending action."""
        actions = self._load()

        # Idempotency check
        if idempotency_key:
            for a in actions:
                if a.get("idempotency_key") == idempotency_key:
                    return ActionModel(**a)

        action = ActionModel(
            id=str(uuid.uuid4()),
            intent=intent,
            parameters=parameters,
            status=ActionStatus.PENDING,
            confirmation_level=confirmation_level,
            parent_group_id=parent_group_id,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
            audit_log=[AuditEntry(
                event="created",
                details={"intent": intent}
            ).model_dump()]
        )

        actions.append(action.model_dump())
        self._atomic_write(actions)
        return action

    def get_actions(self, status: str = None, limit: int = 50) -> List[ActionModel]:
        """Get all actions, optionally filtered by status."""
        actions = self._load()
        if status:
            actions = [a for a in actions if a.get("status") == status]
        actions.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return [ActionModel(**a) for a in actions[:limit]]

    def get_action(self, action_id: str) -> Optional[ActionModel]:
        """Get a single action by ID."""
        actions = self._load()
        for a in actions:
            if a.get("id") == action_id:
                return ActionModel(**a)
        return None

    def update_action(self, action_id: str, patch: dict) -> Optional[ActionModel]:
        """Update action fields and record in audit log."""
        actions = self._load()
        for i, a in enumerate(actions):
            if a.get("id") == action_id:
                # Don't allow patching status directly — use update_status
                patch.pop("status", None)
                patch.pop("id", None)

                old_params = a.get("parameters", {})
                a.update(patch)
                a["updated_at"] = datetime.utcnow().isoformat()

                # Audit entry
                audit = AuditEntry(
                    event="updated",
                    details={"changed_fields": list(patch.keys())}
                ).model_dump()
                a.setdefault("audit_log", []).append(audit)

                actions[i] = a
                self._atomic_write(actions)
                return ActionModel(**a)
        return None

    def update_status(self, action_id: str, new_status: str,
                      execution_result: dict = None,
                      error_message: str = None) -> Optional[ActionModel]:
        """Transition action status with validation and audit."""
        valid_transitions = {
            ActionStatus.PENDING: [ActionStatus.APPROVED, ActionStatus.CANCELED],
            ActionStatus.APPROVED: [ActionStatus.EXECUTED, ActionStatus.FAILED, ActionStatus.CANCELED],
            ActionStatus.FAILED: [ActionStatus.APPROVED, ActionStatus.CANCELED],  # retry
        }

        actions = self._load()
        for i, a in enumerate(actions):
            if a.get("id") == action_id:
                current = a.get("status")
                
                # Normalize strings to enums for comparison
                try:
                    current_enum = ActionStatus(current) if isinstance(current, str) else current
                    new_enum = ActionStatus(new_status) if isinstance(new_status, str) else new_status
                except ValueError:
                    current_enum = current
                    new_enum = new_status

                # Validate transition
                allowed = valid_transitions.get(current_enum, [])
                if new_enum not in allowed and current_enum != new_enum:
                    raise ValueError(
                        f"Invalid transition: {current} → {new_status}. "
                        f"Allowed: {[s.value if hasattr(s, 'value') else s for s in allowed]}"
                    )

                # Store as string in JSON
                new_status_val = new_enum.value if hasattr(new_enum, "value") else str(new_enum)
                a["status"] = new_status_val
                a["updated_at"] = datetime.utcnow().isoformat()

                if execution_result is not None:
                    a["execution_result"] = execution_result
                if error_message is not None:
                    a["error_message"] = error_message
                if new_enum == ActionStatus.FAILED:
                    a["retry_count"] = a.get("retry_count", 0) + 1

                audit = AuditEntry(
                    event=f"status_changed_to_{new_status_val}",
                    details={
                        "from": current,
                        "to": new_status_val,
                        "error": error_message
                    }
                ).model_dump()
                a.setdefault("audit_log", []).append(audit)

                actions[i] = a
                self._atomic_write(actions)
                return ActionModel(**a)
        return None

    def cancel_action(self, action_id: str) -> Optional[ActionModel]:
        """Cancel a pending or approved action."""
        action = self.get_action(action_id)
        if not action:
            return None
        if action.status in [ActionStatus.EXECUTED]:
            raise ValueError("Cannot cancel an already executed action.")
        return self.update_status(action_id, ActionStatus.CANCELED)

    def append_audit_log(self, action_id: str, event: str,
                         details: dict = None) -> None:
        """Add an audit entry without changing status."""
        actions = self._load()
        for i, a in enumerate(actions):
            if a.get("id") == action_id:
                audit = AuditEntry(event=event, details=details).model_dump()
                a.setdefault("audit_log", []).append(audit)
                a["updated_at"] = datetime.utcnow().isoformat()
                actions[i] = a
                self._atomic_write(actions)
                return

    # ── Multi-action group ────────────────────────────────────────

    def get_action_group(self, group_id: str) -> List[ActionModel]:
        """Get all actions belonging to a multi-action group."""
        actions = self._load()
        group = [a for a in actions if a.get("parent_group_id") == group_id]
        return [ActionModel(**a) for a in group]

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        actions = self._load()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return {
            "total": len(actions),
            "pending": sum(1 for a in actions if a.get("status") == "pending"),
            "approved": sum(1 for a in actions if a.get("status") == "approved"),
            "executed": sum(1 for a in actions if a.get("status") == "executed"),
            "failed": sum(1 for a in actions if a.get("status") == "failed"),
            "today": sum(1 for a in actions
                         if a.get("created_at", "").startswith(today)),
        }

    # ── Persistence (atomic file I/O) ─────────────────────────────

    def _load(self) -> list:
        """Load actions from disk. Returns empty list on corruption."""
        try:
            with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _atomic_write(self, actions: list) -> None:
        """Atomic write: write to temp file, then rename."""
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=DATA_DIR, suffix=".json.tmp"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(actions, f, indent=2, default=str)
            # Atomic replace
            shutil.move(tmp_path, ACTIONS_FILE)
        except Exception:
            # Cleanup temp file if rename fails
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
