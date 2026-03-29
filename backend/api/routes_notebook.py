from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
from models.notebook import QueryRequest, QueryResponse
from models.goals import Goal, GoalCreate
import shutil
import os

from core.session import SessionManager
from datetime import datetime

router = APIRouter()
session_manager = SessionManager()

def get_engine(request: Request):
    return request.app.state.engine

@router.post("/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest):
    engine = get_engine(request)
    
    # 1. Retrieve Chat History
    history = []
    if body.session_id:
        session_data = session_manager.get_session(body.session_id)
        if session_data:
            history = session_data.get("messages", [])

    # 2. Add User Message to History (Temporary for context, saved later)
    # Actually, we pass the *past* history to the engine, and the engine/route appends the new turn.
    
    # 3. Execution
    start_time = datetime.now()
    response, sources = engine.query(
        user_query=body.query,
        mode=body.mode,
        session_id=body.session_id,
        chat_history=history, # Pass full history
        intent=body.intent,
        do_not_learn=body.do_not_learn
    )
    exec_time = (datetime.now() - start_time).total_seconds()
    
    # 4. Save to Session
    if body.session_id:
        # Save User Msg
        session_manager.add_message(body.session_id, "user", body.query)
        
        # Auto-title session if it's new
        try:
            current_session = session_manager.get_session(body.session_id)
            if current_session and current_session.get("title") == "New Research":
                new_title = " ".join(body.query.split()[:5]) + "..."
                session_manager.update_session_title(body.session_id, new_title)
        except Exception as e:
            print(f"Auto-title failed: {e}")

        # Save AI Msg
        # Construct metadata with sources
        metadata = {"sources": sources, "mode": body.mode}
        session_manager.add_message(body.session_id, "assistant", response, metadata)
    
    return {
        "response": response,
        "sources": [{"source": s} for s in sources] if sources else [],
        "mode": body.mode,
        "exec_time": exec_time
    }

@router.post("/upload")
async def upload_document(request: Request, file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
    engine = get_engine(request)
    
    # Save temp file
    temp_path = f"data/temp_{file.filename}"
    if not os.path.exists("data"):
         os.makedirs("data")
         
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Ingest
    with open(temp_path, "rb") as f:
        # We need a file-like object with name attribute
        result = engine.ingest_file(f, session_id=session_id)
        
    os.remove(temp_path)
    if "Failed" in result:
        raise HTTPException(status_code=400, detail=result)
    return {"message": result}

@router.get("/sources")
async def get_sources(request: Request):
    engine = get_engine(request)
    stats = engine.get_memory_stats()
    # Frontend expects { sources: [...] } or [...]
    # stats is { "total_chunks": N, "sources": { "filename": count } }
    
    source_list = []
    for src, count in stats.get("sources", {}).items():
        source_list.append({
            "source": src,
            "chunk_count": count
        })
        
    return {"sources": source_list}

@router.delete("/sources/{source_id:path}")
async def delete_source(request: Request, source_id: str):
    engine = get_engine(request)
    chunks_removed = engine.delete_source(source_id)
    if chunks_removed == 0:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found in memory.")
    return {"message": f"Successfully deleted '{source_id}' ({chunks_removed} chunks removed)."}

@router.get("/graph")
async def get_graph(request: Request):
    engine = get_engine(request)
    return engine.get_graph()

# --- COGNITIVE ENDPOINTS ---

@router.get("/goals", response_model=List[Goal])
async def get_goals(request: Request, status: Optional[str] = None, session_id: Optional[str] = None):
    engine = get_engine(request)
    return engine.goals.get_goals(status, session_id)

@router.post("/goals", response_model=Goal)
async def create_goal(request: Request, body: GoalCreate):
    engine = get_engine(request)
    return engine.goals.add_goal(body)

@router.post("/flashcards")
async def generate_flashcards(request: Request, session_id: str):
    engine = get_engine(request)
    return engine.generate_flashcards(session_id)

@router.post("/audio/overview")
async def generate_audio_overview(request: Request):
    engine = get_engine(request)
    audio_stream, script = engine.generate_overview()
    
    if not audio_stream:
        raise HTTPException(status_code=400, detail=script)
        
    import base64
    audio_bytes = audio_stream.read()
    b64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    
    return {"audio": f"data:audio/mpeg;base64,{b64_audio}", "transcript": script}
