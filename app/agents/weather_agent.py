"""
Weather Agent - Provides weather forecasts and climate-related agricultural advice.
Helps farmers make weather-informed decisions.
"""
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta

from app.models.ollama_model import OllamaModel

logger = logging.getLogger(__name__)


class WeatherAgent:
    """
    Specialized agent for weather and climate-related queries.
    Provides forecasts and weather-based agricultural recommendations.
    """
    
    def __init__(self):
        self.llm = OllamaModel()
        
        # System prompt for weather expertise
        self.system_prompt = """You are a weather and climate expert for agricultural planning in Malawi.
Your expertise includes:
- Seasonal weather patterns in Malawi
- Rainfall forecasting and interpretation
- Drought and flood preparedness
- Best planting times based on weather
- Weather-related crop management

Provide practical advice based on Malawi's climate patterns:
- Rainy season: November to April
- Dry season: May to October
- Peak rainfall: January to February

Always tie weather information to actionable agricultural advice."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a weather-related query.
        
        Args:
            message: User's query about weather
            context: Additional context (location, season, etc.)
            
        Returns:
            Response with weather advice
        """
        try:
            # Analyze weather needs
            weather_analysis = self._analyze_weather_needs(message)
            
            # Get location context
            location = context.get("location") if context else None
            
            # Build prompt with weather context
            prompt = self._build_prompt(message, weather_analysis, location)
            
            # Generate response
            response = await self.llm.generate(
                prompt,
                system_prompt=self.system_prompt
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(weather_analysis)
            
            return {
                "response": response,
                "confidence": confidence,
                "sources": [
                    {
                        "type": "weather_knowledge",
                        "description": "Malawi seasonal patterns and climate data"
                    }
                ],
                "context": {
                    "weather_focus": weather_analysis.get("focus"),
                    "current_season": self._get_current_season(),
                    "location": location
                }
            }
            
        except Exception as e:
            logger.error(f"WeatherAgent processing error: {e}")
            return {
                "response": "I apologize, but I'm having trouble providing weather advice right now. Please try again with more specific weather questions.",
                "confidence": 0.0,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    def _analyze_weather_needs(self, query: str) -> Dict[str, Any]:
        """
        Analyze what weather information the user needs.
        
        Args:
            query: User query
            
        Returns:
            Analysis of weather needs
        """
        query_lower = query.lower()
        
        # Weather focus areas
        focus_areas = {
            "forecast": ["forecast", "predict", "will it rain", "tomorrow", "next week"],
            "season": ["season", "rainy season", "dry season", "planting season"],
            "rainfall": ["rain", "rainfall", "precipitation", "wet", "dry spell"],
            "drought": ["drought", "water shortage", "no rain", "dry period"],
            "temperature": ["temperature", "hot", "cold", "heat", "frost"],
            "planting": ["when to plant", "best time to plant", "planting time"],
            "harvest": ["harvest", "when to harvest", "drying"]
        }
        
        detected_focus = []
        for focus, keywords in focus_areas.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_focus.append(focus)
        
        # Determine urgency
        urgent_keywords = ["now", "today", "urgent", "immediate", "should I"]
        is_urgent = any(kw in query_lower for kw in urgent_keywords)
        
        # Determine timeframe
        timeframe = self._determine_timeframe(query_lower)
        
        return {
            "focus": detected_focus,
            "urgent": is_urgent,
            "timeframe": timeframe
        }
    
    def _determine_timeframe(self, query: str) -> str:
        """
        Determine the timeframe of the weather query.
        
        Args:
            query: User query (lowercase)
            
        Returns:
            Timeframe description
        """
        if any(word in query for word in ["tomorrow", "today", "now"]):
            return "immediate"
        elif any(word in query for word in ["next week", "coming week", "this week"]):
            return "short_term"
        elif any(word in query for word in ["next month", "coming month", "season"]):
            return "seasonal"
        elif any(word in query for word in ["year", "annual", "long term"]):
            return "long_term"
        else:
            return "general"
    
    def _get_current_season(self) -> Dict[str, Any]:
        """
        Get current season information for Malawi.
        
        Returns:
            Season information
        """
        current_month = datetime.now().month
        
        # Malawi seasons
        if 11 <= current_month <= 4:
            season = "rainy"
            season_name = "Rainy Season"
            activities = ["Planting", "Weeding", "Top dressing"]
        else:
            season = "dry"
            season_name = "Dry Season"
            activities = ["Harvesting", "Drying", "Storage", "Land preparation"]
        
        return {
            "name": season_name,
            "type": season,
            "month": current_month,
            "typical_activities": activities
        }
    
    def _build_prompt(
        self,
        message: str,
        analysis: Dict[str, Any],
        location: str = None
    ) -> str:
        """
        Build prompt with weather context.
        
        Args:
            message: User message
            analysis: Weather analysis
            location: Optional location
            
        Returns:
            Formatted prompt
        """
        season_info = self._get_current_season()
        
        context_text = f"Current season: {season_info['name']}\n"
        context_text += f"Typical activities: {', '.join(season_info['typical_activities'])}\n"
        
        if location:
            context_text += f"Location: {location}\n"
        
        if analysis.get("focus"):
            context_text += f"Weather focus: {', '.join(analysis['focus'])}\n"
        
        if analysis.get("urgent"):
            context_text += "This appears to be an urgent weather-related decision.\n"
        
        prompt = f"""{context_text}

Farmer's question: {message}

Provide weather-informed agricultural advice. Consider Malawi's climate patterns and give practical recommendations."""
        
        return prompt
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence score.
        
        Args:
            analysis: Weather analysis
            
        Returns:
            Confidence score (0-1)
        """
        base_confidence = 0.6
        
        # Increase confidence with clear focus
        if analysis.get("focus"):
            base_confidence += min(len(analysis["focus"]) * 0.05, 0.15)
        
        # General weather advice is reasonably reliable for seasonal patterns
        return min(base_confidence, 0.85)
