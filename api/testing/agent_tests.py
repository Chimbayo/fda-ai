"""
Comprehensive Testing Suite for All 5 FDA-AI Agents.
Tests specialized agents with Malawi-specific agricultural queries.
"""
import asyncio
import time
import logging
from typing import Dict, Any, List

# Import all agents
from api.agents.crop_agent_new import CropAgent
from api.agents.disease_agent_new import DiseaseAgent
from api.agents.weather_agent_new import WeatherAgent
from api.agents.retrieval_agent_new import RetrievalAgent
from api.agents.conversation_agent import ConversationAgent

logger = logging.getLogger(__name__)


class AgentTestSuite:
    """
    Comprehensive testing suite for FDA-AI agents.
    Tests all 5 agents with Malawi-specific queries.
    """
    
    def __init__(self):
        self.crop_agent = CropAgent()
        self.disease_agent = DiseaseAgent()
        self.weather_agent = WeatherAgent()
        self.retrieval_agent = RetrievalAgent()
        self.conversation_agent = ConversationAgent()
        
        # Test queries for each agent
        self.test_queries = {
            "crop": [
                "What maize varieties grow well in Malawi?",
                "When should I plant tomatoes in the southern region?",
                "What fertilizer schedule do you recommend for cabbage?",
                "How do I prepare soil for groundnut planting?",
                "What's the best spacing for maize in Malawi?"
            ],
            "disease": [
                "My maize leaves have yellow spots and are curling",
                "Tomato plants are wilting and have brown stems",
                "Cabbage leaves have white powder on them",
                "Maize stalks are breaking near the base",
                "Tomato fruits have black spots and are rotting"
            ],
            "weather": [
                "When is the best time to plant maize in Malawi?",
                "What rainfall patterns should I expect this season?",
                "How should I prepare for drought in the southern region?",
                "When does the rainy season start in northern Malawi?",
                "What crops are suitable for dry season farming?"
            ],
            "retrieval": [
                "Tell me about early blight in tomatoes",
                "What research exists on maize streak virus?",
                "Compare fertilizer types for Malawi soils",
                "Show me information about soil pH requirements",
                "What are the best pest control methods?"
            ],
            "conversation": [
                "Hello, I need help with my farm",
                "What can you help me with?",
                "Thank you for the advice",
                "I'm not sure what my problem is",
                "Can you explain that in simpler terms?"
            ]
        }
        
        # Performance tracking
        self.test_results = {
            "crop": [],
            "disease": [],
            "weather": [],
            "retrieval": [],
            "conversation": []
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive tests for all agents.
        
        Returns:
            Complete test results with performance metrics
        """
        logger.info("Starting comprehensive agent testing suite")
        
        start_time = time.time()
        
        # Test each agent
        for agent_name, queries in self.test_queries.items():
            logger.info(f"Testing {agent_name} agent...")
            agent_results = await self._test_agent(agent_name, queries)
            self.test_results[agent_name] = agent_results
        
        total_time = time.time() - start_time
        
        # Generate comprehensive report
        report = self._generate_test_report(total_time)
        
        logger.info(f"Testing completed in {total_time:.2f} seconds")
        return report
    
    async def _test_agent(self, agent_name: str, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Test individual agent with multiple queries.
        
        Args:
            agent_name: Name of agent to test
            queries: List of test queries
            
        Returns:
            Test results for the agent
        """
        agent = getattr(self, f"{agent_name}_agent")
        results = []
        
        for i, query in enumerate(queries, 1):
            logger.info(f"Testing {agent_name} query {i}: {query[:50]}...")
            
            start_time = time.time()
            
            try:
                # Test the agent
                result = await agent.process(query)
                
                response_time = time.time() - start_time
                
                # Evaluate response
                evaluation = self._evaluate_response(result, query, agent_name)
                
                test_result = {
                    "query": query,
                    "response_time": response_time,
                    "confidence": result.get("confidence", 0.0),
                    "sources": result.get("sources", []),
                    "evaluation": evaluation,
                    "response_preview": result.get("response", "")[:100],
                    "success": True
                }
                
                results.append(test_result)
                
                logger.info(f"Query {i} completed in {response_time:.2f}s - Score: {evaluation['score']:.2f}")
                
            except Exception as e:
                logger.error(f"Query {i} failed: {e}")
                results.append({
                    "query": query,
                    "response_time": time.time() - start_time,
                    "error": str(e),
                    "success": False,
                    "evaluation": {"score": 0.0, "issues": ["Agent error"]}
                })
        
        return results
    
    def _evaluate_response(self, result: Dict[str, Any], query: str, agent_type: str) -> Dict[str, Any]:
        """
        Evaluate agent response quality.
        
        Args:
            result: Agent response result
            query: Original query
            agent_type: Type of agent
            
        Returns:
            Evaluation score and feedback
        """
        score = 0.0
        issues = []
        strengths = []
        
        response = result.get("response", "")
        confidence = result.get("confidence", 0.0)
        sources = result.get("sources", [])
        
        # Basic response quality checks
        if len(response) > 50:
            score += 0.2
        else:
            issues.append("Response too short")
        
        if confidence > 0.7:
            score += 0.2
        else:
            issues.append("Low confidence")
        
        # Agent-specific evaluations
        if agent_type == "crop":
            if any(word in response.lower() for word in ["maize", "tomato", "cabbage"]):
                score += 0.2
            if any(word in response.lower() for word in ["plant", "fertilizer", "variety"]):
                score += 0.2
            if "malawi" in response.lower():
                score += 0.2
            else:
                issues.append("Not Malawi-specific")
        
        elif agent_type == "disease":
            if any(word in response.lower() for word in ["disease", "treatment", "symptom"]):
                score += 0.3
            if any(word in response.lower() for word in ["recommend", "suggest", "advise"]):
                score += 0.3
            if "confidence" in response.lower() or "likely" in response.lower():
                score += 0.2
            else:
                issues.append("No confidence indication")
        
        elif agent_type == "weather":
            if any(word in response.lower() for word in ["rain", "season", "climate"]):
                score += 0.3
            if any(word in response.lower() for word in ["planting", "harvest", "timing"]):
                score += 0.3
            if any(region in response.lower() for region in ["northern", "southern", "central"]):
                score += 0.2
            else:
                issues.append("No regional specificity")
        
        elif agent_type == "retrieval":
            if sources:
                score += 0.3
            else:
                issues.append("No sources cited")
            if "knowledge" in response.lower() or "information" in response.lower():
                score += 0.2
            if any(word in response.lower() for word in ["research", "study", "data"]):
                score += 0.3
            else:
                issues.append("No research references")
        
        elif agent_type == "conversation":
            if len(response) > 20:
                score += 0.3
            if any(word in response.lower() for word in ["help", "can", "assist"]):
                score += 0.3
            if "?" in response or "what" in response.lower():
                score += 0.2
            else:
                issues.append("Not conversational")
        
        # Identify strengths
        if score > 0.8:
            strengths.append("Excellent response")
        elif score > 0.6:
            strengths.append("Good response")
        elif score > 0.4:
            strengths.append("Adequate response")
        
        return {
            "score": min(score, 1.0),
            "issues": issues,
            "strengths": strengths,
            "confidence_adequate": confidence > 0.6,
            "response_adequate": len(response) > 30
        }
    
    def _generate_test_report(self, total_time: float) -> Dict[str, Any]:
        """
        Generate comprehensive test report.
        
        Args:
            total_time: Total testing time
            
        Returns:
            Complete test report with metrics
        """
        report = {
            "test_summary": {
                "total_time": total_time,
                "agents_tested": len(self.test_results),
                "total_queries": sum(len(results) for results in self.test_results.values()),
                "timestamp": time.time()
            },
            "agent_performance": {},
            "overall_metrics": {},
            "recommendations": []
        }
        
        # Calculate agent performance
        for agent_name, results in self.test_results.items():
            if results:
                avg_response_time = sum(r.get("response_time", 0) for r in results) / len(results)
                avg_confidence = sum(r.get("confidence", 0) for r in results) / len(results)
                avg_score = sum(r.get("evaluation", {}).get("score", 0) for r in results) / len(results)
                success_rate = sum(1 for r in results if r.get("success", False)) / len(results)
                
                report["agent_performance"][agent_name] = {
                    "avg_response_time": avg_response_time,
                    "avg_confidence": avg_confidence,
                    "avg_score": avg_score,
                    "success_rate": success_rate,
                    "total_queries": len(results)
                }
        
        # Calculate overall metrics
        all_response_times = []
        all_confidences = []
        all_scores = []
        
        for results in self.test_results.values():
            for result in results:
                if result.get("success", False):
                    all_response_times.append(result.get("response_time", 0))
                    all_confidences.append(result.get("confidence", 0))
                    all_scores.append(result.get("evaluation", {}).get("score", 0))
        
        if all_response_times:
            report["overall_metrics"] = {
                "avg_response_time": sum(all_response_times) / len(all_response_times),
                "avg_confidence": sum(all_confidences) / len(all_confidences),
                "avg_score": sum(all_scores) / len(all_scores),
                "fastest_response": min(all_response_times),
                "slowest_response": max(all_response_times),
                "queries_under_2s": sum(1 for t in all_response_times if t < 2.0),
                "queries_over_2s": sum(1 for t in all_response_times if t >= 2.0)
            }
        
        # Generate recommendations
        for agent_name, performance in report["agent_performance"].items():
            if performance["avg_response_time"] > 2.0:
                report["recommendations"].append(f"{agent_name} agent needs optimization - avg response time: {performance['avg_response_time']:.2f}s")
            
            if performance["avg_confidence"] < 0.7:
                report["recommendations"].append(f"{agent_name} agent shows low confidence - avg: {performance['avg_confidence']:.2f}")
            
            if performance["avg_score"] < 0.6:
                report["recommendations"].append(f"{agent_name} agent needs response quality improvement - avg score: {performance['avg_score']:.2f}")
        
        # Performance target assessment
        if report["overall_metrics"].get("queries_under_2s", 0) / len(all_response_times) > 0.8:
            report["performance_target_met"] = True
            report["performance_status"] = "EXCELLENT - <2s target achieved"
        else:
            report["performance_target_met"] = False
            report["performance_status"] = "NEEDS IMPROVEMENT - <2s target not met"
        
        return report
    
    async def run_single_agent_test(self, agent_name: str, query: str) -> Dict[str, Any]:
        """
        Test single agent with specific query.
        
        Args:
            agent_name: Name of agent to test
            query: Test query
            
        Returns:
            Test result for single query
        """
        agent = getattr(self, f"{agent_name}_agent")
        
        start_time = time.time()
        
        try:
            result = await agent.process(query)
            response_time = time.time() - start_time
            
            evaluation = self._evaluate_response(result, query, agent_name)
            
            return {
                "agent": agent_name,
                "query": query,
                "response": result.get("response", ""),
                "response_time": response_time,
                "confidence": result.get("confidence", 0.0),
                "sources": result.get("sources", []),
                "evaluation": evaluation,
                "success": True
            }
            
        except Exception as e:
            return {
                "agent": agent_name,
                "query": query,
                "error": str(e),
                "response_time": time.time() - start_time,
                "success": False
            }


# Global test suite instance
agent_test_suite = AgentTestSuite()
