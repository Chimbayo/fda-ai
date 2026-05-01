"""
FDA-AI: Agricultural Assistant for Malawi

An AI-powered agricultural advisory system using LangGraph and Neo4j.
Provides specialized agents for crop advice, disease diagnosis, weather,
and research-based information retrieval.
"""

__version__ = "2.0.0"
__author__ = "FDA-AI Team"

from app.config import neo4j_config, ollama_config, app_config

__all__ = [
    "neo4j_config",
    "ollama_config", 
    "app_config"
]
