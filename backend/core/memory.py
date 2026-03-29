# Handles Long Term Memory (Embeddings + Vector Storage + Retrieval)
import faiss
import numpy as np
import os
from sentence_transformers import SentenceTransformer

class Memory:
    def __init__(self, embedding_model='all-MiniLM-L6-v2', embedding_dim=384):
        # Embeddings
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Vector Store
        self.dimension = embedding_dim
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = [] # Stores metadata/text alongside vectors

    def get_embedding(self, text):
        """Generates embedding for a single text string."""
        return self.embedding_model.encode(text)

    def get_embeddings(self, texts):
        """Generates embeddings for a list of strings."""
        return self.embedding_model.encode(texts)

    def add_documents(self, documents):
        """Adds documents to the memory. Documents must have 'text' key."""
        if not documents:
            return
            
        texts = [doc['text'] for doc in documents]
        embeddings = self.get_embeddings(texts)
        
        # Add to FAISS
        embeddings_np = np.array(embeddings).astype('float32')
        self.index.add(embeddings_np)
        
        # Store raw docs
        self.documents.extend(documents)

    def retrieve(self, query, k=5):
        """Retrieves top-k relevant documents for a query."""
        if self.index.ntotal == 0:
            return []
            
        query_embedding = self.get_embedding(query)
        query_vec = np.array([query_embedding]).astype('float32')
        
        distances, indices = self.index.search(query_vec, k)
        
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

    def remove_source(self, source_name: str) -> int:
        """Removes all chunks belonging to a specific source from memory."""
        keep_indices = []
        new_docs = []
        
        for i, doc in enumerate(self.documents):
            # The source is often uploaded as 'data/temp_...' or just filename
            doc_source = doc.get("metadata", {}).get("source", "")
            if doc_source != source_name:
                keep_indices.append(i)
                new_docs.append(doc)
        
        if len(keep_indices) == len(self.documents):
            return 0  # Nothing removed
            
        chunks_removed = len(self.documents) - len(keep_indices)
        
        if len(keep_indices) > 0:
            vectors_to_keep = []
            for idx in keep_indices:
                vec = np.zeros(self.dimension, dtype='float32')
                self.index.reconstruct(idx, vec)
                vectors_to_keep.append(vec)
                
            self.index.reset()
            self.documents = new_docs
            self.index.add(np.array(vectors_to_keep).astype('float32'))
        else:
            self.clear()
            
        return chunks_removed

    def get_stats(self):
        """Returns stats about stored documents."""
        stats = {
            "total_chunks": len(self.documents),
            "sources": {}
        }
        for doc in self.documents:
            src = doc.get("metadata", {}).get("source", "Unknown")
            if src not in stats["sources"]:
                stats["sources"][src] = 0
            stats["sources"][src] += 1
        return stats

    def clear(self):
        """Resets the memory."""
        self.index.reset()
        self.documents = []
