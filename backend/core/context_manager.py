"""
Context Manager — Upgrade 1: Memory + Context Layer
Tracks conversation state, last intents, pending clarifications,
user preferences, and active threads per session.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from models.assistant import ContextState


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CONTEXT_DIR = os.path.join(DATA_DIR, "contexts")


class ContextManager:
    """Manages per-session conversational context for multi-turn interactions."""

    def __init__(self):
        os.makedirs(CONTEXT_DIR, exist_ok=True)
        self._cache: Dict[str, ContextState] = {}

    def get_context(self, session_id: str) -> ContextState:
        """Get or create context for a session."""
        if session_id in self._cache:
            return self._cache[session_id]

        # Try load from disk
        path = self._path(session_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ctx = ContextState(**data)
                self._cache[session_id] = ctx
                return ctx
            except (json.JSONDecodeError, Exception):
                pass

        # New session
        ctx = ContextState(session_id=session_id)
        self._cache[session_id] = ctx
        return ctx

    def update_context(self, session_id: str, **kwargs) -> ContextState:
        """Update context fields for a session."""
        ctx = self.get_context(session_id)
        for key, value in kwargs.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value)
        self._save(session_id, ctx)
        return ctx

    def add_to_history(self, session_id: str, role: str,
                       content: str, metadata: dict = None) -> None:
        """Append a message to the conversation history (capped at 50)."""
        ctx = self.get_context(session_id)
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            entry["metadata"] = metadata
        ctx.conversation_history.append(entry)
        # Cap history to last 50 messages
        if len(ctx.conversation_history) > 50:
            ctx.conversation_history = ctx.conversation_history[-50:]
        self._save(session_id, ctx)

    def set_pending_action(self, session_id: str,
                           action_id: Optional[str]) -> None:
        """Set or clear the pending action awaiting approval."""
        self.update_context(session_id, pending_action_id=action_id)

    def set_last_intent(self, session_id: str, intent: str,
                        entities: dict = None) -> None:
        """Record the last parsed intent for context resolution."""
        self.update_context(
            session_id,
            last_intent=intent,
            last_entities=entities or {}
        )

    def set_active_thread(self, session_id: str,
                          thread_id: Optional[str]) -> None:
        """Set the active email thread for thread-aware operations."""
        self.update_context(session_id, active_thread_id=thread_id)

    def add_recent_action(self, session_id: str, action_id: str) -> None:
        """Track recently executed actions (capped at 20)."""
        ctx = self.get_context(session_id)
        ctx.recent_actions.append(action_id)
        if len(ctx.recent_actions) > 20:
            ctx.recent_actions = ctx.recent_actions[-20:]
        self._save(session_id, ctx)

    def set_preference(self, session_id: str, key: str, value: Any) -> None:
        """Store a user preference (e.g., 'default_follow_up_days': 2)."""
        ctx = self.get_context(session_id)
        ctx.user_preferences[key] = value
        self._save(session_id, ctx)

    def add_pending_clarification(self, session_id: str,
                                  field: str) -> None:
        """Track a field that needs clarification."""
        ctx = self.get_context(session_id)
        if field not in ctx.pending_clarifications:
            ctx.pending_clarifications.append(field)
        self._save(session_id, ctx)

    def clear_clarifications(self, session_id: str) -> None:
        """Clear all pending clarifications (after they're resolved)."""
        self.update_context(session_id, pending_clarifications=[])

    def get_conversation_for_llm(self, session_id: str,
                                 max_messages: int = 10) -> List[dict]:
        """Get recent conversation history formatted for LLM context."""
        ctx = self.get_context(session_id)
        recent = ctx.conversation_history[-max_messages:]
        return [
            {"role": m["role"], "content": m["content"]}
            for m in recent
            if m.get("role") in ("user", "assistant")
        ]

    # ── Persistence ───────────────────────────────────────────────

    def _path(self, session_id: str) -> str:
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        return os.path.join(CONTEXT_DIR, f"{safe_id}.json")

    def _save(self, session_id: str, ctx: ContextState) -> None:
        self._cache[session_id] = ctx
        path = self._path(session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ctx.model_dump(), f, indent=2, default=str)
