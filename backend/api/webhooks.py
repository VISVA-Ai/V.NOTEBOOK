"""
Webhooks — Incoming message receivers for Gmail, WhatsApp, etc.
Routes external events into the V.ASSISTANT action system.
"""

from fastapi import APIRouter, Request
from typing import Dict, Any

router = APIRouter()


def _get_engine(request: Request):
    return request.app.state.engine


@router.post("/email")
async def receive_email(request: Request, payload: Dict[str, Any]):
    """
    Receives email payload from external triggers (Gmail push, IMAP watcher).
    Payload: { email_id, from, subject, body, received_at }
    """
    engine = _get_engine(request)

    # Use email intelligence to analyze
    email_text = payload.get("body", "")
    thread_context = payload.get("thread_context")

    analysis = engine.email_intelligence.analyze(email_text, thread_context)

    return {
        "status": "received",
        "action_items": [a.model_dump() for a in analysis.action_items],
        "follow_up": analysis.follow_up.model_dump(),
        "recommendations": [r.model_dump() for r in analysis.recommendations],
    }


@router.post("/whatsapp")
async def receive_whatsapp(request: Request, payload: Dict[str, Any]):
    """
    Receives incoming WhatsApp message webhook.
    Payload: { from, message, timestamp, message_id }
    """
    print(f"WhatsApp message received: {payload}")
    return {"status": "acknowledged"}


@router.post("/status")
async def receive_status(request: Request, payload: Dict[str, Any]):
    """
    Receives completion status from external actions.
    Payload: { action, action_id, success, details }
    """
    engine = _get_engine(request)

    action_id = payload.get("action_id")
    if action_id:
        engine.action_queue.append_audit_log(
            action_id, "external_status",
            details=payload
        )

    return {"status": "acknowledged"}
