"""
LangGraph Workflow for FDA-AI Agricultural Assistant.
Implements multi-agent orchestration with specialized agricultural agents.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Lazy imports to speed up startup
def _lazy_import_langgraph():
    from langgraph.graph import StateGraph, END
    return StateGraph, END

def _lazy_import_agents():
    from api.agents.crop_agent import CropAgent
    from api.agents.disease_agent import DiseaseAgent
    from api.agents.weather_agent import WeatherAgent
    from api.agents.retrieval_agent import RetrievalAgent
    from api.agents.conversation_agent import ConversationAgent
    return CropAgent, DiseaseAgent, WeatherAgent, RetrievalAgent, ConversationAgent

def _lazy_import_services():
    from api.database.neo4j_client import Neo4jClient
    from api.models.ollama_model import OllamaModel
    from api.models.openai_model import OpenAIModel
    from api.memory.memory_store import ConversationMemory
    return Neo4jClient, OllamaModel, OpenAIModel, ConversationMemory

def _lazy_import_knowledge():
    from api.knowledge.json_knowledge_loader import get_json_knowledge_loader
    return get_json_knowledge_loader

logger = logging.getLogger(__name__)


class WorkflowState:
    """State for LangGraph workflow."""
    
    def __init__(self):
        self.messages: List[str] = []
        self.current_agent: Optional[str] = None
        self.agent_reasoning: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.farmer_profile: Optional[Dict[str, Any]] = None
        self.query_count: int = 0
        self.start_time: Optional[datetime] = None


def create_workflow_state() -> WorkflowState:
    """Create initial workflow state."""
    return WorkflowState()


class FDAWorkflow:
    """
    Simplified workflow for FDA-AI agricultural assistant.
    Uses direct routing for maximum performance.
    """
    
    def __init__(self):
        # Ultra-lazy initialization - no heavy imports at startup
        self._agents = {}
        self._services = {}
        
        # Performance optimization
        self.response_cache = {}
        self.query_cache = {}
    
    def _get_agent(self, agent_type):
        """Get agent instance with lazy loading."""
        if agent_type not in self._agents:
            CropAgent, DiseaseAgent, WeatherAgent, RetrievalAgent, ConversationAgent = _lazy_import_agents()
            
            if agent_type == "crop":
                self._agents[agent_type] = CropAgent()
            elif agent_type == "disease":
                self._agents[agent_type] = DiseaseAgent()
            elif agent_type == "weather":
                self._agents[agent_type] = WeatherAgent()
            elif agent_type == "knowledge":
                self._agents[agent_type] = RetrievalAgent()
            else:
                self._agents[agent_type] = ConversationAgent()
        
        return self._agents[agent_type]
    
    
    def _route_query(self, state: Dict[str, Any]) -> str:
        """
        Route user query to appropriate agent using keyword and LLM analysis.
        Also detects specific crops for knowledge base routing.
        
        Args:
            state: Current workflow state
            
        Returns:
            Selected agent type
        """
        try:
            query = state["messages"][-1] if state["messages"] else ""
            
            # Keyword-based routing (fast path) - prioritize disease keywords
            disease_keywords = ["disease", "pest", "blight", "wilt", "spot", "rot", "mildew", "virus", "yellow", "curling", "wilting", "leaf"]
            crop_keywords = ["maize", "tomato", "cabbage", "fertilizer", "variety", "yield", "soil", "harvest"]
            weather_keywords = ["weather", "rain", "climate", "season", "drought", "flood", "planting"]
            knowledge_keywords = ["research", "paper", "study", "data", "statistics"]
            conversation_keywords = ["hello", "hi", "how", "what", "help", "thanks"]
            
            # Crop-specific detection for knowledge base routing
            crop_specific_keywords = {
                "tomato": ["tomato", "tomatoes"],
                "cabbage": ["cabbage", "cabbages"],
                "maize": ["maize", "corn"],
                "beans": ["beans", "bean"]
            }
            
            query_lower = query.lower()
            
            # Detect specific crop for knowledge base routing
            detected_crop = None
            for crop, keywords in crop_specific_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    detected_crop = crop
                    logger.info(f"Detected crop: {crop} from query: {query_lower}")
                    break
            
            # Store detected crop in state for knowledge base routing
            if detected_crop:
                state["detected_crop"] = detected_crop
                logger.info(f"Set detected_crop in state to: {detected_crop}")
            else:
                logger.info(f"No specific crop detected in query: {query_lower}")
            
            # Primary routing logic - check disease keywords first
            if any(keyword in query_lower for keyword in disease_keywords):
                return "disease"
            elif any(keyword in query_lower for keyword in crop_keywords):
                return "crop"
            elif any(keyword in query_lower for keyword in weather_keywords):
                return "weather"
            elif any(keyword in query_lower for keyword in knowledge_keywords):
                return "knowledge"
            elif any(keyword in query_lower for keyword in conversation_keywords):
                return "conversation"
            
            # Fallback to conversation agent for complex queries
            return "conversation"
                
        except Exception as e:
            logger.error(f"Routing error: {e}")
            return "conversation"
    
    def _crop_advisor_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Crop advisory agent node with crop-specific knowledge bases."""
        try:
            query = state["messages"][-1] if state["messages"] else ""
            detected_crop = state.get("detected_crop", "general")
            query_lower = query.lower()
            
            # Debug logging
            logger.info(f"Crop advisor received state with detected_crop: {detected_crop}")
            logger.info(f"Full state keys: {list(state.keys())}")
            if "detected_crop" in state:
                logger.info(f"detected_crop value: {state['detected_crop']}")
            
            # Crop-specific knowledge base routing
            crop_knowledge_bases = {
                "tomato": ["tomato_variety_guide", "tomato_pest_management", "tomato_harvesting_guide"],
                "cabbage": ["cabbage_variety_guide", "cabbage_disease_management", "cabbage_storage_guide"],
                "maize": ["maize_variety_guide", "maize_fertilizer_guide", "maize_planting_calendar"],
                "beans": ["beans_variety_guide", "beans_disease_management", "beans_harvesting_guide"]
            }
            
            # Get crop-specific sources
            sources = crop_knowledge_bases.get(detected_crop, ["general_crop_knowledge_base"])
            
            # Use JSON expert knowledge and PDF knowledge for responses
            try:
                # Force reload knowledge to get latest data including new maize file
                from api.knowledge.json_knowledge_loader import JSONKnowledgeLoader
                from api.knowledge.pdf_knowledge_retriever import get_pdf_knowledge_retriever
                
                knowledge_loader = JSONKnowledgeLoader()  # Create fresh instance
                pdf_retriever = get_pdf_knowledge_retriever()
                
                if detected_crop in knowledge_loader.knowledge_cache:
                    # Get expert knowledge from JSON files
                    if "variety" in query_lower or "varieties" in query_lower:
                        varieties = knowledge_loader.get_crop_varieties(detected_crop)
                        if varieties:
                            # Format variety information from JSON
                            variety_names = []
                            for var in varieties[:5]:  # Top 5 varieties
                                name = var.get('name', '').strip()
                                if name:  # Varieties already filtered in get_crop_varieties
                                    maturity = var.get('maturity_days', '')
                                    yield_info = var.get('yield_tons_ha', '')
                                    characteristics = var.get('characteristics', '')
                                    
                                    var_info = name
                                    if maturity and maturity != 'null':
                                        var_info += f" ({maturity} days)"
                                    if yield_info:
                                        var_info += f" - {yield_info} tons/ha"
                                    if characteristics:
                                        var_info += f": {characteristics}"
                                    
                                    variety_names.append(var_info)
                            
                            if variety_names:
                                response = f"Based on expert knowledge for {detected_crop.title()} in Malawi, recommended varieties include:\n" + "\n".join(f"• {v}" for v in variety_names)
                                
                                # Add PDF knowledge if available
                                if pdf_retriever.is_available():
                                    pdf_results = pdf_retriever.get_crop_specific_knowledge(detected_crop, f"{detected_crop} varieties farming practices")
                                    if pdf_results:
                                        response += f"\n\n📚 **Additional Knowledge from Agricultural Guides:**\n"
                                        for result in pdf_results[:2]:  # Top 2 PDF results
                                            pdf_text = result['text'][:200] + "..." if len(result['text']) > 200 else result['text']
                                            response += f"• From {result['source']}: {pdf_text}\n"
                            else:
                                response = f"I found expert knowledge for {detected_crop.title()}, but variety information needs to be updated. Please consult local agricultural extension for current variety recommendations."
                        else:
                            response = f"No variety information found in expert knowledge for {detected_crop.title()}. Please consult local agricultural extension for variety recommendations."
                    
                    elif "disease" in query_lower or "pest" in query_lower:
                        diseases = knowledge_loader.get_crop_diseases(detected_crop)
                        pests = knowledge_loader.get_crop_pests(detected_crop)
                        
                        disease_info = []
                        for disease in diseases[:3]:
                            name = disease.get('name', '').strip()
                            if name and len(name) > 3:
                                symptoms = disease.get('symptoms', [])
                                treatments = disease.get('treatments', [])
                                disease_text = name
                                if symptoms:
                                    disease_text += f" - Symptoms: {', '.join(symptoms[:2])}"
                                disease_info.append(disease_text)
                        
                        response = f"Common {detected_crop.title()} health issues:\n" + "\n".join(f"• {d}" for d in disease_info)
                    
                    elif "plant" in query_lower or "planting" in query_lower or "method" in query_lower:
                        methods = knowledge_loader.get_farming_methods(detected_crop)
                        method_info = []
                        
                        for method in methods[:3]:
                            name = method.get('name', '').strip()
                            description = method.get('description', '').strip()
                            if name and len(name) > 3:
                                method_text = name
                                if description and len(description) > 10:
                                    method_text += f": {description[:100]}..."
                                method_info.append(method_text)
                        
                        if method_info:
                            response = f"For {detected_crop.title()} cultivation:\n" + "\n".join(f"• {m}" for m in method_info)
                        else:
                            response = f"Expert knowledge available for {detected_crop.title()}, but specific planting methods need to be consulted from agricultural extension officers."
                    
                    else:
                        # General crop information
                        summary = knowledge_loader.get_expert_summary(detected_crop)
                        response = f"I have expert knowledge for {detected_crop.title()} from {summary.get('source', 'agricultural experts')}. The database contains {summary.get('varieties_count', 0)} varieties, {summary.get('diseases_count', 0)} diseases, and {summary.get('methods_count', 0)} farming methods. Please ask specifically about varieties, diseases, or planting methods for detailed information."
                
                else:
                    # Fallback to hardcoded responses for crops without JSON data
                    if detected_crop == "maize":
                        response = "Recommended maize varieties for Malawi: MH18 (drought tolerant), SC627 (early maturing), and local landraces adapted to specific regions. Plant with the first rains for best yields."
                    elif detected_crop == "beans":
                        response = "Good bean varieties for Malawi: NUA 45 (drought tolerant), Kalima (early maturing), and local climbing beans. These fix nitrogen and improve soil fertility."
                    else:
                        response = f"For general crop advice about {query}, I recommend considering local Malawi conditions, disease resistance, and market demand when selecting varieties."
                        
            except Exception as e:
                logger.error(f"Error loading JSON knowledge: {e}")
                # Fallback to basic response
                response = f"I can help with {detected_crop} advice. For specific variety recommendations and detailed information, please consult local agricultural extension officers."
            
            # Return state as dictionary
            updated_state = {
                "messages": state["messages"],
                "current_agent": "crop",
                "detected_crop": detected_crop,
                "agent_reasoning": f"Processed {detected_crop} crop query: {query[:50]}...",
                "context": {
                    "response": response,
                    "confidence": 0.8,
                    "sources": sources,
                    "analysis": f"Analyzed {detected_crop} crop query: {query}"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
            
            logger.info(f"Crop agent processed {detected_crop} query: {response[:100]}...")
            return updated_state
            
        except Exception as e:
            logger.error(f"Crop agent error: {e}")
            return {
                "messages": state["messages"],
                "current_agent": "crop",
                "agent_reasoning": f"Error in crop agent: {str(e)}",
                "context": {
                    "response": "I apologize, but I had trouble processing your crop question.",
                    "confidence": 0.0,
                    "sources": [],
                    "analysis": "Error occurred"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
    
    def _disease_diagnosis_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Disease diagnosis agent node with crop-specific knowledge bases."""
        try:
            query = state["messages"][-1] if state["messages"] else ""
            detected_crop = state.get("detected_crop", "general")
            query_lower = query.lower()
            
            # Crop-specific disease knowledge bases
            disease_knowledge_bases = {
                "tomato": ["tomato_disease_guide", "tomato_pest_identification", "tomato_symptoms_database"],
                "cabbage": ["cabbage_disease_guide", "cabbage_pest_identification", "cabbage_symptoms_database"],
                "maize": ["maize_disease_guide", "maize_pest_identification", "maize_symptoms_database"],
                "beans": ["beans_disease_guide", "beans_pest_identification", "beans_symptoms_database"]
            }
            
            # Get crop-specific disease sources
            sources = disease_knowledge_bases.get(detected_crop, ["general_disease_knowledge_base"])
            
            # Crop-specific disease response with actual diagnostic information
            if detected_crop == "tomato":
                if "yellow" in query_lower or "wilting" in query_lower:
                    response = "Yellow leaves and wilting in tomatoes often indicate early blight or fusarium wilt. Remove affected plants, improve drainage, and apply copper-based fungicides. Use resistant varieties like Tengeru 97."
                elif "spot" in query_lower or "blight" in query_lower:
                    response = "Tomato early blight shows dark spots with yellow halos. Late blight causes water-soaked lesions. Treat with mancozeb or copper sprays and ensure good air circulation between plants."
                else:
                    response = "Common tomato diseases in Malawi: early blight (brown spots), late blight (water-soaked lesions), and fusarium wilt (yellowing, wilting). Use resistant varieties and crop rotation."
            elif detected_crop == "cabbage":
                if "yellow" in query_lower or "wilting" in query_lower:
                    response = "Yellow cabbage leaves often indicate clubroot or nutrient deficiency. Test soil pH (should be 6.0-6.5) and apply balanced fertilizer. Avoid planting in infected fields for 4-5 years."
                elif "rot" in query_lower or "black" in query_lower:
                    response = "Black rot in cabbage causes V-shaped lesions on leaf edges. Use certified seeds, avoid overhead watering, and apply copper sprays. Remove and destroy infected plants."
                else:
                    response = "Common cabbage diseases in Malawi: black rot (V-shaped lesions), clubroot (swollen roots), and downy mildew (white fungal growth). Practice crop rotation and proper spacing."
            elif detected_crop == "maize":
                if "yellow" in query_lower or "streak" in query_lower:
                    response = "Yellow streaks on maize leaves indicate maize streak virus. Control leafhoppers, use resistant varieties like MH18, and remove infected plants promptly."
                elif "rust" in query_lower or "spot" in query_lower:
                    response = "Common rust shows orange-brown pustules on leaves. Apply fungicides like mancozeb and ensure adequate nitrogen fertilization. Early planting reduces infection risk."
                else:
                    response = "Major maize diseases in Malawi: maize streak virus (transmitted by leafhoppers), gray leaf spot (gray lesions), and common rust (orange pustules). Use resistant varieties."
            elif detected_crop == "beans":
                if "yellow" in query_lower or "mosaic" in query_lower:
                    response = "Yellow mosaic patterns on beans indicate bean common mosaic virus. Use disease-free seeds, control aphids, and plant resistant varieties like NUA 45."
                elif "spot" in query_lower or "rot" in query_lower:
                    response = "Angular leaf spot shows brown spots on leaves. Root rot causes yellowing and wilting. Improve drainage and apply appropriate fungicides like metalaxyl."
                else:
                    response = "Common bean diseases in Malawi: common mosaic virus (yellow patterns), angular leaf spot (brown spots), and root rot (wilting). Use certified seeds and proper spacing."
            else:
                response = f"For disease diagnosis, I recommend examining symptoms closely, checking for patterns (spots, wilting, discoloration), and consulting local agricultural extension officers for specific treatment recommendations."
            
            # Return state as dictionary
            updated_state = {
                "messages": state["messages"],
                "current_agent": "disease",
                "detected_crop": detected_crop,
                "agent_reasoning": f"Processed {detected_crop} disease query: {query[:50]}...",
                "context": {
                    "response": response,
                    "confidence": 0.7,
                    "sources": sources,
                    "analysis": f"Analyzed {detected_crop} disease symptoms: {query}"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
            
            logger.info(f"Disease agent processed {detected_crop} query: {response[:100]}...")
            return updated_state
            
        except Exception as e:
            logger.error(f"Disease agent error: {e}")
            return {
                "messages": state["messages"],
                "current_agent": "disease",
                "agent_reasoning": f"Error in disease agent: {str(e)}",
                "context": {
                    "response": "I apologize, but I had trouble processing your disease question.",
                    "confidence": 0.0,
                    "sources": [],
                    "analysis": "Error occurred"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
    
    def _weather_advisor_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Weather advisory agent node."""
        try:
            query = state["messages"][-1] if state["messages"] else ""
            
            # Simple weather response without async for now
            response = f"I can provide weather advice for: {query}. In Malawi, consider the rainy season (November-April) and dry season patterns for planting decisions."
            
            # Return state as dictionary
            updated_state = {
                "messages": state["messages"],
                "current_agent": "weather",
                "agent_reasoning": f"Processed weather query: {query[:50]}...",
                "context": {
                    "response": response,
                    "confidence": 0.8,
                    "sources": ["weather_knowledge_base"],
                    "analysis": f"Analyzed weather patterns: {query}"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
            
            logger.info(f"Weather agent processed: {response[:100]}...")
            return updated_state
            
        except Exception as e:
            logger.error(f"Weather agent error: {e}")
            return {
                "messages": state["messages"],
                "current_agent": "weather",
                "agent_reasoning": f"Error in weather agent: {str(e)}",
                "context": {
                    "response": "I apologize, but I had trouble processing your weather question.",
                    "confidence": 0.0,
                    "sources": [],
                    "analysis": "Error occurred"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
    
    def _knowledge_retrieval_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Knowledge retrieval agent node."""
        try:
            query = state["messages"][-1] if state["messages"] else ""
            
            # Simple knowledge response without async for now
            response = f"I can retrieve agricultural knowledge for: {query}. Based on research data, I can provide evidence-based recommendations for Malawi farming."
            
            # Return state as dictionary
            updated_state = {
                "messages": state["messages"],
                "current_agent": "knowledge",
                "agent_reasoning": f"Processed knowledge query: {query[:50]}...",
                "context": {
                    "response": response,
                    "confidence": 0.8,
                    "sources": ["agricultural_research_database"],
                    "analysis": f"Retrieved knowledge for: {query}"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
            
            logger.info(f"Knowledge agent processed: {response[:100]}...")
            return updated_state
            
        except Exception as e:
            logger.error(f"Knowledge agent error: {e}")
            return {
                "messages": state["messages"],
                "current_agent": "knowledge",
                "agent_reasoning": f"Error in knowledge agent: {str(e)}",
                "context": {
                    "response": "I apologize, but I had trouble retrieving knowledge for your question.",
                    "confidence": 0.0,
                    "sources": [],
                    "analysis": "Error occurred"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
    
    def _conversation_handler_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Conversation agent node."""
        try:
            query = state["messages"][-1] if state["messages"] else ""
            query_lower = query.lower()
            
            # Simple conversation response without async for now
            if any(greeting in query_lower for greeting in ["hello", "hi", "hey"]):
                response = "Hello! I'm your agricultural assistant for Malawi farmers. How can I help you today?"
            elif any(greeting in query_lower for greeting in ["thanks", "thank", "appreciate"]):
                response = "You're welcome! I'm here to help with any agricultural questions you have."
            elif "help" in query_lower:
                response = "I'm your agricultural assistant for Malawi farmers. I can help you with crop varieties, disease diagnosis, weather advice, and farming practices. What specific topic would you like assistance with?"
            else:
                response = f"Hello! I'm your agricultural assistant for Malawi farmers. I can help you with crops, diseases, weather, and farming advice. How can I assist you today?"
            
            # Return state as dictionary
            updated_state = {
                "messages": state["messages"],
                "current_agent": "conversation",
                "agent_reasoning": f"Processed conversation query: {query[:50]}...",
                "context": {
                    "response": response,
                    "confidence": 0.9,
                    "sources": ["conversation_system"],
                    "analysis": f"General conversation: {query}"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
            
            logger.info(f"Conversation agent processed: {response[:100]}...")
            return updated_state
            
        except Exception as e:
            logger.error(f"Conversation agent error: {e}")
            return {
                "messages": state["messages"],
                "current_agent": "conversation",
                "agent_reasoning": f"Error in conversation agent: {str(e)}",
                "context": {
                    "response": "I apologize, but I had trouble processing your message.",
                    "confidence": 0.0,
                    "sources": [],
                    "analysis": "Error occurred"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
    
    def _final_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Final response generation node."""
        try:
            # Get the best response from the active agent
            if state.get("context") and "response" in state["context"]:
                response = state["context"]["response"]
                confidence = state["context"].get("confidence", 0.7)
                sources = state["context"].get("sources", [])
                agent_type = state.get("current_agent") or "unknown"
            else:
                response = "I apologize, but I couldn't process your request properly."
                confidence = 0.0
                sources = []
                agent_type = state.get("current_agent") or "unknown"
            
            # Return state as dictionary
            updated_state = {
                "messages": state["messages"],
                "current_agent": agent_type,
                "detected_crop": state.get("detected_crop", "general"),  # Preserve detected crop
                "agent_reasoning": f"Generated final response via {agent_type} agent",
                "context": {
                    "response": response,
                    "confidence": confidence,
                    "sources": sources,
                    "analysis": f"Final response generated via {agent_type}"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": (state.get("query_count") or 0) + 1,
                "start_time": state.get("start_time")
            }
            
            logger.info(f"Final response generated: {response[:100]}...")
            return updated_state
            
        except Exception as e:
            logger.error(f"Final response error: {e}")
            return {
                "messages": state["messages"],
                "current_agent": state.get("current_agent") or "unknown",
                "agent_reasoning": f"Error generating response: {str(e)}",
                "context": {
                    "response": "I apologize, but I encountered an error generating your response.",
                    "confidence": 0.0,
                    "sources": [],
                    "analysis": "Error occurred"
                },
                "farmer_profile": state.get("farmer_profile"),
                "query_count": state.get("query_count", 0),
                "start_time": state.get("start_time")
            }
    
    def process_query(self, query: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Process user query through simplified routing system.
        
        Args:
            query: User's agricultural question
            user_id: User identifier for memory
            
        Returns:
            Response with agent information and reasoning
        """
        try:
            start_time = datetime.now()
            
            # Create simple state as dictionary
            state = {
                "messages": [query],
                "current_agent": None,
                "agent_reasoning": None,
                "context": {},
                "farmer_profile": None,
                "query_count": 0,
                "start_time": start_time,
                "detected_crop": None
            }
            
            # Route query using keyword-based routing
            agent_type = self._route_query(state)
            
            # Process with appropriate agent
            if agent_type == "crop":
                final_state = self._crop_advisor_node(state)
            elif agent_type == "disease":
                final_state = self._disease_diagnosis_node(state)
            elif agent_type == "weather":
                final_state = self._weather_advisor_node(state)
            elif agent_type == "knowledge":
                final_state = self._knowledge_retrieval_node(state)
            else:
                final_state = self._conversation_handler_node(state)
            
            # Generate final response
            final_state = self._final_response_node(final_state)
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Query processed in {response_time:.2f}s via {final_state.get('current_agent', 'unknown')}")
            
            # Format response - return only response content
            if final_state and final_state.get("context"):
                return final_state["context"].get("response", "No response generated")
            else:
                return "I apologize, but I couldn't process your request."
                
        except Exception as e:
            logger.error(f"Processing error: {e}")
            return f"Error processing your request: {str(e)}"
    
    def _get_workflow_summary(self, state: WorkflowState) -> List[str]:
        """Get summary of workflow steps taken."""
        steps = []
        
        if state.start_time:
            steps.append(f"Started: {state.start_time.strftime('%H:%M:%S')}")
        
        if state.current_agent:
            steps.append(f"Routed to: {state.current_agent} agent")
        
        if state.agent_reasoning:
            steps.append(f"Reasoning: {state.agent_reasoning}")
        
        return steps


# Global workflow instance (lazy-loaded)
fda_workflow = None

def get_fda_workflow():
    """Get or create FDA workflow instance (lazy loading)."""
    global fda_workflow
    if fda_workflow is None:
        fda_workflow = FDAWorkflow()
    return fda_workflow
