"""
Semantic Intent Parser — Phase 1 + 3
Converts natural language user input into structured IntentResult using Groq LLM.
Supports multi-turn context, thread awareness, and follow-up question generation.
"""

import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import time as _time
from core.context_manager import ContextManager
from models.assistant import IntentResult, IntentParameters


# Required fields per intent for validation
REQUIRED_FIELDS = {
    "send_email": ["to", "subject", "body"],
    "draft_email": ["to", "subject", "body"],
    "reply_email": ["thread_id", "body"],
    "read_email": ["time_frame"],
    "search_email": ["query"],
    "summarize_thread": ["thread_id"],
    "suggest_follow_up": [],
    "suggest_reminder": [],
    "suggest_reply": [],
    "detect_action_items": [],
    "create_event": ["title", "datetime"],
    "update_event": ["event_id"],
    "delete_event": ["event_id"],
    "list_events": [],
    "send_whatsapp_message": ["to", "message"],
    "draft_whatsapp_message": ["to", "message"],
    "unknown": [],
}

CONFIDENCE_THRESHOLD = 0.6

SYSTEM_PROMPT = """You are an intent classification and entity extraction system for a personal assistant.

Your job: Given user text (and optional conversation context), output a structured JSON object.

SUPPORTED INTENTS:
- send_email: User wants to send/compose an email
- read_email: General check of recent emails (e.g. 'check my emails'). If the user mentions ANY specific sender, keyword, topic, or wants SENT emails, YOU MUST NOT USE THIS! Use search_email instead! MUST include a time_frame (e.g. 'today').
- search_email: User wants to find SPECIFIC emails (by sender, topic, or sent status). Convert their request into a valid native Gmail search query (e.g. 'is:sent'). BE SMART: Always append `-category:promotions -category:social` to filter out automated ads unless they specifically ask for them! DO NOT add time limits to the query string itself; put time limits in the `time_frame` field ONLY if explicitly requested!
- draft_email: User wants to create a draft (not send immediately)
- reply_email: User wants to REPLY to a specific email they received. You MUST extract the thread_id from conversation context. Subject and to are auto-resolved from the original thread.
- summarize_thread: User wants a summary of an email thread
- suggest_follow_up: User wants follow-up recommendations for an email thread
- suggest_reminder: User wants to extract reminder tasks from an email thread
- suggest_reply: User wants a suggested reply to an email
- detect_action_items: User wants to extract tasks from an email thread
- create_event: User wants to create a calendar event, meeting, or a scheduled reminder
- update_event: User explicitly wants to modify, reschedule, change, or move an EXISTING event. (Do NOT use for 'setting a reminder')
- delete_event: User wants to cancel/remove an event
- list_events: User wants to see upcoming events/schedule
- send_whatsapp_message: User wants to send a WhatsApp message
- draft_whatsapp_message: User wants to draft a WhatsApp message
- unknown: Cannot determine intent clearly

OUTPUT FORMAT (strict JSON, no markdown):
{
  "intent": "one_of_above",
  "confidence": 0.0 to 1.0,
  "parameters": {
    "to": "recipient email or phone",
    "contact_name": "human name if mentioned",
    "subject": "email subject",
    "body": "message body",
    "query": "Gmail search query (e.g., 'from:john -category:promotions in:anywhere'). No time limits unless requested.",
    "time_frame": "Gmail date query (e.g., 'newer_than:1d', 'after:2026-03-15')",
    "thread_id": "thread identifier if known",
    "datetime": "STRICT ISO 8601 string with LOCAL timezone offset (e.g. 2026-09-14T09:00:00+05:30). You MUST use the SAME offset as CURRENT_DATETIME. NEVER default to +00:00.",
    "end_datetime": "STRICT ISO 8601 string if end time is specified",
    "title": "event title",
    "attendees": ["list of attendees"],
    "location": "event location",
    "message": "WhatsApp message body",
    "priority": "low/normal/high/urgent"
  },
  "missing_fields": ["fields that are required but not provided"],
  "requires_confirmation": true,
  "message": "brief explanation or question for user",
  "next_step": "question | action_preview | clarification_needed | recommendation"
}

RULES:
- ONLY extract what the user explicitly stated. NEVER invent values.
- If a required field is missing, list it in missing_fields and set next_step to "question".
- If user provides a full new command (e.g., 'set a reminder for...', 'send an email to...'), treat it as a NEW INTENT and ignore prior pending fields.
- If intent is unclear, set intent to "unknown", confidence low, and ask for clarification.
- If user says "send it" or "yes" without context, check conversation history for prior intent.
- For "reply" vs "new email" — check if thread context exists.
- For dates: The current exact date and time is {CURRENT_DATETIME}. You MUST format all dates as strict ISO 8601 strings using the SAME timezone offset as {CURRENT_DATETIME}. Do not use +00:00 (UTC) unless the user explicitly says UTC. If no time is specified, default to 09:00:00 local time.
- Confidence: 0.9+ for clear explicit requests, 0.6-0.8 for implied, <0.6 for ambiguous.
- For multi-intent ("email John and create a meeting"), identify BOTH intents and list them in message.
- Output ONLY the JSON object, nothing else."""


class AssistantChatParser:
    """Semantic intent parser using Groq LLM with multi-turn context."""

    def __init__(self, llm_handler, context_manager: ContextManager):
        self.llm = llm_handler
        self.context = context_manager

    def parse(self, user_text: str, session_id: str,
              thread_context: str = None) -> IntentResult:
        """Parse user text into structured intent with context awareness."""

        ctx = self.context.get_context(session_id)

        # Add user message to history
        self.context.add_to_history(session_id, "user", user_text)

        # Build LLM prompt with context
        prompt = self._build_prompt(user_text, ctx, thread_context)

        # Inject current datetime WITH local timezone offset
        # Get local UTC offset
        utc_offset_seconds = -_time.timezone if _time.daylight == 0 else -_time.altzone
        utc_offset = timezone(offset=__import__('datetime').timedelta(seconds=utc_offset_seconds))
        current_time = datetime.now(utc_offset).isoformat()
        dynamic_system_prompt = SYSTEM_PROMPT.replace(
            "{CURRENT_DATETIME}", current_time
        )

        # Call LLM
        raw_response = self.llm.get_response(
            prompt=prompt,
            system_prompt=dynamic_system_prompt,
            model="llama-3.3-70b-versatile",
        )

        # Parse LLM output
        result = self._parse_response(raw_response, user_text)

        # Apply context resolution (handle "send it", "yes", etc.)
        result = self._resolve_with_context(result, ctx)

        # Validate required fields
        result = self._validate_fields(result)

        # Update context state
        self.context.set_last_intent(
            session_id, result.intent,
            result.parameters.model_dump(exclude_none=True)
        )

        # Add assistant response to history
        self.context.add_to_history(
            session_id, "assistant", result.message,
            metadata={"intent": result.intent, "confidence": result.confidence}
        )

        return result

    def _build_prompt(self, user_text: str, ctx, thread_context: str = None) -> str:
        """Build the full prompt with conversation and thread context."""
        parts = []

        # Conversation history (last 6 messages for LLM context)
        history = ctx.conversation_history[-6:]
        if history:
            parts.append("CONVERSATION HISTORY:")
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"  {role}: {content}")
            parts.append("")

        # Pending clarifications
        if ctx.pending_clarifications:
            parts.append(f"PENDING FIELDS NEEDING ANSWERS: {ctx.pending_clarifications}")
            parts.append(f"LAST INTENT: {ctx.last_intent}")
            parts.append(f"EXISTING ENTITIES: {json.dumps(ctx.last_entities)}")
            parts.append("")

        # Active thread context
        if thread_context:
            parts.append(f"EMAIL THREAD CONTEXT:\n{thread_context[:2000]}")
            parts.append("")

        if ctx.active_thread_id:
            parts.append(f"ACTIVE THREAD ID: {ctx.active_thread_id}")
            parts.append("")

        parts.append(f"USER MESSAGE: {user_text}")

        return "\n".join(parts)

    def _parse_response(self, raw: str, original_text: str) -> IntentResult:
        """Parse LLM JSON output, handling malformed responses."""
        try:
            # Extract JSON from response (strip markdown fences if present)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
                cleaned = cleaned.rstrip("`").strip()

            data = json.loads(cleaned)

            params = data.get("parameters", {})
            # Map 'datetime' key to 'datetime_str' for Pydantic alias
            if "datetime" in params and "datetime_str" not in params:
                params["datetime_str"] = params.pop("datetime")

            return IntentResult(
                intent=data.get("intent", "unknown"),
                confidence=float(data.get("confidence", 0.0)),
                parameters=IntentParameters(**params),
                missing_fields=data.get("missing_fields", []),
                requires_confirmation=data.get("requires_confirmation", True),
                message=data.get("message", ""),
                next_step=data.get("next_step", "question"),
            )
        except (json.JSONDecodeError, Exception) as e:
            err_msg = str(e).lower()
            if "expecting value" in err_msg or "empty" in err_msg:
                friendly = "The AI service is temporarily busy. Please wait a few seconds and try again."
            else:
                friendly = "I had trouble understanding the AI's response. Could you rephrase your request?"
            return IntentResult(
                intent="unknown",
                confidence=0.0,
                message=friendly,
                next_step="clarification_needed",
            )

    def _resolve_with_context(self, result: IntentResult, ctx) -> IntentResult:
        """Resolve contextual references like 'send it', 'yes', 'make it tomorrow'."""

        text_lower = result.message.lower() if result.message else ""
        user_text = ctx.conversation_history[-1]["content"] if ctx.conversation_history else ""
        user_lower = user_text.lower().strip()

        # Escape hatch & greetings immunity
        greetings = ("hello", "hi", "hey", "hola", "sup", "greetings")
        cancels = ("cancel", "clear", "stop", "reset", "abort", "nevermind")
        
        if user_lower in cancels:
            # Clear context
            ctx.pending_clarifications = []
            ctx.last_intent = None
            ctx.last_entities = {}
            return IntentResult(
                intent="unknown",
                confidence=1.0,
                message="Context cleared. What would you like to do next?",
                next_step="result"
            )

        if user_lower in greetings or result.intent == "unknown":
            # Don't try to merge "hello", it shouldn't auto-fill a missing parameter, unless it's explicitly a required body text (which is rare).
            pass

        # Handle affirmative responses that reference the last intent
        affirmatives = ["yes", "send it", "do it", "go ahead", "confirm", "ok", "sure", "yep", "yeah"]

        if user_lower in affirmatives and ctx.last_intent:
            # Re-use last intent and entities
            result.intent = ctx.last_intent
            result.confidence = max(result.confidence, 0.85)
            # Merge in last entities
            existing = result.parameters.model_dump(exclude_none=True)
            merged = {**ctx.last_entities, **existing}
            # Re-map datetime if needed
            if "datetime" in merged and "datetime_str" not in merged:
                merged["datetime_str"] = merged.pop("datetime")
            merged.pop("datetime", None)
            result.parameters = IntentParameters(**merged)
            result.next_step = "action_preview"
            result.message = "Proceeding with the previous request."

        # Handle "pending clarification" fill-in
        elif ctx.pending_clarifications and ctx.last_intent:
            # Only override if the user is likely answering the question.
            # If the LLM strongly detected a completely NEW intent, allow context breakout.
            is_new_command = result.intent != "unknown" and result.intent != ctx.last_intent and result.confidence >= 0.8
            
            # Don't swallow greetings as parameter answers
            if user_lower not in greetings and not is_new_command:
                # User is answering a follow-up question
                result.intent = ctx.last_intent
                # Merge new params over last entities
                new_params = result.parameters.model_dump(exclude_none=True)
                merged = {**ctx.last_entities, **new_params}
                
                # Directly assign raw user text to the first pending field
                # if the LLM didn't extract it as a named parameter
                for pending_field in ctx.pending_clarifications:
                    if pending_field not in merged or not merged[pending_field]:
                        merged[pending_field] = user_text
                
                if "datetime" in merged and "datetime_str" not in merged:
                    merged["datetime_str"] = merged.pop("datetime")
                merged.pop("datetime", None)
                result.parameters = IntentParameters(**merged)
                result.confidence = max(result.confidence, 0.8)

        return result


    def _validate_fields(self, result: IntentResult) -> IntentResult:
        """Check required fields and set missing_fields if incomplete."""
        required = REQUIRED_FIELDS.get(result.intent, [])
        params_dict = result.parameters.model_dump(exclude_none=True, by_alias=True)

        missing = []
        for field in required:
            val = params_dict.get(field)
            if not val or (isinstance(val, str) and not val.strip()):
                missing.append(field)

        result.missing_fields = missing

        if missing and result.confidence >= CONFIDENCE_THRESHOLD:
            result.next_step = "question"
            field_list = ", ".join(missing)
            result.message = f"I need a few more details. What should the {field_list} be?"
            result.requires_confirmation = True

        elif result.confidence < CONFIDENCE_THRESHOLD:
            result.next_step = "clarification_needed"
            if not result.message:
                result.message = "I'm not confident I understood correctly. Could you clarify?"

        elif not missing:
            result.next_step = "action_preview"

        return result

    def detect_multi_intent(self, user_text: str) -> bool:
        """Disabled: Heuristic multi-intent splitting causes more harm than good for conversational context."""
        return False
