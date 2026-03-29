"""
V.ASSISTANT Pydantic Models — Schema layer for the controlled execution system.
Covers: intent parsing, action queue, recommendations, decision engine, API contracts.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid


# ── Enums ──────────────────────────────────────────────────────────

class Intent(str, Enum):
    SEND_EMAIL = "send_email"
    READ_EMAIL = "read_email"
    SEARCH_EMAIL = "search_email"
    DRAFT_EMAIL = "draft_email"
    REPLY_EMAIL = "reply_email"
    SUMMARIZE_THREAD = "summarize_thread"
    SUGGEST_FOLLOW_UP = "suggest_follow_up"
    SUGGEST_REMINDER = "suggest_reminder"
    SUGGEST_REPLY = "suggest_reply"
    DETECT_ACTION_ITEMS = "detect_action_items"
    CREATE_EVENT = "create_event"
    UPDATE_EVENT = "update_event"
    DELETE_EVENT = "delete_event"
    LIST_EVENTS = "list_events"
    SEND_WHATSAPP = "send_whatsapp_message"
    DRAFT_WHATSAPP = "draft_whatsapp_message"
    UNKNOWN = "unknown"


class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELED = "canceled"


class ResponseType(str, Enum):
    QUESTION = "question"
    RECOMMENDATION = "recommendation"
    ACTION_PREVIEW = "action_preview"
    MULTI_ACTION_PREVIEW = "multi_action_preview"
    RESULT = "result"
    ERROR = "error"


class NextStep(str, Enum):
    QUESTION = "question"
    ACTION_PREVIEW = "action_preview"
    RESULT = "result"
    CLARIFICATION_NEEDED = "clarification_needed"
    RECOMMENDATION = "recommendation"
    MULTI_ACTION = "multi_action"


class ConfirmationLevel(str, Enum):
    NORMAL = "normal"
    STRONG = "strong"
    DOUBLE = "double"


class RecommendationKind(str, Enum):
    FOLLOW_UP = "follow_up"
    REMINDER = "reminder"
    REPLY = "reply"
    CALENDAR_EVENT = "calendar_event"
    ACTION_ITEM = "action_item"


# ── Intent Parser Output ──────────────────────────────────────────

class IntentParameters(BaseModel):
    to: Optional[str] = None
    contact_name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    query: Optional[str] = None
    time_frame: Optional[str] = None
    thread_id: Optional[str] = None
    datetime_str: Optional[str] = Field(None, alias="datetime")
    end_datetime: Optional[str] = None
    title: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    timezone: Optional[str] = None
    channel: Optional[str] = None
    message: Optional[str] = None
    priority: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)
    follow_up_suggestion: Optional[str] = None
    reminder_suggestion: Optional[str] = None
    reply_suggestion: Optional[str] = None
    action_items: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    event_id: Optional[str] = None
    patch: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class IntentResult(BaseModel):
    intent: str
    confidence: float = 0.0
    parameters: IntentParameters = Field(default_factory=IntentParameters)
    missing_fields: List[str] = Field(default_factory=list)
    requires_confirmation: bool = True
    message: str = ""
    next_step: str = "question"


# ── Recommendation ────────────────────────────────────────────────

class Recommendation(BaseModel):
    kind: str
    reason: str
    suggested_delay: Optional[str] = None
    suggested_action: Optional[Dict[str, Any]] = None
    confidence: float = 0.0


class RecommendationPayload(BaseModel):
    type: str = "recommendation"
    recommendations: List[Recommendation] = Field(default_factory=list)
    requires_confirmation: bool = True
    message: Optional[str] = None


# ── Action Queue ──────────────────────────────────────────────────

class AuditEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    event: str
    details: Optional[Dict[str, Any]] = None


class ActionModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = ActionStatus.PENDING
    confirmation_level: str = ConfirmationLevel.NORMAL
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    audit_log: List[AuditEntry] = Field(default_factory=list)
    parent_group_id: Optional[str] = None  # For multi-action plans


class ActionPreview(BaseModel):
    type: str = "action_preview"
    action_id: str
    intent: str
    parameters: Dict[str, Any]
    summary: str
    requires_confirmation: bool = True
    confirmation_level: str = ConfirmationLevel.NORMAL
    can_edit: bool = True
    can_cancel: bool = True
    recommendations: List[Recommendation] = Field(default_factory=list)


class MultiActionPreview(BaseModel):
    type: str = "multi_action_preview"
    group_id: str
    actions: List[ActionPreview]
    summary: str
    requires_confirmation: bool = True
    can_approve_all: bool = True
    can_approve_individually: bool = True


# ── Context / Memory ─────────────────────────────────────────────

class ContextState(BaseModel):
    session_id: str
    last_intent: Optional[str] = None
    last_entities: Dict[str, Any] = Field(default_factory=dict)
    pending_action_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    active_thread_id: Optional[str] = None
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    recent_actions: List[str] = Field(default_factory=list)
    pending_clarifications: List[str] = Field(default_factory=list)


# ── Email Intelligence ────────────────────────────────────────────

class ExtractedActionItem(BaseModel):
    action: str
    deadline: Optional[str] = None
    owner: Optional[str] = None
    confidence: float = 0.0


class FollowUpDetection(BaseModel):
    needs_follow_up: bool = False
    reason: Optional[str] = None
    suggested_delay: Optional[str] = None
    confidence: float = 0.0


class ReplyClassification(BaseModel):
    reply_type: str = "general"  # confirmation, clarification, negotiation, scheduling
    urgency: str = "normal"  # low, normal, high, urgent
    sentiment: str = "neutral"  # positive, neutral, negative
    suggested_reply: Optional[str] = None


class EmailCognitionResult(BaseModel):
    action_items: List[ExtractedActionItem] = Field(default_factory=list)
    follow_up: FollowUpDetection = Field(default_factory=FollowUpDetection)
    reply_classification: Optional[ReplyClassification] = None
    deadlines: List[Dict[str, Any]] = Field(default_factory=list)
    is_reply_vs_new: Optional[str] = None  # "reply" | "new" | "forward"
    recommendations: List[Recommendation] = Field(default_factory=list)


# ── API Request / Response ────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    thread_context: Optional[str] = None  # email thread text for context


class ChatResponse(BaseModel):
    type: str  # question, recommendation, action_preview, multi_action_preview, result, error
    status: Optional[str] = None  # success, failure (for result type)
    message: str = ""
    action_id: Optional[str] = None
    group_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # Inline payloads
    question: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
    action_preview: Optional[Dict[str, Any]] = None
    multi_action_preview: Optional[Dict[str, Any]] = None


class ActionPatchRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = None


class DashboardSummary(BaseModel):
    emails_pending: int = 0
    actions_pending: int = 0
    actions_today: int = 0
    recommendations_active: int = 0
    recent_actions: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    success: bool
    action_id: str
    intent: str
    provider_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: str = ""
