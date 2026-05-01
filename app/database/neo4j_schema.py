"""
Neo4j Schema Definition for FDA-AI Knowledge Graph.
Defines all entity nodes, relationships, and constraints for agricultural knowledge.
"""
from typing import List, Dict, Any
import logging

from app.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class Neo4jSchema:
    """
    Manages Neo4j database schema for agricultural knowledge graph.
    Implements all entity nodes and relationships as specified in assignment.
    """
    
    def __init__(self):
        self.db = Neo4jClient()
    
    def create_all_constraints(self):
        """Create all constraints and indexes for performance."""
        constraints = [
            # Unique constraints
            "CREATE CONSTRAINT crop_name IF NOT EXISTS FOR (c:Crop) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT disease_name IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT pest_name IF NOT EXISTS FOR (p:Pest) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT fertilizer_name IF NOT EXISTS FOR (f:Fertilizer) REQUIRE f.name IS UNIQUE",
            "CREATE CONSTRAINT soil_type_name IF NOT EXISTS FOR (s:SoilType) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT region_name IF NOT EXISTS FOR (r:Region) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT treatment_id IF NOT EXISTS FOR (t:Treatment) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT method_name IF NOT EXISTS FOR (m:FarmingMethod) REQUIRE m.name IS UNIQUE",
            "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:ResearchPaper) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT expert_id IF NOT EXISTS FOR (e:Expert) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:Farmer) REQUIRE u.id IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX crop_type_index IF NOT EXISTS FOR (c:Crop) ON (c.type)",
            "CREATE INDEX disease_severity_index IF NOT EXISTS FOR (d:Disease) ON (d.severity)",
            "CREATE INDEX symptom_text_index IF NOT EXISTS FOR (s:Symptom) ON (s.description)",
            "CREATE INDEX weather_season_index IF NOT EXISTS FOR (w:WeatherPattern) ON (w.season)",
        ]
        
        for constraint in constraints:
            try:
                self.db.execute_query(constraint)
                logger.info(f"Created: {constraint[:50]}...")
            except Exception as e:
                logger.warning(f"Constraint may already exist: {e}")
    
    def create_entity_nodes(self, entity_type: str, data: List[Dict[str, Any]]):
        """
        Create entity nodes in batch.
        
        Args:
            entity_type: Type of entity (Crop, Disease, etc.)
            data: List of entity data dictionaries
        """
        cypher_query = f"""
        UNWIND $data as item
        MERGE (e:{entity_type} {{name: item.name}})
        SET e += apoc.map.removeKeys(item, ['name'])
        RETURN e.name as name
        """
        
        try:
            result = self.db.execute_query(cypher_query, {"data": data})
            logger.info(f"Created/Updated {len(result)} {entity_type} nodes")
            return True
        except Exception as e:
            logger.error(f"Error creating {entity_type} nodes: {e}")
            return False
    
    def create_relationships(self, rel_type: str, from_type: str, to_type: str, 
                            from_key: str, to_key: str, relationships: List[Dict]):
        """
        Create relationships between nodes.
        
        Args:
            rel_type: Relationship type (SUSCEPTIBLE_TO, TREATED_BY, etc.)
            from_type: Source node label
            to_type: Target node label
            from_key: Key to match source
            to_key: Key to match target
            relationships: List of relationship data
        """
        cypher_query = f"""
        UNWIND $relationships as rel
        MATCH (a:{from_type} {{{from_key}: rel.from}})
        MATCH (b:{to_type} {{{to_key}: rel.to}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += apoc.map.removeKeys(rel, ['from', 'to'])
        RETURN count(r) as count
        """
        
        try:
            result = self.db.execute_query(cypher_query, {"relationships": relationships})
            count = result[0]["count"] if result else 0
            logger.info(f"Created {count} {rel_type} relationships")
            return True
        except Exception as e:
            logger.error(f"Error creating {rel_type} relationships: {e}")
            return False
    
    def setup_complete_schema(self):
        """
        Setup complete schema with sample agricultural data for Malawi.
        """
        logger.info("Setting up complete Neo4j schema...")
        
        # 1. Create constraints
        self.create_all_constraints()
        
        # 2. Create Crop nodes
        crops = [
            {"name": "Maize", "type": "Cereal", "family": "Poaceae", 
             "description": "Staple food crop in Malawi", "season": "Rainy"},
            {"name": "Soybeans", "type": "Legume", "family": "Fabaceae",
             "description": "Important protein source and soil improver", "season": "Rainy"},
            {"name": "Groundnuts", "type": "Legume", "family": "Fabaceae",
             "description": "Cash crop and food source", "season": "Rainy"},
            {"name": "Tobacco", "type": "Cash Crop", "family": "Solanaceae",
             "description": "Major export crop for Malawi", "season": "Rainy"},
            {"name": "Cassava", "type": "Root Crop", "family": "Euphorbiaceae",
             "description": "Drought-resistant staple", "season": "Year-round"},
            {"name": "Rice", "type": "Cereal", "family": "Poaceae",
             "description": "Grown in wetland areas", "season": "Rainy"},
            {"name": "Tomato", "type": "Vegetable", "family": "Solanaceae",
             "description": "Popular vegetable crop", "season": "Year-round"},
        ]
        self.create_entity_nodes("Crop", crops)
        
        # 3. Create Disease nodes
        diseases = [
            {"name": "Maize Leaf Blight", "severity": "High", "type": "Fungal",
             "symptoms": "Long brown lesions on leaves", 
             "favorable_conditions": "High humidity, warm temperatures"},
            {"name": "Maize Streak Virus", "severity": "High", "type": "Viral",
             "symptoms": "Yellow streaks along veins, stunted growth",
             "favorable_conditions": "Dry conditions, leafhopper vectors"},
            {"name": "Early Blight", "severity": "Medium", "type": "Fungal",
             "symptoms": "Dark spots with concentric rings",
             "favorable_conditions": "Warm, humid weather"},
            {"name": "Groundnut Rosette", "severity": "High", "type": "Viral",
             "symptoms": "Mottled leaves, stunted plants",
             "favorable_conditions": "Aphid vectors"},
        ]
        self.create_entity_nodes("Disease", diseases)
        
        # 4. Create Pest nodes
        pests = [
            {"name": "Fall Armyworm", "type": "Caterpillar", 
             "description": "Destructive pest of maize",
             "active_season": "Rainy season", "control_methods": "Biological, Chemical"},
            {"name": "Aphids", "type": "Sucking insect",
             "description": "Transmit viral diseases",
             "active_season": "Year-round", "control_methods": "Biological, Chemical"},
            {"name": "Stem Borer", "type": "Caterpillar",
             "description": "Bores into maize stalks",
             "active_season": "Rainy season", "control_methods": "Cultural, Chemical"},
        ]
        self.create_entity_nodes("Pest", pests)
        
        # 5. Create Fertilizer nodes
        fertilizers = [
            {"name": "NPK 23:21:0+4S", "type": "Compound", 
             "nutrients": {"N": 23, "P": 21, "K": 0, "S": 4},
             "application": "Basal dressing", "rate_kg_ha": 200},
            {"name": "Urea", "type": "Nitrogen",
             "nutrients": {"N": 46}, 
             "application": "Top dressing", "rate_kg_ha": 100},
            {"name": "D-Compound", "type": "Compound",
             "nutrients": {"N": 8, "P": 18, "K": 15},
             "application": "Basal dressing", "rate_kg_ha": 150},
        ]
        self.create_entity_nodes("Fertilizer", fertilizers)
        
        # 6. Create SoilType nodes
        soils = [
            {"name": "Loam", "texture": "Sandy-clay loam", 
             "drainage": "Good", "fertility": "High",
             "suitable_crops": ["Maize", "Tobacco", "Vegetables"]},
            {"name": "Clay", "texture": "Heavy clay",
             "drainage": "Poor", "fertility": "High",
             "suitable_crops": ["Rice", "Cassava"]},
            {"name": "Sandy", "texture": "Sandy",
             "drainage": "Excessive", "fertility": "Low",
             "suitable_crops": ["Groundnuts", "Sweet potatoes"]},
        ]
        self.create_entity_nodes("SoilType", soils)
        
        # 7. Create Region nodes
        regions = [
            {"name": "Central Region", "climate": "Subtropical",
             "rainfall_mm": 800, "main_crops": ["Maize", "Tobacco", "Groundnuts"]},
            {"name": "Southern Region", "climate": "Tropical",
             "rainfall_mm": 700, "main_crops": ["Maize", "Cassava", "Cotton"]},
            {"name": "Northern Region", "climate": "Highland",
             "rainfall_mm": 1200, "main_crops": ["Maize", "Beans", "Coffee"]},
        ]
        self.create_entity_nodes("Region", regions)
        
        # 8. Create Treatment nodes
        treatments = [
            {"id": "T1", "name": "Mancozeb Spray", "type": "Fungicide",
             "application": "Spray every 14 days", "effectiveness": "High"},
            {"id": "T2", "name": "Crop Rotation", "type": "Cultural",
             "application": "Rotate with legumes", "effectiveness": "Medium"},
            {"id": "T3", "name": "Resistant Varieties", "type": "Preventive",
             "application": "Plant resistant hybrids", "effectiveness": "High"},
        ]
        self.create_entity_nodes("Treatment", treatments)
        
        # 9. Create Relationships
        
        # Crop -> SUSCEPTIBLE_TO -> Disease
        crop_disease_rel = [
            {"from": "Maize", "to": "Maize Leaf Blight", "severity": "High"},
            {"from": "Maize", "to": "Maize Streak Virus", "severity": "High"},
            {"from": "Tomato", "to": "Early Blight", "severity": "Medium"},
        ]
        self.create_relationships("SUSCEPTIBLE_TO", "Crop", "Disease", "name", "name", crop_disease_rel)
        
        # Disease -> TREATED_BY -> Treatment
        disease_treatment_rel = [
            {"from": "Maize Leaf Blight", "to": "T1", "priority": "First line"},
            {"from": "Maize Leaf Blight", "to": "T2", "priority": "Preventive"},
            {"from": "Maize Streak Virus", "to": "T3", "priority": "Primary"},
        ]
        self.create_relationships("TREATED_BY", "Disease", "Treatment", "name", "id", disease_treatment_rel)
        
        # Crop -> REQUIRES -> Fertilizer
        crop_fertilizer_rel = [
            {"from": "Maize", "to": "NPK 23:21:0+4S", "stage": "Planting", "rate": "200 kg/ha"},
            {"from": "Maize", "to": "Urea", "stage": "Top dressing", "rate": "100 kg/ha"},
        ]
        self.create_relationships("REQUIRES", "Crop", "Fertilizer", "name", "name", crop_fertilizer_rel)
        
        # Region -> SUITABLE_FOR -> Crop
        region_crop_rel = [
            {"from": "Central Region", "to": "Maize", "suitability": "High"},
            {"from": "Central Region", "to": "Tobacco", "suitability": "High"},
            {"from": "Southern Region", "to": "Cassava", "suitability": "High"},
        ]
        self.create_relationships("SUITABLE_FOR", "Region", "Crop", "name", "name", region_crop_rel)
        
        logger.info("✓ Complete schema setup finished")
    
    def get_schema_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        queries = {
            "crops": "MATCH (c:Crop) RETURN count(c) as count",
            "diseases": "MATCH (d:Disease) RETURN count(d) as count",
            "pests": "MATCH (p:Pest) RETURN count(p) as count",
            "fertilizers": "MATCH (f:Fertilizer) RETURN count(f) as count",
            "treatments": "MATCH (t:Treatment) RETURN count(t) as count",
            "relationships": "MATCH ()-[r]->() RETURN count(r) as count"
        }
        
        stats = {}
        for key, query in queries.items():
            try:
                result = self.db.execute_query(query)
                stats[key] = result[0]["count"] if result else 0
            except:
                stats[key] = 0
        
        return stats


if __name__ == "__main__":
    schema = Neo4jSchema()
    schema.setup_complete_schema()
    
    print("\nSchema Statistics:")
    stats = schema.get_schema_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
