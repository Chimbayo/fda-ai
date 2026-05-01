"""
Formatter Utilities - Functions for formatting responses and data.
Provides consistent output formatting for the chatbot.
"""
from typing import Dict, Any, List
import re
import logging

logger = logging.getLogger(__name__)


def format_response(response: str, max_length: int = 2000) -> str:
    """
    Format and clean the AI response.
    
    Args:
        response: Raw response text
        max_length: Maximum response length
        
    Returns:
        Formatted response
    """
    if not response:
        return "I apologize, but I couldn't generate a response. Please try again."
    
    # Clean up the response
    formatted = response.strip()
    
    # Remove excessive newlines
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    
    # Ensure response ends with proper punctuation
    if formatted and not formatted[-1] in '.!?':
        formatted += '.'
    
    # Truncate if too long
    if len(formatted) > max_length:
        formatted = formatted[:max_length].rsplit('.', 1)[0] + '.'
    
    return formatted


def format_sources(sources: List[Dict[str, Any]]) -> str:
    """
    Format sources for display in response.
    
    Args:
        sources: List of source documents
        
    Returns:
        Formatted sources string
    """
    if not sources:
        return ""
    
    formatted = "\n\n**Sources:**\n"
    
    for i, source in enumerate(sources, 1):
        title = source.get("title", "Untitled")
        author = source.get("author", "Unknown")
        year = source.get("year", "N/A")
        source_type = source.get("type", "document")
        
        formatted += f"{i}. {title}"
        
        if author and author != "Unknown":
            formatted += f" by {author}"
        
        if year and year != "N/A":
            formatted += f" ({year})"
        
        formatted += f" [{source_type}]\n"
    
    return formatted


def format_confidence_indicator(confidence: float) -> str:
    """
    Create a visual confidence indicator.
    
    Args:
        confidence: Confidence score (0-1)
        
    Returns:
        Visual indicator string
    """
    if confidence >= 0.8:
        return "High confidence"
    elif confidence >= 0.6:
        return "Medium confidence"
    elif confidence >= 0.4:
        return "Moderate confidence"
    else:
        return "Low confidence"


def format_agricultural_advice(
    response: str,
    topic: str,
    include_warnings: bool = True
) -> str:
    """
    Format agricultural advice with proper structure.
    
    Args:
        response: Raw advice text
        topic: Topic of advice
        include_warnings: Whether to include safety warnings
        
    Returns:
        Formatted advice
    """
    formatted = f"**{topic}**\n\n"
    formatted += response
    
    if include_warnings:
        formatted += "\n\n---\n*Remember: Consider your local conditions and consult with agricultural extension officers for site-specific advice.*"
    
    return formatted


def format_conversation_history(
    history: List[Dict[str, Any]],
    max_exchanges: int = 5
) -> str:
    """
    Format conversation history for context.
    
    Args:
        history: Conversation history
        max_exchanges: Maximum exchanges to include
        
    Returns:
        Formatted history
    """
    if not history:
        return ""
    
    # Get recent exchanges
    recent = history[-max_exchanges:] if len(history) > max_exchanges else history
    
    formatted = "**Previous Conversation:**\n"
    
    for exchange in recent:
        user_msg = exchange.get("user_message", "")
        ai_msg = exchange.get("ai_response", "")
        
        if user_msg:
            formatted += f"\nFarmer: {user_msg[:100]}{'...' if len(user_msg) > 100 else ''}\n"
        
        if ai_msg:
            formatted += f"Assistant: {ai_msg[:100]}{'...' if len(ai_msg) > 100 else ''}\n"
    
    formatted += "\n---\n"
    
    return formatted


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix


def clean_text_for_display(text: str) -> str:
    """
    Clean text for display by removing special characters and formatting.
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    cleaned = ' '.join(text.split())
    
    # Remove special control characters
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
    
    return cleaned


def format_number(value: float, decimal_places: int = 2) -> str:
    """
    Format number for display.
    
    Args:
        value: Number to format
        decimal_places: Decimal places
        
    Returns:
        Formatted number string
    """
    try:
        return f"{value:.{decimal_places}f}"
    except (TypeError, ValueError):
        return str(value)


def create_bullet_list(items: List[str], ordered: bool = False) -> str:
    """
    Create a formatted bullet or numbered list.
    
    Args:
        items: List items
        ordered: Whether to use numbers instead of bullets
        
    Returns:
        Formatted list
    """
    if not items:
        return ""
    
    formatted = ""
    
    for i, item in enumerate(items, 1):
        if ordered:
            formatted += f"{i}. {item}\n"
        else:
            formatted += f"• {item}\n"
    
    return formatted
