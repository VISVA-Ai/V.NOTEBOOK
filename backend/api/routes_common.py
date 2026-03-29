from fastapi import APIRouter, HTTPException, Depends
from models import HealthCheck, Session, SessionCreate
from core.session import SessionManager
from typing import List

router = APIRouter()
session_manager = SessionManager()

@router.get("/health", response_model=HealthCheck)
async def health_check():
    return {"status": "ok", "version": "4.0.0"}

@router.get("/sessions", response_model=List[Session])
async def list_sessions():
    sessions = session_manager.list_sessions()
    full_sessions = []
    for s in sessions:
        # Check for key compatibility
        sid = s.get("session_id", s.get("id"))
        created = s.get("created_at", s.get("timestamp"))
        
        full_sessions.append({
            "session_id": sid,
            "title": s.get("title", "Untitled"),
            "created_at": created,
            "messages": [] # Omit messages in list view
        })
    return full_sessions

@router.post("/sessions", response_model=Session)
async def create_session(session: SessionCreate):
    # Pass title directly
    title = session.title if session.title else "New Research"
    session_id = session_manager.create_session(title=title)
    
    # Return the new session
    s_data = session_manager.get_session(session_id)
    return {
        "session_id": session_id,
        "title": s_data["title"],
        "created_at": s_data["created_at"],
        "messages": []
    }

@router.get("/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    s_data = session_manager.get_session(session_id)
    if not s_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "title": s_data["title"],
        "created_at": s_data.get("created_at", s_data.get("timestamp")),
        "messages": s_data.get("messages", [])
    }

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    session_manager.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}

@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, title: str):
    session_manager.update_session_title(session_id, title)
    return {"status": "updated", "session_id": session_id, "title": title}
