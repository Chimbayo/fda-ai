"""
Extract Tomato Knowledge from PDFs and create structured knowledge base.
Processes tomato-specific information from PDF documents and converts to JSON format.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import PyPDF2
import re

logger = logging.getLogger(__name__)


class TomatoKnowledgeExtractor:
    """
    Extracts tomato farming knowledge from PDF documents and structures it
    for ingestion into the Neo4j knowledge graph.
    """
    
    def __init__(self):
        self.pdf_dir = Path("data/pdfs")
        self.tomato_knowledge = {
            "expert_report": {
                "expert_id": "PDF_TOMATO_001",
                "specialization": "Tomato Farming",
                "source": "PDF Documents: Agricultural Guides",
                "date": "2024-05-05",
                "data": {
                    "crops": [],
                    "varieties": [],
                    "farming_methods": [],
                    "diseases": [],
                    "pests": [],
                    "chemicals": [],
                    "harvesting": [],
                    "regional_adaptations": {}
                }
            }
        }
    
    def extract_from_pdfs(self) -> Dict[str, Any]:
        """
        Main method to extract tomato knowledge from all PDFs.
        
        Returns:
            Structured tomato knowledge dictionary
        """
        try:
            # Process each PDF
            for pdf_file in self.pdf_dir.glob("*.pdf"):
                if "tomato" in pdf_file.name.lower():
                    logger.info(f"Processing PDF: {pdf_file.name}")
                    self._process_pdf(pdf_file)
            
            # Structure the extracted information
            self._structure_knowledge()
            
            logger.info("✅ Tomato knowledge extraction completed")
            return self.tomato_knowledge
            
        except Exception as e:
            logger.error(f"❌ Error extracting tomato knowledge: {e}")
            return {}
    
    def _process_pdf(self, pdf_path: Path):
        """Extract text content from a PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
                
                # Extract specific information
                self._extract_tomato_info(text_content, pdf_path.name)
                
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
    
    def _extract_tomato_info(self, text: str, pdf_name: str):
        """Extract tomato-specific information from text content."""
        
        # Extract varieties
        varieties = self._extract_varieties(text)
        self.tomato_knowledge["expert_report"]["data"]["varieties"].extend(varieties)
        
        # Extract diseases
        diseases = self._extract_diseases(text)
        self.tomato_knowledge["expert_report"]["data"]["diseases"].extend(diseases)
        
        # Extract pests
        pests = self._extract_pests(text)
        self.tomato_knowledge["expert_report"]["data"]["pests"].extend(pests)
        
        # Extract farming methods
        methods = self._extract_farming_methods(text)
        self.tomato_knowledge["expert_report"]["data"]["farming_methods"].extend(methods)
        
        # Extract chemical recommendations
        chemicals = self._extract_chemicals(text)
        self.tomato_knowledge["expert_report"]["data"]["chemicals"].extend(chemicals)
        
        # Extract harvesting information
        harvesting = self._extract_harvesting_info(text)
        self.tomato_knowledge["expert_report"]["data"]["harvesting"].extend(harvesting)
    
    def _extract_varieties(self, text: str) -> List[Dict]:
        """Extract tomato varieties from text."""
        varieties = []
        
        # Look for variety names and characteristics
        variety_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:variety|hybrid| cultivar)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*-\s*(\d+)\s*days',
            r'(?:variety|hybrid):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in variety_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    variety_name = match[0]
                else:
                    variety_name = match
                
                # Extract maturity if mentioned
                maturity_match = re.search(rf'{re.escape(variety_name)}.*?(\d+)\s*days', text, re.IGNORECASE)
                maturity = maturity_match.group(1) if maturity_match else None
                
                varieties.append({
                    "name": variety_name,
                    "type": "Hybrid" if "hybrid" in text.lower() else "Open-pollinated",
                    "maturity_days": int(maturity) if maturity else None,
                    "source": "PDF extraction"
                })
        
        # Remove duplicates
        seen = set()
        unique_varieties = []
        for variety in varieties:
            key = variety["name"].lower()
            if key not in seen:
                seen.add(key)
                unique_varieties.append(variety)
        
        return unique_varieties
    
    def _extract_diseases(self, text: str) -> List[Dict]:
        """Extract tomato diseases from text."""
        diseases = []
        
        # Common tomato disease patterns
        disease_keywords = [
            "blight", " wilt", "spot", "mold", "rot", "virus", "mildew",
            "early blight", "late blight", "bacterial wilt", "fusarium wilt",
            "tomato yellow leaf curl", "powdery mildew", "septoria leaf spot"
        ]
        
        for keyword in disease_keywords:
            if keyword.lower() in text.lower():
                # Extract symptoms and treatments
                symptoms = self._extract_symptoms(text, keyword)
                treatments = self._extract_treatments(text, keyword)
                
                diseases.append({
                    "name": keyword.title(),
                    "symptoms": symptoms,
                    "treatments": treatments,
                    "prevention": self._extract_prevention(text, keyword),
                    "source": "PDF extraction"
                })
        
        return diseases
    
    def _extract_pests(self, text: str) -> List[Dict]:
        """Extract tomato pests from text."""
        pests = []
        
        # Common tomato pest patterns
        pest_keywords = [
            "aphid", "whitefly", "thrips", "hornworm", "cutworm", "fruitworm",
            "spider mite", "leafminer", "nematode", "armyworm"
        ]
        
        for keyword in pest_keywords:
            if keyword.lower() in text.lower():
                damage = self._extract_damage(text, keyword)
                control = self._extract_control_methods(text, keyword)
                
                pests.append({
                    "name": keyword.title(),
                    "damage_symptoms": damage,
                    "control_methods": control,
                    "source": "PDF extraction"
                })
        
        return pests
    
    def _extract_farming_methods(self, text: str) -> List[Dict]:
        """Extract farming methods from text."""
        methods = []
        
        # Look for farming method sections
        method_sections = [
            ("Planting", r"planting|sowing|transplant"),
            ("Watering", r"water|irrigat|moisture"),
            ("Fertilizing", r"fertiliz|nutrient|feeding"),
            ("Pruning", r"prun|pinch|sucker"),
            ("Staking", r"stake|trellis|support|cage"),
            ("Soil Preparation", r"soil|compost|organic|ph")
        ]
        
        for method_name, pattern in method_sections:
            if re.search(pattern, text, re.IGNORECASE):
                # Extract relevant sentences
                sentences = re.split(r'[.!?]+', text)
                relevant_sentences = [
                    s.strip() for s in sentences 
                    if re.search(pattern, s, re.IGNORECASE) and len(s.strip()) > 10
                ]
                
                if relevant_sentences:
                    methods.append({
                        "name": method_name,
                        "description": " ".join(relevant_sentences[:3]),  # First 3 relevant sentences
                        "stage": self._get_stage_for_method(method_name),
                        "source": "PDF extraction"
                    })
        
        return methods
    
    def _extract_chemicals(self, text: str) -> List[Dict]:
        """Extract chemical recommendations from text."""
        chemicals = []
        
        # Look for chemical names and application rates
        chemical_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(\d+)\s*(?:ml|g|kg|l)',
            r'(?:spray|apply|use)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:fungicide|pesticide|insecticide)'
        ]
        
        for pattern in chemical_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                chemical_name = match[0] if isinstance(match, tuple) else match
                
                # Extract application rate
                rate_match = re.search(rf'{re.escape(chemical_name)}.*?(\d+)\s*(ml|g|kg|l)', text, re.IGNORECASE)
                rate = f"{rate_match.group(1)} {rate_match.group(2)}" if rate_match else None
                
                # Determine chemical type
                chemical_type = "Fungicide" if any(word in text.lower() for word in ["fungus", "mold", "blight"]) else "Pesticide"
                
                chemicals.append({
                    "name": chemical_name,
                    "type": chemical_type,
                    "application_rate": rate,
                    "target": self._extract_chemical_targets(text, chemical_name),
                    "safety_precautions": self._extract_safety_info(text, chemical_name),
                    "source": "PDF extraction"
                })
        
        # Remove duplicates
        seen = set()
        unique_chemicals = []
        for chemical in chemicals:
            key = chemical["name"].lower()
            if key not in seen:
                seen.add(key)
                unique_chemicals.append(chemical)
        
        return unique_chemicals
    
    def _extract_harvesting_info(self, text: str) -> List[Dict]:
        """Extract harvesting information from text."""
        harvesting = []
        
        harvest_keywords = ["harvest", "pick", "ripe", "mature", "ready"]
        
        if any(keyword in text.lower() for keyword in harvest_keywords):
            # Extract harvesting sentences
            sentences = re.split(r'[.!?]+', text)
            harvest_sentences = [
                s.strip() for s in sentences 
                if any(keyword in s.lower() for keyword in harvest_keywords) and len(s.strip()) > 10
            ]
            
            if harvest_sentences:
                harvesting.append({
                    "method": "Hand harvesting",
                    "timing": "When fruits are fully colored and firm",
                    "techniques": " ".join(harvest_sentences[:3]),
                    "storage": self._extract_storage_info(text),
                    "source": "PDF extraction"
                })
        
        return harvesting
    
    def _extract_symptoms(self, text: str, disease: str) -> List[str]:
        """Extract disease symptoms from text."""
        symptoms = []
        symptom_patterns = [
            r"symptoms?:\s*([^.!?]+)",
            r"signs?:\s*([^.!?]+)",
            rf"{disease}.*?causes?\s*([^.!?]+)"
        ]
        
        for pattern in symptom_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            symptoms.extend(matches)
        
        return symptoms[:3] if symptoms else ["Symptoms information available in PDF"]
    
    def _extract_treatments(self, text: str, disease: str) -> List[str]:
        """Extract disease treatments from text."""
        treatments = []
        treatment_patterns = [
            r"treat?:\s*([^.!?]+)",
            r"control?:\s*([^.!?]+)",
            r"manage?:\s*([^.!?]+)",
            rf"{disease}.*?treat?\s*([^.!?]+)"
        ]
        
        for pattern in treatment_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            treatments.extend(matches)
        
        return treatments[:3] if treatments else ["Treatment information available in PDF"]
    
    def _extract_prevention(self, text: str, disease: str) -> List[str]:
        """Extract disease prevention methods from text."""
        prevention = []
        prevention_patterns = [
            r"prevent?:\s*([^.!?]+)",
            r"avoid?:\s*([^.!?]+)",
            rf"{disease}.*?prevent?\s*([^.!?]+)"
        ]
        
        for pattern in prevention_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prevention.extend(matches)
        
        return prevention[:3] if prevention else ["Prevention information available in PDF"]
    
    def _extract_damage(self, text: str, pest: str) -> List[str]:
        """Extract pest damage symptoms from text."""
        damage = []
        damage_patterns = [
            rf"{pest}.*?damage?\s*([^.!?]+)",
            rf"{pest}.*?cause?\s*([^.!?]+)",
            r"damage:\s*([^.!?]+)"
        ]
        
        for pattern in damage_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            damage.extend(matches)
        
        return damage[:3] if damage else ["Damage information available in PDF"]
    
    def _extract_control_methods(self, text: str, pest: str) -> List[str]:
        """Extract pest control methods from text."""
        control = []
        control_patterns = [
            rf"{pest}.*?control?\s*([^.!?]+)",
            r"control:\s*([^.!?]+)",
            r"manage:\s*([^.!?]+)"
        ]
        
        for pattern in control_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            control.extend(matches)
        
        return control[:3] if control else ["Control information available in PDF"]
    
    def _get_stage_for_method(self, method_name: str) -> str:
        """Determine the growth stage for a farming method."""
        stage_mapping = {
            "Planting": "Pre-planting",
            "Watering": "Growing",
            "Fertilizing": "Growing",
            "Pruning": "Growing",
            "Staking": "Growing",
            "Soil Preparation": "Pre-planting"
        }
        return stage_mapping.get(method_name, "General")
    
    def _extract_chemical_targets(self, text: str, chemical: str) -> List[str]:
        """Extract what a chemical targets."""
        targets = []
        target_patterns = [
            rf"{chemical}.*?(?:target|control|treat)\s*([^.!?]+)",
            r"(?:target|control|treat):\s*([^.!?]+)"
        ]
        
        for pattern in target_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            targets.extend(matches)
        
        return targets[:3] if targets else ["Target information available in PDF"]
    
    def _extract_safety_info(self, text: str, chemical: str) -> List[str]:
        """Extract safety precautions for chemicals."""
        safety = []
        safety_patterns = [
            rf"{chemical}.*?(?:safe|precaution|warning)\s*([^.!?]+)",
            r"(?:safe|precaution|warning):\s*([^.!?]+)"
        ]
        
        for pattern in safety_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            safety.extend(matches)
        
        return safety[:3] if safety else ["Follow label instructions"]
    
    def _extract_storage_info(self, text: str) -> str:
        """Extract storage information from text."""
        storage_patterns = [
            r"storage?:\s*([^.!?]+)",
            r"store?:\s*([^.!?]+)",
            r"keep?:\s*([^.!?]+)"
        ]
        
        for pattern in storage_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return "Store in cool, dry place"
    
    def _structure_knowledge(self):
        """Structure and organize the extracted knowledge."""
        data = self.tomato_knowledge["expert_report"]["data"]
        
        # Create main crop entry
        if data["varieties"] or data["diseases"] or data["pests"]:
            data["crops"].append({
                "name": "Tomato",
                "type": "Vegetable",
                "scientific_name": "Solanum lycopersicum",
                "varieties": data["varieties"],
                "common_diseases": [d["name"] for d in data["diseases"]],
                "common_pests": [p["name"] for p in data["pests"]],
                "farming_methods": [m["name"] for m in data["farming_methods"]],
                "harvesting_methods": [h["method"] for h in data["harvesting"]]
            })
        
        # Add regional adaptations for Malawi
        data["regional_adaptations"] = {
            "malawi_climate": {
                "planting_season": "March - May (winter planting) and August - October (summer planting)",
                "temperature_range": "15-30°C optimal",
                "rainfall_requirements": "Regular watering, 25-50mm per week",
                "soil_type": "Well-drained loamy soils, pH 6.0-6.8",
                "challenges": ["High temperatures", "Heavy rains", "Pest pressure"]
            }
        }
    
    def save_knowledge(self, output_path: str = "data/tomato_expert_knowledge.json"):
        """Save the extracted knowledge to JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.tomato_knowledge, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Tomato knowledge saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving tomato knowledge: {e}")
            return False


if __name__ == "__main__":
    # Extract tomato knowledge from PDFs
    extractor = TomatoKnowledgeExtractor()
    knowledge = extractor.extract_from_pdfs()
    
    if knowledge:
        extractor.save_knowledge()
        print("✅ Tomato knowledge extraction completed!")
        print(f"📊 Extracted:")
        print(f"  - Varieties: {len(knowledge['expert_report']['data']['varieties'])}")
        print(f"  - Diseases: {len(knowledge['expert_report']['data']['diseases'])}")
        print(f"  - Pests: {len(knowledge['expert_report']['data']['pests'])}")
        print(f"  - Farming methods: {len(knowledge['expert_report']['data']['farming_methods'])}")
        print(f"  - Chemicals: {len(knowledge['expert_report']['data']['chemicals'])}")
    else:
        print("❌ No tomato knowledge extracted")
