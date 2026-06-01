"""
FDA-AI Main Application with LangGraph Multi-Agent System.
Implements the Tensorview assignment requirements with specialized agricultural agents.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.graph.langgraph_flow import get_fda_workflow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    user_id: Optional[str] = "default_user"


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    knowledge_base: Dict[str, Any]


# Create FastAPI app
app = FastAPI(
    title="FDA-AI Agricultural Assistant",
    redirect_slashes=False
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with system info - fast startup."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        knowledge_base={
            "agents": ["crop", "disease", "weather", "knowledge", "conversation"]
        }
    )


@app.post("/chat", include_in_schema=False)
@app.post("/chat/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint that uses the LangGraph multi-agent workflow."""
    try:
        logger.info(f"Received query: {request.message}")
        
        workflow = get_fda_workflow()
        result = workflow.process_query(request.message, request.user_id)
        
        return ChatResponse(response=result)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# NEW ENDPOINT FOR VERCEL - with /api prefix
@app.post("/api/chat", include_in_schema=False)
@app.post("/api/chat/", response_model=ChatResponse)
async def api_chat(request: ChatRequest):
    """Chat endpoint with /api prefix for Vercel compatibility."""
    try:
        logger.info(f"Received query (via /api/chat): {request.message}")
        
        workflow = get_fda_workflow()
        result = workflow.process_query(request.message, request.user_id)
        
        return ChatResponse(response=result)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/knowledge")
async def debug_knowledge():
    """Debug endpoint to check what knowledge is loaded."""
    try:
        from api.knowledge.json_knowledge_loader import get_json_knowledge
        from api.knowledge.pdf_knowledge_retriever import get_pdf_retriever
        
        json_knowledge = get_json_knowledge()
        pdf_retriever = get_pdf_retriever()
        
        return {
            "json_knowledge_loaded": len(json_knowledge) if json_knowledge else 0,
            "pdf_retriever_ready": pdf_retriever is not None,
            "status": "ok"
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.post("/ask-with-knowledge")
async def ask_with_knowledge(request: ChatRequest):
    """Force use of knowledge base for answers."""
    try:
        from api.knowledge.json_knowledge_loader import search_json_knowledge
        from api.knowledge.pdf_knowledge_retriever import search_pdfs
        
        # Search both knowledge sources
        json_results = search_json_knowledge(request.message)
        pdf_results = search_pdfs(request.message)
        
        combined_knowledge = json_results + pdf_results
        
        if combined_knowledge:
            # Use the knowledge to answer
            context = "\n".join(combined_knowledge[:3])
            answer = f"Based on our agricultural guides:\n\n{context}"
            return ChatResponse(response=answer)
        else:
            # Fall back to normal flow
            workflow = get_fda_workflow()
            result = workflow.process_query(request.message, request.user_id)
            return ChatResponse(response=result)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)