# Handles deep research workflows
from core.llm import LLMHandler
from core.research.web_search import WebSearcher

class Researcher:
    def __init__(self):
        self.llm = LLMHandler()
        self.searcher = WebSearcher()
        
    def research(self, query, model=None):
        if not model:
            from api.routes_settings import _load_preferences
            model = _load_preferences().get('default_model', 'groq/llama-3.3-70b-versatile')
        print(f"Searching for: {query}")
        results = self.searcher.search(query, max_results=5)
        
        if not results: return "No information found on the web.", []
            
        context = ""
        for res in results:
            context += f"Source: {res['title']} ({res['href']})\nContent: {res['body']}\n\n"
            
        json_instruction = """
You MUST output your answer as a strict JSON object without markdown formatting. Use this schema:
{
  "summary": "A concise summary of the research.",
  "key_points": ["Point 1", "Point 2"],
  "evidence": [{"source": "Title (URL)", "text": "Exact quote"}],
  "gaps": ["Any missing info or contradictions"]
}
"""
        prompt = f"You are a Deep Research Assistant.\nAnswer based strictly on the provided web search results.\n\nSearch Results:\n{context}\n\nUser Question: {query}\n\n{json_instruction}\n\nResponse:"
        
        response = self.llm.get_response(prompt, model=model, mode="Deep Research")
        print(f"[Researcher] Research complete: {query[:80]}, {len(results)} sources")
        return response, results
