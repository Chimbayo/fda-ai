"""
RAG (Retrieval-Augmented Generation) for FDA-AI.
Uses local PDF knowledge + Ollama for responses.
NO OpenAI API - completely local.
"""
import logging
from typing import Dict, Any, List

from app.database.pdf_ingestion import PDFIngestion
from app.models.ollama_model import OllamaModel

logger = logging.getLogger(__name__)


class RAGSystem:
    """
    Retrieval-Augmented Generation system.
    Provides answers based ONLY on PDF knowledge using Ollama.
    """
    
    def __init__(self, model_name: str = "phi3"):
        self.pdf_store = PDFIngestion()
        self.llm = OllamaModel(model=model_name)
        self.model_name = model_name
        
        # System prompt that STRICTLY enforces using only provided context
        self.system_prompt = """You are an agricultural expert for Malawi farmers.

ABSOLUTE RULES:
1. You MUST answer ONLY using the provided Context
2. If the Context doesn't contain the answer, say: "I don't have specific information about that in the provided documents."
3. NEVER use general knowledge outside the Context
4. NEVER say "As an AI" or refer to external knowledge
5. If asked about topics not in the Context, clearly state the documents don't cover that topic

Your responses should:
- Be practical and actionable for farmers
- Use simple, clear language
- Cite specific information from the Context when possible
- Be honest about limitations of the provided documents"""
    
    def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """
        Query the RAG system.
        
        Args:
            question: User question
            k: Number of chunks to retrieve
            
        Returns:
            Response with answer and metadata
        """
        try:
            # Retrieve relevant chunks
            logger.info(f"Retrieving chunks for: {question}")
            chunks = self.pdf_store.search(question, k=k)
            
            if not chunks:
                logger.warning("No relevant chunks found")
                return {
                    "answer": "I don't have specific information about that in the provided documents. The PDFs available don't contain relevant information for this question.",
                    "sources": [],
                    "context_used": False,
                    "confidence": 0.0
                }
            
            # Build context from chunks
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(chunks, 1):
                text = chunk["text"]
                source = chunk["metadata"].get("source", "Unknown PDF")
                
                context_parts.append(f"[Document {i}] From {source}:\n{text}")
                sources.append({
                    "source": source,
                    "score": chunk["score"],
                    "preview": text[:100] + "..." if len(text) > 100 else text
                })
            
            context = "\n\n".join(context_parts)
            
            # Build user prompt
            user_prompt = f"""Context from PDF documents:

{context}

---

Question: {question}

Answer based ONLY on the Context provided above. If the answer is not in the Context, clearly state that the documents don't contain this information."""
            
            # Generate response
            logger.info("Generating response with Ollama...")
            answer = self.llm.generate(
                user_prompt,
                system_prompt=self.system_prompt,
                temperature=0.1  # Low temperature for strict adherence
            )
            
            # Check if model is giving generic response
            generic_indicators = [
                "as an ai",
                "i don't have access to",
                "i don't have information about",
                "my knowledge cutoff",
                "i don't know anything about"
            ]
            
            answer_lower = answer.lower()
            is_generic = any(indicator in answer_lower for indicator in generic_indicators)
            
            if is_generic:
                logger.warning("Model gave generic response, forcing context usage")
                # Retry with stronger prompt
                user_prompt += "\n\nREMEMBER: The Context above contains ALL the information you have. Do NOT use any external knowledge."
                answer = self.llm.generate(user_prompt, system_prompt=self.system_prompt, temperature=0.0)
            
            return {
                "answer": answer,
                "sources": sources,
                "context_used": True,
                "chunks_retrieved": len(chunks),
                "confidence": 0.8 if not is_generic else 0.4
            }
            
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return {
                "answer": f"Error processing your question: {str(e)}",
                "sources": [],
                "context_used": False,
                "confidence": 0.0
            }
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        return self.pdf_store.get_stats()
    
    def reload_pdfs(self) -> bool:
        """Reload all PDFs from the pdf directory."""
        return self.pdf_store.process_all_pdfs()


# Global RAG instance
rag_system = RAGSystem()


def get_answer(question: str) -> Dict[str, Any]:
    """
    Simple interface to get answer from RAG.
    
    Args:
        question: User question
        
    Returns:
        Answer dictionary
    """
    return rag_system.query(question)


def get_stats() -> Dict[str, Any]:
    """Get knowledge base statistics."""
    return rag_system.get_knowledge_stats()


def reload_knowledge() -> bool:
    """Reload PDF knowledge base."""
    return rag_system.reload_pdfs()


if __name__ == "__main__":
    # Test the RAG system
    print("\n" + "="*60)
    print("FDA-AI RAG System Test")
    print("="*60)
    
    # Show stats
    stats = get_stats()
    print(f"\nKnowledge Base Stats:")
    print(f"  PDFs: {stats['pdf_count']}")
    print(f"  Chunks: {stats['chunk_count']}")
    print(f"  Has Index: {stats['has_index']}")
    
    if stats['pdf_count'] == 0:
        print("\n⚠️  No PDFs found! Please upload PDFs to data/pdfs/ directory")
    else:
        # Test queries
        test_questions = [
            "What maize varieties are recommended for Malawi?",
            "How can I improve maize farming efficiency?",
            "What are the symptoms of maize leaf blight?"
        ]
        
        for question in test_questions:
            print(f"\n{'='*60}")
            print(f"Q: {question}")
            print('-'*60)
            
            result = get_answer(question)
            print(f"A: {result['answer'][:300]}...")
            print(f"\nSources: {len(result['sources'])}")
            print(f"Confidence: {result['confidence']}")
