import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from models.goals import Goal, GoalCreate, GoalUpdate

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
GOALS_FILE = os.path.join(DATA_DIR, 'goals.json')

class GoalManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(GOALS_FILE):
            self._save_goals([])
            
    def _load_goals(self) -> List[Dict]:
        try:
            with open(GOALS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []

    def _save_goals(self, goals: List[Dict]):
        with open(GOALS_FILE, 'w') as f:
            json.dump(goals, f, indent=2, default=str)

    def add_goal(self, goal_create: GoalCreate) -> Goal:
        goals = self._load_goals()
        new_goal = Goal(
            goal_id=str(uuid.uuid4()),
            session_id=goal_create.session_id,
            title=goal_create.title,
            description=goal_create.description,
            status="active",
            confidence=1.0 if goal_create.source == "user_declared" else 0.5,
            source=goal_create.source,
            last_touched=datetime.now(),
            touch_count=0
        )
        goals.append(new_goal.dict())
        self._save_goals(goals)
        return new_goal

    def update_goal(self, goal_id: str, updates: GoalUpdate) -> Optional[Goal]:
        goals = self._load_goals()
        for g in goals:
            if g["goal_id"] == goal_id:
                if updates.status:
                    g["status"] = updates.status
                if updates.description:
                    g["description"] = updates.description
                g["last_touched"] = datetime.now()
                self._save_goals(goals)
                return Goal(**g)
        return None

    def get_goals(self, status: Optional[str] = None, session_id: Optional[str] = None) -> List[Goal]:
        goals = self._load_goals()
        if session_id:
            goals = [g for g in goals if g.get("session_id", "default") == session_id]
        if status:
            goals = [g for g in goals if g["status"] == status]
        return [Goal(**g) for g in goals]

    def match_context(self, input_text: str, session_id: str) -> List[Goal]:
        """
        Find relevant active goals based on input text keywords.
        Simple keyword matching for now, could be embedding-based later.
        """
        active_goals = self.get_goals(status="active", session_id=session_id)
        matches = []
        input_lower = input_text.lower()
        
        for goal in active_goals:
            # Simple keyword overlap
            keywords = goal.title.lower().split()
            if any(k in input_lower for k in keywords):
                matches.append(goal)
                
        # Update touch count for matched goals
        if matches:
            self._touch_goals([g.goal_id for g in matches])
            
        return matches

    def _touch_goals(self, goal_ids: List[str]):
        """Increment touch count and update last_touched."""
        goals = self._load_goals()
        for g in goals:
            if g["goal_id"] in goal_ids:
                g["touch_count"] = g.get("touch_count", 0) + 1
                g["last_touched"] = datetime.now()
        self._save_goals(goals)

    def check_lifecycle(self):
        """
        Suggest state transitions based on decay or usage.
        Returns suggestions (not actions).
        """
        suggestions = []
        active_goals = self.get_goals(status="active")
        now = datetime.now()
        
        for goal in active_goals:
            # Check for staleness (e.g. not touched in 7 days)
            last_touched = goal.last_touched
            if isinstance(last_touched, str):
                last_touched = datetime.fromisoformat(last_touched)
                
            delta = now - last_touched
            if delta.days > 7:
                suggestions.append({
                    "type": "pause_suggestion",
                    "goal_id": goal.goal_id,
                    "reason": f"Goal '{goal.title}' hasn't been active for {delta.days} days."
                })
                
        return suggestions

    def delete_session_goals(self, session_id: str):
        """Delete all goals associated with a specific session."""
        if not session_id:
            return
        goals = self._load_goals()
        filtered_goals = [g for g in goals if g.get("session_id", "default") != session_id]
        if len(goals) != len(filtered_goals):
            self._save_goals(filtered_goals)

