"""
Crop Advisory Agent - Handles crop varieties, planting, fertilizer, and harvesting advice.
Provides Malawi-specific crop recommendations with Neo4j knowledge integration.
"""
from typing import Dict, Any, List
import logging

from app.models.ollama_model import OllamaModel
from app.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class CropAgent:
    """
    Crop advisory agent for Malawi farmers.
    Provides expert advice on crop selection, planting, fertilization, and harvesting.
    """
    
    def __init__(self):
        self.llm = OllamaModel()
        self.neo4j = Neo4jClient()
        
        # Crop advisory system prompt
        self.system_prompt = """You are an expert agricultural agronomist specializing in Malawi's crops.
You can:
- Recommend suitable crop varieties for Malawi conditions
- Provide planting and harvesting guidance
- Advise on fertilizer schedules and soil management
- Suggest pest prevention strategies
- Recommend crop rotation patterns

Use Malawi-specific knowledge:
- Local crop varieties and their performance
- Regional soil types and nutrient needs
- Climate-appropriate planting schedules
- Smallholder farmer constraints and resources
- Market preferences and storage considerations

Always provide:
1. Crop variety recommendations with maturity periods
2. Planting guidance (spacing, timing, depth)
3. Fertilizer schedules (NPK ratios, application timing)
4. Harvesting advice and storage recommendations
5. Pest and disease prevention strategies
6. Yield optimization techniques

Be practical and consider farmer resources. Include local market knowledge."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process crop-related query with Neo4j knowledge integration.
        
        Args:
            message: User's crop-related question
            context: Conversation history and farmer context
            
        Returns:
            Crop advisory with expert recommendations
        """
        try:
            # Analyze crop intent and extract entities
            crop_analysis = self._analyze_crop_intent(message)
            
            # Retrieve relevant knowledge from Neo4j
            neo4j_knowledge = await self._retrieve_crop_knowledge(crop_analysis)
            
            # Build crop advisory prompt with context and Neo4j data
            crop_prompt = self._build_crop_prompt(message, crop_analysis, neo4j_knowledge, context)
            
            # Generate expert crop advice
            crop_response = await self.llm.generate(
                crop_prompt,
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            # Extract structured information
            structured_result = self._structure_crop_response(crop_response)
            
            return {
                "response": crop_response,
                "confidence": structured_result.get("confidence", 0.8),
                "sources": structured_result.get("sources", []),
                "context": {
                    "crop_type": crop_analysis.get("crop_type"),
                    "advisory_type": crop_analysis.get("advisory_type"),
                    "neo4j_entities": neo4j_knowledge.get("entities", []),
                    "recommendations": structured_result.get("recommendations", []),
                    "analysis": f"Analyzed {crop_analysis.get('advisory_type')} for {crop_analysis.get('crop_type', 'unknown')}"
                }
            }
            
        except Exception as e:
            logger.error(f"CropAgent processing error: {e}")
            return {
                "response": "I'm having trouble providing crop advice. Could you specify which crop you're asking about and what type of guidance you need (variety, planting, fertilizer, or harvesting)?",
                "confidence": 0.4,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    def _analyze_crop_intent(self, message: str) -> Dict[str, Any]:
        """
        Analyze message for crop-related intent and entities.
        
        Args:
            message: User's crop-related question
            
        Returns:
            Crop intent analysis with entities
        """
        message_lower = message.lower()
        
        # Crop types mentioned
        crop_types = {
            "maize": ["maize", "corn", "chimanga", "nsima"],
            "tomato": ["tomato", "tomatoes", "nyanya"],
            "cabbage": ["cabbage", "mbewa", "kale"],
            "groundnuts": ["groundnut", "peanut", "nthochi"],
            "soybeans": ["soybean", "soya", "soy"],
            "tobacco": ["tobacco", "fodya", "burley"],
            "cassava": ["cassava", "manioc", "chimondela"],
            "rice": ["rice", "paddy", "mawa"]
        }
        
        detected_crop = None
        for crop, synonyms in crop_types.items():
            for synonym in synonyms:
                if synonym in message_lower:
                    detected_crop = crop
                    break
        
        # Advisory types
        advisory_patterns = {
            "variety": ["variety", "type", "breed", "hybrid", "seed"],
            "planting": ["plant", "sow", "seed", "transplant", "spacing", "depth"],
            "fertilizer": ["fertilizer", "nutrient", "npk", "manure", "urea", "can"],
            "harvesting": ["harvest", "ready", "mature", "yield", "storage"],
            "soil": ["soil", "ph", "organic", "preparation"],
            "rotation": ["rotate", "rotation", "follow", "sequence"]
        }
        
        detected_advisory = []
        for advisory_type, patterns in advisory_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    detected_advisory.append(advisory_type)
        
        # Determine primary advisory type
        primary_advisory = "general"
        if detected_advisory:
            primary_advisory = detected_advisory[0]  # First detected
        
        return {
            "crop_type": detected_crop,
            "advisory_type": primary_advisory,
            "all_advisories": detected_advisory,
            "entities": self._extract_entities(message_lower),
            "complexity": len(detected_advisory)
        }
    
    def _extract_entities(self, message: str) -> List[str]:
        """Extract specific entities from message."""
        entities = []
        
        # Numbers and measurements
        import re
        numbers = re.findall(r'\d+', message)
        if numbers:
            entities.extend([f"numbers: {', '.join(numbers)}"])
        
        # Specific terms
        terms = ["kg", "bags", "hectares", "acres", "weeks", "days", "months"]
        for term in terms:
            if term in message:
                entities.append(term)
        
        return entities
    
    async def _retrieve_crop_knowledge(self, crop_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve crop-specific knowledge from Neo4j.
        
        Args:
            crop_analysis: Crop intent analysis
            
        Returns:
            Neo4j knowledge entities and relationships
        """
        try:
            crop_type = crop_analysis.get("crop_type")
            if not crop_type:
                return {"entities": [], "relationships": []}
            
            # Query Neo4j for crop information
            crop_query = """
            MATCH (c:Crop {name: $crop_name})
            OPTIONAL MATCH (c)-[:HAS_VARIETY]->(v:Variety)
            OPTIONAL MATCH (c)-[:SUSCEPTIBLE_TO]->(d:Disease)
            OPTIONAL MATCH (c)-[:REQUIRES]->(f:Fertilizer)
            OPTIONAL MATCH (c)-[:AFFECTED_BY]->(p:Pest)
            OPTIONAL MATCH (c)-[:USES_METHOD]->(m:FarmingMethod)
            RETURN c, v, d, f, p, m
            """
            
            result = self.neo4j.execute_query(crop_query, {"crop_name": crop_type.capitalize()})
            
            # Process results
            entities = []
            relationships = []
            
            if result:
                for record in result:
                    if record.get("c"):
                        entities.append({
                            "type": "crop",
                            "name": record["c"].get("name"),
                            "properties": record["c"]
                        })
                    
                    if record.get("v"):
                        entities.append({
                            "type": "variety",
                            "name": record["v"].get("name"),
                            "properties": record["v"]
                        })
                        relationships.append({
                            "from": "crop",
                            "to": "variety",
                            "type": "HAS_VARIETY"
                        })
                    
                    if record.get("d"):
                        entities.append({
                            "type": "disease",
                            "name": record["d"].get("name"),
                            "properties": record["d"]
                        })
                        relationships.append({
                            "from": "crop",
                            "to": "disease",
                            "type": "SUSCEPTIBLE_TO"
                        })
                    
                    if record.get("f"):
                        entities.append({
                            "type": "fertilizer",
                            "name": record["f"].get("name"),
                            "properties": record["f"]
                        })
                        relationships.append({
                            "from": "crop",
                            "to": "fertilizer",
                            "type": "REQUIRES"
                        })
            
            return {
                "entities": entities,
                "relationships": relationships,
                "query_results": result
            }
            
        except Exception as e:
            logger.error(f"Neo4j retrieval error: {e}")
            return {"entities": [], "relationships": []}
    
    def _build_crop_prompt(
        self,
        message: str,
        crop_analysis: Dict[str, Any],
        neo4j_knowledge: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> str:
        """
        Build crop advisory prompt with analysis and Neo4j knowledge.
        
        Args:
            message: Original user message
            crop_analysis: Crop intent analysis
            neo4j_knowledge: Knowledge from Neo4j
            context: Conversation context
            
        Returns:
            Formatted crop advisory prompt
        """
        # Get conversation history if available
        history_text = ""
        if context and context.get("history"):
            recent_history = context["history"][-2:]  # Last 2 exchanges
            history_text = "Recent conversation context:\n"
            for exchange in recent_history:
                history_text += f"User: {exchange.get('user', '')}\n"
                history_text += f"Assistant: {exchange.get('assistant', '')}\n\n"
        
        # Format Neo4j knowledge
        knowledge_text = "Available knowledge from database:\n"
        entities = neo4j_knowledge.get("entities", [])
        for entity in entities:
            knowledge_text += f"- {entity.get('type', 'unknown')}: {entity.get('name', 'unknown')}\n"
        
        prompt = f"""{history_text}
Current farmer query: {message}

Crop analysis: {crop_analysis.get('advisory_type')} advice for {crop_analysis.get('crop_type', 'unknown')}

{knowledge_text}

Please provide expert Malawi crop advice:
1. Recommend specific varieties if asking about varieties
2. Provide detailed planting guidance (spacing, timing, depth)
3. Suggest fertilizer schedules with NPK ratios
4. Recommend harvesting and storage practices
5. Include pest and disease prevention
6. Consider smallholder farmer resources
7. Use Malawi-specific knowledge and local conditions

Be practical and actionable. Include specific measurements and timing."""
        
        return prompt
    
    def _structure_crop_response(self, response: str) -> Dict[str, Any]:
        """
        Structure crop response into components.
        
        Args:
            response: LLM crop response
            
        Returns:
            Structured crop information
        """
        response_lower = response.lower()
        
        # Extract recommendations
        recommendations = []
        recommendation_patterns = [
            "plant", "use", "apply", "recommend", "suggest", "consider"
        ]
        for pattern in recommendation_patterns:
            if pattern in response_lower:
                # Extract surrounding text for context
                words = response_lower.split()
                for i, word in enumerate(words):
                    if word == pattern and i + 1 < len(words):
                        recommendations.append(f"{word} {words[i + 1]}")
        
        # Extract confidence indicators
        confidence = 0.8  # Default confidence
        if "high confidence" in response_lower or "certain" in response_lower:
            confidence = 0.9
        elif "moderate confidence" in response_lower or "likely" in response_lower:
            confidence = 0.7
        elif "low confidence" in response_lower or "possible" in response_lower:
            confidence = 0.6
        
        # Extract specific advice types
        advice_types = []
        if "variety" in response_lower or "type" in response_lower:
            advice_types.append("variety_recommendation")
        if "plant" in response_lower or "sow" in response_lower:
            advice_types.append("planting_guidance")
        if "fertilizer" in response_lower or "nutrient" in response_lower:
            advice_types.append("fertilizer_schedule")
        if "harvest" in response_lower or "yield" in response_lower:
            advice_types.append("harvesting_advice")
        
        return {
            "recommendations": recommendations,
            "confidence": confidence,
            "advice_types": advice_types,
            "sources": ["neo4j_knowledge_graph", "malawi_crop_database", "expert_agronomy"]
        }
