"""
Disease Agent - Specialized in plant diseases and pest management.
Provides diagnosis and treatment recommendations for crop diseases.
"""
from typing import Dict, Any, List
import logging

from app.models.ollama_model import OllamaModel
from app.database.neo4j_client import Neo4jClient
from app.utils.ranking import rank_sources

logger = logging.getLogger(__name__)


class DiseaseAgent:
    """
    Specialized agent for disease and pest-related queries.
    Handles diagnosis, treatment recommendations, and prevention strategies.
    """
    
    def __init__(self):
        self.llm = OllamaModel()
        self.db = Neo4jClient()
        
        # System prompt for disease expertise
        self.system_prompt = """You are a plant pathology expert specializing in crop diseases in Malawi.
Your expertise includes:
- Disease identification from symptoms
- Pest identification and management
- Treatment recommendations (chemical and organic)
- Preventive measures
- Integrated Pest Management (IPM)

Provide accurate diagnoses based on symptoms described.
Recommend both immediate treatment and long-term prevention.
Consider smallholder farmer constraints (cost, availability, safety).
Be specific about local diseases affecting maize, tomatoes, and other common crops."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a disease-related query.
        
        Args:
            message: User's query about diseases or pests
            context: Additional context
            
        Returns:
            Response with diagnosis and treatment advice
        """
        try:
            # Analyze symptoms and retrieve disease info
            analysis = await self._analyze_symptoms(message)
            
            # Retrieve treatment information
            treatments = await self._retrieve_treatments(analysis.get("diseases", []))
            
            # Build prompt with diagnosis
            prompt = self._build_prompt(message, analysis, treatments, context)
            
            # Generate response
            response = await self.llm.generate(
                prompt,
                system_prompt=self.system_prompt
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(analysis, treatments)
            
            # Format sources
            sources = rank_sources(treatments)
            
            return {
                "response": response,
                "confidence": confidence,
                "sources": sources,
                "context": {
                    "detected_diseases": analysis.get("diseases", []),
                    "symptoms": analysis.get("symptoms", []),
                    "severity": analysis.get("severity", "unknown")
                }
            }
            
        except Exception as e:
            logger.error(f"DiseaseAgent processing error: {e}")
            return {
                "response": "I apologize, but I'm having trouble analyzing the disease symptoms right now. Please try describing the symptoms more specifically.",
                "confidence": 0.0,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    async def _analyze_symptoms(self, query: str) -> Dict[str, Any]:
        """
        Analyze symptoms described in the query.
        
        Args:
            query: User's description
            
        Returns:
            Analysis results with detected diseases and symptoms
        """
        # Common symptoms and their associated diseases
        symptom_patterns = {
            "leaf blight": ["maize leaf blight", "turcicum leaf blight"],
            "brown lesions": ["maize leaf blight", "gray leaf spot"],
            "yellow spots": ["maize streak virus", "rust"],
            "dark spots": ["tomato early blight", "septoria leaf spot"],
            "concentric rings": ["tomato early blight"],
            "wilting": ["wilt diseases", "fusarium wilt", "bacterial wilt"],
            "stunted growth": ["root rot", "viral diseases", "nutrient deficiency"],
            "white patches": ["powdery mildew"],
            "holes in leaves": ["caterpillars", "beetles", "stem borers"],
            "tunneling": ["stem borers", "stalk borers"]
        }
        
        query_lower = query.lower()
        
        detected_symptoms = []
        possible_diseases = []
        
        for symptom, diseases in symptom_patterns.items():
            if symptom in query_lower:
                detected_symptoms.append(symptom)
                possible_diseases.extend(diseases)
        
        # Remove duplicates
        possible_diseases = list(set(possible_diseases))
        
        # Determine severity
        severity = self._assess_severity(query_lower, detected_symptoms)
        
        return {
            "symptoms": detected_symptoms,
            "diseases": possible_diseases,
            "severity": severity
        }
    
    def _assess_severity(self, query: str, symptoms: List[str]) -> str:
        """
        Assess disease severity based on description.
        
        Args:
            query: User query
            symptoms: Detected symptoms
            
        Returns:
            Severity level
        """
        severe_indicators = ["widespread", "severe", "dying", "all plants", "entire field", "heavy"]
        moderate_indicators = ["some", "several", "patches", "spreading"]
        
        query_lower = query.lower()
        
        if any(ind in query_lower for ind in severe_indicators) or len(symptoms) > 2:
            return "severe"
        elif any(ind in query_lower for ind in moderate_indicators) or len(symptoms) > 1:
            return "moderate"
        else:
            return "mild"
    
    async def _retrieve_treatments(self, diseases: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve treatment information for detected diseases.
        
        Args:
            diseases: List of detected diseases
            
        Returns:
            Treatment information
        """
        if not diseases:
            return []
        
        try:
            treatments = []
            
            for disease in diseases:
                cypher_query = """
                MATCH (d:Disease)-[:TREATED_WITH]->(t:Treatment)
                WHERE d.name CONTAINS $disease OR d.symptoms CONTAINS $disease
                RETURN d.name as disease, d.symptoms as symptoms,
                       t.name as treatment, t.type as type, 
                       t.application as application, t.effectiveness as effectiveness
                """
                
                results = self.db.execute_query(cypher_query, {"disease": disease})
                treatments.extend(results)
            
            return treatments
            
        except Exception as e:
            logger.error(f"Treatment retrieval error: {e}")
            return []
    
    def _build_prompt(
        self,
        message: str,
        analysis: Dict[str, Any],
        treatments: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Build prompt with diagnosis and treatment information.
        
        Args:
            message: User message
            analysis: Symptom analysis
            treatments: Treatment information
            context: Additional context
            
        Returns:
            Formatted prompt
        """
        # Format diagnosis
        diagnosis_text = ""
        if analysis.get("diseases"):
            diagnosis_text = f"Detected diseases: {', '.join(analysis['diseases'])}\n"
            diagnosis_text += f"Symptoms: {', '.join(analysis['symptoms'])}\n"
            diagnosis_text += f"Severity: {analysis['severity']}\n\n"
        
        # Format treatments
        treatment_text = ""
        if treatments:
            treatment_text = "Recommended treatments:\n"
            for i, treatment in enumerate(treatments[:5], 1):
                treatment_text += f"{i}. {treatment}\n"
        
        prompt = f"""{diagnosis_text}{treatment_text}

Farmer's description: {message}

Provide a clear diagnosis and practical treatment recommendations. Include both immediate action and prevention strategies."""
        
        return prompt
    
    def _calculate_confidence(
        self,
        analysis: Dict[str, Any],
        treatments: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence score.
        
        Args:
            analysis: Symptom analysis
            treatments: Treatment information
            
        Returns:
            Confidence score (0-1)
        """
        if not analysis.get("symptoms"):
            return 0.2
        
        base_confidence = 0.4
        
        # Increase confidence with clear symptoms
        base_confidence += min(len(analysis["symptoms"]) * 0.1, 0.2)
        
        # Increase confidence with treatment information
        if treatments:
            base_confidence += min(len(treatments) * 0.05, 0.2)
        
        # Decrease confidence if severity is unknown
        if analysis.get("severity") == "unknown":
            base_confidence -= 0.1
        
        return min(max(base_confidence, 0.1), 0.9)
