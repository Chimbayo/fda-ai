"""
Memory Store - Manages conversation history and user context.
Uses Neo4j for persistent storage of conversations.
"""
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.database.neo4j_client import Neo4jClient
from app.config import app_config

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation history using Neo4j.
    Stores and retrieves user conversations for context awareness.
    """
    
    def __init__(self):
        self.db = Neo4jClient()
        self.max_history = app_config.max_conversation_history
    
    def add_message(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        ai_response: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Add a message exchange to conversation history.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            user_message: User's message
            ai_response: AI's response
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        try:
            timestamp = datetime.now().isoformat()
            
            cypher_query = """
            MERGE (u:User {id: $user_id})
            MERGE (s:Session {id: $session_id, user_id: $user_id})
            MERGE (u)-[:HAS_SESSION]->(s)
            CREATE (m:Message {
                id: $message_id,
                user_message: $user_message,
                ai_response: $ai_response,
                timestamp: $timestamp,
                metadata: $metadata
            })
            MERGE (s)-[:CONTAINS]->(m)
            WITH s
            MATCH (s)-[:CONTAINS]->(old:Message)
            WITH s, old
            ORDER BY old.timestamp DESC
            SKIP $max_history
            DETACH DELETE old
            """
            
            message_id = f"{session_id}_{timestamp}"
            
            self.db.execute_query(cypher_query, {
                "user_id": user_id,
                "session_id": session_id,
                "message_id": message_id,
                "user_message": user_message,
                "ai_response": ai_response,
                "timestamp": timestamp,
                "metadata": str(metadata or {}),
                "max_history": self.max_history
            })
            
            logger.debug(f"Added message for user {user_id}, session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message to memory: {e}")
            return False
    
    def get_history(
        self,
        user_id: str,
        session_id: str = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a user.
        
        Args:
            user_id: User identifier
            session_id: Optional specific session
            limit: Maximum number of messages
            
        Returns:
            List of conversation exchanges
        """
        try:
            if limit is None:
                limit = self.max_history
            
            if session_id:
                # Get specific session history
                cypher_query = """
                MATCH (s:Session {id: $session_id})-[:CONTAINS]->(m:Message)
                RETURN m.user_message as user_message,
                       m.ai_response as ai_response,
                       m.timestamp as timestamp,
                       m.metadata as metadata
                ORDER BY m.timestamp ASC
                LIMIT $limit
                """
                
                results = self.db.execute_query(cypher_query, {
                    "session_id": session_id,
                    "limit": limit
                })
            else:
                # Get recent history across all sessions
                cypher_query = """
                MATCH (u:User {id: $user_id})-[:HAS_SESSION]->(s:Session)
                MATCH (s)-[:CONTAINS]->(m:Message)
                RETURN m.user_message as user_message,
                       m.ai_response as ai_response,
                       m.timestamp as timestamp,
                       m.metadata as metadata,
                       s.id as session_id
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """
                
                results = self.db.execute_query(cypher_query, {
                    "user_id": user_id,
                    "limit": limit
                })
                
                # Reverse to get chronological order
                results.reverse()
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving history: {e}")
            return []
    
    def clear_history(self, user_id: str, session_id: str = None) -> bool:
        """
        Clear conversation history.
        
        Args:
            user_id: User identifier
            session_id: Optional specific session to clear
            
        Returns:
            Success status
        """
        try:
            if session_id:
                # Clear specific session
                cypher_query = """
                MATCH (s:Session {id: $session_id, user_id: $user_id})
                MATCH (s)-[:CONTAINS]->(m:Message)
                DETACH DELETE m
                """
                
                self.db.execute_query(cypher_query, {
                    "session_id": session_id,
                    "user_id": user_id
                })
            else:
                # Clear all user history
                cypher_query = """
                MATCH (u:User {id: $user_id})-[:HAS_SESSION]->(s:Session)
                MATCH (s)-[:CONTAINS]->(m:Message)
                DETACH DELETE m
                """
                
                self.db.execute_query(cypher_query, {"user_id": user_id})
            
            logger.info(f"Cleared history for user {user_id}, session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return False
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get user context and preferences from conversation history.
        
        Args:
            user_id: User identifier
            
        Returns:
            User context information
        """
        try:
            cypher_query = """
            MATCH (u:User {id: $user_id})
            OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session)
            OPTIONAL MATCH (s)-[:CONTAINS]->(m:Message)
            WITH u, count(DISTINCT s) as session_count, count(DISTINCT m) as message_count,
                 max(m.timestamp) as last_active
            RETURN session_count, message_count, last_active
            """
            
            results = self.db.execute_query(cypher_query, {"user_id": user_id})
            
            if results:
                return {
                    "user_id": user_id,
                    "session_count": results[0].get("session_count", 0),
                    "message_count": results[0].get("message_count", 0),
                    "last_active": results[0].get("last_active"),
                    "is_returning_user": results[0].get("message_count", 0) > 5
                }
            
            return {"user_id": user_id, "is_new_user": True}
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {"user_id": user_id}
