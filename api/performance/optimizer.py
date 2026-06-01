"""
Performance Optimizer for <2s Initial Token Latency.
Implements caching, streaming, and response optimization techniques.
"""
import logging
import time
from typing import Dict, Any, Optional
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """
    Performance optimization system for FDA-AI.
    Implements caching, streaming, and response optimization for <2s latency.
    """
    
    def __init__(self):
        self.response_cache = {}
        self.query_cache = {}
        self.max_cache_size = 100
        self.cache_ttl = 300  # 5 minutes
        self.compression_enabled = True
        
        # Performance metrics
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0.0,
            "streaming_enabled": True
        }
    
    @lru_cache(maxsize=50)
    async def get_cached_response(self, query_hash: str) -> Optional[str]:
        """
        Get cached response if available and not expired.
        
        Args:
            query_hash: Hash of user query
            
        Returns:
            Cached response or None
        """
        if query_hash in self.response_cache:
            cached_item = self.response_cache[query_hash]
            current_time = time.time()
            
            # Check if cache is still valid
            if current_time - cached_item["timestamp"] < self.cache_ttl:
                self.metrics["cache_hits"] += 1
                logger.debug(f"Cache hit for query: {query_hash[:8]}...")
                return cached_item["response"]
        
        self.metrics["cache_misses"] += 1
        return None
    
    def cache_response(self, query_hash: str, response: str, confidence: float = 0.8):
        """
        Cache response for future queries.
        
        Args:
            query_hash: Hash of user query
            response: Generated response
            confidence: Response confidence
            
        Returns:
            Success status
        """
        try:
            # Remove oldest cache entries if at max size
            if len(self.response_cache) >= self.max_cache_size:
                oldest_key = min(self.response_cache.keys(), 
                                   key=lambda k: self.response_cache[k]["timestamp"])
                del self.response_cache[oldest_key]
            
            # Store in cache
            self.response_cache[query_hash] = {
                "response": response,
                "confidence": confidence,
                "timestamp": time.time()
            }
            
            logger.debug(f"Cached response for query: {query_hash[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False
    
    def generate_query_hash(self, query: str) -> str:
        """
        Generate hash for query caching.
        
        Args:
            query: User query string
            
        Returns:
            Query hash
        """
        # Simple hash generation for caching
        import hashlib
        return hashlib.md5(query.encode()).hexdigest()[:16]
    
    async def optimize_prompt(
        self,
        prompt: str,
        max_tokens: int = 500
    ) -> str:
        """
        Optimize prompt for faster processing.
        
        Args:
            prompt: Original prompt
            max_tokens: Maximum tokens to use
            
        Returns:
            Optimized prompt
        """
        if not self.compression_enabled:
            return prompt
        
        # Basic prompt compression
        # Remove redundant phrases and compress common patterns
        
        # Remove excessive whitespace
        compressed = " ".join(prompt.split())
        
        # Truncate if too long
        if len(compressed) > max_tokens * 4:  # Rough token estimate
            compressed = compressed[:max_tokens * 4]
            logger.warning(f"Prompt truncated from {len(prompt)} to {len(compressed)} characters")
        
        return compressed
    
    async def stream_response(
        self,
        response_generator,
        query: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream response for immediate token delivery.
        
        Args:
            response_generator: Async generator yielding response chunks
            query: User query for tracking
            
        Yields:
            Response chunks for immediate delivery
        """
        start_time = time.time()
        first_token_time = None
        token_count = 0
        
        try:
            async for chunk in response_generator:
                if chunk:
                    # Record first token time
                    if first_token_time is None:
                        first_token_time = time.time() - start_time
                        logger.info(f"First token delivered in {first_token_time:.2f}s")
                        
                        # Check if <2s target met
                        if first_token_time > 2.0:
                            logger.warning(f"First token latency exceeded 2s: {first_token_time:.2f}s")
                    
                    token_count += 1
                    
                    # Yield chunk immediately
                    yield chunk
            
            # Log streaming metrics
            total_time = time.time() - start_time
            self.metrics["streaming_enabled"] = True
            self.metrics["last_response_time"] = total_time
            self.metrics["tokens_generated"] = token_count
            
            logger.info(f"Streaming completed: {token_count} tokens in {total_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"Error: {str(e)}"
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Performance statistics
        """
        cache_hit_rate = 0.0
        total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        if total_requests > 0:
            cache_hit_rate = self.metrics["cache_hits"] / total_requests
        
        return {
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self.response_cache),
            "total_requests": total_requests,
            "avg_response_time": self.metrics.get("avg_response_time", 0.0),
            "streaming_enabled": self.metrics["streaming_enabled"],
            "compression_enabled": self.compression_enabled,
            "last_response_time": self.metrics.get("last_response_time", 0.0)
        }
    
    def update_response_time(self, response_time: float):
        """
        Update average response time metric.
        
        Args:
            response_time: Response time in seconds
        """
        if self.metrics["avg_response_time"] == 0:
            self.metrics["avg_response_time"] = response_time
        else:
            # Weighted average (more recent responses weighted more heavily)
            alpha = 0.3  # Weight for recent responses
            self.metrics["avg_response_time"] = (
                alpha * response_time + 
                (1 - alpha) * self.metrics["avg_response_time"]
            )
    
    def clear_cache(self):
        """Clear response cache."""
        self.response_cache.clear()
        self.metrics["cache_hits"] = 0
        self.metrics["cache_misses"] = 0
        logger.info("Response cache cleared")
    
    async def precompute_common_queries(self):
        """
        Precompute responses for common queries.
        """
        common_queries = {
            "hello": "Hello! I'm your agricultural assistant for Malawi farmers. How can I help you today?",
            "help": "I can help you with: crop advice, disease diagnosis, weather information, and agricultural research. What do you need assistance with?",
            "what can you do": "I provide expert agricultural advice including: crop selection, planting guidance, disease identification, treatment recommendations, weather patterns, and seasonal farming advice for Malawi.",
            "maize": "I can help with maize farming! Ask me about varieties (Kalulu, Kanyani, Mbidzi), planting schedules, fertilizer recommendations, or common issues like leaf blight and stem borer.",
            "tomato": "For tomato farming, I can advise on varieties (Roma VF, Money Maker), disease management (early blight, late blight), and optimal growing conditions for Malawi's climate."
        }
        
        for query, response in common_queries.items():
            query_hash = self.generate_query_hash(query)
            self.cache_response(query_hash, response, 0.9)
        
        logger.info(f"Precomputed {len(common_queries)} common queries")


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()
