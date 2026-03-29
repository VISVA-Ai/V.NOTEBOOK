from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field

class Goal(BaseModel):
    goal_id: str
    session_id: str = "default"
    title: str
    description: str
    status: str  # active | paused | completed
    confidence: float
    source: str  # user_declared | inferred
    last_touched: datetime
    touch_count: int

class GoalCreate(BaseModel):
    session_id: str = "default"
    title: str
    description: str
    source: str = "user_declared"

class GoalUpdate(BaseModel):
    status: Optional[str]
    description: Optional[str]
