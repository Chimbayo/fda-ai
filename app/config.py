"""
Configuration management for FDA-AI application.
Handles Neo4j, Ollama, and application settings.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Neo4jConfig:
    """Neo4j database configuration."""
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    
    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """Load configuration from environment variables."""
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )


@dataclass
class OllamaConfig:
    """Ollama LLM configuration - Optimized for Gemma 4B."""
    base_url: str = "http://localhost:11434"
    model: str = "gemma:4b"  # Assignment requires Gemma 4B
    temperature: float = 0.3  # Lower for faster, more focused responses
    max_tokens: int = 512  # Reduced for speed (under 2s target)
    context_window: int = 4096
    
    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Load configuration from environment variables."""
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "gemma:4b"),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "512"))
        )


@dataclass
class AppConfig:
    """Application configuration."""
    debug: bool = False
    log_level: str = "INFO"
    max_conversation_history: int = 10
    similarity_threshold: float = 0.7
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        return cls(
            debug=os.getenv("DEBUG", "False").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_conversation_history=int(os.getenv("MAX_CONVERSATION_HISTORY", "10")),
            similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
        )


# Global configuration instances
neo4j_config = Neo4jConfig.from_env()
ollama_config = OllamaConfig.from_env()
app_config = AppConfig.from_env()
