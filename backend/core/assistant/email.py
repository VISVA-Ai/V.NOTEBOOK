from typing import Optional, Dict
from models.assistant import EmailAnalysis
from core.personas import Personas

class EmailAnalyzer:
    def __init__(self, llm_handler):
        self.llm = llm_handler
        self.pending_emails = {}  # email_id -> EmailAnalysis
        
    def analyze(self, email_data: Dict) -> EmailAnalysis:
        email_id = email_data.get("email_id")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        sender = email_data.get("from", "")
        
        # Build prompt for LLM
        prompt = (
            f"Analyze the following email:\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Body: {body}\n\n"
            f"Tasks:\n"
            f"1. Summarize in one sentence.\n"
            f"2. Determine priority (high/medium/low).\n"
            f"3. Does it require a reply? (yes/no)\n"
            f"4. Drafting a suggested reply if needed.\n"
            f"Output as JSON: {{ 'summary': '...', 'priority': '...', 'reply_needed': bool, 'draft': '...' }}"
        )
        
        # Use Assistant Persona
        response_text = self.llm.get_response(prompt, mode="Assistant")
        
        # Parse response (naive implementation, assume LLM follows instruction)
        # In production, use structured output parsing or robust extraction
        import json
        try:
            # Extract JSON block
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != -1:
                analysis_dict = json.loads(response_text[start:end])
            else:
                raise ValueError("No JSON found")
                
            analysis = EmailAnalysis(
                email_id=email_id,
                sender=sender,
                subject=subject,
                priority=analysis_dict.get("priority", "low").lower(),
                summary=analysis_dict.get("summary", "No summary available."),
                suggested_reply=analysis_dict.get("draft") if analysis_dict.get("reply_needed") else None,
                requires_approval=True
            )
        except Exception as e:
            # Fallback
            print(f"Error parsing email analysis: {e}")
            analysis = EmailAnalysis(
                email_id=email_id,
                sender=sender,
                subject=subject,
                priority="medium",
                summary="Analysis failed. Please review manually.",
                suggested_reply=None,
                requires_approval=True
            )
            
        self.pending_emails[email_id] = analysis
        return analysis

    def get_draft(self, email_id: str) -> Optional[str]:
        if email_id in self.pending_emails:
            return self.pending_emails[email_id].suggested_reply
        return None

    def approve_reply(self, email_id: str, edited_draft: str = None) -> Dict:
        """
        Mark reply as approved. Returns execution payload for n8n.
        Does NOT send email directly.
        """
        if email_id not in self.pending_emails:
             return {"error": "Email not found"}
             
        original = self.pending_emails[email_id]
        final_draft = edited_draft if edited_draft else original.suggested_reply
        
        if not final_draft:
            return {"error": "No draft to approve"}
            
        # Create payload for n8n
        payload = {
            "action": "send_reply",
            "email_id": email_id,
            "reply_body": final_draft,
            "approved_at": "now" # timestamp
        }
        
        # Log approval?
        
        return payload
