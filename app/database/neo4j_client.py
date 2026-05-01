"""
Neo4j Client - Database connection and query execution.
Handles all interactions with the Neo4j knowledge graph.
"""
from typing import Dict, Any, List, Optional
import logging

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.config import neo4j_config

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Client for Neo4j graph database operations.
    Manages connections and executes Cypher queries.
    """
    
    def __init__(self):
        self.uri = neo4j_config.uri
        self.user = neo4j_config.user
        self.password = neo4j_config.password
        self.database = neo4j_config.database
        self._driver: Optional[Driver] = None
    
    def _get_driver(self) -> Driver:
        """
        Get or create Neo4j driver instance.
        
        Returns:
            Neo4j Driver
        """
        if self._driver is None or self._driver.closed():
            try:
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password)
                )
                logger.info("Neo4j driver initialized successfully")
            except Exception as e:
                logger.error(f"Failed to create Neo4j driver: {e}")
                raise
        
        return self._driver
    
    def verify_connection(self) -> bool:
        """
        Verify database connection is working.
        
        Returns:
            True if connection successful
        """
        try:
            driver = self._get_driver()
            with driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                return record and record["test"] == 1
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False
    
    def execute_query(
        self,
        query: str,
        parameters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of records as dictionaries
        """
        parameters = parameters or {}
        
        try:
            driver = self._get_driver()
            
            with driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                
                # Convert records to list of dictionaries
                records = []
                for record in result:
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        # Handle Neo4j types
                        if hasattr(value, "items"):  # Node or Relationship
                            record_dict[key] = dict(value.items())
                        else:
                            record_dict[key] = value
                    records.append(record_dict)
                
                return records
                
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            return []
        except Neo4jError as e:
            logger.error(f"Neo4j error executing query: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            return []
    
    def execute_write(
        self,
        query: str,
        parameters: Dict[str, Any] = None
    ) -> bool:
        """
        Execute a write query (CREATE, MERGE, etc.).
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            True if successful
        """
        parameters = parameters or {}
        
        try:
            driver = self._get_driver()
            
            with driver.session(database=self.database) as session:
                with session.begin_transaction() as tx:
                    tx.run(query, parameters)
                    return True
                    
        except Exception as e:
            logger.error(f"Error executing write query: {e}")
            return False
    
    def create_indexes(self) -> bool:
        """
        Create necessary database indexes.
        
        Returns:
            True if successful
        """
        indexes = [
            "CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.id)",
            "CREATE INDEX session_id_index IF NOT EXISTS FOR (s:Session) ON (s.id)",
            "CREATE INDEX message_id_index IF NOT EXISTS FOR (m:Message) ON (m.id)",
            "CREATE INDEX crop_name_index IF NOT EXISTS FOR (c:Crop) ON (c.name)",
            "CREATE INDEX variety_name_index IF NOT EXISTS FOR (v:Variety) ON (v.name)",
            "CREATE INDEX disease_name_index IF NOT EXISTS FOR (d:Disease) ON (d.name)",
            "CREATE INDEX document_id_index IF NOT EXISTS FOR (d:Document) ON (d.id)"
        ]
        
        try:
            for index_query in indexes:
                self.execute_query(index_query)
            
            logger.info("Database indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return False
    
    def close(self):
        """Close database connection."""
        if self._driver and not self._driver.closed():
            self._driver.close()
            logger.info("Neo4j connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
