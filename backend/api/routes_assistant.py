"""
V.ASSISTANT API Routes — Phase 10
Full API surface for the controlled execution system.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional, Dict, Any
from models.assistant import (
    ChatRequest, ChatResponse, ActionPatchRequest,
    DashboardSummary, ActionStatus
)

router = APIRouter()


def _get_engine(request: Request):
    return request.app.state.engine


# ── Chat (main entry point) ──────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(request: Request, body: ChatRequest):
    """
    Main assistant endpoint. Processes user text through:
    Parser → Decision Engine → Action Preview / Question / Recommendation
    """
    engine = _get_engine(request)

    try:
        session_id = body.session_id or "default"
        result = engine.assistant_process(
            user_text=body.message,
            session_id=session_id,
            thread_context=body.thread_context,
        )

        return ChatResponse(
            type=result.get("type", "error"),
            status=result.get("status"),
            message=result.get("message", ""),
            action_id=result.get("action_id"),
            group_id=result.get("group_id"),
            data=result.get("data"),
            error=result.get("error"),
            question=result if result.get("type") == "question" else None,
            recommendations=result.get("recommendations"),
            action_preview=result if result.get("type") == "action_preview" else None,
            multi_action_preview=result if result.get("type") == "multi_action_preview" else None,
        )
    except Exception as e:
        return ChatResponse(
            type="error",
            message=f"Assistant error: {str(e)}",
            error=str(e),
        )


# ── Session Reset ─────────────────────────────────────────────────

@router.post("/reset")
async def reset_session(request: Request, session_id: str = "assistant-default"):
    """Reset assistant session context for a fresh start."""
    engine = _get_engine(request)
    engine.context.update_context(
        session_id,
        conversation_history=[],
        pending_clarifications=[],
        last_intent=None,
        last_entities={},
        pending_action_id=None,
        active_thread_id=None,
    )
    return {"status": "ok", "message": "Session reset"}


# ── Actions CRUD ──────────────────────────────────────────────────

@router.get("/actions")
async def list_actions(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=100),
):
    """List all actions, optionally filtered by status."""
    engine = _get_engine(request)
    actions = engine.action_queue.get_actions(status=status, limit=limit)
    return [a.model_dump() for a in actions]


@router.get("/actions/{action_id}")
async def get_action(request: Request, action_id: str):
    """Get a single action by ID."""
    engine = _get_engine(request)
    action = engine.action_queue.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action.model_dump()


@router.post("/actions/{action_id}/approve")
async def approve_action(request: Request, action_id: str):
    """Approve a pending action."""
    engine = _get_engine(request)
    try:
        action = engine.action_queue.update_status(
            action_id, ActionStatus.APPROVED
        )
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        return {
            "status": "approved",
            "action_id": action_id,
            "message": f"Action approved. Ready to execute.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/actions/{action_id}/execute")
async def execute_action(request: Request, action_id: str):
    """Execute an approved action."""
    engine = _get_engine(request)

    # Validate action exists and is approved
    action = engine.action_queue.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != ActionStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail=f"Action must be approved before execution. Current status: {action.status}"
        )

    result = engine.executor.execute(action_id)
    return result.model_dump()


@router.post("/actions/{action_id}/cancel")
async def cancel_action(request: Request, action_id: str):
    """Cancel a pending or approved action."""
    engine = _get_engine(request)
    try:
        action = engine.action_queue.cancel_action(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        return {
            "status": "canceled",
            "action_id": action_id,
            "message": "Action canceled.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/actions/{action_id}")
async def edit_action(request: Request, action_id: str, body: ActionPatchRequest):
    """Edit action parameters before approval."""
    engine = _get_engine(request)

    action = engine.action_queue.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status not in (ActionStatus.PENDING, "pending"):
        raise HTTPException(
            status_code=400,
            detail="Can only edit pending actions."
        )

    patch = {}
    if body.parameters:
        # Merge new params into existing
        merged = {**action.parameters, **body.parameters}
        patch["parameters"] = merged

    updated = engine.action_queue.update_action(action_id, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Update failed")

    return {
        "status": "updated",
        "action_id": action_id,
        "parameters": updated.parameters,
        "message": "Action updated. Review and approve when ready.",
    }


# ── Dashboard ─────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard(request: Request):
    """Get assistant dashboard stats."""
    engine = _get_engine(request)
    stats = engine.action_queue.get_stats()

    recent = engine.action_queue.get_actions(limit=5)
    recent_list = [
        {
            "id": a.id,
            "intent": a.intent,
            "status": a.status,
            "created_at": a.created_at,
            "summary": a.parameters.get("subject", a.parameters.get("title", a.intent)),
        }
        for a in recent
    ]

    return {
        "actions_pending": stats.get("pending", 0),
        "actions_today": stats.get("today", 0),
        "emails_pending": 0,
        "recommendations_active": 0,
        "recent_actions": recent_list,
    }


# ── Provider Status ───────────────────────────────────────────────

@router.get("/status")
async def provider_status(request: Request):
    """Check which providers are configured."""
    engine = _get_engine(request)
    return {
        "gmail": engine.executor.gmail.is_configured(),
        "calendar": engine.executor.calendar.is_configured(),
        "whatsapp": engine.executor.whatsapp.is_configured(),
    }
