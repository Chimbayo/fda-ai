"""
OpenAI Model Interface - Serverless-compatible LLM for FDA-AI Assignment.
Features: Caching, streaming, cloud-based deployment support.
"""
import logging
import hashlib
import time
from typing import Optional, Dict, Any
from functools import lru_cache

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Simple in-memory cache for responses
_response_cache = {}
_cache_max_size = 100


class OpenAIModel:
    """
    OpenAI client for LLM API - serverless-compatible.
    Targets: <2s initial token latency, 3-8s full response.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_cache: bool = True
    ):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        
        self.api_key = api_key
        self.model = model or "gpt-3.5-turbo"
        self.temperature = 0.7
        self.max_tokens = 500
        self.enable_cache = enable_cache
        
        # Initialize OpenAI client
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            # Try to get from environment
            self.client = openai.OpenAI()
        
        # Context window optimization
        self.max_context_length = 3000
        
        logger.info(f"OpenAIModel initialized: {self.model}")
    
    def _get_cache_key(self, prompt: str, system_prompt: Optional[str], temp: float) -> str:
        """Generate cache key from prompt parameters."""
        key_content = f"{self.model}:{system_prompt}:{prompt}:{temp}"
        return hashlib.md5(key_content.encode()).hexdigest()
    
    def _compress_prompt(self, prompt: str, max_length: int = 3000) -> str:
        """
        Compress prompt to fit within context window.
        Removes redundant whitespace and truncates if necessary.
        """
        # Remove excessive whitespace
        compressed = ' '.join(prompt.split())
        
        # Truncate if too long
        if len(compressed) > max_length:
            # Try to truncate at sentence boundary
            truncated = compressed[:max_length]
            last_period = truncated.rfind('.')
            if last_period > max_length * 0.8:  # If we can find a period in last 20%
                compressed = truncated[:last_period + 1]
            else:
                compressed = truncated + "..."
        
        return compressed
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True
    ) -> str:
        """
        Generate text with caching and compression optimizations.
        Target: <2s initial token latency.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use response caching
            
        Returns:
            Generated text
        """
        start_time = time.time()
        
        temp = temperature or self.temperature
        max_tok = max_tokens or self.max_tokens
        
        # Check cache first
        if self.enable_cache and use_cache:
            cache_key = self._get_cache_key(prompt, system_prompt, temp)
            if cache_key in _response_cache:
                logger.debug(f"Cache hit: {cache_key[:8]}...")
                return _response_cache[cache_key]
        
        # Use prompt directly for now (compression disabled for stability)
        compressed_prompt = prompt
        
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": compressed_prompt
        })
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok
            )
            
            content = response.choices[0].message.content
            
            # Cache the response
            if self.enable_cache and use_cache and len(_response_cache) < _cache_max_size:
                cache_key = self._get_cache_key(prompt, system_prompt, temp)
                _response_cache[cache_key] = content
            
            elapsed = time.time() - start_time
            logger.info(f"Generated in {elapsed:.2f}s (prompt: {len(compressed_prompt)} chars)")
            
            return content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return "I apologize, but I'm having trouble generating a response. Please try again."
    
    async def is_available(self) -> bool:
        """
        Check if OpenAI service is available.
        
        Returns:
            True if available
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI availability check failed: {e}")
            return False
