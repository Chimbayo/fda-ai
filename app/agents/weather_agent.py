"""
Weather & Seasonal Advisory Agent - Handles climate patterns and seasonal farming advice.
Provides Malawi-specific weather information and planting recommendations.
"""
from typing import Dict, Any, List
import logging
import os

from app.models.ollama_model import OllamaModel
from app.models.openai_model import OpenAIModel

logger = logging.getLogger(__name__)


class WeatherAgent:
    """
    Weather and seasonal advisory agent for Malawi farmers.
    Provides climate patterns, rainfall data, and seasonal planting recommendations.
    """
    
    def __init__(self):
        # Use OpenAI if API key is available, otherwise fall back to Ollama
        if os.getenv("OPENAI_API_KEY"):
            self.llm = OpenAIModel()
            logger.info("WeatherAgent using OpenAI model")
        else:
            self.llm = OllamaModel()
            logger.info("WeatherAgent using Ollama model")
        
        # Weather advisory system prompt
        self.system_prompt = """You are an expert agricultural meteorologist specializing in Malawi's climate patterns.
You can:
- Analyze seasonal weather patterns and rainfall
- Provide planting window recommendations
- Advise on drought and flood mitigation
- Recommend climate-appropriate crops
- Predict weather-related risks

Use Malawi-specific knowledge:
- Regional climate zones (Northern, Central, Southern)
- Rainfall patterns (October-April main rains)
- Temperature variations by altitude
- Common weather risks (droughts, floods, dry spells)
- Smallholder farmer adaptation strategies

Always provide:
1. Current seasonal analysis
2. Planting/harvesting timing recommendations
3. Weather risk assessments
4. Mitigation strategies
5. Regional climate considerations

Be practical and specific to Malawi's agricultural calendar."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process weather-related query with Malawi climate expertise.
        
        Args:
            message: User's weather-related question
            context: Conversation history and farmer context
            
        Returns:
            Weather advisory with seasonal recommendations
        """
        try:
            # Analyze weather patterns and intent
            weather_analysis = self._analyze_weather_intent(message)
            
            # Build weather advisory prompt with context
            weather_prompt = self._build_weather_prompt(message, weather_analysis, context)
            
            # Generate expert weather advice
            weather_response = await self.llm.generate(
                weather_prompt,
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            # Extract structured information
            structured_result = self._structure_weather_response(weather_response)
            
            return {
                "response": weather_response,
                "confidence": structured_result.get("confidence", 0.8),
                "sources": structured_result.get("sources", []),
                "context": {
                    "weather_type": weather_analysis.get("type"),
                    "season": structured_result.get("season"),
                    "region": structured_result.get("region"),
                    "recommendations": structured_result.get("recommendations", []),
                    "analysis": f"Analyzed {weather_analysis.get('type')} weather pattern for Malawi"
                }
            }
            
        except Exception as e:
            logger.error(f"WeatherAgent processing error: {e}")
            return {
                "response": "I'm having trouble analyzing the weather information. Could you specify which region of Malawi you're asking about and what type of weather guidance you need?",
                "confidence": 0.4,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    def _analyze_weather_intent(self, message: str) -> Dict[str, Any]:
        """
        Analyze message for weather-related intent and patterns.
        
        Args:
            message: User's weather-related question
            
        Returns:
            Weather intent analysis
        """
        message_lower = message.lower()
        
        # Weather pattern keywords
        weather_patterns = {
            "seasonal": ["season", "planting", "harvest", "when", "time", "calendar"],
            "rainfall": ["rain", "rainfall", "wet", "dry", "drought", "flood"],
            "temperature": ["temperature", "hot", "cold", "heat", "climate"],
            "regional": ["region", "area", "zone", "north", "south", "central"],
            "prediction": ["forecast", "predict", "expect", "coming", "trend"]
        }
        
        detected_patterns = []
        for category, patterns in weather_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    detected_patterns.append({
                        "category": category,
                        "pattern": pattern
                    })
        
        # Determine primary intent
        intent_type = "general"
        if any(p["category"] == "seasonal" for p in detected_patterns):
            intent_type = "seasonal_advisory"
        elif any(p["category"] == "rainfall" for p in detected_patterns):
            intent_type = "rainfall_analysis"
        elif any(p["category"] == "temperature" for p in detected_patterns):
            intent_type = "temperature_analysis"
        elif any(p["category"] == "regional" for p in detected_patterns):
            intent_type = "regional_climate"
        elif any(p["category"] == "prediction" for p in detected_patterns):
            intent_type = "weather_prediction"
        
        return {
            "type": intent_type,
            "patterns": detected_patterns,
            "complexity": len(detected_patterns)
        }
    
    def _build_weather_prompt(
        self,
        message: str,
        weather_analysis: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> str:
        """
        Build weather advisory prompt with analysis and context.
        
        Args:
            message: Original user message
            weather_analysis: Weather intent analysis
            context: Conversation context
            
        Returns:
            Formatted weather advisory prompt
        """
        # Get conversation history if available
        history_text = ""
        if context and context.get("history"):
            recent_history = context["history"][-2:]  # Last 2 exchanges
            history_text = "Recent conversation context:\n"
            for exchange in recent_history:
                history_text += f"User: {exchange.get('user', '')}\n"
                history_text += f"Assistant: {exchange.get('assistant', '')}\n\n"
        
        # Format weather patterns
        patterns_text = "Detected weather patterns:\n"
        for pattern in weather_analysis.get("patterns", []):
            patterns_text += f"- {pattern.get('pattern', 'unknown')} ({pattern.get('category', 'unknown')})\n"
        
        prompt = f"""{history_text}
Current farmer query: {message}

{patterns_text}

Weather intent type: {weather_analysis.get('type')}

Please provide expert Malawi weather advisory:
1. Analyze seasonal patterns and rainfall expectations
2. Recommend optimal planting/harvesting windows
3. Assess weather-related risks (drought, flood, temperature)
4. Suggest climate-appropriate farming strategies
5. Consider regional variations (Northern, Central, Southern Malawi)

Include specific:
- Expected rainfall patterns by month
- Temperature considerations by altitude
- Risk mitigation for smallholder farmers
- Traditional weather knowledge integration"""
        
        return prompt
    
    def _structure_weather_response(self, response: str) -> Dict[str, Any]:
        """
        Structure weather response into components.
        
        Args:
            response: LLM weather response
            
        Returns:
            Structured weather information
        """
        response_lower = response.lower()
        
        # Extract season information
        seasons = ["planting season", "growing season", "harvest season", "dry season", "rainy season"]
        detected_season = None
        for season in seasons:
            if season in response_lower:
                detected_season = season
                break
        
        # Extract region information
        regions = ["northern", "central", "southern", "lilongwe", "blantyre", "mzuzu"]
        detected_region = None
        for region in regions:
            if region in response_lower:
                detected_region = region
                break
        
        # Extract recommendations
        recommendations = []
        recommendation_keywords = ["plant", "harvest", "prepare", "monitor", "irrigate", "protect"]
        for keyword in recommendation_keywords:
            if keyword in response_lower:
                recommendations.append(keyword)
        
        # Determine confidence
        confidence = 0.8  # Default confidence
        if "high confidence" in response_lower or "certain" in response_lower:
            confidence = 0.9
        elif "moderate confidence" in response_lower or "likely" in response_lower:
            confidence = 0.7
        elif "low confidence" in response_lower or "possible" in response_lower:
            confidence = 0.6
        
        return {
            "season": detected_season,
            "region": detected_region,
            "recommendations": recommendations,
            "confidence": confidence,
            "sources": ["malawi_meteorological_data", "agricultural_calendar", "farmer_knowledge"]
        }
