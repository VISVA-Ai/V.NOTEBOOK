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

    def retrieve(self, query, k=5, session_id=None):
        """Retrieves top-k relevant documents for a query, optionally filtered by session_id."""
        if self.index.ntotal == 0:
            return []
            
        query_embedding = self.get_embedding(query)
        query_vec = np.array([query_embedding]).astype('float32')
        
        # If filtering by session, over-fetch to compensate for filtering
        fetch_k = k * 4 if session_id else k
        fetch_k = min(fetch_k, self.index.ntotal)
        
        distances, indices = self.index.search(query_vec, fetch_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.documents):
                doc = self.documents[idx]
                # Filter by session_id if provided
                if session_id:
                    doc_session = doc.get('metadata', {}).get('session_id')
                    if doc_session != session_id:
                        continue
                results.append({
                    'text': doc['text'],
                    'metadata': doc.get('metadata', {}),
                    'distance': float(distances[0][i])
                })
                if len(results) >= k:
                    break
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

    def get_stats(self, session_id=None):
        """Returns stats about stored documents, optionally filtered by session_id."""
        stats = {
            "total_chunks": 0,
            "sources": {}
        }
        for doc in self.documents:
            meta = doc.get("metadata", {})
            # Filter by session_id if provided
            if session_id:
                doc_session = meta.get("session_id")
                if doc_session != session_id:
                    continue
            src = meta.get("source", "Unknown")
            if src not in stats["sources"]:
                stats["sources"][src] = 0
            stats["sources"][src] += 1
        stats["total_chunks"] = sum(stats["sources"].values())
        return stats

    def clear(self):
        """Resets the memory."""
        self.index.reset()
        self.documents = []
