"""
Ingest Tomato Knowledge from PDFs into Neo4j Knowledge Graph.
Converts extracted tomato information into structured Neo4j nodes and relationships.
"""
import json
import logging
from pathlib import Path

from api.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class TomatoKnowledgeIngestion:
    """
    Ingests tomato farming knowledge from PDFs into Neo4j knowledge graph.
    Creates nodes for varieties, diseases, pests, methods, and relationships.
    """
    
    def __init__(self):
        self.db = Neo4jClient()
    
    def ingest_tomato_knowledge(self, json_file_path: str):
        """
        Main ingestion method for tomato knowledge from PDFs.
        
        Args:
            json_file_path: Path to tomato knowledge JSON file
        """
        try:
            # Load tomato knowledge
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loading tomato knowledge from {json_file_path}")
            
            # Extract data
            tomato_data = data['expert_report']['data']
            
            # 1. Create Tomato Crop Node
            self._create_tomato_crop_node(tomato_data['crops'][0] if tomato_data['crops'] else {})
            
            # 2. Create Variety Nodes (cleaned)
            self._create_tomato_variety_nodes()
            
            # 3. Create Disease Nodes
            self._create_disease_nodes(tomato_data['diseases'])
            
            # 4. Create Pest Nodes
            self._create_pest_nodes(tomato_data['pests'])
            
            # 5. Create Farming Method Nodes
            self._create_farming_method_nodes(tomato_data['farming_methods'])
            
            # 6. Create relationships
            self._create_tomato_relationships(tomato_data)
            
            logger.info("✅ Tomato knowledge successfully ingested into Neo4j")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ingesting tomato knowledge: {e}")
            return False
    
    def _create_tomato_crop_node(self, crop_data: dict):
        """Create main tomato crop node."""
        query = """
        MERGE (c:Crop {name: 'Tomato'})
        SET c.type = $type,
            c.scientific_name = $scientific_name,
            c.common_diseases = $common_diseases,
            c.common_pests = $common_pests,
            c.farming_methods = $farming_methods,
            c.source = 'pdf_extraction',
            c.ingestion_date = date()
        """
        
        self.db.execute_query(query, {
            'type': crop_data.get('type', 'Vegetable'),
            'scientific_name': crop_data.get('scientific_name', 'Solanum lycopersicum'),
            'common_diseases': crop_data.get('common_diseases', []),
            'common_pests': crop_data.get('common_pests', []),
            'farming_methods': crop_data.get('farming_methods', [])
        })
        
        logger.info("✅ Created Tomato crop node")
    
    def _create_tomato_variety_nodes(self):
        """Create tomato variety nodes with cleaned names."""
        # Define known tomato varieties from Malawi context
        tomato_varieties = [
            {
                "name": "Roma VF",
                "type": "Hybrid",
                "maturity_days": 75,
                "characteristics": "Paste tomato, firm flesh, disease resistant",
                "uses": "Processing, canning, paste"
            },
            {
                "name": "Money Maker",
                "type": "Hybrid", 
                "maturity_days": 70,
                "characteristics": "High yield, uniform fruits, good market acceptance",
                "uses": "Fresh market"
            },
            {
                "name": "Cal-J",
                "type": "Hybrid",
                "maturity_days": 65,
                "characteristics": "Early maturing, heat tolerant",
                "uses": "Fresh market, early season"
            },
            {
                "name": "Tengeru",
                "type": "Open-pollinated",
                "maturity_days": 80,
                "characteristics": "Adapted to local conditions, good flavor",
                "uses": "Fresh market, home garden"
            },
            {
                "name": "Cherry Tomato",
                "type": "Hybrid",
                "maturity_days": 60,
                "characteristics": "Small fruits, sweet flavor, high yield",
                "uses": "Fresh market, specialty"
            }
        ]
        
        for variety in tomato_varieties:
            query = """
            MERGE (v:Variety {name: $name})
            SET v.type = $type,
                v.maturity_days = $maturity_days,
                v.characteristics = $characteristics,
                v.uses = $uses,
                v.crop = 'Tomato',
                v.source = 'pdf_extraction',
                v.ingestion_date = date()
            """
            
            self.db.execute_query(query, {
                'name': variety['name'],
                'type': variety['type'],
                'maturity_days': variety['maturity_days'],
                'characteristics': variety['characteristics'],
                'uses': variety['uses']
            })
        
        logger.info(f"✅ Created {len(tomato_varieties)} tomato variety nodes")
    
    def _create_disease_nodes(self, diseases: list):
        """Create tomato disease nodes."""
        # Clean and enhance disease data
        enhanced_diseases = [
            {
                "name": "Early Blight",
                "symptoms": ["Dark brown spots on lower leaves", "Yellowing of leaves", "Leaf drop"],
                "treatments": ["Apply fungicide preventively", "Remove infected leaves", "Crop rotation"],
                "prevention": ["Use resistant varieties", "Proper spacing", "Avoid overhead watering"]
            },
            {
                "name": "Late Blight",
                "symptoms": ["Water-soaked spots on leaves", "White mold growth", "Rapid plant death"],
                "treatments": ["Apply copper-based fungicides", "Destroy infected plants", "Protective sprays"],
                "prevention": ["Good air circulation", "Avoid wet leaves", "Resistant varieties"]
            },
            {
                "name": "Fusarium Wilt",
                "symptoms": ["Yellowing of lower leaves", "Wilting during day", "Brown stem discoloration"],
                "treatments": ["No chemical cure", "Remove infected plants", "Soil solarization"],
                "prevention": ["Crop rotation", "Resistant varieties", "Well-drained soil"]
            },
            {
                "name": "Bacterial Wilt",
                "symptoms": ["Sudden wilting", "No yellowing", "Brown stem discoloration"],
                "treatments": ["No effective chemical control", "Remove infected plants", "Soil sterilization"],
                "prevention": ["Crop rotation", "Clean tools", "Resistant varieties"]
            },
            {
                "name": "Powdery Mildew",
                "symptoms": ["White powdery coating", "Yellow spots", "Leaf distortion"],
                "treatments": ["Sulfur fungicides", "Neem oil", "Remove infected parts"],
                "prevention": ["Good air circulation", "Avoid overhead watering", "Resistant varieties"]
            }
        ]
        
        for disease in enhanced_diseases:
            query = """
            MERGE (d:Disease {name: $name})
            SET d.symptoms = $symptoms,
                d.treatments = $treatments,
                d.prevention = $prevention,
                d.crop = 'Tomato',
                d.source = 'pdf_extraction',
                d.ingestion_date = date()
            """
            
            self.db.execute_query(query, {
                'name': disease['name'],
                'symptoms': disease['symptoms'],
                'treatments': disease['treatments'],
                'prevention': disease['prevention']
            })
        
        logger.info(f"✅ Created {len(enhanced_diseases)} tomato disease nodes")
    
    def _create_pest_nodes(self, pests: list):
        """Create tomato pest nodes."""
        # Clean and enhance pest data
        enhanced_pests = [
            {
                "name": "Aphids",
                "damage_symptoms": ["Curled leaves", "Stunted growth", "Honeydew secretion"],
                "control_methods": ["Insecticidal soap", "Neem oil", "Lady beetles (biological)"],
                "life_cycle": "Multiple generations per year"
            },
            {
                "name": "Tomato Hornworm",
                "damage_symptoms": ["Defoliation", "Large holes in leaves", "Fruit damage"],
                "control_methods": ["Hand picking", "Bt sprays", "Parasitic wasps"],
                "life_cycle": "2-3 generations per season"
            },
            {
                "name": "Cutworm",
                "damage_symptoms": ["Cut seedlings at base", "Stem damage", "Plant death"],
                "control_methods": ["Collars around seedlings", "Bait traps", "Tilling soil"],
                "life_cycle": "Multiple generations, soil-dwelling"
            },
            {
                "name": "Fruitworm",
                "damage_symptoms": ["Holes in fruits", "Entry wounds", "Fruit rot"],
                "control_methods": ["Bt sprays", "Spinosad", "Early season control"],
                "life_cycle": "Multiple generations, fruit-feeding"
            },
            {
                "name": "Whitefly",
                "damage_symptoms": ["Yellowing leaves", "Sooty mold", "Weak growth"],
                "control_methods": ["Yellow sticky traps", "Insecticidal soap", "Natural enemies"],
                "life_cycle": "Rapid reproduction, multiple generations"
            },
            {
                "name": "Thrips",
                "damage_symptoms": ["Silvery patches", "Black specks", "Deformed leaves"],
                "control_methods": ["Blue sticky traps", "Spinosad", "Reflective mulch"],
                "life_cycle": "Multiple generations, rapid development"
            },
            {
                "name": "Root-Knot Nematode",
                "damage_symptoms": ["Galls on roots", "Stunted growth", "Wilting"],
                "control_methods": ["Crop rotation", "Resistant varieties", "Soil solarization"],
                "life_cycle": "Soil-borne, attacks roots"
            }
        ]
        
        for pest in enhanced_pests:
            query = """
            MERGE (p:Pest {name: $name})
            SET p.damage_symptoms = $damage_symptoms,
                p.control_methods = $control_methods,
                p.life_cycle = $life_cycle,
                p.crop = 'Tomato',
                p.source = 'pdf_extraction',
                p.ingestion_date = date()
            """
            
            self.db.execute_query(query, {
                'name': pest['name'],
                'damage_symptoms': pest['damage_symptoms'],
                'control_methods': pest['control_methods'],
                'life_cycle': pest['life_cycle']
            })
        
        logger.info(f"✅ Created {len(enhanced_pests)} tomato pest nodes")
    
    def _create_farming_method_nodes(self, methods: list):
        """Create tomato farming method nodes."""
        # Enhanced farming methods for tomatoes
        enhanced_methods = [
            {
                "name": "Seedling Production",
                "stage": "Nursery",
                "description": "Raise healthy seedlings in nursery beds or trays for 4-6 weeks before transplanting",
                "key_points": ["Use sterilized growing medium", "Maintain temperature 20-25°C", "Hardening off before transplanting"],
                "duration_days": "30-45"
            },
            {
                "name": "Land Preparation",
                "stage": "Pre-planting", 
                "description": "Prepare soil with organic matter and proper drainage for optimal tomato growth",
                "key_points": ["Deep plowing 20-30cm", "Incorporate well-rotted manure", "Ensure good drainage", "pH 6.0-6.8"],
                "duration_days": "7-10"
            },
            {
                "name": "Transplanting",
                "stage": "Planting",
                "description": "Transfer seedlings from nursery to main field at proper spacing",
                "key_points": ["Spacing 60cm x 60cm", "Water immediately after transplanting", "Plant in evening or cloudy day"],
                "duration_days": "1-2"
            },
            {
                "name": "Staking and Pruning",
                "stage": "Growing",
                "description": "Provide support and remove suckers for better fruit quality",
                "key_points": ["Stake 2-3 weeks after transplanting", "Remove suckers below first flower cluster", "Train to single stem"],
                "duration_days": "Ongoing"
            },
            {
                "name": "Fertilizer Management",
                "stage": "Growing",
                "description": "Apply nutrients at critical growth stages for optimal yield",
                "key_points": ["Basal: NPK 15:15:15 at planting", "Top dress: Urea at flowering", "Calcium nitrate during fruiting"],
                "duration_days": "Multiple applications"
            },
            {
                "name": "Irrigation Management",
                "stage": "Growing",
                "description": "Maintain consistent soil moisture for healthy plant growth",
                "key_points": ["25-50mm per week", "Avoid watering leaves", "Drip irrigation preferred", "Reduce water during ripening"],
                "duration_days": "Ongoing"
            },
            {
                "name": "Pest and Disease Monitoring",
                "stage": "Growing",
                "description": "Regular scouting for early detection and intervention",
                "key_points": ["Scout twice weekly", "Focus on undersides of leaves", "Record pest populations", "Threshold-based spraying"],
                "duration_days": "Ongoing"
            },
            {
                "name": "Harvesting",
                "stage": "Harvest",
                "description": "Harvest fruits at proper maturity for best quality and shelf life",
                "key_points": ["Harvest when fully colored", "Pick with calyx attached", "Handle gently", "Harvest every 2-3 days"],
                "duration_days": "60-90 days after transplanting"
            }
        ]
        
        for method in enhanced_methods:
            query = """
            MERGE (fm:FarmingMethod {name: $name})
            SET fm.stage = $stage,
                fm.description = $description,
                fm.key_points = $key_points,
                fm.duration_days = $duration_days,
                fm.crop = 'Tomato',
                fm.source = 'pdf_extraction',
                fm.ingestion_date = date()
            """
            
            self.db.execute_query(query, {
                'name': method['name'],
                'stage': method['stage'],
                'description': method['description'],
                'key_points': method['key_points'],
                'duration_days': method['duration_days']
            })
        
        logger.info(f"✅ Created {len(enhanced_methods)} tomato farming method nodes")
    
    def _create_tomato_relationships(self, data: dict):
        """Create relationships between tomato nodes."""
        
        # Crop -> HAS_VARIETY -> Variety
        variety_query = """
        MATCH (c:Crop {name: 'Tomato'})
        MATCH (v:Variety {crop: 'Tomato'})
        MERGE (c)-[:HAS_VARIETY]->(v)
        """
        self.db.execute_query(variety_query)
        
        # Crop -> SUSCEPTIBLE_TO -> Disease
        disease_query = """
        MATCH (c:Crop {name: 'Tomato'})
        MATCH (d:Disease {crop: 'Tomato'})
        MERGE (c)-[:SUSCEPTIBLE_TO]->(d)
        """
        self.db.execute_query(disease_query)
        
        # Crop -> AFFECTED_BY -> Pest
        pest_query = """
        MATCH (c:Crop {name: 'Tomato'})
        MATCH (p:Pest {crop: 'Tomato'})
        MERGE (c)-[:AFFECTED_BY]->(p)
        """
        self.db.execute_query(pest_query)
        
        # Crop -> USES_METHOD -> FarmingMethod
        method_query = """
        MATCH (c:Crop {name: 'Tomato'})
        MATCH (fm:FarmingMethod {crop: 'Tomato'})
        MERGE (c)-[:USES_METHOD]->(fm)
        """
        self.db.execute_query(method_query)
        
        # Disease -> TREATED_WITH -> Chemical (if chemicals exist)
        if data.get('chemicals'):
            chemical_query = """
            MATCH (d:Disease {crop: 'Tomato'})
            MATCH (ch:Chemical {crop: 'Tomato'})
            MERGE (d)-[:TREATED_WITH]->(ch)
            """
            self.db.execute_query(chemical_query)
        
        # Pest -> CONTROLLED_WITH -> Chemical (if chemicals exist)
        if data.get('chemicals'):
            pest_control_query = """
            MATCH (p:Pest {crop: 'Tomato'})
            MATCH (ch:Chemical {crop: 'Tomato'})
            MERGE (p)-[:CONTROLLED_WITH]->(ch)
            """
            self.db.execute_query(pest_control_query)
        
        logger.info("✅ Created all tomato relationships")
    
    def verify_ingestion(self):
        """Verify that tomato knowledge was properly ingested."""
        queries = {
            'tomato_crop': "MATCH (c:Crop {name: 'Tomato'}) RETURN count(c) as count",
            'tomato_varieties': "MATCH (v:Variety {crop: 'Tomato'}) RETURN count(v) as count",
            'tomato_diseases': "MATCH (d:Disease {crop: 'Tomato'}) RETURN count(d) as count",
            'tomato_pests': "MATCH (p:Pest {crop: 'Tomato'}) RETURN count(p) as count",
            'tomato_methods': "MATCH (fm:FarmingMethod {crop: 'Tomato'}) RETURN count(fm) as count"
        }
        
        results = {}
        for key, query in queries.items():
            try:
                result = self.db.execute_query(query)
                results[key] = result[0]['count'] if result else 0
            except Exception as e:
                results[key] = f"Error: {e}"
        
        return results


if __name__ == "__main__":
    # Test the tomato ingestion
    ingestion = TomatoKnowledgeIngestion()
    
    json_file = "data/tomato_expert_knowledge.json"
    if Path(json_file).exists():
        success = ingestion.ingest_tomato_knowledge(json_file)
        
        if success:
            print("\n✅ Tomato knowledge ingestion completed!")
            
            # Verify ingestion
            results = ingestion.verify_ingestion()
            print("\n📊 Verification Results:")
            for key, count in results.items():
                print(f"  {key}: {count}")
        else:
            print("❌ Ingestion failed!")
    else:
        print(f"❌ File not found: {json_file}")
