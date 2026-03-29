# Handles chat session persistence
from typing import Dict, List, Optional
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
from datetime import datetime
from typing import Dict, List, Optional
from core.goals import GoalManager

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
CURRENT_SESSION_FILE = os.path.join(DATA_DIR, 'current_session.json') # To store current session ID

class SessionManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR)
        if not os.path.exists(CURRENT_SESSION_FILE):
            self._save_current_session_id(None)

    def _get_path(self, session_id: str) -> str:
        """Returns the file path for a given session ID."""
        return os.path.join(SESSIONS_DIR, f"{session_id}.json")

    def _load_current_session_id(self) -> Optional[str]:
        """Loads the ID of the currently active session."""
        try:
            with open(CURRENT_SESSION_FILE, 'r') as f:
                data = json.load(f)
                return data.get("current_session_id")
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _save_current_session_id(self, session_id: Optional[str]):
        """Saves the ID of the currently active session."""
        with open(CURRENT_SESSION_FILE, 'w') as f:
            json.dump({"current_session_id": session_id}, f, indent=2)

    def get_current_session_id(self) -> Optional[str]:
        return self._load_current_session_id()

    def set_current_session_id(self, session_id: Optional[str]):
        self._save_current_session_id(session_id)

    def save_session(self, session_id: str, session_data: Dict):
        """Saves the full session data to its dedicated file."""
        if not session_id:
            return
        path = self._get_path(session_id)
        with open(path, 'w') as f:
            json.dump(session_data, f, indent=2)

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve full session data."""
        path = self._get_path(session_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def create_session(self, title: str = "New Research") -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "goals": []
        }
        self.save_session(session_id, session_data)
        self.set_current_session_id(session_id)
        return session_id

    def add_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """Append a message to the session's history."""
        if metadata is None:
            metadata = {}
            
        session = self.get_session(session_id)
        if not session:
            return None
        
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **metadata
        }
        
        if "messages" not in session:
            session["messages"] = []
        
        # Auto-title session from first user message
        if role == "user" and session.get("title") in ["New Research", "New Chat", "Untitled"]:
            session["title"] = content[:40] + ("..." if len(content) > 40 else "")
            
        session["messages"].append(msg)
        self.save_session(session_id, session)
        return msg

    # The following methods (get_session, save_messages, update_session_title, list_sessions, delete_session)
    # seem to be based on an older, single-file data structure.
    # They need to be updated to use the new per-session file structure.
    # For now, I will comment them out or adapt them if possible based on the new structure.
    # The user only asked to add `add_message`, so I will keep the existing methods as they are,
    # but note that they might be inconsistent with the new `save_session`/`get_session` logic.

    # The original `get_session(self, sid)` method was duplicated and had different logic.
    # The one above `create_session` is the correct one for the new file structure.
    # This one below is likely from the old structure and should be removed or updated.
    # def get_session(self, sid):
    #     data = self._load_data() # This method doesn't exist in the new structure
    #     return data["sessions"].get(sid)

    # The following methods need significant refactoring to work with the new per-session file structure.
    # They currently assume a single data file with a "sessions" dictionary.

    def get_all_sessions(self) -> List[Dict]:
        """List all available sessions."""
        sessions = []
        if not os.path.exists(SESSIONS_DIR):
            return []
            
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(SESSIONS_DIR, filename), 'r') as f:
                        data = json.load(f)
                        # Ensure basic keys
                        if "session_id" in data:
                            sessions.append(data)
                except Exception as e:
                    print(f"Error loading session file {filename}: {e}")
                    continue
        
        # Sort by timestamp desc (newest first)
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return sessions

    def save_messages(self, session_id: str, messages: List[Dict]):
        """Overwrite messages for a session (rarely used given add_message)."""
        session = self.get_session(session_id)
        if session:
            session["messages"] = messages
            # Update title based on first user message if generic
            if session.get("title") in ["New Research", "New Chat"] and len(messages) > 0:
                for m in messages:
                    if m["role"] == "user":
                        session["title"] = m["content"][:30]
                        break
            self.save_session(session_id, session)

    def update_session_title(self, session_id: str, new_title: str):
        session = self.get_session(session_id)
        if session:
            session["title"] = new_title
            self.save_session(session_id, session)

    def list_sessions(self):
        """Return raw sessions list (legacy format adapter)."""
        return self.get_all_sessions()
        
    def delete_session(self, session_id: str):
        path = self._get_path(session_id)
        if os.path.exists(path):
            os.remove(path)
            
        # Clean up goals associated with this session
        try:
            GoalManager().delete_session_goals(session_id)
        except Exception as e:
            print(f"Failed to delete goals for session {session_id}: {e}")
            
        # Reset current if deleted
        if self.get_current_session_id() == session_id:
            self.set_current_session_id(None)
