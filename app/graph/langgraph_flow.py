"""
LangGraph workflow orchestration for FDA-AI.
Manages the flow between router and specialized agents.
"""
from typing import Dict, Any, List, TypedDict, Annotated
import operator
import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.router import AgentRouter, AgentType
from app.agents.crop_agent import CropAgent
from app.agents.disease_agent import DiseaseAgent
from app.agents.weather_agent import WeatherAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.conversation_agent import ConversationAgent

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State structure for the LangGraph workflow."""
    message: str
    user_id: str
    session_id: str
    location: str
    history: List[Dict[str, Any]]
    agent_type: AgentType
    response: str
    confidence: float
    sources: List[Dict[str, Any]]
    context: Dict[str, Any]
    error: str


class LangGraphWorkflow:
    """
    Main workflow orchestrator using LangGraph.
    Coordinates routing and agent execution.
    """
    
    def __init__(self):
        self.router = AgentRouter()
        
        # Initialize agents
        self.agents = {
            AgentType.CROP: CropAgent(),
            AgentType.DISEASE: DiseaseAgent(),
            AgentType.WEATHER: WeatherAgent(),
            AgentType.RETRIEVAL: RetrievalAgent(),
            AgentType.CONVERSATION: ConversationAgent()
        }
        
        # Build workflow graph
        self.workflow = self._build_graph()
        logger.info("LangGraph workflow initialized successfully")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow graph.
        
        Returns:
            Compiled workflow graph
        """
        # Create state graph
        graph = StateGraph(WorkflowState)
        
        # Add nodes
        graph.add_node("router", self._route_node)
        graph.add_node("crop_agent", self._agent_node_factory(AgentType.CROP))
        graph.add_node("disease_agent", self._agent_node_factory(AgentType.DISEASE))
        graph.add_node("weather_agent", self._agent_node_factory(AgentType.WEATHER))
        graph.add_node("retrieval_agent", self._agent_node_factory(AgentType.RETRIEVAL))
        graph.add_node("conversation_agent", self._agent_node_factory(AgentType.CONVERSATION))
        graph.add_node("finalize", self._finalize_node)
        
        # Add conditional edges from router
        graph.add_conditional_edges(
            "router",
            self._route_decision,
            {
                AgentType.CROP.value: "crop_agent",
                AgentType.DISEASE.value: "disease_agent",
                AgentType.WEATHER.value: "weather_agent",
                AgentType.RETRIEVAL.value: "retrieval_agent",
                AgentType.CONVERSATION.value: "conversation_agent"
            }
        )
        
        # Add edges from agents to finalize
        for agent_type in AgentType:
            graph.add_edge(f"{agent_type.value}_agent", "finalize")
        
        # Set entry point
        graph.set_entry_point("router")
        
        # Compile with memory checkpointing
        memory = MemorySaver()
        return graph.compile(checkpointer=memory)
    
    async def _route_node(self, state: WorkflowState) -> WorkflowState:
        """
        Router node - determines which agent to use.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with routing decision
        """
        try:
            agent_type = await self.router.route(
                state["message"],
                context={
                    "location": state.get("location"),
                    "history": state.get("history", [])
                }
            )
            
            state["agent_type"] = agent_type
            logger.info(f"Routed to {agent_type.value} agent")
            
        except Exception as e:
            logger.error(f"Routing error: {e}")
            state["agent_type"] = AgentType.CONVERSATION
            state["error"] = str(e)
        
        return state
    
    def _route_decision(self, state: WorkflowState) -> str:
        """
        Determine next node based on routing decision.
        
        Args:
            state: Current workflow state
            
        Returns:
            Next node name
        """
        agent_type = state.get("agent_type", AgentType.CONVERSATION)
        return agent_type.value
    
    def _agent_node_factory(self, agent_type: AgentType):
        """
        Factory function to create agent nodes.
        
        Args:
            agent_type: Type of agent to create node for
            
        Returns:
            Agent node function
        """
        async def agent_node(state: WorkflowState) -> WorkflowState:
            try:
                agent = self.agents[agent_type]
                
                # Execute agent
                result = await agent.process(
                    message=state["message"],
                    context={
                        "location": state.get("location"),
                        "history": state.get("history", []),
                        "user_id": state.get("user_id")
                    }
                )
                
                # Update state with results
                state["response"] = result.get("response", "")
                state["confidence"] = result.get("confidence", 0.0)
                state["sources"] = result.get("sources", [])
                state["context"] = result.get("context", {})
                
                logger.info(f"{agent_type.value} agent completed with confidence {state['confidence']}")
                
            except Exception as e:
                logger.error(f"{agent_type.value} agent error: {e}")
                state["error"] = str(e)
                state["response"] = "I apologize, but I encountered an error processing your request. Please try again."
                state["confidence"] = 0.0
            
            return state
        
        return agent_node
    
    async def _finalize_node(self, state: WorkflowState) -> WorkflowState:
        """
        Finalize node - post-process and format output.
        
        Args:
            state: Current workflow state
            
        Returns:
            Final state
        """
        # Add metadata
        state["context"] = state.get("context", {})
        state["context"]["timestamp"] = datetime.now().isoformat()
        state["context"]["agent_type"] = state.get("agent_type", AgentType.CONVERSATION).value
        
        return state
    
    async def process(
        self,
        message: str,
        user_id: str,
        session_id: str = None,
        location: str = None,
        history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message through the workflow.
        
        Args:
            message: User's query
            user_id: User identifier
            session_id: Session identifier
            location: Optional location context
            history: Conversation history
            
        Returns:
            Processing results
        """
        # Initialize state
        initial_state: WorkflowState = {
            "message": message,
            "user_id": user_id,
            "session_id": session_id or f"{user_id}_{datetime.now().timestamp()}",
            "location": location,
            "history": history or [],
            "agent_type": AgentType.CONVERSATION,
            "response": "",
            "confidence": 0.0,
            "sources": [],
            "context": {},
            "error": ""
        }
        
        # Execute workflow
        try:
            config = {"configurable": {"thread_id": initial_state["session_id"]}}
            result = await self.workflow.ainvoke(initial_state, config=config)
            
            return {
                "response": result["response"],
                "agent_type": result["agent_type"].value,
                "confidence": result["confidence"],
                "sources": result["sources"],
                "context": result["context"]
            }
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {
                "response": "I apologize, but I encountered an error. Please try again.",
                "agent_type": "error",
                "confidence": 0.0,
                "sources": [],
                "context": {"error": str(e)}
            }
