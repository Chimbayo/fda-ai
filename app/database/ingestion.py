"""
Data Ingestion - Loads agricultural knowledge into Neo4j.
Processes and stores documents, crops, varieties, diseases, and treatments.
"""
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

from app.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class KnowledgeIngestion:
    """
    Handles ingestion of agricultural knowledge into Neo4j.
    Processes various data sources and creates the knowledge graph.
    """
    
    def __init__(self):
        self.db = Neo4jClient()
    
    def ingest_crops_and_varieties(self, data: List[Dict[str, Any]]) -> bool:
        """
        Ingest crop and variety information.
        
        Args:
            data: List of crop data with varieties
            
        Returns:
            True if successful
        """
        try:
            for crop_data in data:
                crop_name = crop_data.get("name")
                
                # Create crop node
                cypher = """
                MERGE (c:Crop {name: $crop_name})
                SET c.description = $description,
                    c.type = $type
                """
                
                self.db.execute_write(cypher, {
                    "crop_name": crop_name,
                    "description": crop_data.get("description", ""),
                    "type": crop_data.get("type", "")
                })
                
                # Create variety nodes and relationships
                for variety in crop_data.get("varieties", []):
                    var_cypher = """
                    MATCH (c:Crop {name: $crop_name})
                    MERGE (v:Variety {name: $variety_name})
                    SET v.maturity = $maturity,
                        v.yield = $yield,
                        v.characteristics = $characteristics,
                        v.recommended_regions = $regions
                    MERGE (c)-[:HAS_VARIETY]->(v)
                    """
                    
                    self.db.execute_write(var_cypher, {
                        "crop_name": crop_name,
                        "variety_name": variety.get("name"),
                        "maturity": variety.get("maturity", ""),
                        "yield": variety.get("yield", ""),
                        "characteristics": variety.get("characteristics", ""),
                        "regions": variety.get("regions", [])
                    })
            
            logger.info(f"Ingested {len(data)} crops with varieties")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting crops: {e}")
            return False
    
    def ingest_diseases_and_treatments(self, data: List[Dict[str, Any]]) -> bool:
        """
        Ingest disease and treatment information.
        
        Args:
            data: List of disease data with treatments
            
        Returns:
            True if successful
        """
        try:
            for disease_data in data:
                disease_name = disease_data.get("name")
                
                # Create disease node
                cypher = """
                MERGE (d:Disease {name: $disease_name})
                SET d.symptoms = $symptoms,
                    d.affected_crops = $crops,
                    d.severity = $severity,
                    d.description = $description
                """
                
                self.db.execute_write(cypher, {
                    "disease_name": disease_name,
                    "symptoms": disease_data.get("symptoms", ""),
                    "crops": disease_data.get("affected_crops", []),
                    "severity": disease_data.get("severity", "medium"),
                    "description": disease_data.get("description", "")
                })
                
                # Create treatment nodes
                for treatment in disease_data.get("treatments", []):
                    treat_cypher = """
                    MATCH (d:Disease {name: $disease_name})
                    MERGE (t:Treatment {name: $treatment_name})
                    SET t.type = $type,
                        t.application = $application,
                        t.effectiveness = $effectiveness,
                        t.cost_level = $cost
                    MERGE (d)-[:TREATED_WITH]->(t)
                    """
                    
                    self.db.execute_write(treat_cypher, {
                        "disease_name": disease_name,
                        "treatment_name": treatment.get("name"),
                        "type": treatment.get("type", ""),
                        "application": treatment.get("application", ""),
                        "effectiveness": treatment.get("effectiveness", ""),
                        "cost": treatment.get("cost_level", "")
                    })
                
                # Link to affected crops
                for crop in disease_data.get("affected_crops", []):
                    link_cypher = """
                    MATCH (d:Disease {name: $disease_name})
                    MATCH (c:Crop {name: $crop_name})
                    MERGE (d)-[:AFFECTS]->(c)
                    """
                    
                    self.db.execute_write(link_cypher, {
                        "disease_name": disease_name,
                        "crop_name": crop
                    })
            
            logger.info(f"Ingested {len(data)} diseases with treatments")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting diseases: {e}")
            return False
    
    def ingest_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Ingest research documents.
        
        Args:
            documents: List of document data
            
        Returns:
            True if successful
        """
        try:
            for doc in documents:
                # Create document node
                cypher = """
                MERGE (d:Document {id: $doc_id})
                SET d.title = $title,
                    d.author = $author,
                    d.year = $year,
                    d.abstract = $abstract,
                    d.content = $content,
                    d.source = $source,
                    d.keywords = $keywords,
                    d.doi = $doi,
                    d.url = $url
                """
                
                self.db.execute_write(cypher, {
                    "doc_id": doc.get("id") or doc.get("title", "").replace(" ", "_"),
                    "title": doc.get("title", ""),
                    "author": doc.get("author", ""),
                    "year": doc.get("year", ""),
                    "abstract": doc.get("abstract", ""),
                    "content": doc.get("content", "")[:50000],  # Limit content size
                    "source": doc.get("source", ""),
                    "keywords": doc.get("keywords", []),
                    "doi": doc.get("doi", ""),
                    "url": doc.get("url", "")
                })
                
                # Create topic nodes and relationships
                for topic in doc.get("topics", []):
                    topic_cypher = """
                    MATCH (d:Document {id: $doc_id})
                    MERGE (t:Topic {name: $topic_name})
                    MERGE (t)-[:DISCUSSED_IN]->(d)
                    """
                    
                    self.db.execute_write(topic_cypher, {
                        "doc_id": doc.get("id") or doc.get("title", "").replace(" ", "_"),
                        "topic_name": topic
                    })
            
            logger.info(f"Ingested {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting documents: {e}")
            return False
    
    def ingest_from_json(self, file_path: str) -> bool:
        """
        Ingest knowledge from JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            True if successful
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            success = True
            
            # Ingest crops
            if "crops" in data:
                success = success and self.ingest_crops_and_varieties(data["crops"])
            
            # Ingest diseases
            if "diseases" in data:
                success = success and self.ingest_diseases_and_treatments(data["diseases"])
            
            # Ingest documents
            if "documents" in data:
                success = success and self.ingest_documents(data["documents"])
            
            return success
            
        except Exception as e:
            logger.error(f"Error ingesting from JSON: {e}")
            return False
    
    def create_sample_data(self) -> Dict[str, Any]:
        """
        Create sample agricultural knowledge data.
        
        Returns:
            Sample data dictionary
        """
        return {
            "crops": [
                {
                    "name": "Maize",
                    "description": "Staple food crop in Malawi",
                    "type": "Cereal",
                    "varieties": [
                        {
                            "name": "SC 301 (Kalulu)",
                            "maturity": "Ultra-early (90-100 days)",
                            "yield": "3-4 tons/ha",
                            "characteristics": "Drought tolerant, good for low rainfall areas",
                            "regions": ["Southern Region", "Central Region"]
                        },
                        {
                            "name": "SC 303 (Kalulu)",
                            "maturity": "Ultra-early (90-100 days)",
                            "yield": "3-4 tons/ha",
                            "characteristics": "Compact plant type, excellent standability",
                            "regions": ["All regions"]
                        },
                        {
                            "name": "SC 403 (Kanyani)",
                            "maturity": "Early (100-110 days)",
                            "yield": "4-5 tons/ha",
                            "characteristics": "High yielding under good management",
                            "regions": ["Central Region", "Northern Region"]
                        },
                        {
                            "name": "SC 419 (Kanyani)",
                            "maturity": "Early (100-110 days)",
                            "yield": "4-6 tons/ha",
                            "characteristics": "Excellent yield stability",
                            "regions": ["All regions"]
                        },
                        {
                            "name": "SC 529 (Mbidzi)",
                            "maturity": "Medium (110-120 days)",
                            "yield": "5-7 tons/ha",
                            "characteristics": "Good tolerance to major diseases",
                            "regions": ["Central Region", "Northern Region"]
                        },
                        {
                            "name": "SC 653 (Mkango)",
                            "maturity": "Medium-late (120-130 days)",
                            "yield": "6-8 tons/ha",
                            "characteristics": "Very high yielder under optimal conditions",
                            "regions": ["High potential areas"]
                        },
                        {
                            "name": "SC 719 (Njobvu)",
                            "maturity": "Medium-late (120-130 days)",
                            "yield": "6-8 tons/ha",
                            "characteristics": "Excellent husk cover, good tip filling",
                            "regions": ["All regions with good rainfall"]
                        }
                    ]
                }
            ],
            "diseases": [
                {
                    "name": "Maize Leaf Blight",
                    "description": "Fungal disease causing yield loss",
                    "symptoms": "Long brown lesions on leaves, starting from tips",
                    "affected_crops": ["Maize"],
                    "severity": "high",
                    "treatments": [
                        {
                            "name": "Fungicide Application",
                            "type": "Chemical",
                            "application": "Apply fungicide at first sign of disease, repeat every 14 days",
                            "effectiveness": "High",
                            "cost_level": "Medium"
                        },
                        {
                            "name": "Resistant Varieties",
                            "type": "Preventive",
                            "application": "Plant resistant varieties like SC 529, SC 653",
                            "effectiveness": "High",
                            "cost_level": "Low"
                        },
                        {
                            "name": "Crop Rotation",
                            "type": "Cultural",
                            "application": "Rotate with non-host crops like legumes",
                            "effectiveness": "Medium",
                            "cost_level": "Low"
                        }
                    ]
                },
                {
                    "name": "Tomato Early Blight",
                    "description": "Common fungal disease in tomatoes",
                    "symptoms": "Dark spots with concentric rings, starting on older leaves",
                    "affected_crops": ["Tomato"],
                    "severity": "medium",
                    "treatments": [
                        {
                            "name": "Remove Infected Leaves",
                            "type": "Cultural",
                            "application": "Remove and destroy infected plant parts",
                            "effectiveness": "Medium",
                            "cost_level": "Low"
                        },
                        {
                            "name": "Copper-based Fungicide",
                            "type": "Chemical",
                            "application": "Apply preventively or at first symptoms",
                            "effectiveness": "High",
                            "cost_level": "Medium"
                        }
                    ]
                }
            ]
        }
