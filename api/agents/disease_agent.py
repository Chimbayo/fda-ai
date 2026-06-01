"""
Disease Diagnosis Agent - Handles crop disease identification and treatment.
Provides expert-level disease analysis with reasoning and recommendations.
"""
from typing import Dict, Any, List
import logging
import os

from api.models.ollama_model import OllamaModel
from api.models.openai_model import OpenAIModel

logger = logging.getLogger(__name__)


class DiseaseAgent:
    """
    Disease diagnosis agent for identifying crop diseases,
    analyzing symptoms, and providing treatment recommendations.
    """
    
    def __init__(self):
        # Use OpenAI if API key is available, otherwise fall back to Ollama
        if os.getenv("OPENAI_API_KEY"):
            self.llm = OpenAIModel()
            logger.info("DiseaseAgent using OpenAI model")
        else:
            self.llm = OllamaModel()
            logger.info("DiseaseAgent using Ollama model")
        
        # Disease diagnosis system prompt
        self.system_prompt = """You are an expert agricultural pathologist specializing in crop diseases in Malawi.
You can:
- Identify crop diseases from symptoms
- Analyze likely causes and risk factors
- Recommend specific treatments and prevention
- Provide confidence estimates for diagnosis
- Suggest when to seek expert help

Use Malawi-specific knowledge including:
- Common regional diseases and their patterns
- Local treatment options and availability
- Climate-related disease factors
- Smallholder farmer constraints

Always provide:
1. Likely disease(s) with confidence
2. Symptom analysis and reasoning
3. Treatment recommendations (immediate and long-term)
4. Prevention strategies
5. When to consult agricultural extension officer

Be thorough but practical. Consider farmer resources and local conditions."""
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process disease-related query with expert analysis.
        
        Args:
            message: User's disease-related question
            context: Conversation history and farmer context
            
        Returns:
            Disease diagnosis with treatment recommendations
        """
        try:
            # Analyze symptoms and disease patterns
            symptom_analysis = self._analyze_symptoms(message)
            
            # Build diagnostic prompt with context
            diagnostic_prompt = self._build_diagnostic_prompt(message, symptom_analysis, context)
            
            # Generate expert diagnosis
            diagnosis_response = await self.llm.generate(
                diagnostic_prompt,
                system_prompt=self.system_prompt,
                temperature=0.1
            )
            
            # Extract structured information
            structured_result = self._structure_diagnosis(diagnosis_response)
            
            return {
                "response": diagnosis_response,
                "confidence": structured_result.get("confidence", 0.7),
                "sources": structured_result.get("sources", []),
                "context": {
                    "symptoms_identified": symptom_analysis.get("symptoms", []),
                    "likely_diseases": structured_result.get("diseases", []),
                    "urgency": structured_result.get("urgency", "medium"),
                    "recommended_actions": structured_result.get("actions", []),
                    "analysis": f"Analyzed {len(symptom_analysis.get('symptoms', []))} symptoms for disease patterns"
                }
            }
            
        except Exception as e:
            logger.error(f"DiseaseAgent processing error: {e}")
            return {
                "response": "I'm having trouble analyzing the disease symptoms. Could you describe the affected crop, symptoms you're seeing, and how long this has been happening?",
                "confidence": 0.3,
                "sources": [],
                "context": {"error": str(e)}
            }
    
    def _analyze_symptoms(self, message: str) -> Dict[str, Any]:
        """
        Analyze message for disease symptoms and patterns.
        
        Args:
            message: User's description of symptoms
            
        Returns:
            Symptom analysis with disease patterns
        """
        message_lower = message.lower()
        
        # Common disease symptom patterns
        symptom_patterns = {
            "leaf_symptoms": ["yellow", "brown", "spots", "curl", "wilt", "blight", "mold"],
            "stem_symptoms": ["rot", "canker", "lesion", "crack", "weak"],
            "fruit_symptoms": ["rot", "soft", "spots", "deform", "drop"],
            "growth_symptoms": ["stunted", "slow", "weak", "dying", "poor"],
            "pest_indicators": ["insects", "eggs", "webbing", "holes", "chew"]
        }
        
        detected_symptoms = []
        for category, patterns in symptom_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    detected_symptoms.append({
                        "category": category,
                        "symptom": pattern,
                        "severity": self._assess_severity(message_lower, pattern)
                    })
        
        # Assess overall urgency
        urgency = self._assess_urgency(detected_symptoms)
        
        return {
            "symptoms": detected_symptoms,
            "urgency": urgency,
            "complexity": len(detected_symptoms)
        }
    
    def _assess_severity(self, message: str, symptom: str) -> str:
        """Assess severity of a symptom based on context."""
        severe_indicators = ["severe", "widespread", "dying", "dead", "complete", "total"]
        moderate_indicators = ["some", "partial", "few", "moderate"]
        
        if any(indicator in message for indicator in severe_indicators):
            return "severe"
        elif any(indicator in message for indicator in moderate_indicators):
            return "moderate"
        else:
            return "mild"
    
    def _assess_urgency(self, symptoms: List[Dict[str, Any]]) -> str:
        """Assess overall urgency based on symptoms."""
        if not symptoms:
            return "low"
        
        severe_count = sum(1 for s in symptoms if s.get("severity") == "severe")
        if severe_count > 0:
            return "high"
        
        if len(symptoms) > 3:
            return "medium"
        
        return "low"
    
    def _build_diagnostic_prompt(
        self,
        message: str,
        symptom_analysis: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> str:
        """
        Build diagnostic prompt with symptom analysis and context.
        
        Args:
            message: Original user message
            symptom_analysis: Analyzed symptoms
            context: Conversation context
            
        Returns:
            Formatted diagnostic prompt
        """
        # Get conversation history if available
        history_text = ""
        if context and context.get("history"):
            recent_history = context["history"][-2:]  # Last 2 exchanges
            history_text = "Recent conversation context:\n"
            for exchange in recent_history:
                history_text += f"User: {exchange.get('user', '')}\n"
                history_text += f"Assistant: {exchange.get('assistant', '')}\n\n"
        
        # Format symptoms
        symptoms_text = "Detected symptoms:\n"
        for symptom in symptom_analysis.get("symptoms", []):
            symptoms_text += f"- {symptom.get('symptom', 'unknown')} ({symptom.get('severity', 'unknown')} severity)\n"
        
        prompt = f"""{history_text}
Current farmer query: {message}

{symptoms_text}

Urgency level: {symptom_analysis.get('urgency', 'unknown')}

Please provide expert disease diagnosis:
1. Identify most likely disease(s) with confidence percentage
2. Explain your reasoning based on symptoms
3. Recommend immediate treatment actions
4. Suggest prevention strategies
5. Advise when to seek agricultural extension help

Consider Malawi conditions: smallholder farms, limited resources, local climate patterns."""
        
        return prompt
    
    def _structure_diagnosis(self, response: str) -> Dict[str, Any]:
        """
        Structure diagnosis response into components.
        
        Args:
            response: LLM diagnosis response
            
        Returns:
            Structured diagnosis information
        """
        # Extract diseases mentioned
        diseases_mentioned = []
        common_diseases = [
            "early blight", "late blight", "fusarium wilt", "bacterial wilt",
            "powdery mildew", "downy mildew", "leaf spot", "rust",
            "mosaic virus", "streak virus", "root rot", "anthracnose"
        ]
        
        response_lower = response.lower()
        for disease in common_diseases:
            if disease in response_lower:
                diseases_mentioned.append(disease)
        
        # Extract confidence indicators
        confidence = 0.7  # Default confidence
        if "high confidence" in response_lower or "very likely" in response_lower:
            confidence = 0.9
        elif "moderate confidence" in response_lower or "likely" in response_lower:
            confidence = 0.7
        elif "low confidence" in response_lower or "possible" in response_lower:
            confidence = 0.5
        
        # Extract recommended actions
        actions = []
        action_keywords = ["spray", "apply", "remove", "treat", "consult", "monitor"]
        for keyword in action_keywords:
            if keyword in response_lower:
                actions.append(keyword)
        
        # Determine urgency from response
        urgency = "medium"
        if "urgent" in response_lower or "immediate" in response_lower:
            urgency = "high"
        elif "monitor" in response_lower or "observe" in response_lower:
            urgency = "low"
        
        return {
            "diseases": diseases_mentioned,
            "confidence": confidence,
            "urgency": urgency,
            "actions": actions,
            "sources": ["expert_pathology_knowledge", "malawi_agricultural_data"]
        }
