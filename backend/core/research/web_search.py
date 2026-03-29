# Handles web search operations
from ddgs import DDGS

class WebSearcher:
    def __init__(self):
        self.ddgs = DDGS()
        
    def search(self, query, max_results=5):
        try:
            results = self.ddgs.text(query, max_results=max_results)
            return results if results else []
        except Exception as e:
            print(f"Error searching web: {e}")
            return []
