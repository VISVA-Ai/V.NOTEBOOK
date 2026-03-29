# Handles text embedding generation
from sentence_transformers import SentenceTransformer

class EmbeddingHandler:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        
    def get_embedding(self, text):
        return self.model.encode(text)
        
    def get_embeddings(self, texts):
        return self.model.encode(texts)
