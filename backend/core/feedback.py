import json
import os
from datetime import datetime
from typing import List, Dict, Any
from models.feedback import FeedbackEvent, FeedbackDirectives

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
FEEDBACK_FILE = os.path.join(DATA_DIR, 'feedback.json')
PREFERENCES_FILE = os.path.join(DATA_DIR, 'preferences.json')

class FeedbackMemory:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        # Ensure files exist
        if not os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, 'w') as f:
                json.dump([], f)
        if not os.path.exists(PREFERENCES_FILE):
             with open(PREFERENCES_FILE, 'w') as f:
                json.dump({}, f)

    def record_event(self, event: FeedbackEvent):
        """Log a feedback event and optionally update preferences."""
        # 1. Log Event
        try:
            with open(FEEDBACK_FILE, 'r') as f:
                events = json.load(f)
        except:
            events = []
            
        events.append(event.dict())
        
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(events, f, indent=2, default=str)
            
        # 2. Update Preferences (Simple Logic)
        # If we see repeated patterns in `delta`, update `preferences.json`
        # This is a heuristic placeholder. In a real system, an LLM would process this periodically.
        if event.type == "edit" and "length" in event.delta:
            self._update_preference("email_length", event.delta["length"])
        elif event.type == "edit" and "tone" in event.delta:
            self._update_preference("email_tone", event.delta["tone"])

    def _update_preference(self, key: str, value: str):
        try:
            with open(PREFERENCES_FILE, 'r') as f:
                prefs = json.load(f)
        except:
            prefs = {}
            
        prefs[key] = value
        
        with open(PREFERENCES_FILE, 'w') as f:
            json.dump(prefs, f, indent=2)

    def get_preference_directives(self, context: str) -> Dict[str, str]:
        """Return structured directives based on context."""
        try:
            with open(PREFERENCES_FILE, 'r') as f:
                prefs = json.load(f)
        except:
            return {}
            
        # Filter based on context if needed
        # For now return all relevant keys
        if context == "email":
            return {k: v for k, v in prefs.items() if k.startswith("email_")}
        elif context == "research":
            return {k: v for k, v in prefs.items() if k.startswith("research_")}
            
        return prefs
