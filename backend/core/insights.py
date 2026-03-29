import json
import os
from datetime import datetime
from typing import List, Dict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
INSIGHTS_FILE = os.path.join(DATA_DIR, 'insights.json')

class InsightMemory:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(INSIGHTS_FILE):
             with open(INSIGHTS_FILE, 'w') as f:
                json.dump([], f)

    def add_insight(self, content: str, source: str, session_id: str):
        try:
            with open(INSIGHTS_FILE, 'r') as f:
                insights = json.load(f)
        except:
            insights = []
            
        new_insight = {
            "content": content,
            "source": source,
            "session_id": session_id,
            "created_at": datetime.now().isoformat()
        }
        
        insights.append(new_insight)
        
        with open(INSIGHTS_FILE, 'w') as f:
            json.dump(insights, f, indent=2)

    def get_relevant_insights(self, query: str, k: int = 3) -> List[str]:
        # Simple keyword matching for MVP
        try:
            with open(INSIGHTS_FILE, 'r') as f:
                insights = json.load(f)
        except:
            return []
            
        matches = []
        tokens = query.lower().split()
        
        for insight in insights:
            score = sum(1 for t in tokens if t in insight["content"].lower())
            if score > 0:
                matches.append((score, insight["content"]))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:k]]
