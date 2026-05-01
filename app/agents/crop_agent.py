"""
Crop Agent - Specialized in crop varieties, planting, and soil management.
Provides expert advice on maize cultivation in Malawi.
"""
from typing import Dict, Any, List
import logging

from app.models.ollama_model import OllamaModel
from app.database.neo4j_client import Neo4jClient
from app.utils.ranking import rank_sources

logger = logging.getLogger(__name__)


class CropAgent:
    """
    Specialized agent for crop-related queries.
    Handles questions about varieties, planting, fertilizers, and yields.
    """
    
    def __init__(self):
        self.llm = OllamaModel()
        self.db = Neo4jClient()
        
        # System prompt for crop expertise
        self.system_prompt = """You are an expert agricultural advisor specializing in crop cultivation in Malawi.
Your expertise includes:
- Maize varieties and their characteristics
- Planting techniques and timing
- Fertilizer recommendations
- Soil management
- Yield optimization
- Spacing and seed rates

Provide practical, actionable advice suitable for smallholder farmers in Malawi.
Be specific about local varieties like Kalulu, Kanyani, Mbidzi, Mkango, and Njobvu.
Always consider the farmer's context and provide clear, step-by-step guidance."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a crop-related query.
        
        Args:
            message: User's query about crops
            context: Additional context (location, history, etc.)
            
        Returns:
            Response with crop advice
        """
        try:
            # Retrieve relevant knowledge from Neo4j
            knowledge = await self._retrieve_knowledge(message)
            
            # Build prompt with context
            prompt = self._build_prompt(message, knowledge, context)
            
            # Generate response
            response = await self.llm.generate(
                prompt,
                system_prompt=self.system_prompt
            )
            
            # Calculate confidence based on knowledge quality
            confidence = self._calculate_confidence(knowledge)
            
            # Rank and format sources
            sources = rank_sources(knowledge)
            
            return {
                "response": response,
                "confidence": confidence,
                "sources": sources,
                "context": {
                    "knowledge_items": len(knowledge),
                    "location": context.get("location") if context else None
                }
            }
            
        except Exception as e:
            logger.error(f"CropAgent processing error: {e}")
            return {
                "response": "I apologize, but I'm having trouble accessing crop information right now. Please try again.",
                "confidence": 0.0,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    async def _retrieve_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant crop knowledge from Neo4j.
        
        Args:
            query: Search query
            
        Returns:
            List of knowledge items
        """
        try:
            # Search for crop varieties, planting info, and soil management
            cypher_query = """
            MATCH (c:Crop)-[:HAS_VARIETY]->(v:Variety)
            WHERE c.name CONTAINS $term OR v.name CONTAINS $term
            RETURN c.name as crop, v.name as variety, v.maturity as maturity, 
                   v.yield as yield, v.characteristics as characteristics
            UNION
            MATCH (t:Technique)-[:APPLIES_TO]->(c:Crop)
            WHERE t.description CONTAINS $term
            RETURN c.name as crop, t.name as technique, t.description as details
            """
            
            # Extract key terms from query
            terms = self._extract_search_terms(query)
            
            results = []
            for term in terms:
                db_results = self.db.execute_query(cypher_query, {"term": term})
                results.extend(db_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Knowledge retrieval error: {e}")
            return []
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """
        Extract relevant search terms from query.
        
        Args:
            query: User query
            
        Returns:
            List of search terms
        """
        # Common crop-related keywords
        keywords = [
            "maize", "corn", "variety", "kalulu", "kanyani", "mbidzi",
            "mkango", "njobvu", "planting", "fertilizer", "soil", "yield",
            "seed", "spacing", "sc 301", "sc 303", "sc 403", "sc 419",
            "sc 423", "sc 529", "sc 537", "sc 627", "sc 653", "sc 719"
        ]
        
        query_lower = query.lower()
        found_terms = [kw for kw in keywords if kw in query_lower]
        
        # If no specific terms found, use general terms
        if not found_terms:
            found_terms = ["maize", "crop"]
        
        return found_terms
    
    def _build_prompt(
        self,
        message: str,
        knowledge: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Build prompt with knowledge and context.
        
        Args:
            message: User message
            knowledge: Retrieved knowledge
            context: Additional context
            
        Returns:
            Formatted prompt
        """
        # Format knowledge
        knowledge_text = ""
        if knowledge:
            knowledge_text = "Relevant information:\n"
            for item in knowledge[:5]:  # Top 5 results
                knowledge_text += f"- {item}\n"
        
        # Add location context if available
        location_context = ""
        if context and context.get("location"):
            location_context = f"\nFarmer location: {context['location']}"
        
        prompt = f"""{knowledge_text}
{location_context}

Farmer's question: {message}

Provide a helpful, practical response based on the information above and your expertise in Malawian agriculture."""
        
        return prompt
    
    def _calculate_confidence(self, knowledge: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score based on knowledge retrieved.
        
        Args:
            knowledge: Retrieved knowledge items
            
        Returns:
            Confidence score (0-1)
        """
        if not knowledge:
            return 0.3  # Low confidence with no knowledge
        
        # Higher confidence with more relevant knowledge
        base_confidence = min(0.5 + (len(knowledge) * 0.1), 0.9)
        
        return base_confidence
