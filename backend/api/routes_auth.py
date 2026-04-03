"""
Google OAuth 2.0 routes for V.NOTEBOOK.
Handles the browser-based sign-in flow for Gmail & Calendar access.
Persists PKCE state to disk so it survives server auto-reloads.
"""
import os
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

router = APIRouter()

# ── Path Resolution ───────────────────────────────────────────────
_api_dir = os.path.dirname(__file__)
_backend_dir = os.path.dirname(_api_dir)
_project_root = os.path.dirname(_backend_dir)

REDIRECT_URI = "http://localhost:8000/api/auth/google/callback"

def _find_file(filename):
    """Search backend/ then project root for a file."""
    for d in [_backend_dir, _project_root]:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return path
    return os.path.join(_backend_dir, filename)

CREDENTIALS_PATH = _find_file("credentials.json")
TOKEN_PATH = os.path.join(_backend_dir, "token.json")
_PKCE_STATE_PATH = os.path.join(_backend_dir, "_oauth_pkce_state.json")

# Scopes for Gmail + Calendar
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Allow http for localhost dev
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


# ── Helpers ───────────────────────────────────────────────────────

def _load_client_config():
    """
    Load the OAuth client config from credentials.json.
    Works with both 'installed' and 'web' client types.
    """
    with open(CREDENTIALS_PATH, "r") as f:
        data = json.load(f)

    # Determine the client type key
    if "web" in data:
        return data, "web"
    elif "installed" in data:
        return data, "installed"
    else:
        raise ValueError("credentials.json must contain 'web' or 'installed' key")


def _save_pkce_state(state: str, code_verifier: str):
    """Persist PKCE code_verifier to disk so it survives server restarts."""
    with open(_PKCE_STATE_PATH, "w") as f:
        json.dump({"state": state, "code_verifier": code_verifier}, f)


def _load_pkce_state(state: str):
    """Load and consume the saved PKCE code_verifier."""
    if not os.path.exists(_PKCE_STATE_PATH):
        return None
    try:
        with open(_PKCE_STATE_PATH, "r") as f:
            data = json.load(f)
        # Clean up the file after reading
        os.remove(_PKCE_STATE_PATH)
        if data.get("state") == state:
            return data.get("code_verifier")
    except Exception:
        pass
    return None


# ── Routes ────────────────────────────────────────────────────────

@router.get("/auth/google/status")
async def get_auth_status():
    """Returns the current status of Google Auth integration."""
    has_credentials = os.path.exists(CREDENTIALS_PATH)
    has_token = os.path.exists(TOKEN_PATH)

    is_valid = False
    if has_token:
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            if creds and creds.valid:
                is_valid = True
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(GoogleRequest())
                # Save refreshed token
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
                is_valid = True
        except Exception:
            pass

    return {
        "is_configured": has_credentials,
        "is_authenticated": has_token and is_valid,
    }


@router.get("/auth/google/login")
async def login_google():
    """Initiates the Google OAuth 2.0 web flow."""
    if not os.path.exists(CREDENTIALS_PATH):
        raise HTTPException(status_code=400, detail="credentials.json not found on server.")

    client_config, client_type = _load_client_config()

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    # Generate authorization URL
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    # Persist the PKCE code_verifier to disk (survives server restarts)
    code_verifier = flow.code_verifier
    _save_pkce_state(state, code_verifier or "")

    print(f"[Auth] Login initiated — state={state[:12]}... verifier={'yes' if code_verifier else 'no'}")
    return RedirectResponse(auth_url)


@router.get("/auth/google/callback")
async def auth_callback(code: str, state: str = ""):
    """Handles the OAuth callback, exchanges code for token."""
    if not os.path.exists(CREDENTIALS_PATH):
        raise HTTPException(status_code=400, detail="credentials.json not found.")

    try:
        client_config, client_type = _load_client_config()

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        # Restore the PKCE code_verifier from disk
        saved_verifier = _load_pkce_state(state)
        if saved_verifier:
            flow.code_verifier = saved_verifier
            print(f"[Auth] Restored PKCE verifier for state={state[:12]}...")
        else:
            # No saved verifier — clear it to avoid mismatch
            flow.code_verifier = None
            print(f"[Auth] No saved PKCE verifier, proceeding without")

        flow.fetch_token(code=code)
        creds = flow.credentials

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

        print(f"[Auth] ✓ Token saved to {TOKEN_PATH}")
        return RedirectResponse(url="/#settings-success")

    except Exception as e:
        print(f"[Auth] OAuth Callback Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
