# Handles document retrieval
class Retriever:
    def __init__(self, vector_store, embedding_handler):
        self.vector_store = vector_store
        self.embedding_handler = embedding_handler
        
    def retrieve(self, query, k=5):
        query_embedding = self.embedding_handler.get_embedding(query)
        results = self.vector_store.search(query_embedding, k=k)
        return results
