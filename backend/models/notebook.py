from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    mode: str = "Fast Mode"  # "Fast Mode" | "Grounded Mode" | "Deep Research"
    session_id: Optional[str] = None
    context_files: List[str] = []
    intent: str = "Explore"
    do_not_learn: bool = False

class QueryResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    mode: str
    exec_time: float
    goals_context: List[Any] = [] # For debugging/transparency
    directives_used: Dict[str, str] = {} # For debugging/transparency

class SessionCreate(BaseModel):
    title: str = "New Research Session"

class Session(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    messages: List[Dict[str, Any]]
