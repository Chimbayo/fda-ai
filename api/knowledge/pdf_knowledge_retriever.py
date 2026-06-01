"""
PDF Knowledge Retriever - Search and retrieve information from processed PDFs.
Provides semantic search across all PDF documents for chatbot responses.
"""
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import faiss
import pickle

logger = logging.getLogger(__name__)


class PDFKnowledgeRetriever:
    """
    Retrieves knowledge from processed PDF documents using semantic search.
    Provides crop-specific and general PDF knowledge retrieval.
    """
    
    def __init__(self, vector_dir: str = "data/vectors"):
        self.vector_dir = Path(vector_dir)
        self.model = None
        self.index = None
        self.chunks = []
        self.chunk_metadata = []
        
        self._load_index()
    
    def _load_index(self):
        """Load FAISS index and chunks from disk."""
        try:
            index_path = self.vector_dir / "faiss_index.bin"
            chunks_path = self.vector_dir / "chunks.pkl"
            metadata_path = self.vector_dir / "metadata.pkl"
            
            if not index_path.exists() or not chunks_path.exists():
                logger.warning("No PDF index found. Run PDF ingestion first.")
                return
            
            # Load FAISS index
            self.index = faiss.read_index(str(index_path))
            
            # Load chunks and metadata
            with open(chunks_path, 'rb') as f:
                self.chunks = pickle.load(f)
            
            with open(metadata_path, 'rb') as f:
                self.chunk_metadata = pickle.load(f)
            
            # Load embedding model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            logger.info(f"✅ Loaded PDF knowledge base with {len(self.chunks)} chunks")
            
        except Exception as e:
            logger.error(f"❌ Error loading PDF index: {e}")
    
    def search_knowledge(self, query: str, top_k: int = 5, crop_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search PDF knowledge base for relevant information.
        
        Args:
            query: Search query
            top_k: Number of results to return
            crop_filter: Optional crop filter (maize, tomato, cabbage)
            
        Returns:
            List of relevant knowledge chunks with metadata
        """
        if not self.index or not self.model:
            logger.warning("PDF knowledge base not available")
            return []
        
        try:
            # Create query embedding
            query_embedding = self.model.encode([query])
            query_embedding = np.array(query_embedding).astype('float32')
            
            # Search index
            distances, indices = self.index.search(query_embedding, top_k)
            
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx >= 0 and idx < len(self.chunks):
                    chunk_text = self.chunks[idx]
                    metadata = self.chunk_metadata[idx]
                    
                    # Apply crop filter if specified
                    if crop_filter:
                        source_lower = metadata.get('source', '').lower()
                        crop_lower = crop_filter.lower()
                        
                        if crop_lower not in source_lower:
                            continue
                    
                    results.append({
                        'text': chunk_text,
                        'source': metadata.get('source', 'Unknown'),
                        'score': float(1.0 / (1.0 + dist)),  # Convert distance to similarity
                        'rank': i + 1
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching PDF knowledge: {e}")
            return []
    
    def get_crop_specific_knowledge(self, crop: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Get crop-specific knowledge from PDFs.
        
        Args:
            crop: Crop name (maize, tomato, cabbage)
            query: Specific query about the crop
            top_k: Number of results to return
            
        Returns:
            List of crop-specific knowledge chunks
        """
        # Search with crop filter
        results = self.search_knowledge(query, top_k * 2, crop_filter=crop)
        
        # Filter for crop-relevant content
        crop_results = []
        for result in results:
            text_lower = result['text'].lower()
            crop_lower = crop.lower()
            
            # Check if content mentions the crop
            if crop_lower in text_lower or any(word in text_lower for word in [crop_lower + 's', crop_lower + 'ing']):
                crop_results.append(result)
        
        return crop_results[:top_k]
    
    def get_available_sources(self) -> List[str]:
        """Get list of available PDF sources."""
        if not self.chunk_metadata:
            return []
        
        sources = set()
        for metadata in self.chunk_metadata:
            sources.add(metadata.get('source', 'Unknown'))
        
        return sorted(list(sources))
    
    def is_available(self) -> bool:
        """Check if PDF knowledge base is available."""
        return self.index is not None and self.model is not None and len(self.chunks) > 0


# Global instance for easy access
_pdf_retriever = None

def get_pdf_knowledge_retriever() -> PDFKnowledgeRetriever:
    """Get global PDF knowledge retriever instance."""
    global _pdf_retriever
    if _pdf_retriever is None:
        _pdf_retriever = PDFKnowledgeRetriever()
    return _pdf_retriever
