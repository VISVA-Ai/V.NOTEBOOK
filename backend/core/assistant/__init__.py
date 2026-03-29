from core.assistant.email import EmailAnalyzer
from core.assistant.calendar import CalendarAnalyzer

class AssistantIntelligence:
    def __init__(self, llm_handler):
        self.llm = llm_handler
        self.email_analyzer = EmailAnalyzer(llm_handler)
        self.calendar_analyzer = CalendarAnalyzer(llm_handler)

    def analyze_email(self, email_payload: dict) -> dict:
        return self.email_analyzer.analyze(email_payload)
        
    def suggest_reply(self, email_id: str) -> str:
        return self.email_analyzer.get_draft(email_id)
        
    def approve_reply(self, email_id: str, edited_draft: str = None) -> bool:
        return self.email_analyzer.approve_reply(email_id, edited_draft)
        
    def suggest_calendar_event(self, email_id: str) -> dict:
        # For now, just a stub
        return None
        
    def approve_event(self, event_id: str) -> bool:
        return self.calendar_analyzer.approve_event(event_id)

    def get_dashboard(self) -> dict:
        pending_emails = self.email_analyzer.pending_emails.values()
        pending_count = len(pending_emails)
        
        # Find top priority email
        top_email = None
        for analysis in pending_emails:
            if analysis.priority == "high":
                # Convert to dict for response if model is object
                top_email = analysis
                break
                
        return {
            "emails_pending": pending_count,
            "calendar_suggestions": 0, # Stub for now
            "top_priority_email": top_email.dict() if top_email else None
        }
