"""
LangGraph Workflow for FDA-AI Agricultural Assistant.
Implements multi-agent orchestration with specialized agricultural agents.
"""
import logging
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.crop_agent import CropAgent
from app.agents.disease_agent import DiseaseAgent
from app.agents.weather_agent import WeatherAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.conversation_agent import ConversationAgent
from app.database.neo4j_client import Neo4jClient
from app.models.ollama_model import OllamaModel
from app.memory.memory_store import ConversationMemory

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
    Main LangGraph workflow for FDA-AI agricultural assistant.
    Orchestrates 5 specialized agents with intelligent routing and memory.
    """
    
    def __init__(self):
        self.neo4j = Neo4jClient()
        self.llm = OllamaModel()
        self.memory = ConversationMemory()
        
        # Initialize agents
        self.crop_agent = CropAgent()
        self.disease_agent = DiseaseAgent()
        self.weather_agent = WeatherAgent()
        self.retrieval_agent = RetrievalAgent()
        self.conversation_agent = ConversationAgent()
        
        # Performance optimization
        self.response_cache = {}
        self.query_cache = {}
    
    def create_graph(self) -> StateGraph:
        """
        Create LangGraph workflow with all agents and routing logic.
        
        Returns:
            Configured StateGraph with nodes and edges
        """
        # Create workflow graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("route_query", self._route_query)
        workflow.add_node("crop_advisor", self._crop_advisor_node)
        workflow.add_node("disease_diagnosis", self._disease_diagnosis_node)
        workflow.add_node("weather_advisor", self._weather_advisor_node)
        workflow.add_node("knowledge_retrieval", self._knowledge_retrieval_node)
        workflow.add_node("conversation_handler", self._conversation_handler_node)
        workflow.add_node("final_response", self._final_response_node)
        
        # Add conditional routing
        workflow.add_conditional_edges(
            "route_query",
            {
                "crop": "crop_advisor",
                "disease": "disease_diagnosis", 
                "weather": "weather_advisor",
                "knowledge": "knowledge_retrieval",
                "conversation": "conversation_handler"
            }
        )
        
        # Add edges to final response
        for agent_node in ["crop_advisor", "disease_diagnosis", "weather_advisor", "knowledge_retrieval", "conversation_handler"]:
            workflow.add_edge(agent_node, "final_response")
        
        # Add entry and exit points
        workflow.set_entry_point("route_query")
        workflow.add_edge("final_response", END)
        
        # Add memory for persistence
        memory = MemorySaver()
        
        return workflow.compile(checkpointer=memory)
    
    async def _route_query(self, state: WorkflowState) -> str:
        """
        Route user query to appropriate agent using keyword and LLM analysis.
        
        Args:
            state: Current workflow state
            
        Returns:
            Selected agent type
        """
        try:
            query = state.messages[-1] if state.messages else ""
            
            # Keyword-based routing (fast path)
            crop_keywords = ["maize", "tomato", "cabbage", "plant", "fertilizer", "variety", "yield", "soil"]
            disease_keywords = ["disease", "pest", "blight", "wilt", "spot", "rot", "mildew", "virus"]
            weather_keywords = ["weather", "rain", "climate", "season", "planting", "harvest", "drought", "flood"]
            knowledge_keywords = ["research", "paper", "study", "data", "statistics"]
            conversation_keywords = ["hello", "hi", "how", "what", "help", "thanks"]
            
            query_lower = query.lower()
            
            # Primary routing logic
            if any(keyword in query_lower for keyword in crop_keywords):
                return "crop"
            elif any(keyword in query_lower for keyword in disease_keywords):
                return "disease"
            elif any(keyword in query_lower for keyword in weather_keywords):
                return "weather"
            elif any(keyword in query_lower for keyword in knowledge_keywords):
                return "knowledge"
            elif any(keyword in query_lower for keyword in conversation_keywords):
                return "conversation"
            
            # LLM-based routing (fallback for complex queries)
            routing_prompt = f"""
            Analyze this agricultural query and route to the most appropriate agent:
            
            Query: "{query}"
            
            Available agents:
            - crop: Crop varieties, planting, fertilizer, harvesting
            - disease: Disease diagnosis, treatment, prevention
            - weather: Climate patterns, planting windows, seasonal advice
            - knowledge: Research papers, technical data, statistics
            - conversation: General chat, greetings, unclear queries
            
            Return only one word: crop, disease, weather, knowledge, or conversation
            """
            
            # Use LLM for complex routing
            try:
                llm_response = await self.llm.generate(routing_prompt, temperature=0.1)
                
                # Extract agent type from LLM response
                response_lower = llm_response.lower().strip()
                for agent_type in ["crop", "disease", "weather", "knowledge", "conversation"]:
                    if agent_type in response_lower:
                        return agent_type
                        
            except Exception as e:
                logger.warning(f"LLM routing failed: {e}, using keyword routing")
                # Fallback to conversation agent
                return "conversation"
                
        except Exception as e:
            logger.error(f"Routing error: {e}")
            return "conversation"
    
    async def _crop_advisor_node(self, state: WorkflowState) -> WorkflowState:
        """Crop advisory agent node."""
        try:
            query = state.messages[-1] if state.messages else ""
            
            # Get farmer context from memory
            farmer_context = await self.memory.get_conversation_context("default_user")
            
            # Process with crop agent
            result = await self.crop_agent.process(query, farmer_context)
            
            # Update state
            state.current_agent = "crop"
            state.agent_reasoning = f"Analyzed query for crop advice: {result.get('analysis', 'No analysis')}"
            state.context.update(result.get('context', {}))
            
            logger.info(f"Crop agent processed: {result.get('response', 'No response')[:100]}...")
            return state
            
        except Exception as e:
            logger.error(f"Crop agent error: {e}")
            state.current_agent = "crop"
            state.agent_reasoning = f"Error in crop agent: {str(e)}"
            return state
    
    async def _disease_diagnosis_node(self, state: WorkflowState) -> WorkflowState:
        """Disease diagnosis agent node."""
        try:
            query = state.messages[-1] if state.messages else ""
            
            # Get farmer context
            farmer_context = await self.memory.get_conversation_context("default_user")
            
            # Process with disease agent
            result = await self.disease_agent.process(query, farmer_context)
            
            # Update state
            state.current_agent = "disease"
            state.agent_reasoning = f"Diagnosed disease/treatment: {result.get('analysis', 'No diagnosis')}"
            state.context.update(result.get('context', {}))
            
            logger.info(f"Disease agent processed: {result.get('response', 'No response')[:100]}...")
            return state
            
        except Exception as e:
            logger.error(f"Disease agent error: {e}")
            state.current_agent = "disease"
            state.agent_reasoning = f"Error in disease agent: {str(e)}"
            return state
    
    async def _weather_advisor_node(self, state: WorkflowState) -> WorkflowState:
        """Weather advisory agent node."""
        try:
            query = state.messages[-1] if state.messages else ""
            
            # Get farmer context
            farmer_context = await self.memory.get_conversation_context("default_user")
            
            # Process with weather agent
            result = await self.weather_agent.process(query, farmer_context)
            
            # Update state
            state.current_agent = "weather"
            state.agent_reasoning = f"Weather analysis: {result.get('analysis', 'No analysis')}"
            state.context.update(result.get('context', {}))
            
            logger.info(f"Weather agent processed: {result.get('response', 'No response')[:100]}...")
            return state
            
        except Exception as e:
            logger.error(f"Weather agent error: {e}")
            state.current_agent = "weather"
            state.agent_reasoning = f"Error in weather agent: {str(e)}"
            return state
    
    async def _knowledge_retrieval_node(self, state: WorkflowState) -> WorkflowState:
        """Knowledge retrieval agent node."""
        try:
            query = state.messages[-1] if state.messages else ""
            
            # Get farmer context
            farmer_context = await self.memory.get_conversation_context("default_user")
            
            # Process with retrieval agent
            result = await self.retrieval_agent.process(query, farmer_context)
            
            # Update state
            state.current_agent = "knowledge"
            state.agent_reasoning = f"Retrieved knowledge: {result.get('analysis', 'No analysis')}"
            state.context.update(result.get('context', {}))
            
            logger.info(f"Knowledge agent processed: {result.get('response', 'No response')[:100]}...")
            return state
            
        except Exception as e:
            logger.error(f"Knowledge agent error: {e}")
            state.current_agent = "knowledge"
            state.agent_reasoning = f"Error in knowledge agent: {str(e)}"
            return state
    
    async def _conversation_handler_node(self, state: WorkflowState) -> WorkflowState:
        """Conversation agent node."""
        try:
            query = state.messages[-1] if state.messages else ""
            
            # Get farmer context
            farmer_context = await self.memory.get_conversation_context("default_user")
            
            # Process with conversation agent
            result = await self.conversation_agent.process(query, farmer_context)
            
            # Update state
            state.current_agent = "conversation"
            state.agent_reasoning = f"General conversation: {result.get('analysis', 'No analysis')}"
            state.context.update(result.get('context', {}))
            
            logger.info(f"Conversation agent processed: {result.get('response', 'No response')[:100]}...")
            return state
            
        except Exception as e:
            logger.error(f"Conversation agent error: {e}")
            state.current_agent = "conversation"
            state.agent_reasoning = f"Error in conversation agent: {str(e)}"
            return state
    
    async def _final_response_node(self, state: WorkflowState) -> WorkflowState:
        """Final response generation node."""
        try:
            # Get the best response from the active agent
            if state.context and "response" in state.context:
                response = state.context["response"]
                confidence = state.context.get("confidence", 0.7)
                sources = state.context.get("sources", [])
                agent_type = state.current_agent or "unknown"
            else:
                response = "I apologize, but I couldn't process your request properly."
                confidence = 0.0
                sources = []
                agent_type = state.current_agent or "unknown"
            
            # Store conversation in memory
            await self.memory.add_message(
                user_id="default_user",
                message=state.messages[-1] if state.messages else "",
                response=response,
                agent_type=agent_type,
                confidence=confidence,
                sources=sources
            )
            
            # Update state
            state.agent_reasoning = f"Generated final response via {agent_type} agent"
            state.query_count = (state.query_count or 0) + 1
            
            logger.info(f"Final response generated: {response[:100]}...")
            return state
            
        except Exception as e:
            logger.error(f"Final response error: {e}")
            state.agent_reasoning = f"Error generating response: {str(e)}"
            return state
    
    async def process_query(self, query: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Process user query through LangGraph workflow.
        
        Args:
            query: User's agricultural question
            user_id: User identifier for memory
            
        Returns:
            Response with agent information and reasoning
        """
        try:
            start_time = datetime.now()
            
            # Create initial state
            initial_state = create_workflow_state()
            initial_state.messages = [query]
            initial_state.start_time = start_time
            initial_state.query_count = 0
            
            # Get workflow graph
            workflow = self.create_graph()
            
            # Process through workflow
            config = {"recursion_limit": 10}  # Prevent infinite loops
            
            final_state = None
            async for event in workflow.astream(initial_state, config):
                final_state = event
                if final_state is not None:
                    break
            
            # Calculate response time
            if final_state and final_state.start_time:
                response_time = (datetime.now() - final_state.start_time).total_seconds()
                logger.info(f"Query processed in {response_time:.2f}s via {final_state.current_agent}")
            
            # Format response
            if final_state and final_state.context:
                return {
                    "response": final_state.context.get("response", "No response generated"),
                    "agent_type": final_state.current_agent,
                    "confidence": final_state.context.get("confidence", 0.0),
                    "sources": final_state.context.get("sources", []),
                    "reasoning": final_state.agent_reasoning,
                    "response_time": response_time,
                    "query_count": final_state.query_count,
                    "workflow_steps": self._get_workflow_summary(final_state)
                }
            else:
                return {
                    "response": "I apologize, but I couldn't process your request.",
                    "agent_type": "error",
                    "confidence": 0.0,
                    "sources": [],
                    "reasoning": "Workflow failed to complete",
                    "response_time": 0.0,
                    "query_count": 0,
                    "workflow_steps": []
                }
                
        except Exception as e:
            logger.error(f"Workflow processing error: {e}")
            return {
                "response": f"Error processing your request: {str(e)}",
                "agent_type": "error",
                "confidence": 0.0,
                "sources": [],
                "reasoning": f"System error: {str(e)}",
                "response_time": 0.0,
                "query_count": 0,
                "workflow_steps": []
            }
    
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


# Global workflow instance
fda_workflow = FDAWorkflow()
