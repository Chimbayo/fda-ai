"""
Conversation Agent - Handles general conversation, greetings, and unclear queries.
Provides friendly interaction and clarifies user intent.
"""
from typing import Dict, Any, List
import logging

from app.models.ollama_model import OllamaModel

logger = logging.getLogger(__name__)


class ConversationAgent:
    """
    General conversation agent for handling greetings, chitchat,
    and queries that don't fit other specialized agents.
    Also helps clarify ambiguous user intents.
    """
    
    def __init__(self):
        self.llm = OllamaModel()
        
        # System prompt for friendly conversation
        self.system_prompt = """You are a friendly and helpful agricultural assistant for farmers in Malawi.
You can:
- Greet users warmly and professionally
- Answer general questions about the service
- Clarify ambiguous or unclear queries
- Direct users to the right type of help
- Provide encouragement and support

If a query seems agricultural but unclear, try to understand what the farmer needs help with.
Suggest specific ways you can help (crop advice, disease diagnosis, weather info, research findings).

Always be respectful of farmers' knowledge and experience. Use a conversational but professional tone."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a general conversation query.
        
        Args:
            message: User's message
            context: Conversation history and other context
            
        Returns:
            Friendly response with helpful guidance
        """
        try:
            # Analyze intent
            intent_analysis = self._analyze_intent(message)
            
            # Check if this might actually be a specific query in disguise
            if intent_analysis.get("potential_agricultural"):
                clarification = await self._offer_clarification(message)
                return clarification
            
            # Build prompt with context
            prompt = self._build_prompt(message, context, intent_analysis)
            
            # Generate response
            response = await self.llm.generate(
                prompt,
                system_prompt=self.system_prompt
            )
            
            return {
                "response": response,
                "confidence": 0.7,
                "sources": [],
                "context": {
                    "intent": intent_analysis.get("type"),
                    "is_greeting": intent_analysis.get("is_greeting", False),
                    "suggested_topics": intent_analysis.get("suggested_topics", [])
                }
            }
            
        except Exception as e:
            logger.error(f"ConversationAgent processing error: {e}")
            return {
                "response": "Hello! I'm your agricultural assistant. I can help you with crop advice, disease identification, weather information, or research findings. What would you like to know?",
                "confidence": 0.5,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """
        Analyze the intent of the user's message.
        
        Args:
            message: User message
            
        Returns:
            Intent analysis
        """
        message_lower = message.lower()
        
        # Greeting patterns
        greetings = [
            "hello", "hi", "hey", "good morning", "good afternoon",
            "good evening", "morning", "afternoon", "evening", "howdy"
        ]
        
        # Check for greeting
        is_greeting = any(greeting in message_lower for greeting in greetings)
        
        # Check if it might be agricultural despite being unclear
        agricultural_hints = [
            "plant", "grow", "field", "farm", "crop", "seed", "harvest",
            "problem", "issue", "sick", "dying", "yellow", "brown", "spots"
        ]
        
        potential_agricultural = any(hint in message_lower for hint in agricultural_hints)
        
        # Determine type
        if is_greeting:
            intent_type = "greeting"
        elif potential_agricultural:
            intent_type = "unclear_agricultural"
        elif any(word in message_lower for word in ["help", "what can you do", "how"]): 
            intent_type = "help_request"
        elif any(word in message_lower for word in ["thank", "thanks"]):
            intent_type = "gratitude"
        else:
            intent_type = "general"
        
        # Suggest topics if unclear
        suggested_topics = []
        if is_greeting or intent_type == "help_request":
            suggested_topics = [
                "Crop varieties and planting advice",
                "Disease and pest identification",
                "Weather and climate information",
                "Research findings and technical information"
            ]
        
        return {
            "type": intent_type,
            "is_greeting": is_greeting,
            "potential_agricultural": potential_agricultural,
            "suggested_topics": suggested_topics
        }
    
    async def _offer_clarification(self, message: str) -> Dict[str, Any]:
        """
        Offer clarification when query seems agricultural but unclear.
        
        Args:
            message: Unclear message
            
        Returns:
            Clarification response
        """
        clarification_prompt = f"""The user said: "{message}"

This message seems agricultural but is unclear. Generate a helpful response that:
1. Acknowledges what you understood
2. Asks clarifying questions to better help
3. Suggests what you can help with (crops, diseases, weather, research)

Be friendly and encouraging. The farmer might not know technical terms."""
        
        response = await self.llm.generate(
            clarification_prompt,
            system_prompt=self.system_prompt
        )
        
        return {
            "response": response,
            "confidence": 0.5,
            "sources": [],
            "context": {
                "intent": "needs_clarification",
                "suggested_topics": [
                    "Crop advice",
                    "Disease diagnosis",
                    "Weather information",
                    "Research information"
                ]
            }
        }
    
    def _build_prompt(
        self,
        message: str,
        context: Dict[str, Any],
        intent_analysis: Dict[str, Any]
    ) -> str:
        """
        Build prompt for conversation.
        
        Args:
            message: User message
            context: Conversation context
            intent_analysis: Intent analysis
            
        Returns:
            Formatted prompt
        """
        # Get conversation history if available
        history_text = ""
        if context and context.get("history"):
            recent_history = context["history"][-3:]  # Last 3 exchanges
            history_text = "Recent conversation:\n"
            for exchange in recent_history:
                history_text += f"User: {exchange.get('user', '')}\n"
                history_text += f"Assistant: {exchange.get('assistant', '')}\n\n"
        
        # Add suggestions if appropriate
        suggestions_text = ""
        if intent_analysis.get("suggested_topics"):
            suggestions_text = "\nAvailable topics I can help with:\n"
            for topic in intent_analysis["suggested_topics"]:
                suggestions_text += f"- {topic}\n"
        
        prompt = f"""{history_text}
User message: {message}

Detected intent: {intent_analysis.get('type')}
{ suggestions_text }

Generate an appropriate, friendly response."""
        
        return prompt
