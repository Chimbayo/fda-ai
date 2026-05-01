"""
Agent router for LangGraph workflow.
Determines which agent should handle a given query.
"""
from enum import Enum
from typing import Dict, Any, List
import logging

from app.models.ollama_model import OllamaModel

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Available agent types for query routing."""
    CROP = "crop"
    DISEASE = "disease"
    WEATHER = "weather"
    RETRIEVAL = "retrieval"
    CONVERSATION = "conversation"


class AgentRouter:
    """
    Routes user queries to appropriate specialized agents.
    Uses LLM-based classification with keyword fallback.
    """
    
    def __init__(self):
        self.llm = OllamaModel()
        
        # Keyword-based routing patterns
        self.keywords = {
            AgentType.CROP: [
                "maize", "corn", "variety", "seed", "planting", "fertilizer",
                "yield", "harvest", "soil", "irrigation", "spacing", "seed rate",
                "kalulu", "kanyani", "mbidzi", "mkango", "njobvu", "sc 301", "sc 303",
                "sc 403", "sc 419", "sc 423", "sc 529", "sc 537", "sc 627", "sc 653", "sc 719"
            ],
            AgentType.DISEASE: [
                "disease", "pest", "blight", "mold", "rust", "rot", "virus",
                "symptom", "infection", "fungicide", "pesticide", "control",
                "leaf spot", "wilting", "lesions"
            ],
            AgentType.WEATHER: [
                "weather", "rain", "temperature", "climate", "season", "drought",
                "rainfall", "forecast", "sunny", "cloudy", "humidity", "wind"
            ],
            AgentType.RETRIEVAL: [
                "research", "study", "paper", "document", "pdf", "article",
                "efficiency", "technical", "analysis", "data", "statistics"
            ]
        }
    
    async def route(self, message: str, context: Dict[str, Any] = None) -> AgentType:
        """
        Route a message to the appropriate agent.
        
        Args:
            message: User's query message
            context: Additional context (location, history, etc.)
            
        Returns:
            AgentType: The selected agent type
        """
        message_lower = message.lower()
        
        # Try keyword-based routing first (faster)
        keyword_match = self._keyword_route(message_lower)
        if keyword_match:
            logger.info(f"Keyword routing: {keyword_match.value}")
            return keyword_match
        
        # Fall back to LLM-based classification
        try:
            llm_route = await self._llm_route(message, context)
            logger.info(f"LLM routing: {llm_route.value}")
            return llm_route
        except Exception as e:
            logger.error(f"LLM routing failed: {e}, falling back to conversation")
            return AgentType.CONVERSATION
    
    def _keyword_route(self, message: str) -> AgentType:
        """
        Route based on keyword matching.
        
        Args:
            message: Lowercase message string
            
        Returns:
            AgentType or None if no match
        """
        scores = {}
        
        for agent_type, keywords in self.keywords.items():
            score = sum(1 for keyword in keywords if keyword in message)
            if score > 0:
                scores[agent_type] = score
        
        if scores:
            # Return agent with highest score
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    async def _llm_route(self, message: str, context: Dict[str, Any] = None) -> AgentType:
        """
        Route using LLM classification.
        
        Args:
            message: User's query message
            context: Additional context
            
        Returns:
            AgentType: The selected agent type
        """
        prompt = f"""You are an intelligent router for an agricultural assistant. 
Analyze the following query and classify it into one of these categories:

- CROP: Questions about crop varieties, planting, fertilizers, soil management, yields
- DISEASE: Questions about plant diseases, pests, symptoms, treatments
- WEATHER: Questions about weather, climate, rainfall, temperature forecasts
- RETRIEVAL: Questions requiring research papers, technical documents, studies
- CONVERSATION: General greetings, chitchat, unclear queries

Query: "{message}"

Respond with ONLY the category name (CROP, DISEASE, WEATHER, RETRIEVAL, or CONVERSATION)."""

        response = await self.llm.generate(prompt)
        response_clean = response.strip().upper()
        
        # Map response to AgentType
        agent_map = {
            "CROP": AgentType.CROP,
            "DISEASE": AgentType.DISEASE,
            "WEATHER": AgentType.WEATHER,
            "RETRIEVAL": AgentType.RETRIEVAL,
            "CONVERSATION": AgentType.CONVERSATION
        }
        
        return agent_map.get(response_clean, AgentType.CONVERSATION)
    
    def get_agent_description(self, agent_type: AgentType) -> str:
        """Get description of an agent type."""
        descriptions = {
            AgentType.CROP: "Specialized in crop varieties, planting techniques, and soil management",
            AgentType.DISEASE: "Expert in plant diseases, pests, and treatment options",
            AgentType.WEATHER: "Provides weather forecasts and climate-related advice",
            AgentType.RETRIEVAL: "Retrieves information from research papers and technical documents",
            AgentType.CONVERSATION: "Handles general conversation and clarifies user intent"
        }
        return descriptions.get(agent_type, "General purpose agent")
