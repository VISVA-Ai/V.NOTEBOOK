"""
Email Intelligence — Upgrade 2: Gmail Cognition
Deep analysis of email content: action item extraction, follow-up detection,
reply classification, deadline extraction, intent shift detection.
"""

import json
import re
from typing import Optional, List, Dict, Any
from models.assistant import (
    ExtractedActionItem, FollowUpDetection, ReplyClassification,
    EmailCognitionResult, Recommendation
)


EMAIL_COGNITION_PROMPT = """You are an email intelligence system. Analyze the provided email text and conversation context.

OUTPUT FORMAT (strict JSON, no markdown):
{
  "action_items": [
    {
      "action": "description of the task",
      "deadline": "extracted deadline or null",
      "owner": "who should do it, 'user' or person name",
      "confidence": 0.0 to 1.0
    }
  ],
  "follow_up": {
    "needs_follow_up": true/false,
    "reason": "why follow-up is needed",
    "suggested_delay": "e.g. '2 days', 'tomorrow', '1 week'",
    "confidence": 0.0 to 1.0
  },
  "reply_classification": {
    "reply_type": "confirmation | clarification | negotiation | scheduling | informational | action_request",
    "urgency": "low | normal | high | urgent",
    "sentiment": "positive | neutral | negative",
    "suggested_reply": "brief suggested reply text or null"
  },
  "deadlines": [
    {
      "text": "original text mentioning deadline",
      "parsed": "ISO date or natural description",
      "confidence": 0.0 to 1.0
    }
  ],
  "is_reply_vs_new": "reply | new | forward",
  "recommendations": [
    {
      "kind": "follow_up | reminder | reply | calendar_event | action_item",
      "reason": "why this is recommended",
      "suggested_delay": "time suggestion or null",
      "confidence": 0.0 to 1.0
    }
  ]
}

RULES:
- Extract action items ONLY if explicitly or strongly implied in the text.
- For deadlines, only extract clearly stated times. "ASAP" → urgency high, but no specific deadline.
- For follow-up detection: check for unanswered questions, pending requests, stalled conversations.
- For reply classification: determine the nature of the expected response.
- Recommendations: proactively suggest follow-ups, reminders, calendar events, or reply actions.
- Never fabricate deadlines or commitments not present in the text.
- Output ONLY the JSON object."""


class EmailIntelligence:
    """Advanced email analysis and recommendation engine."""

    def __init__(self, llm_handler):
        self.llm = llm_handler

    def analyze(self, email_text: str,
                thread_context: str = None) -> EmailCognitionResult:
        """Full cognition analysis of an email or thread."""
        prompt = self._build_prompt(email_text, thread_context)

        raw = self.llm.get_response(
            prompt=prompt,
            system_prompt=EMAIL_COGNITION_PROMPT,
            model="llama-3.3-70b-versatile",
        )

        return self._parse_result(raw)

    def extract_action_items(self, email_text: str) -> List[ExtractedActionItem]:
        """Extract just action items from email text."""
        result = self.analyze(email_text)
        return result.action_items

    def detect_follow_up(self, email_text: str,
                         thread_context: str = None) -> FollowUpDetection:
        """Detect if the email needs a follow-up."""
        result = self.analyze(email_text, thread_context)
        return result.follow_up

    def classify_reply(self, email_text: str) -> ReplyClassification:
        """Classify the type of reply needed for an email."""
        result = self.analyze(email_text)
        return result.reply_classification or ReplyClassification()

    def suggest_reply(self, email_text: str,
                      thread_context: str = None) -> str:
        """Generate a suggested reply for an email."""
        prompt = f"""Based on this email, draft a concise, professional reply.

EMAIL:
{email_text[:3000]}

{f'THREAD CONTEXT: {thread_context[:2000]}' if thread_context else ''}

Output ONLY the reply text, nothing else."""

        return self.llm.get_response(
            prompt=prompt,
            system_prompt="You are a professional email writing assistant. Write concise, well-structured replies.",
            model="llama-3.3-70b-versatile",
        )

    def suggest_follow_up(self, email_text: str,
                          thread_context: str = None) -> Dict[str, Any]:
        """Generate follow-up recommendation."""
        result = self.analyze(email_text, thread_context)
        if result.follow_up.needs_follow_up:
            return {
                "needs_follow_up": True,
                "reason": result.follow_up.reason,
                "suggested_delay": result.follow_up.suggested_delay,
                "confidence": result.follow_up.confidence,
                "recommendations": [r.model_dump() for r in result.recommendations],
            }
        return {"needs_follow_up": False, "recommendations": []}

    def suggest_reminder(self, email_text: str) -> Dict[str, Any]:
        """Generate reminder recommendation from email content."""
        result = self.analyze(email_text)
        reminders = [r for r in result.recommendations if r.kind == "reminder"]
        deadlines = result.deadlines

        return {
            "reminders": [r.model_dump() for r in reminders],
            "deadlines": deadlines,
            "action_items": [a.model_dump() for a in result.action_items],
        }

    def detect_intent_shift(self, user_text: str,
                            has_existing_thread: bool) -> Dict[str, Any]:
        """Detect if user wants to reply to existing thread vs new email."""
        if has_existing_thread:
            # Check if user explicitly says "new email" or "compose"
            new_indicators = ["new email", "compose", "fresh", "new message"]
            if any(ind in user_text.lower() for ind in new_indicators):
                return {"suggestion": None, "is_new": True}
            return {
                "suggestion": "It looks like there's an existing thread. Do you want to reply to it instead of sending a new email?",
                "is_new": False,
            }
        return {"suggestion": None, "is_new": True}

    def summarize_thread(self, thread_messages: List[Dict]) -> str:
        """Summarize an email thread."""
        thread_text = "\n\n---\n\n".join([
            f"From: {m.get('from', 'Unknown')}\n"
            f"Date: {m.get('date', 'Unknown')}\n"
            f"{m.get('body', m.get('snippet', ''))}"
            for m in thread_messages
        ])

        return self.llm.get_response(
            prompt=f"Summarize this email thread concisely:\n\n{thread_text[:4000]}",
            system_prompt="You are an email summarization assistant. Provide a concise, structured summary with key points, decisions made, and outstanding items.",
            model="llama-3.3-70b-versatile",
        )

    # ── Internal ──────────────────────────────────────────────────

    def _build_prompt(self, email_text: str,
                      thread_context: str = None) -> str:
        parts = [f"EMAIL TEXT:\n{email_text[:3000]}"]
        if thread_context:
            parts.append(f"\nTHREAD CONTEXT:\n{thread_context[:2000]}")
        parts.append("\nAnalyze this email and provide the structured analysis.")
        return "\n".join(parts)

    def _parse_result(self, raw: str) -> EmailCognitionResult:
        """Parse LLM JSON output into EmailCognitionResult."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
                cleaned = cleaned.rstrip("`").strip()

            data = json.loads(cleaned)

            action_items = [
                ExtractedActionItem(**item)
                for item in data.get("action_items", [])
            ]

            follow_up = FollowUpDetection(**data.get("follow_up", {}))

            reply_class = None
            if data.get("reply_classification"):
                reply_class = ReplyClassification(**data["reply_classification"])

            recommendations = [
                Recommendation(**r) for r in data.get("recommendations", [])
            ]

            return EmailCognitionResult(
                action_items=action_items,
                follow_up=follow_up,
                reply_classification=reply_class,
                deadlines=data.get("deadlines", []),
                is_reply_vs_new=data.get("is_reply_vs_new"),
                recommendations=recommendations,
            )
        except (json.JSONDecodeError, Exception):
            return EmailCognitionResult()
