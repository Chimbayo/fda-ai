"""
Knowledge Retrieval Agent - Handles graph-based search and ranking.
Provides intelligent retrieval from Neo4j with citation generation.
"""
from typing import Dict, Any, List
import logging

from app.models.ollama_model import OllamaModel
from app.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """
    Knowledge retrieval agent for graph-based search,
    ranking, and citation generation from Neo4j.
    """
    
    def __init__(self):
        self.llm = OllamaModel()
        self.neo4j = Neo4jClient()
        
        # Retrieval system prompt
        self.system_prompt = """You are an expert knowledge manager for Malawi's agricultural database.
You can:
- Search and retrieve agricultural knowledge from Neo4j graph
- Rank information by relevance and confidence
- Generate proper citations for sources
- Provide context-aware search results
- Cross-reference multiple knowledge sources

Use Neo4j knowledge including:
- Crop varieties and their characteristics
- Disease and pest information
- Fertilizer recommendations
- Farming methods and best practices
- Research findings and expert advice
- Regional agricultural data

Always provide:
1. Relevant knowledge with confidence scores
2. Proper citations and source attribution
3. Ranked results by relevance
4. Cross-references between related entities
5. Contextual explanations for farmers

Be thorough and cite sources properly. Consider Malawi's agricultural context."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process knowledge retrieval query with graph-based search.
        
        Args:
            message: User's knowledge query
            context: Conversation history and farmer context
            
        Returns:
            Retrieved knowledge with rankings and citations
        """
        try:
            # Analyze query for retrieval strategy
            query_analysis = self._analyze_query(message)
            
            # Retrieve relevant knowledge from Neo4j
            neo4j_results = await self._retrieve_knowledge(query_analysis)
            
            # Rank and filter results
            ranked_results = self._rank_results(neo4j_results, query_analysis)
            
            # Build retrieval prompt with context
            retrieval_prompt = self._build_retrieval_prompt(message, query_analysis, ranked_results, context)
            
            # Generate intelligent retrieval response
            retrieval_response = await self.llm.generate(
                retrieval_prompt,
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            # Extract structured information
            structured_result = self._structure_retrieval_response(retrieval_response, ranked_results)
            
            return {
                "response": retrieval_response,
                "confidence": structured_result.get("confidence", 0.8),
                "sources": structured_result.get("citations", []),
                "context": {
                    "query_type": query_analysis.get("type"),
                    "entities_found": query_analysis.get("entities", []),
                    "results_count": len(ranked_results),
                    "top_results": ranked_results[:3],
                    "analysis": f"Retrieved {len(ranked_results)} results for {query_analysis.get('type')} query"
                }
            }
            
        except Exception as e:
            logger.error(f"RetrievalAgent processing error: {e}")
            return {
                "response": "I'm having trouble retrieving knowledge from the database. Could you specify what information you're looking for?",
                "confidence": 0.4,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    def _analyze_query(self, message: str) -> Dict[str, Any]:
        """
        Analyze query for retrieval strategy and entity extraction.
        
        Args:
            message: User's knowledge query
            
        Returns:
            Query analysis with entities and strategy
        """
        message_lower = message.lower()
        
        # Query type patterns
        query_patterns = {
            "entity_search": ["what is", "tell me about", "information on", "details of"],
            "relationship_search": ["how does", "relate to", "connect to", "affect"],
            "comparison": ["compare", "difference", "better", "versus"],
            "research_search": ["research", "study", "paper", "finding", "data"]
        }
        
        detected_pattern = None
        for pattern_type, patterns in query_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                detected_pattern = pattern_type
                break
        
        # Extract entities
        entities = self._extract_entities(message_lower)
        
        # Determine search strategy
        search_strategy = "entity_based"
        if entities:
            search_strategy = "entity_based"
        elif detected_pattern == "relationship_search":
            search_strategy = "relationship_based"
        elif detected_pattern == "comparison":
            search_strategy = "comparison_based"
        else:
            search_strategy = "general_search"
        
        return {
            "type": detected_pattern or "general_search",
            "entities": entities,
            "strategy": search_strategy,
            "complexity": len(entities)
        }
    
    def _extract_entities(self, message: str) -> List[str]:
        """Extract agricultural entities from message."""
        entities = []
        
        # Crop entities
        crops = ["maize", "tomato", "cabbage", "groundnut", "soybean", "tobacco", "cassava", "rice"]
        for crop in crops:
            if crop in message:
                entities.append(crop)
        
        # Disease entities
        diseases = ["blight", "wilt", "mildew", "rot", "virus", "spot"]
        for disease in diseases:
            if disease in message:
                entities.append(disease)
        
        # Treatment entities
        treatments = ["fertilizer", "pesticide", "fungicide", "herbicide"]
        for treatment in treatments:
            if treatment in message:
                entities.append(treatment)
        
        return list(set(entities))  # Remove duplicates
    
    async def _retrieve_knowledge(self, query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge from Neo4j based on query analysis.
        
        Args:
            query_analysis: Query analysis with entities
            
        Returns:
            List of Neo4j results
        """
        try:
            entities = query_analysis.get("entities", [])
            strategy = query_analysis.get("strategy", "general_search")
            
            if strategy == "entity_based" and entities:
                # Entity-based search
                results = []
                for entity in entities:
                    entity_query = """
                    MATCH (n)
                    WHERE n.name CONTAINS $entity OR n.type CONTAINS $entity
                    OPTIONAL MATCH (n)-[r]->(related)
                    RETURN n, r, labels(n)
                    """
                    
                    entity_results = self.neo4j.execute_query(entity_query, {"entity": entity})
                    results.extend(entity_results)
                
                return results
            
            elif strategy == "relationship_based":
                # Relationship-based search
                relationship_query = """
                MATCH (a)-[r]->(b)
                WHERE a.name CONTAINS $entity1 OR b.name CONTAINS $entity2
                RETURN a, r, b, type(r)
                """
                
                if len(entities) >= 2:
                    results = self.neo4j.execute_query(relationship_query, {
                        "entity1": entities[0],
                        "entity2": entities[1]
                    })
                    return results
            
            else:
                # General semantic search
                general_query = """
                MATCH (n)
                WHERE n.name CONTAINS $query OR n.description CONTAINS $query
                RETURN n, labels(n)
                ORDER BY n.relevance DESC
                LIMIT 10
                """
                
                query_text = " ".join(entities) if entities else "agricultural"
                results = self.neo4j.execute_query(general_query, {"query": query_text})
                return results
                
        except Exception as e:
            logger.error(f"Neo4j retrieval error: {e}")
            return []
    
    def _rank_results(self, results: List[Dict[str, Any]], query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Rank retrieval results by relevance and confidence.
        
        Args:
            results: Raw Neo4j results
            query_analysis: Query analysis
            
        Returns:
            Ranked list of results
        """
        if not results:
            return []
        
        # Calculate relevance scores
        entities = query_analysis.get("entities", [])
        strategy = query_analysis.get("strategy", "general_search")
        
        for result in results:
            score = 0.5  # Base score
            
            # Entity matching bonus
            if strategy == "entity_based":
                result_entities = result.get("entities", [])
                for entity in entities:
                    if any(entity.lower() in str(result_entities).lower() for entity in entities):
                        score += 0.3
            
            # Label relevance
            labels = result.get("labels", [])
            if "Crop" in labels:
                score += 0.2
            if "Disease" in labels or "Pest" in labels:
                score += 0.2
            if "Research" in labels:
                score += 0.1
            
            result["relevance_score"] = score
        
        # Sort by relevance score
        ranked_results = sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return ranked_results
    
    def _build_retrieval_prompt(
        self,
        message: str,
        query_analysis: Dict[str, Any],
        ranked_results: List[Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> str:
        """
        Build retrieval prompt with ranked results and context.
        
        Args:
            message: Original user message
            query_analysis: Query analysis
            ranked_results: Ranked Neo4j results
            context: Conversation context
            
        Returns:
            Formatted retrieval prompt
        """
        # Get conversation history if available
        history_text = ""
        if context and context.get("history"):
            recent_history = context["history"][-2:]  # Last 2 exchanges
            history_text = "Recent conversation context:\n"
            for exchange in recent_history:
                history_text += f"User: {exchange.get('user', '')}\n"
                history_text += f"Assistant: {exchange.get('assistant', '')}\n\n"
        
        # Format top results
        results_text = "Top knowledge results:\n"
        for i, result in enumerate(ranked_results[:5], 1):
            labels = result.get("labels", [])
            labels_str = ", ".join(labels)
            score = result.get("relevance_score", 0)
            
            results_text += f"{i}. {result.get('name', 'Unknown')} ({labels_str}) - Score: {score:.2f}\n"
        
        prompt = f"""{history_text}
Current query: {message}
Query analysis: {query_analysis.get('type')} search with entities: {query_analysis.get('entities', [])}

{results_text}

Please provide comprehensive answer using these results:
1. Synthesize information from multiple sources
2. Provide proper citations for each piece of information
3. Explain relationships between entities
4. Include confidence levels for different information
5. Be specific to Malawi agricultural context

Generate expert-level response with proper source attribution."""
        
        return prompt
    
    def _structure_retrieval_response(self, response: str, ranked_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Structure retrieval response with citations and metadata.
        
        Args:
            response: LLM retrieval response
            ranked_results: Original ranked results
            
        Returns:
            Structured retrieval information
        """
        # Generate citations from ranked results
        citations = []
        for i, result in enumerate(ranked_results[:5], 1):
            citations.append({
                "source": "neo4j_knowledge_graph",
                "entity": result.get("name", "Unknown"),
                "type": result.get("labels", ["Unknown"])[0] if result.get("labels") else "Unknown",
                "confidence": result.get("relevance_score", 0.5),
                "reference": f"Result {i}"
            })
        
        # Determine overall confidence
        avg_confidence = sum(r.get("relevance_score", 0.5) for r in ranked_results[:5]) / len(ranked_results[:5]) if ranked_results else 0.5
        
        # Extract information types
        info_types = []
        for result in ranked_results[:3]:
            labels = result.get("labels", [])
            info_types.extend(labels)
        
        return {
            "citations": citations,
            "confidence": min(avg_confidence + 0.2, 0.9),  # Boost confidence slightly
            "information_types": list(set(info_types)),
            "sources_used": len(ranked_results),
            "ranking_quality": "high" if ranked_results and ranked_results[0].get("relevance_score", 0) > 0.7 else "medium"
        }
