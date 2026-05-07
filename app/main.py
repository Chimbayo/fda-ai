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

from app.graph.langgraph_flow import get_fda_workflow

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
    description="Multi-agent agricultural advisory system for Malawi farmers",
    version="2.0.0"
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

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    
    try:
        logger.info(f"Received query: {request.message}")
        
        # Get lazy-loaded workflow and process query
        workflow = get_fda_workflow()
        result = workflow.process_query(request.message, request.user_id)
        
        # Return only the response content
        return ChatResponse(response=result)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
