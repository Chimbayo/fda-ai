"""
Conversation Memory and Farmer Profile System.
Manages conversation history and farmer profiles for personalized responses.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Conversation memory system for FDA-AI.
    Provides conversation persistence and farmer profile management.
    """
    
    def __init__(self):
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.farmer_profiles: Dict[str, Dict[str, Any]] = {}
        self.max_conversation_length = 20  # Keep last 20 exchanges
        self.max_profile_age_days = 30  # Update profiles every 30 days
    
    async def add_message(
        self,
        user_id: str,
        message: str,
        response: str,
        agent_type: str,
        confidence: float,
        sources: List[str] = None
    ) -> bool:
        """
        Add message to conversation history.
        
        Args:
            user_id: Farmer identifier
            message: User's message
            response: Assistant's response
            agent_type: Type of agent that responded
            confidence: Response confidence
            sources: Knowledge sources used
            
        Returns:
            Success status
        """
        try:
            # Initialize conversation if not exists
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            
            # Create conversation entry
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "assistant_response": response,
                "agent_type": agent_type,
                "confidence": confidence,
                "sources": sources or [],
                "session_id": self._generate_session_id()
            }
            
            # Add to conversation history
            self.conversations[user_id].append(conversation_entry)
            
            # Trim conversation if too long
            if len(self.conversations[user_id]) > self.max_conversation_length:
                self.conversations[user_id] = self.conversations[user_id][-self.max_conversation_length:]
            
            # Update farmer profile
            await self._update_farmer_profile(user_id, message, response, agent_type)
            
            logger.info(f"Added message to conversation for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Memory add error: {e}")
            return False
    
    async def get_conversation_context(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Get conversation context for agent processing.
        
        Args:
            user_id: Farmer identifier
            limit: Number of recent exchanges to return
            
        Returns:
            Conversation context with history and profile
        """
        try:
            # Get conversation history
            history = self.conversations.get(user_id, [])
            recent_history = history[-limit:] if history else []
            
            # Get farmer profile
            profile = self.farmer_profiles.get(user_id, {})
            
            return {
                "history": recent_history,
                "profile": profile,
                "conversation_count": len(history),
                "last_interaction": history[-1] if history else None
            }
            
        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
            return {"history": [], "profile": {}}
    
    async def update_farmer_profile(
        self,
        user_id: str,
        message: str,
        response: str,
        agent_type: str
    ) -> bool:
        """
        Update farmer profile based on interaction.
        
        Args:
            user_id: Farmer identifier
            message: User's message
            response: Assistant's response
            agent_type: Agent type used
            
        Returns:
            Success status
        """
        try:
            # Initialize profile if not exists
            if user_id not in self.farmer_profiles:
                self.farmer_profiles[user_id] = {
                    "created_at": datetime.now().isoformat(),
                    "interaction_count": 0,
                    "preferred_topics": [],
                    "location": None,
                    "crop_focus": None,
                    "experience_level": "unknown"
                }
            
            profile = self.farmer_profiles[user_id]
            
            # Update interaction count
            profile["interaction_count"] += 1
            profile["last_interaction"] = datetime.now().isoformat()
            
            # Extract topics and preferences from message
            topics = self._extract_topics(message)
            profile["preferred_topics"] = list(set(profile["preferred_topics"] + topics))
            
            # Update crop focus if mentioned
            crop_keywords = ["maize", "tomato", "cabbage", "groundnut", "soybean"]
            if any(crop in message.lower() for crop in crop_keywords):
                for crop in crop_keywords:
                    if crop in message.lower():
                        profile["crop_focus"] = crop
                        break
            
            # Update experience level based on interaction complexity
            if agent_type in ["disease", "crop"] and len(message) > 50:
                profile["experience_level"] = "intermediate"
            elif agent_type in ["disease", "crop"] and len(message) > 100:
                profile["experience_level"] = "advanced"
            
            # Store updated profile
            self.farmer_profiles[user_id] = profile
            
            logger.info(f"Updated profile for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            return False
    
    def _extract_topics(self, message: str) -> List[str]:
        """Extract topics from user message."""
        topics = []
        
        # Topic keywords
        topic_patterns = {
            "crops": ["maize", "tomato", "cabbage", "planting", "harvest"],
            "diseases": ["disease", "pest", "blight", "wilt", "treatment"],
            "weather": ["rain", "climate", "season", "weather"],
            "fertilizer": ["fertilizer", "nutrient", "soil", "npk"],
            "general": ["help", "what", "how", "information"]
        }
        
        message_lower = message.lower()
        for topic, keywords in topic_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
        
        return list(set(topics))  # Remove duplicates
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier."""
        import uuid
        return str(uuid.uuid4())[:8]  # Short session ID
    
    async def get_farmer_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get farmer profile summary for context.
        
        Args:
            user_id: Farmer identifier
            
        Returns:
            Farmer profile summary
        """
        try:
            profile = self.farmer_profiles.get(user_id, {})
            history = self.conversations.get(user_id, [])
            
            if not profile:
                return {"status": "no_profile"}
            
            # Calculate interaction statistics
            recent_interactions = history[-10:]  # Last 10 interactions
            agent_usage = {}
            for interaction in recent_interactions:
                agent = interaction.get("agent_type", "unknown")
                agent_usage[agent] = agent_usage.get(agent, 0) + 1
            
            return {
                "profile": profile,
                "interaction_stats": {
                    "total_interactions": len(history),
                    "recent_interactions": len(recent_interactions),
                    "agent_usage": agent_usage
                },
                "preferences": {
                    "preferred_topics": profile.get("preferred_topics", []),
                    "crop_focus": profile.get("crop_focus"),
                    "experience_level": profile.get("experience_level", "unknown")
                }
            }
            
        except Exception as e:
            logger.error(f"Summary retrieval error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def clear_conversation(self, user_id: str) -> bool:
        """
        Clear conversation history for a user.
        
        Args:
            user_id: Farmer identifier
            
        Returns:
            Success status
        """
        try:
            if user_id in self.conversations:
                self.conversations[user_id] = []
                logger.info(f"Cleared conversation for user {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Clear conversation error: {e}")
            return False
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.
        
        Returns:
            Memory statistics
        """
        try:
            total_conversations = sum(len(conv) for conv in self.conversations.values())
            total_profiles = len(self.farmer_profiles)
            
            return {
                "total_users": total_profiles,
                "total_conversations": total_conversations,
                "average_conversations_per_user": total_conversations / total_profiles if total_profiles > 0 else 0,
                "memory_usage_mb": self._estimate_memory_usage(),
                "max_conversation_length": self.max_conversation_length
            }
            
        except Exception as e:
            logger.error(f"Memory stats error: {e}")
            return {"error": str(e)}
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        try:
            # Rough estimation of memory usage
            import sys
            import pickle
            
            # Serialize current data to estimate size
            data_size = len(json.dumps({
                "conversations": self.conversations,
                "profiles": self.farmer_profiles
            }))
            
            return data_size / (1024 * 1024)  # Convert to MB
            
        except Exception:
            return 0.0
    
    async def export_conversation_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export conversation data for analysis.
        
        Args:
            user_id: Farmer identifier
            
        Returns:
            Exportable conversation data
        """
        try:
            history = self.conversations.get(user_id, [])
            profile = self.farmer_profiles.get(user_id, {})
            
            return {
                "user_id": user_id,
                "conversation_history": history,
                "farmer_profile": profile,
                "export_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return {"error": str(e)}
    
    def get_recent_conversations(self, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get recent conversations across all users.
        
        Args:
            limit: Number of recent conversations per user
            
        Returns:
            Recent conversations by user
        """
        recent = {}
        for user_id, history in self.conversations.items():
            if history:
                recent[user_id] = history[-limit:]
        
        return recent
