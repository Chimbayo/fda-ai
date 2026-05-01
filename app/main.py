"""
FastAPI entry point for FDA-AI agricultural assistant.
Simple RAG-based system using local PDFs + Ollama.
NO OpenAI API - completely local.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import shutil
from pathlib import Path

from app.rag import get_answer, get_stats, reload_knowledge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="FDA-AI Agricultural Assistant",
    description="AI-powered agricultural advisory using local PDFs and Ollama",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None
    location: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    sources: List[Dict[str, Any]]
    confidence: float
    context_used: bool


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    knowledge_base: Dict[str, Any]


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with system info."""
    stats = get_stats()
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        knowledge_base=stats
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    stats = get_stats()
    return {
        "status": "healthy",
        "pdfs_loaded": stats["pdf_count"],
        "chunks_indexed": stats["chunk_count"],
        "has_index": stats["has_index"]
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - uses PDF knowledge + Ollama.
    
    CRITICAL: This uses ONLY local PDF knowledge, NOT OpenAI.
    """
    try:
        logger.info(f"Received query: {request.message}")
        
        # Get answer from RAG system
        result = get_answer(request.message)
        
        return ChatResponse(
            response=result["answer"],
            sources=result["sources"],
            confidence=result["confidence"],
            context_used=result["context_used"]
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file to the knowledge base.
    """
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        pdf_dir = Path("data/pdfs")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = pdf_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Uploaded PDF: {file.filename}")
        
        # Reload knowledge base
        success = reload_knowledge()
        
        return {
            "message": f"PDF '{file.filename}' uploaded successfully",
            "processed": success,
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge-stats")
async def knowledge_stats():
    """Get knowledge base statistics."""
    return get_stats()


@app.post("/reload-knowledge")
async def reload_knowledge_base():
    """Reload all PDFs from the pdf directory."""
    try:
        success = reload_knowledge()
        stats = get_stats()
        
        return {
            "success": success,
            "message": "Knowledge base reloaded" if success else "Reload failed",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
