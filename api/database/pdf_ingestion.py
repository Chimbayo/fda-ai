"""
PDF Ingestion Module for FDA-AI.
Extracts text from PDFs and stores in vector database.
"""
import os
import re
import logging
from typing import List, Dict, Any
from pathlib import Path

import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle

logger = logging.getLogger(__name__)


class PDFIngestion:
    """
    Handles PDF text extraction and vector storage.
    Creates searchable knowledge base from PDF documents.
    """
    
    def __init__(self, pdf_dir: str = "data/pdfs", vector_dir: str = "data/vectors"):
        self.pdf_dir = Path(pdf_dir)
        self.vector_dir = Path(vector_dir)
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        logger.info("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # FAISS index and chunks
        self.index = None
        self.chunks = []
        self.chunk_metadata = []
        
        # Load existing index if available
        self._load_existing_index()
    
    def _load_existing_index(self):
        """Load existing FAISS index if available."""
        index_path = self.vector_dir / "faiss_index.bin"
        chunks_path = self.vector_dir / "chunks.pkl"
        metadata_path = self.vector_dir / "metadata.pkl"
        
        if index_path.exists() and chunks_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))
                with open(chunks_path, 'rb') as f:
                    self.chunks = pickle.load(f)
                if metadata_path.exists():
                    with open(metadata_path, 'rb') as f:
                        self.chunk_metadata = pickle.load(f)
                logger.info(f"Loaded existing index with {len(self.chunks)} chunks")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                self.index = None
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                
            logger.info(f"Extracted {len(text)} characters from {pdf_path.name}")
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
        
        return text
    
    def chunk_text(self, text: str, source: str, chunk_size: int = 500, overlap: int = 100) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks for better retrieval.
        
        Args:
            text: Full text content
            source: Source document name
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into sentences (rough approximation)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence exceeds chunk size
            if current_size + len(sentence) > chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "source": source,
                    "length": len(current_chunk)
                })
                
                # Keep overlap for context
                words = current_chunk.split()
                overlap_text = " ".join(words[-overlap//10:])  # Approximate word count
                current_chunk = overlap_text + " " + sentence
                current_size = len(current_chunk)
            else:
                current_chunk += " " + sentence
                current_size += len(sentence) + 1
        
        # Add remaining text
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "source": source,
                "length": len(current_chunk)
            })
        
        return chunks
    
    def process_all_pdfs(self) -> bool:
        """
        Process all PDFs in the pdf directory.
        
        Returns:
            True if successful
        """
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDFs found in {self.pdf_dir}")
            return False
        
        logger.info(f"Found {len(pdf_files)} PDFs to process")
        
        all_chunks = []
        
        for pdf_file in pdf_files:
            logger.info(f"Processing: {pdf_file.name}")
            
            # Extract text
            text = self.extract_text_from_pdf(pdf_file)
            
            if not text.strip():
                logger.warning(f"No text extracted from {pdf_file.name}")
                continue
            
            # Chunk the text
            chunks = self.chunk_text(text, pdf_file.name)
            logger.info(f"Created {len(chunks)} chunks from {pdf_file.name}")
            
            all_chunks.extend(chunks)
        
        if not all_chunks:
            logger.error("No chunks created from PDFs")
            return False
        
        # Store chunks and create embeddings
        self.chunks = [c["text"] for c in all_chunks]
        self.chunk_metadata = all_chunks
        
        # Create embeddings
        logger.info(f"Creating embeddings for {len(self.chunks)} chunks...")
        embeddings = self.model.encode(self.chunks)
        embeddings = np.array(embeddings).astype('float32')
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)
        
        # Save index and chunks
        self._save_index()
        
        logger.info(f"Successfully processed {len(pdf_files)} PDFs into {len(self.chunks)} chunks")
        return True
    
    def _save_index(self):
        """Save FAISS index and chunks to disk."""
        index_path = self.vector_dir / "faiss_index.bin"
        chunks_path = self.vector_dir / "chunks.pkl"
        metadata_path = self.vector_dir / "metadata.pkl"
        
        faiss.write_index(self.index, str(index_path))
        
        with open(chunks_path, 'wb') as f:
            pickle.dump(self.chunks, f)
        
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.chunk_metadata, f)
        
        logger.info(f"Saved index to {self.vector_dir}")
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks.
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of relevant chunks with scores
        """
        if self.index is None:
            logger.error("No index available. Please process PDFs first.")
            return []
        
        # Create query embedding
        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.chunks):
                results.append({
                    "text": self.chunks[idx],
                    "metadata": self.chunk_metadata[idx] if idx < len(self.chunk_metadata) else {},
                    "score": float(distances[0][i]),
                    "index": int(idx)
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        return {
            "pdf_count": len(pdf_files),
            "pdfs": [f.name for f in pdf_files],
            "chunk_count": len(self.chunks),
            "has_index": self.index is not None,
            "vector_dir": str(self.vector_dir)
        }


if __name__ == "__main__":
    # Test ingestion
    ingestion = PDFIngestion()
    
    # Show stats
    stats = ingestion.get_stats()
    print(f"\nPDF Statistics:")
    print(f"  PDFs found: {stats['pdf_count']}")
    print(f"  PDF files: {stats['pdfs']}")
    print(f"  Has index: {stats['has_index']}")
    print(f"  Chunks: {stats['chunk_count']}")
    
    if stats['pdf_count'] > 0:
        print("\nProcessing PDFs...")
        success = ingestion.process_all_pdfs()
        
        if success:
            print("\nTesting search...")
            results = ingestion.search("What maize varieties are recommended?", k=3)
            
            print(f"\nFound {len(results)} relevant chunks:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Score: {result['score']:.4f}")
                print(f"   Source: {result['metadata'].get('source', 'Unknown')}")
                print(f"   Text: {result['text'][:200]}...")
