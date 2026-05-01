"""
Retrieval Agent - Searches and retrieves information from research papers and documents.
Provides evidence-based answers from the knowledge base.
"""
from typing import Dict, Any, List
import logging

from app.models.ollama_model import OllamaModel
from app.database.neo4j_client import Neo4jClient
from app.utils.ranking import rank_sources

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """
    Specialized agent for retrieving information from research documents.
    Handles queries requiring technical information, studies, and papers.
    """
    
    def __init__(self):
        self.llm = OllamaModel()
        self.db = Neo4jClient()
        
        # System prompt for research expertise
        self.system_prompt = """You are a research librarian and technical expert for agricultural studies.
Your expertise includes:
- Finding relevant research papers and studies
- Extracting key findings from technical documents
- Summarizing complex research for farmers
- Citing sources and providing evidence-based answers

Focus on practical applications of research findings.
Be accurate about study details, authors, and key conclusions.
Clearly distinguish between established research and preliminary findings."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a retrieval query.
        
        Args:
            message: User's query about research/documents
            context: Additional context
            
        Returns:
            Response with retrieved information
        """
        try:
            # Search for relevant documents
            documents = await self._search_documents(message)
            
            # Extract key information
            key_findings = await self._extract_findings(documents, message)
            
            # Build prompt with retrieved information
            prompt = self._build_prompt(message, documents, key_findings)
            
            # Generate synthesized response
            response = await self.llm.generate(
                prompt,
                system_prompt=self.system_prompt
            )
            
            # Calculate confidence based on document quality
            confidence = self._calculate_confidence(documents, key_findings)
            
            # Format sources
            sources = self._format_sources(documents)
            
            return {
                "response": response,
                "confidence": confidence,
                "sources": sources,
                "context": {
                    "documents_found": len(documents),
                    "search_terms": self._extract_search_terms(message)
                }
            }
            
        except Exception as e:
            logger.error(f"RetrievalAgent processing error: {e}")
            return {
                "response": "I apologize, but I'm having trouble retrieving the research information you requested. Please try a more specific query about agricultural research.",
                "confidence": 0.0,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    async def _search_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for relevant documents in the knowledge base.
        
        Args:
            query: Search query
            
        Returns:
            List of relevant documents
        """
        search_terms = self._extract_search_terms(query)
        
        documents = []
        
        try:
            # Search in Neo4j for documents
            for term in search_terms:
                cypher_query = """
                MATCH (d:Document)
                WHERE d.title CONTAINS $term 
                   OR d.content CONTAINS $term
                   OR d.keywords CONTAINS $term
                RETURN d.id as id, d.title as title, d.author as author,
                       d.year as year, d.abstract as abstract, d.content as content,
                       d.source as source
                LIMIT 10
                """
                
                results = self.db.execute_query(cypher_query, {"term": term})
                documents.extend(results)
            
            # Also search for specific topics
            topic_query = """
            MATCH (t:Topic)-[:DISCUSSED_IN]->(d:Document)
            WHERE t.name CONTAINS $term
            RETURN d.id as id, d.title as title, d.author as author,
                   d.year as year, d.abstract as abstract, d.content as content,
                   t.name as topic, d.source as source
            LIMIT 10
            """
            
            for term in search_terms:
                results = self.db.execute_query(topic_query, {"term": term})
                documents.extend(results)
            
            # Remove duplicates
            seen_ids = set()
            unique_documents = []
            for doc in documents:
                doc_id = doc.get("id") or doc.get("title", "")
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    unique_documents.append(doc)
            
            return unique_documents[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Document search error: {e}")
            return []
    
    async def _extract_findings(
        self,
        documents: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Extract key findings relevant to the query.
        
        Args:
            documents: Retrieved documents
            query: Original query
            
        Returns:
            Key findings
        """
        findings = []
        
        for doc in documents[:5]:  # Process top 5
            try:
                # Create extraction prompt
                extraction_prompt = f"""Extract key findings from this research document that answer the following question:

Question: {query}

Document Title: {doc.get('title', 'Unknown')}
Author: {doc.get('author', 'Unknown')}
Year: {doc.get('year', 'Unknown')}

Content:
{doc.get('content', doc.get('abstract', ''))[:2000]}

List 2-3 key findings that directly address the question. Be specific and quote important statistics or conclusions."""
                
                extraction = await self.llm.generate(extraction_prompt)
                
                findings.append({
                    "document": doc.get("title"),
                    "author": doc.get("author"),
                    "year": doc.get("year"),
                    "findings": extraction,
                    "source": doc.get("source", "Research database")
                })
                
            except Exception as e:
                logger.error(f"Error extracting findings: {e}")
                continue
        
        return findings
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """
        Extract relevant search terms from query.
        
        Args:
            query: User query
            
        Returns:
            List of search terms
        """
        # Common research-related terms
        research_terms = [
            "maize", "efficiency", "farming", "agriculture", "productivity",
            "technical", "study", "research", "analysis", "data",
            "malawi", "smallholder", "soil fertility", "fertilizer",
            "yield", "crop", "variety", "sustainability"
        ]
        
        query_lower = query.lower()
        terms = [term for term in research_terms if term in query_lower]
        
        # If no terms found, extract all nouns (simplified)
        if not terms:
            words = query_lower.split()
            terms = [w for w in words if len(w) > 4][:3]
        
        return terms if terms else ["agriculture"]
    
    def _build_prompt(
        self,
        message: str,
        documents: List[Dict[str, Any]],
        findings: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt with retrieved information.
        
        Args:
            message: User message
            documents: Retrieved documents
            findings: Extracted findings
            
        Returns:
            Formatted prompt
        """
        # Format findings
        findings_text = ""
        if findings:
            findings_text = "Key findings from research:\n\n"
            for i, finding in enumerate(findings, 1):
                findings_text += f"{i}. From '{finding['document']}' ({finding['author']}, {finding['year']}):\n"
                findings_text += f"   {finding['findings']}\n\n"
        
        # Format document list
        doc_list = ""
        if documents:
            doc_list = "\nRelevant documents:\n"
            for doc in documents[:5]:
                doc_list += f"- {doc.get('title', 'Untitled')} by {doc.get('author', 'Unknown')} ({doc.get('year', 'N/A')})\n"
        
        prompt = f"""{findings_text}{doc_list}

User question: {message}

Based on the research findings above, provide a comprehensive answer. Include specific data points and cite the sources. If the findings don't fully answer the question, acknowledge the limitations."""
        
        return prompt
    
    def _format_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format documents as sources.
        
        Args:
            documents: Retrieved documents
            
        Returns:
            Formatted sources
        """
        sources = []
        
        for doc in documents[:5]:
            sources.append({
                "type": "research_paper",
                "title": doc.get("title", "Untitled"),
                "author": doc.get("author", "Unknown"),
                "year": doc.get("year", "N/A"),
                "source": doc.get("source", "Research database"),
                "abstract": doc.get("abstract", "")[:200] + "..." if doc.get("abstract") else ""
            })
        
        return sources
    
    def _calculate_confidence(
        self,
        documents: List[Dict[str, Any]],
        findings: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence score.
        
        Args:
            documents: Retrieved documents
            findings: Extracted findings
            
        Returns:
            Confidence score (0-1)
        """
        if not documents:
            return 0.2
        
        base_confidence = 0.4
        
        # Increase with number of documents
        base_confidence += min(len(documents) * 0.05, 0.2)
        
        # Increase with successful findings extraction
        if findings:
            base_confidence += min(len(findings) * 0.1, 0.3)
        
        return min(base_confidence, 0.9)
