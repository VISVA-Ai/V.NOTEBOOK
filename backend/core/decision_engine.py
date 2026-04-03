"""
Decision Engine — Upgrade 3: The layer between parsing and action queue.
Decides: is this an action? a recommendation? ambiguous? multi-intent?
Handles conditional intents, multi-action planning, confidence gating.
"""

import uuid
from typing import List, Dict, Any, Optional
from models.assistant import (
    IntentResult, IntentParameters, ActionModel, ActionPreview, MultiActionPreview,
    Recommendation, ConfirmationLevel
)
from core.actions import ActionQueue
from core.context_manager import ContextManager
from core.email_intelligence import EmailIntelligence
from core.assistant_chat import AssistantChatParser


# Intents that require strong confirmation
DESTRUCTIVE_INTENTS = {"delete_event"}

# Intents that are analysis/read-only (no action queue needed)
READ_ONLY_INTENTS = {
    "read_email", "search_email", "summarize_thread", "suggest_follow_up",
    "suggest_reminder", "suggest_reply", "detect_action_items", "list_events",
}

# Confirmation levels by intent
CONFIRMATION_MAP = {
    "send_email": ConfirmationLevel.NORMAL,
    "draft_email": ConfirmationLevel.NORMAL,
    "send_whatsapp_message": ConfirmationLevel.NORMAL,
    "draft_whatsapp_message": ConfirmationLevel.NORMAL,
    "create_event": ConfirmationLevel.NORMAL,
    "update_event": ConfirmationLevel.NORMAL,
    "delete_event": ConfirmationLevel.STRONG,
}


class DecisionEngine:
    """
    Routes parsed intents to the correct outcome:
    - Action preview (for execution intents)
    - Recommendation cards (for analysis intents)
    - Clarification questions (for ambiguous input)
    - Multi-action plans (for compound requests)
    """

    def __init__(self, parser: AssistantChatParser,
                 action_queue: ActionQueue,
                 context_manager: ContextManager,
                 email_intelligence: EmailIntelligence,
                 executor=None):
        self.parser = parser
        self.actions = action_queue
        self.context = context_manager
        self.email_intel = email_intelligence
        self._executor = executor

    def _get_executor(self):
        """Get executor instance — lazy import if not injected."""
        if self._executor:
            return self._executor
        # Fallback: create a temporary executor
        from core.executor import Executor
        self._executor = Executor(self.actions)
        return self._executor

    def process(self, user_text: str, session_id: str,
                thread_context: str = None) -> Dict[str, Any]:
        """
        Main entry point. Takes user text, returns a structured response
        that the frontend can render directly.
        """
        # Check for multi-intent
        if self.parser.detect_multi_intent(user_text):
            return self._handle_multi_intent(user_text, session_id, thread_context)

        # Single intent parsing
        result = self.parser.parse(user_text, session_id, thread_context)

        # Route based on next_step and intent type
        if result.next_step == "clarification_needed" or result.intent == "unknown":
            return self._clarification_response(result, session_id)

        # Smart Intercept: Auto-generate subject if body is provided, and polish the email text
        if result.intent in ("send_email", "draft_email"):
            if "body" in result.missing_fields:
                # Force the engine to ask the user what they want to say
                pass
            else:
                # Body is provided! Auto-generate subject if missing
                if "subject" in result.missing_fields:
                    result.missing_fields.remove("subject")
                if "mail_subject" in result.missing_fields:
                    result.missing_fields.remove("mail_subject")
                
                if not result.missing_fields:
                    params_dict = result.parameters.model_dump(exclude_none=True, by_alias=True)
                    updated_params = self._smart_fill_email(params_dict, session_id)
                    if updated_params.get("body"):
                        result.parameters = IntentParameters(**updated_params)
                        result.next_step = "action_preview"
                        self.context.clear_clarifications(session_id)

        # Auto-route: if draft_email has thread_id, upgrade to reply_email
        if result.intent in ("draft_email", "reply_email") and result.parameters.thread_id:
            result.intent = "reply_email"
            # reply_email only needs thread_id + body; relax other requirements
            result.missing_fields = [f for f in result.missing_fields
                                     if f in ("body", "thread_id")]
            if not result.missing_fields:
                result.next_step = "action_preview"

        # Smart Reply: if reply body is brief,
        # fetch the thread and auto-generate a professional reply
        if result.intent == "reply_email" and result.parameters.thread_id and not result.missing_fields:
            body = result.parameters.body or ""
            # If body is brief, we treat it as an intent hint (like "thank them")
            if len(body.strip()) < 150:
                try:
                    smart_body = self._smart_follow_up(
                        result.parameters.thread_id, body, session_id
                    )
                    if smart_body:
                        result.parameters.body = smart_body
                except Exception as e:
                    print(f"[DecisionEngine] Smart reply failed: {e}")

        if result.next_step == "question" and result.missing_fields:
            return self._question_response(result, session_id)

        if result.intent in READ_ONLY_INTENTS:
            return self._handle_read_only(result, session_id, thread_context)

        # Execution intent with all fields → create action preview
        if result.next_step == "action_preview" and not result.missing_fields:
            return self._create_action_preview(result, session_id)

        # Fallback: question for missing info
        return self._question_response(result, session_id)

    def _handle_multi_intent(self, user_text: str, session_id: str,
                             thread_context: str = None) -> Dict[str, Any]:
        """Handle compound requests like 'email John and create a meeting'."""
        # Parse the compound request
        result = self.parser.parse(user_text, session_id, thread_context)

        # Use LLM to split into individual intents
        split_prompt = f"""The user said: "{user_text}"

This appears to contain multiple requests. Split into separate intents.
Output a JSON array of intent objects, each with: intent, parameters (extract what you can), missing_fields.
Output ONLY the JSON array."""

        from api.routes_settings import _load_preferences
        _model = _load_preferences().get('default_model', 'groq/llama-3.3-70b-versatile')
        raw = self.parser.llm.get_response(
            prompt=split_prompt,
            system_prompt="You split compound user requests into individual action intents. Output strict JSON array only.",
            model=_model,
        )

        try:
            import json, re
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
                cleaned = cleaned.rstrip("`").strip()
            intents = json.loads(cleaned)

            if not isinstance(intents, list) or len(intents) < 2:
                # Couldn't split — treat as single
                return self._create_action_preview(result, session_id)

            # Create multi-action preview
            group_id = str(uuid.uuid4())
            previews = []
            all_missing = []

            for intent_data in intents:
                intent = intent_data.get("intent", "unknown")
                params = intent_data.get("parameters", {})
                missing = intent_data.get("missing_fields", [])

                if missing:
                    all_missing.extend(missing)

                action = self.actions.create_action(
                    intent=intent,
                    parameters=params,
                    confirmation_level=CONFIRMATION_MAP.get(intent, ConfirmationLevel.NORMAL),
                    parent_group_id=group_id,
                )

                previews.append(ActionPreview(
                    action_id=action.id,
                    intent=intent,
                    parameters=params,
                    summary=self._generate_summary(intent, params),
                    confirmation_level=CONFIRMATION_MAP.get(intent, ConfirmationLevel.NORMAL),
                ).model_dump())

            if all_missing:
                return {
                    "type": "question",
                    "message": f"I identified {len(intents)} actions, but need some details: {', '.join(set(all_missing))}",
                    "missing_fields": list(set(all_missing)),
                    "group_id": group_id,
                    "data": {"partial_actions": previews},
                }

            self.context.clear_clarifications(session_id)
            
            return {
                "type": "multi_action_preview",
                "group_id": group_id,
                "actions": previews,
                "summary": f"{len(previews)} actions ready for approval",
                "requires_confirmation": True,
                "can_approve_all": True,
                "can_approve_individually": True,
                "message": f"I've prepared {len(previews)} actions. Review and approve when ready.",
            }

        except Exception:
            # Fallback to single intent handling
            return self._create_action_preview(result, session_id)

    def _handle_read_only(self, result: IntentResult, session_id: str,
                          thread_context: str = None) -> Dict[str, Any]:
        """Handle analysis/read-only intents — execute directly or return recommendations."""
        intent = result.intent
        params = result.parameters.model_dump(exclude_none=True)

        # For email analysis intents, use email intelligence
        if intent in ("suggest_follow_up", "suggest_reminder", "suggest_reply",
                       "detect_action_items", "summarize_thread"):
            email_text = thread_context or params.get("body", "")

            if not email_text:
                return {
                    "type": "question",
                    "message": "I need the email text or thread to analyze. Can you paste it or specify which thread?",
                    "missing_fields": ["email_text"],
                }

            cognition = self.email_intel.analyze(email_text, thread_context)

            recommendations = []
            if cognition.follow_up.needs_follow_up:
                recommendations.append({
                    "kind": "follow_up",
                    "reason": cognition.follow_up.reason or "Follow-up may be needed",
                    "suggested_delay": cognition.follow_up.suggested_delay,
                    "confidence": cognition.follow_up.confidence,
                })

            for r in cognition.recommendations:
                recommendations.append(r.model_dump())

            return {
                "type": "recommendation",
                "message": "Here's my analysis of this email:",
                "recommendations": recommendations,
                "data": {
                    "action_items": [a.model_dump() for a in cognition.action_items],
                    "follow_up": cognition.follow_up.model_dump(),
                    "reply_classification": cognition.reply_classification.model_dump() if cognition.reply_classification else None,
                    "deadlines": cognition.deadlines,
                },
                "requires_confirmation": True,
            }

        # ── Auto-execute read_email / search_email / list_events ──
        # These are safe read-only operations that don't need approval
        from core.executor import Executor

        try:
            executor = self._get_executor()

            if intent == "read_email":
                time_query = params.get("time_frame", "newer_than:1d")
                # Smart filtering: exclude ads and social noise by default
                if "-category" not in time_query:
                    time_query = f"{time_query} -category:promotions -category:social".strip()
                data = executor.gmail.read_emails(query=time_query)
                messages = data.get("messages", [])
                if not messages:
                    return {
                        "type": "result",
                        "status": "success",
                        "message": "Your inbox is empty — no new emails found.",
                        "data": data,
                    }
                return {
                    "type": "result",
                    "status": "success",
                    "message": f"📧 Found {len(messages)} email(s):",
                    "data": {"emails": messages, "count": len(messages)},
                }

            if intent == "search_email":
                query = params.get("query", "")
                time_query = params.get("time_frame", "")
                if time_query and time_query not in query:
                    query = f"{query} {time_query}".strip()
                data = executor.gmail.search_emails(query=query)
                messages = data.get("messages", [])
                # GAP 4: Relevance ranking
                messages = executor.gmail._rank_results(query, messages)
                return {
                    "type": "result",
                    "status": "success",
                    "message": f"🔍 Search for \"{query}\" — {len(messages)} result(s):",
                    "data": {"emails": messages, "count": len(messages)},
                }

            if intent == "list_events":
                data = executor.calendar.list_events()
                events = data.get("events", [])
                if not events:
                    return {
                        "type": "result",
                        "status": "success",
                        "message": "📅 No upcoming events found.",
                        "data": data,
                    }
                return {
                    "type": "result",
                    "status": "success",
                    "message": f"📅 {len(events)} upcoming event(s):",
                    "data": {"events": events, "count": len(events)},
                }

        except Exception as e:
            error_msg = str(e)
            # Graceful fallback for unconfigured providers
            if "not configured" in error_msg.lower():
                return {
                    "type": "error",
                    "message": f"Provider not configured: {error_msg}",
                    "error": error_msg,
                }
            return {
                "type": "error",
                "message": f"Failed to execute: {error_msg}",
                "error": error_msg,
            }

        # Fallback
        return {
            "type": "result",
            "status": "success",
            "intent": intent,
            "message": f"Ready to {intent.replace('_', ' ')}.",
            "data": {"intent": intent, "parameters": params},
        }


    def _create_action_preview(self, result: IntentResult,
                               session_id: str) -> Dict[str, Any]:
        """Create an action in the queue and return a preview for approval."""
        params = result.parameters.model_dump(exclude_none=True, by_alias=True)
        conf_level = CONFIRMATION_MAP.get(result.intent, ConfirmationLevel.NORMAL)

        # ── Smart Draft: already handled in process() intercept ──

        action = self.actions.create_action(
            intent=result.intent,
            parameters=params,
            confirmation_level=conf_level,
        )

        # Track pending action in context
        self.context.set_pending_action(session_id, action.id)
        self.context.clear_clarifications(session_id)

        # Generate email-specific recommendations if applicable
        recommendations = []
        if result.intent in ("send_email", "draft_email") and params.get("body"):
            try:
                cognition = self.email_intel.analyze(params.get("body", ""))
                for r in cognition.recommendations:
                    recommendations.append(r.model_dump())
            except Exception:
                pass

        summary = self._generate_summary(result.intent, params)

        return {
            "type": "action_preview",
            "action_id": action.id,
            "intent": result.intent,
            "parameters": params,
            "summary": summary,
            "requires_confirmation": True,
            "confirmation_level": conf_level,
            "can_edit": True,
            "can_cancel": True,
            "recommendations": recommendations,
            "message": f"Action ready for review: {summary}",
        }

    def _smart_fill_email(self, params: dict, session_id: str) -> dict:
        """Use LLM to generate professional email content when user gives a topic."""
        body_text = params.get("body", "")
        subject_text = params.get("subject", "")
        
        is_detailed_body = len(body_text.strip()) > 100
        has_subject = len(subject_text.strip()) > 3

        # If body is already detailed, don't override
        if is_detailed_body and has_subject:
            return params

        # Build a prompt from what we have
        topic_hints = []
        if subject_text:
            topic_hints.append(f"Subject/Topic: {subject_text}")
        if body_text:
            topic_hints.append(f"Notes/Context: {body_text}")
        if params.get("to"):
            topic_hints.append(f"Recipient: {params['to']}")
        if params.get("contact_name"):
            topic_hints.append(f"Recipient Name: {params['contact_name']}")

        if not topic_hints:
            return params

        prompt = f"""You are an expert executive assistant. Generate a fully written, professional email based on the notes below.

User Notes/Context:
{chr(10).join(topic_hints)}

Generate ONLY a JSON object with these fields:
{{
  "subject": "a clear, engaging subject line",
  "body": "the COMPLETE email body, fully fleshed out with a professional tone, greeting, and sign-off. Expand significantly on the user's notes."
}}

CRITICAL RULES:
1. DO NOT just echo the user's notes. You MUST write a full, comprehensive email expanding on their topics.
2. If the user asks for a specific length or format, oblige them.
3. Use the recipient's name if available.
4. DO NOT use phrases like 'as we discussed previously', 'follow up', 'following up on our previous conversation'. Write as if this is a BRAND NEW email.
5. Output ONLY the raw JSON object, no markdown blocks, no thinking text."""

        try:
            from api.routes_settings import _load_preferences
            _model = _load_preferences().get('default_model', 'groq/llama-3.3-70b-versatile')
            raw = self.parser.llm.get_response(
                prompt=prompt,
                system_prompt="You are a professional email writer. Output strict JSON only.",
                model=_model,
            )

            import json, re
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
                cleaned = cleaned.rstrip("`").strip()

            # Check if LLM returned an error string
            if cleaned.startswith("Error calling"):
                raise ValueError(cleaned)

            generated = json.loads(cleaned)

            if not has_subject and generated.get("subject"):
                params["subject"] = generated["subject"]
            
            # We always write back the generated body if our initial body wasn't fully detailed
            if generated.get("body"):
                params["body"] = generated["body"]

        except Exception as e:
            print(f"[DecisionEngine] Smart draft failed: {e}, using fallback")
            # Fallback: construct a basic draft from what we know
            topic = subject_text if subject_text else "your request"
            recipient = params.get("contact_name") or params.get("to", "")
            greeting = f"Dear {recipient},\n\n" if recipient else "Hello,\n\n"
            
            if not has_subject:
                params["subject"] = topic.title() if topic else "Follow Up"
            if not is_detailed_body:
                params["body"] = (
                    f"{greeting}"
                    f"I am writing to you regarding {topic}. "
                    f"I would like to discuss this matter further and share some insights.\n\n"
                    f"Please let me know your thoughts or if you need any additional information.\n\n"
                    f"Best regards"
                )

        return params

    def _smart_follow_up(self, thread_id: str, user_hint: str,
                         session_id: str) -> str:
        """Fetch the original thread and generate an intelligent reply body."""
        executor = self._get_executor()

        # Fetch thread context from Gmail
        thread_data = executor.gmail.get_thread(thread_id)
        messages = thread_data.get("messages", [])
        if not messages:
            return None

        last_msg = messages[-1]
        orig_from = last_msg.get("from", "")
        orig_subject = last_msg.get("subject", "")
        orig_body = last_msg.get("body", "") or last_msg.get("snippet", "")

        # Build a rich context string for the LLM
        thread_summary = "\n".join([
            f"--- Message {i+1} ---\nFrom: {m.get('from', '')}\nDate: {m.get('date', '')}\n{m.get('body', m.get('snippet', ''))[:500]}"
            for i, m in enumerate(messages[-3:])  # Last 3 messages max
        ])

        prompt = f"""You are a professional email assistant. Generate a polite, context-aware email reply based on the user's intent.

ORIGINAL THREAD CONTEXT:
Subject: {orig_subject}
Last sender: {orig_from}

Recent thread messages:
{thread_summary}

USER'S REPLY INTENT / NOTES: "{user_hint}"

RULES:
1. Be polite and professional. Your reply MUST directly address the original thread AND fulfill the user's intent.
2. Do NOT repeat the entire original email. Just reference it naturally.
3. Keep it concise but fully fleshed out (3-6 sentences max).
4. Add a professional greeting and sign-off.
5. Output ONLY the email body text, no JSON, no markdown.
"""

        from api.routes_settings import _load_preferences
        _model = _load_preferences().get('default_model', 'groq/llama-3.3-70b-versatile')
        raw = self.parser.llm.get_response(
            prompt=prompt,
            system_prompt="You write concise, professional email replies. Output the email body only.",
            model=_model,
        )

        body = raw.strip()
        # Strip any accidental markdown wrapping
        if body.startswith("```"):
            import re
            body = re.sub(r"```(?:\w+)?\s*", "", body).rstrip("`").strip()

        return body if len(body) > 20 else None

    def _question_response(self, result: IntentResult,
                           session_id: str) -> Dict[str, Any]:
        """Return a follow-up question for missing fields."""
        # Track what we're waiting for
        for field in result.missing_fields:
            self.context.add_pending_clarification(session_id, field)

        return {
            "type": "question",
            "message": result.message,
            "missing_fields": result.missing_fields,
            "intent": result.intent,
            "data": {
                "partial_parameters": result.parameters.model_dump(exclude_none=True),
            },
        }

    def _clarification_response(self, result: IntentResult,
                                session_id: str) -> Dict[str, Any]:
        """Return a clarification request for ambiguous input."""
        return {
            "type": "question",
            "message": result.message or "I'm not sure I understood. Could you provide more details?",
            "missing_fields": [],
            "intent": "unknown",
        }

    def _generate_summary(self, intent: str, params: dict) -> str:
        """Generate a human-readable summary of an action."""
        summaries = {
            "send_email": lambda p: f"Send email to {p.get('to', '?')} — \"{p.get('subject', 'No subject')}\"",
            "draft_email": lambda p: f"Draft email to {p.get('to', '?')} — \"{p.get('subject', 'No subject')}\"",
            "create_event": lambda p: f"Create event \"{p.get('title', '?')}\" at {p.get('datetime', p.get('datetime_str', '?'))}",
            "update_event": lambda p: f"Update event {p.get('event_id', '?')}",
            "delete_event": lambda p: f"Delete event {p.get('event_id', '?')}",
            "send_whatsapp_message": lambda p: f"Send WhatsApp to {p.get('to', '?')}: \"{p.get('message', '?')[:50]}\"",
            "draft_whatsapp_message": lambda p: f"Draft WhatsApp to {p.get('to', '?')}",
        }

        fn = summaries.get(intent)
        if fn:
            try:
                return fn(params)
            except Exception:
                pass
        return f"{intent.replace('_', ' ').title()}"
