# Settings API Routes — API Key management, memory stats, preferences
import os
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict
from dotenv import load_dotenv, set_key

router = APIRouter()

# Path to the project root .env file
_backend_dir = os.path.dirname(os.path.dirname(__file__))
_project_root = os.path.dirname(_backend_dir)
_env_path = os.path.join(_project_root, ".env")
_prefs_path = os.path.join(_backend_dir, "data", "user_preferences.json")

# ── Models ────────────────────────────────────────────────────────

class KeysPayload(BaseModel):
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    whatsapp_api_url: Optional[str] = None
    whatsapp_api_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None

class PreferencesPayload(BaseModel):
    default_model: Optional[str] = None
    auto_goal_inference: Optional[bool] = None
    default_workspace: Optional[str] = None
    compact_mode: Optional[bool] = None


# ── Helpers ───────────────────────────────────────────────────────

def _ensure_env_file():
    """Make sure .env exists."""
    if not os.path.exists(_env_path):
        with open(_env_path, "w") as f:
            f.write("# V.NOTEBOOK Environment Variables\n")

def _load_preferences() -> dict:
    """Load saved user preferences from JSON."""
    if os.path.exists(_prefs_path):
        try:
            with open(_prefs_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_preferences(prefs: dict):
    """Persist user preferences to JSON."""
    os.makedirs(os.path.dirname(_prefs_path), exist_ok=True)
    with open(_prefs_path, "w") as f:
        json.dump(prefs, f, indent=2)


# ── API Keys ─────────────────────────────────────────────────────

@router.get("/settings/keys")
async def get_keys_status():
    """Returns which keys are configured (not the actual values)."""
    load_dotenv(_env_path, override=True)

    def _mask(val):
        if not val:
            return None
        if len(val) <= 8:
            return "••••"
        return val[:4] + "••••" + val[-4:]

    return {
        "groq_api_key": _mask(os.getenv("GROQ_API_KEY")),
        "openai_api_key": _mask(os.getenv("OPENAI_API_KEY")),
        "anthropic_api_key": _mask(os.getenv("ANTHROPIC_API_KEY")),
        "gemini_api_key": _mask(os.getenv("GEMINI_API_KEY")),
        "tavily_api_key": _mask(os.getenv("TAVILY_API_KEY")),
        "whatsapp_api_url": os.getenv("WHATSAPP_API_URL") or None,
        "whatsapp_api_token": _mask(os.getenv("WHATSAPP_API_TOKEN")),
        "whatsapp_phone_number_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID") or None,
    }

@router.post("/settings/keys")
async def save_keys(payload: KeysPayload, request: Request):
    """Saves API keys to .env and hot-reloads the LLM handler."""
    _ensure_env_file()

    mapping = {
        "GROQ_API_KEY": payload.groq_api_key,
        "OPENAI_API_KEY": payload.openai_api_key,
        "ANTHROPIC_API_KEY": payload.anthropic_api_key,
        "GEMINI_API_KEY": payload.gemini_api_key,
        "TAVILY_API_KEY": payload.tavily_api_key,
        "WHATSAPP_API_URL": payload.whatsapp_api_url,
        "WHATSAPP_API_TOKEN": payload.whatsapp_api_token,
        "WHATSAPP_PHONE_NUMBER_ID": payload.whatsapp_phone_number_id,
    }

    updated = []
    for env_key, value in mapping.items():
        if value is not None and value.strip():
            set_key(_env_path, env_key, value.strip())
            os.environ[env_key] = value.strip()
            updated.append(env_key)

    # Hot-reload the LLM handler so new Groq keys take effect immediately
    if any(k.startswith("GROQ") for k in updated):
        try:
            engine = request.app.state.engine
            engine.llm.reload_keys()
        except Exception as e:
            print(f"[Settings] LLM reload warning: {e}")

    return {"status": "saved", "updated_keys": updated}


# ── Memory / Archive ─────────────────────────────────────────────

@router.get("/settings/memory")
async def get_memory_stats(request: Request):
    """Returns archive stats (total chunks, sources)."""
    engine = request.app.state.engine
    stats = engine.memory.get_stats()
    return {
        "total_chunks": stats.get("total_chunks", 0),
        "sources": stats.get("sources", {}),
        "index_size": engine.memory.index.ntotal,
    }

@router.post("/settings/memory/wipe")
async def wipe_memory(request: Request):
    """Wipes the entire knowledge archive (FAISS + documents list)."""
    engine = request.app.state.engine
    engine.memory.clear()
    return {"status": "wiped", "total_chunks": 0}


# ── User Preferences ─────────────────────────────────────────────

@router.get("/settings/preferences")
async def get_preferences():
    """Returns saved user preferences."""
    prefs = _load_preferences()
    return {
        "default_model": prefs.get("default_model", "groq/llama-3.3-70b-versatile"),
        "auto_goal_inference": prefs.get("auto_goal_inference", True),
        "default_workspace": prefs.get("default_workspace", "notebook"),
        "compact_mode": prefs.get("compact_mode", False),
    }

@router.post("/settings/preferences")
async def save_preferences(payload: PreferencesPayload):
    """Saves user preferences."""
    prefs = _load_preferences()

    if payload.default_model is not None:
        prefs["default_model"] = payload.default_model
    if payload.auto_goal_inference is not None:
        prefs["auto_goal_inference"] = payload.auto_goal_inference
    if payload.default_workspace is not None:
        prefs["default_workspace"] = payload.default_workspace
    if payload.compact_mode is not None:
        prefs["compact_mode"] = payload.compact_mode

    _save_preferences(prefs)
    return {"status": "saved", "preferences": prefs}
