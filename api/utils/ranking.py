"""
Ranking Utilities - Functions for ranking and scoring sources.
Provides confidence scoring and source quality assessment.
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def rank_sources(sources: List[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
    """
    Rank sources by relevance and quality.
    
    Args:
        sources: List of source documents
        query: Optional query for relevance scoring
        
    Returns:
        Ranked list of sources
    """
    if not sources:
        return []
    
    scored_sources = []
    
    for source in sources:
        # Calculate quality score
        quality_score = calculate_source_quality(source)
        
        # Calculate relevance score if query provided
        relevance_score = 0.5
        if query:
            relevance_score = calculate_relevance_score(source, query)
        
        # Combined score (weighted average)
        combined_score = (quality_score * 0.4) + (relevance_score * 0.6)
        
        scored_sources.append({
            **source,
            "quality_score": quality_score,
            "relevance_score": relevance_score,
            "combined_score": combined_score
        })
    
    # Sort by combined score (descending)
    ranked = sorted(scored_sources, key=lambda x: x["combined_score"], reverse=True)
    
    # Return top 5 sources without internal scores
    return [
        {
            k: v for k, v in source.items()
            if k not in ["quality_score", "relevance_score", "combined_score"]
        }
        for source in ranked[:5]
    ]


def calculate_source_quality(source: Dict[str, Any]) -> float:
    """
    Calculate quality score for a source.
    
    Args:
        source: Source document
        
    Returns:
        Quality score (0-1)
    """
    score = 0.5  # Base score
    
    # Check for author information
    if source.get("author") and source["author"] != "Unknown":
        score += 0.1
    
    # Check for publication year
    if source.get("year") and source["year"] != "N/A":
        try:
            year = int(source["year"])
            # Recent publications get higher scores
            if year >= 2020:
                score += 0.15
            elif year >= 2015:
                score += 0.1
            else:
                score += 0.05
        except ValueError:
            pass
    
    # Check for abstract or description
    if source.get("abstract") and len(source["abstract"]) > 50:
        score += 0.1
    
    # Check for source type (research papers are higher quality)
    if source.get("type") == "research_paper":
        score += 0.1
    
    # Check for content length (more content = more comprehensive)
    if source.get("content"):
        content_length = len(source["content"])
        if content_length > 5000:
            score += 0.05
    
    return min(score, 1.0)


def calculate_relevance_score(source: Dict[str, Any], query: str) -> float:
    """
    Calculate relevance score between source and query.
    
    Args:
        source: Source document
        query: Search query
        
    Returns:
        Relevance score (0-1)
    """
    if not query:
        return 0.5
    
    query_lower = query.lower()
    query_terms = set(query_lower.split())
    
    # Fields to check for term matching
    fields_to_check = [
        source.get("title", ""),
        source.get("abstract", ""),
        source.get("content", ""),
        source.get("description", ""),
        str(source.get("keywords", ""))
    ]
    
    # Count term matches
    total_matches = 0
    for field in fields_to_check:
        field_lower = field.lower()
        for term in query_terms:
            if len(term) > 3:  # Only check meaningful terms
                total_matches += field_lower.count(term)
    
    # Calculate score based on matches
    if total_matches == 0:
        return 0.3
    
    score = 0.5 + min(total_matches * 0.05, 0.5)
    
    return min(score, 1.0)


def calculate_confidence(
    sources: List[Dict[str, Any]],
    has_retrieval: bool = True,
    base_confidence: float = 0.5
) -> float:
    """
    Calculate overall confidence score based on sources.
    
    Args:
        sources: Retrieved sources
        has_retrieval: Whether retrieval was performed
        base_confidence: Base confidence level
        
    Returns:
        Confidence score (0-1)
    """
    if not has_retrieval or not sources:
        return 0.3
    
    confidence = base_confidence
    
    # Increase confidence with more sources
    confidence += min(len(sources) * 0.05, 0.2)
    
    # Increase confidence with high-quality sources
    quality_scores = [calculate_source_quality(s) for s in sources]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    confidence += avg_quality * 0.2
    
    return min(confidence, 0.95)


def filter_sources_by_threshold(
    sources: List[Dict[str, Any]],
    threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Filter sources by minimum quality threshold.
    
    Args:
        sources: List of sources
        threshold: Minimum quality score
        
    Returns:
        Filtered sources
    """
    filtered = []
    
    for source in sources:
        quality = calculate_source_quality(source)
        if quality >= threshold:
            filtered.append(source)
    
    return filtered
