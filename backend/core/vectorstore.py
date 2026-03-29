# Handles vector storage and similarity search
import faiss
import numpy as np
import pickle
import os

class VectorStore:
    def __init__(self, embedding_dim=384):
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.documents = []
        
    def add_documents(self, embeddings, documents):
        if len(documents) == 0:
            return
        embeddings = np.array(embeddings).astype('float32')
        self.index.add(embeddings)
        self.documents.extend(documents)
        
    def search(self, query_embedding, k=5):
        query_embedding = np.array([query_embedding]).astype('float32')
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.documents):
                doc = self.documents[idx]
                results.append({
                    'text': doc['text'],
                    'metadata': doc.get('metadata', {}),
                    'distance': float(distances[0][i])
                })
        return results
        
    def clear(self):
        self.index.reset()
        self.documents = []
