from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class FeedbackEvent(BaseModel):
    type: str  # approve | edit | reject | ignore
    source: str  # email | calendar | research
    object_id: str
    delta: Dict[str, Any]  # what changed
    timestamp: datetime = Field(default_factory=datetime.now)

class FeedbackDirectives(BaseModel):
    directives: Dict[str, str]  # e.g. {"tone": "concise"}
