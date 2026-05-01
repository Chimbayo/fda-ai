"""
Ollama Model Interface - Optimized for FDA-AI Assignment.
Features: Caching, connection pooling, streaming, <2s latency target.
"""
import aiohttp
import logging
import hashlib
import time
from typing import Optional, Dict, Any, AsyncGenerator
from functools import lru_cache

from app.config import ollama_config

logger = logging.getLogger(__name__)

# Simple in-memory cache for responses
_response_cache = {}
_cache_max_size = 100


class OllamaModel:
    """
    Optimized client for Ollama LLM API.
    Targets: <2s initial token latency, 3-8s full response.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        enable_cache: bool = True
    ):
        self.base_url = base_url or ollama_config.base_url
        self.model = model or ollama_config.model
        self.temperature = ollama_config.temperature
        self.max_tokens = ollama_config.max_tokens
        self.enable_cache = enable_cache
        
        # Performance optimizations
        self.timeout = 30  # Reduced from 120 for faster failure
        self.connector = None  # Will be initialized with connection pooling
        
        # Context window optimization
        self.max_context_length = 3000  # Leave room for response
        
        logger.info(f"OllamaModel initialized: {self.model}")
    
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
    
    def _get_session(self):
        """Get or create aiohttp session with connection pooling."""
        if self.connector is None or self.connector.closed:
            self.connector = aiohttp.TCPConnector(
                limit=10,  # Connection pool size
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
        return aiohttp.ClientSession(connector=self.connector)
    
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
        
        # Compress prompt for speed
        compressed_prompt = self._compress_prompt(prompt, self.max_context_length)
        
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
        
        # Optimized payload for Gemma 4B speed
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": max_tok,
                "top_k": 20,  # Reduced for speed
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "seed": 42  # For reproducibility
            }
        }
        
        try:
            session = self._get_session()
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result.get("message", {}).get("content", "")
                    
                    # Cache the response
                    if self.enable_cache and use_cache and len(_response_cache) < _cache_max_size:
                        _response_cache[cache_key] = content
                    
                    elapsed = time.time() - start_time
                    logger.info(f"Generated in {elapsed:.2f}s (prompt: {len(compressed_prompt)} chars)")
                    
                    return content
                else:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: {response.status} - {error_text}")
                    return "I apologize, but I'm having trouble generating a response. Please try again."
                    
        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error: {e}")
            return "I'm unable to connect to the language model. Please check if Ollama is running."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "An unexpected error occurred. Please try again."
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate text with streaming response.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            
        Yields:
            Generated text chunks
        """
        temp = temperature or self.temperature
        
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temp
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                try:
                                    import json
                                    data = json.loads(line)
                                    if "message" in data and "content" in data["message"]:
                                        yield data["message"]["content"]
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama streaming error: {response.status} - {error_text}")
                        yield "Error: Unable to generate response"
                        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield "Error: Connection failed"
    
    async def list_models(self) -> list:
        """
        List available models in Ollama.
        
        Returns:
            List of available models
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("models", [])
                    else:
                        return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    async def is_available(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if available
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except:
            return False
