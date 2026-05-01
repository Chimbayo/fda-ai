"""
Setup script for FDA-AI.
Initializes the knowledge base and verifies system components.
"""
import asyncio
import logging
from pathlib import Path

from app.database.neo4j_client import Neo4jClient
from app.database.ingestion import KnowledgeIngestion
from app.models.ollama_model import OllamaModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_ollama():
    """Verify Ollama is running."""
    logger.info("Checking Ollama connection...")
    try:
        ollama = OllamaModel()
        is_available = await ollama.is_available()
        
        if is_available:
            models = await ollama.list_models()
            logger.info(f"✓ Ollama is running with {len(models)} models")
            for model in models:
                logger.info(f"  - {model.get('name', 'unknown')}")
            return True
        else:
            logger.error("✗ Ollama is not available. Please start Ollama.")
            return False
    except Exception as e:
        logger.error(f"✗ Ollama connection failed: {e}")
        return False


def verify_neo4j():
    """Verify Neo4j is running."""
    logger.info("Checking Neo4j connection...")
    try:
        neo4j = Neo4jClient()
        is_connected = neo4j.verify_connection()
        
        if is_connected:
            logger.info("✓ Neo4j is connected")
            
            # Create indexes
            logger.info("Creating database indexes...")
            neo4j.create_indexes()
            return True
        else:
            logger.error("✗ Neo4j connection failed. Please check your Neo4j instance.")
            return False
    except Exception as e:
        logger.error(f"✗ Neo4j verification failed: {e}")
        return False


def ingest_knowledge():
    """Ingest sample knowledge into Neo4j."""
    logger.info("Ingesting knowledge base...")
    try:
        ingestion = KnowledgeIngestion()
        
        # Load sample data
        data_path = Path(__file__).parent / "data" / "sample_knowledge.json"
        
        if data_path.exists():
            success = ingestion.ingest_from_json(str(data_path))
            if success:
                logger.info("✓ Knowledge base ingested successfully")
                return True
            else:
                logger.error("✗ Knowledge ingestion failed")
                return False
        else:
            logger.warning(f"Sample knowledge file not found at {data_path}")
            return False
    except Exception as e:
        logger.error(f"✗ Knowledge ingestion failed: {e}")
        return False


async def main():
    """Main setup function."""
    logger.info("=" * 50)
    logger.info("FDA-AI Setup")
    logger.info("=" * 50)
    
    # Verify components
    ollama_ok = await verify_ollama()
    neo4j_ok = verify_neo4j()
    
    if not (ollama_ok and neo4j_ok):
        logger.error("\n✗ Setup incomplete - please fix the issues above")
        return False
    
    # Ingest knowledge
    knowledge_ok = ingest_knowledge()
    
    if all([ollama_ok, neo4j_ok, knowledge_ok]):
        logger.info("\n" + "=" * 50)
        logger.info("✓ Setup completed successfully!")
        logger.info("=" * 50)
        logger.info("\nYou can now start the application with:")
        logger.info("  python -m app.main")
        logger.info("\nOr run with uvicorn:")
        logger.info("  uvicorn app.main:app --reload")
        return True
    else:
        logger.warning("\n⚠ Setup completed with warnings")
        return False


if __name__ == "__main__":
    asyncio.run(main())
