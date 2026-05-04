"""
Ingest Cabbage Expert Knowledge into Neo4j Knowledge Graph.
Converts expert interview data into structured Neo4j nodes and relationships.
"""
import json
import logging
from pathlib import Path

from app.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class CabbageKnowledgeIngestion:
    """
    Ingests cabbage farming expertise into Neo4j knowledge graph.
    Creates nodes for varieties, methods, chemicals, and relationships.
    """
    
    def __init__(self):
        self.db = Neo4jClient()
    
    def ingest_cabbage_knowledge(self, json_file_path: str):
        """
        Main ingestion method for cabbage expert knowledge.
        
        Args:
            json_file_path: Path to cabbage knowledge JSON file
        """
        try:
            # Load expert knowledge
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loading cabbage knowledge from {json_file_path}")
            
            # Extract data
            expert_data = data['expert_report']['data']
            
            # 1. Create Crop Node
            self._create_crop_node(expert_data['crops'][0])
            
            # 2. Create Variety Nodes
            self._create_variety_nodes(expert_data['crops'][0]['varieties'])
            
            # 3. Create Farming Method Nodes
            self._create_farming_method_nodes(expert_data['farming_methods'])
            
            # 4. Create Chemical Nodes
            self._create_chemical_nodes(expert_data['chemicals'])
            
            # 5. Create relationships
            self._create_relationships(expert_data)
            
            logger.info("✅ Cabbage knowledge successfully ingested into Neo4j")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ingesting cabbage knowledge: {e}")
            return False
    
    def _create_crop_node(self, crop_data: dict):
        """Create main cabbage crop node."""
        query = """
        MERGE (c:Crop {name: 'Cabbage'})
        SET c.type = $type,
            c.spacing_cm = $spacing_cm,
            c.nursery_duration_days = $nursery_duration_days,
            c.source = 'expert_interview',
            c.ingestion_date = date()
        """
        
        self.db.execute_query(query, {
            'type': crop_data['type'],
            'spacing_cm': crop_data['spacing_cm'],
            'nursery_duration_days': crop_data['nursery_duration_days']
        })
        
        logger.info("✅ Created Cabbage crop node")
    
    def _create_variety_nodes(self, varieties: list):
        """Create cabbage variety nodes."""
        for variety in varieties:
            query = """
            MERGE (v:Variety {name: $name})
            SET v.type = $type,
                v.maturity_days = $maturity_days,
                v.yield_tons_ha = $yield_tons_ha,
                v.characteristics = $characteristics,
                v.market_acceptance = $market_acceptance,
                v.crop = 'Cabbage',
                v.source = 'expert_interview',
                v.ingestion_date = date()
            """
            
            self.db.execute_query(query, {
                'name': variety['name'],
                'type': variety['type'],
                'maturity_days': variety['maturity_days'],
                'yield_tons_ha': variety['yield_tons_ha'],
                'characteristics': variety['characteristics'],
                'market_acceptance': variety['market_acceptance']
            })
        
        logger.info(f"✅ Created {len(varieties)} cabbage variety nodes")
    
    def _create_farming_method_nodes(self, methods: list):
        """Create farming method nodes."""
        for method in methods:
            query = """
            MERGE (fm:FarmingMethod {name: $name})
            SET fm.stage = $stage,
                fm.steps = $steps,
                fm.crop = 'Cabbage',
                fm.source = 'expert_interview',
                fm.ingestion_date = date()
            """
            
            self.db.execute_query(query, {
                'name': method['name'],
                'stage': method['stage'],
                'steps': method['steps']
            })
            
            # Create fertilizer schedule nodes if present
            if 'fertilizer_schedule' in method:
                self._create_fertilizer_schedule_nodes(method['fertilizer_schedule'], method['name'])
        
        logger.info(f"✅ Created {len(methods)} farming method nodes")
    
    def _create_fertilizer_schedule_nodes(self, schedules: list, method_name: str):
        """Create fertilizer schedule nodes."""
        for schedule in schedules:
            query = """
            MERGE (fs:FertilizerSchedule {
                timing: $timing,
                fertilizer_type: $type,
                application: $application,
                purpose: $purpose,
                method: $method,
                source: 'expert_interview',
                ingestion_date: date()
            })
            """
            
            self.db.execute_query(query, {
                'timing': schedule['timing'],
                'type': schedule['type'],
                'application': schedule['application'],
                'purpose': schedule['purpose'],
                'method': method_name
            })
    
    def _create_chemical_nodes(self, chemicals: list):
        """Create chemical nodes."""
        for chemical in chemicals:
            query = """
            MERGE (ch:Chemical {name: $type})
            SET ch.application_rate = $application_rate,
                ch.mixing_instructions = $mixing_instructions,
                ch.safety_precautions = $safety_precautions,
                ch.crop = 'Cabbage',
                ch.source = 'expert_interview',
                ch.ingestion_date = date()
            """
            
            self.db.execute_query(query, {
                'type': chemical['type'],
                'application_rate': chemical['application_rate'],
                'mixing_instructions': chemical['mixing_instructions'],
                'safety_precautions': chemical['safety_precautions']
            })
        
        logger.info(f"✅ Created {len(chemicals)} chemical nodes")
    
    def _create_relationships(self, data: dict):
        """Create relationships between nodes."""
        
        # Crop -> HAS_VARIETY -> Variety
        for variety in data['crops'][0]['varieties']:
            query = """
            MATCH (c:Crop {name: 'Cabbage'})
            MATCH (v:Variety {name: $variety_name})
            MERGE (c)-[:HAS_VARIETY]->(v)
            """
            self.db.execute_query(query, {'variety_name': variety['name']})
        
        # Crop -> USES_METHOD -> FarmingMethod
        for method in data['farming_methods']:
            query = """
            MATCH (c:Crop {name: 'Cabbage'})
            MATCH (fm:FarmingMethod {name: $method_name})
            MERGE (c)-[:USES_METHOD]->(fm)
            """
            self.db.execute_query(query, {'method_name': method['name']})
            
            # Method -> REQUIRES -> FertilizerSchedule
            if 'fertilizer_schedule' in method:
                for schedule in method['fertilizer_schedule']:
                    query = """
                    MATCH (fm:FarmingMethod {name: $method_name})
                    MATCH (fs:FertilizerSchedule {timing: $timing, method: $method_name})
                    MERGE (fm)-[:REQUIRES]->(fs)
                    """
                    self.db.execute_query(query, {
                        'method_name': method['name'],
                        'timing': schedule['timing']
                    })
        
        # Crop -> TREATED_WITH -> Chemical
        for chemical in data['chemicals']:
            query = """
            MATCH (c:Crop {name: 'Cabbage'})
            MATCH (ch:Chemical {name: $chemical_name})
            MERGE (c)-[:TREATED_WITH]->(ch)
            """
            self.db.execute_query(query, {'chemical_name': chemical['type']})
        
        logger.info("✅ Created all relationships")
    
    def verify_ingestion(self):
        """Verify that cabbage knowledge was properly ingested."""
        queries = {
            'cabbage_crop': "MATCH (c:Crop {name: 'Cabbage'}) RETURN count(c) as count",
            'cabbage_varieties': "MATCH (v:Variety {crop: 'Cabbage'}) RETURN count(v) as count",
            'cabbage_methods': "MATCH (fm:FarmingMethod {crop: 'Cabbage'}) RETURN count(fm) as count",
            'cabbage_chemicals': "MATCH (ch:Chemical {crop: 'Cabbage'}) RETURN count(ch) as count"
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
    # Test the ingestion
    ingestion = CabbageKnowledgeIngestion()
    
    json_file = "data/cabbage_expert_knowledge.json"
    if Path(json_file).exists():
        success = ingestion.ingest_cabbage_knowledge(json_file)
        
        if success:
            print("\n✅ Cabbage knowledge ingestion completed!")
            
            # Verify ingestion
            results = ingestion.verify_ingestion()
            print("\n📊 Verification Results:")
            for key, count in results.items():
                print(f"  {key}: {count}")
        else:
            print("❌ Ingestion failed!")
    else:
        print(f"❌ File not found: {json_file}")
