"""
Production Demo with Performance Metrics for FDA-AI.
Demonstrates all 5 agents with comprehensive performance reporting.
"""
import asyncio
import time
import logging
from typing import Dict, Any, List
from datetime import datetime

from app.graph.langgraph_flow_new import fda_workflow
from app.testing.agent_tests import agent_test_suite
from app.performance.optimizer import performance_optimizer

logger = logging.getLogger(__name__)


class ProductionDemo:
    """
    Production demonstration system for FDA-AI.
    Shows all agent capabilities with performance metrics.
    """
    
    def __init__(self):
        self.workflow = fda_workflow
        self.test_suite = agent_test_suite
        self.optimizer = performance_optimizer
        
        # Demo scenarios
        self.demo_scenarios = [
            {
                "name": "Crop Advisory Demo",
                "query": "What maize varieties grow best in southern Malawi and when should I plant them?",
                "expected_agent": "crop",
                "expected_response_time": 2.0
            },
            {
                "name": "Disease Diagnosis Demo",
                "query": "My tomato leaves have yellow spots and are curling, what should I do?",
                "expected_agent": "disease",
                "expected_response_time": 2.0
            },
            {
                "name": "Weather Advisory Demo",
                "query": "When does the rainy season start in northern Malawi and what crops should I plant?",
                "expected_agent": "weather",
                "expected_response_time": 2.0
            },
            {
                "name": "Knowledge Retrieval Demo",
                "query": "Tell me about early blight in tomatoes and treatment options",
                "expected_agent": "knowledge",
                "expected_response_time": 2.0
            },
            {
                "name": "Conversation Demo",
                "query": "Hello, I need help with my farm but I'm not sure what the problem is",
                "expected_agent": "conversation",
                "expected_response_time": 2.0
            }
        ]
    
    async def run_production_demo(self) -> Dict[str, Any]:
        """
        Run complete production demonstration.
        
        Returns:
            Comprehensive demo results with performance metrics
        """
        logger.info("Starting FDA-AI Production Demo")
        
        demo_results = {
            "demo_info": {
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0",
                "agents_tested": 5,
                "scenarios_count": len(self.demo_scenarios)
            },
            "scenario_results": [],
            "performance_metrics": {},
            "agent_routing_accuracy": {},
            "response_time_analysis": {},
            "overall_assessment": {}
        }
        
        # Precompute common queries for performance
        await self.optimizer.precompute_common_queries()
        
        # Run each demo scenario
        for scenario in self.demo_scenarios:
            logger.info(f"Running scenario: {scenario['name']}")
            
            scenario_result = await self._run_scenario(scenario)
            demo_results["scenario_results"].append(scenario_result)
        
        # Generate performance metrics
        demo_results["performance_metrics"] = self._calculate_performance_metrics(demo_results["scenario_results"])
        
        # Analyze agent routing accuracy
        demo_results["agent_routing_accuracy"] = self._analyze_routing_accuracy(demo_results["scenario_results"])
        
        # Response time analysis
        demo_results["response_time_analysis"] = self._analyze_response_times(demo_results["scenario_results"])
        
        # Overall assessment
        demo_results["overall_assessment"] = self._generate_overall_assessment(demo_results)
        
        logger.info("Production demo completed")
        return demo_results
    
    async def _run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run individual demo scenario.
        
        Args:
            scenario: Demo scenario configuration
            
        Returns:
            Scenario execution results
        """
        start_time = time.time()
        
        try:
            # Run query through workflow
            result = await self.workflow.process_query(scenario["query"])
            
            response_time = time.time() - start_time
            
            # Evaluate scenario success
            success_evaluation = self._evaluate_scenario_success(scenario, result, response_time)
            
            return {
                "scenario_name": scenario["name"],
                "query": scenario["query"],
                "expected_agent": scenario["expected_agent"],
                "actual_agent": result.get("agent_type"),
                "response_time": response_time,
                "expected_response_time": scenario["expected_response_time"],
                "response": result.get("response", ""),
                "confidence": result.get("confidence", 0.0),
                "sources": result.get("sources", []),
                "workflow_steps": result.get("workflow_steps", []),
                "success_evaluation": success_evaluation,
                "performance_met": response_time <= scenario["expected_response_time"]
            }
            
        except Exception as e:
            logger.error(f"Scenario {scenario['name']} failed: {e}")
            return {
                "scenario_name": scenario["name"],
                "query": scenario["query"],
                "error": str(e),
                "response_time": time.time() - start_time,
                "success_evaluation": {"score": 0.0, "issues": ["System error"]},
                "performance_met": False
            }
    
    def _evaluate_scenario_success(self, scenario: Dict[str, Any], result: Dict[str, Any], response_time: float) -> Dict[str, Any]:
        """
        Evaluate scenario success criteria.
        
        Args:
            scenario: Original scenario configuration
            result: Workflow result
            response_time: Actual response time
            
        Returns:
            Success evaluation with score and feedback
        """
        score = 0.0
        issues = []
        strengths = []
        
        # Agent routing accuracy
        if result.get("agent_type") == scenario["expected_agent"]:
            score += 0.3
            strengths.append("Correct agent routing")
        else:
            issues.append(f"Expected {scenario['expected_agent']}, got {result.get('agent_type')}")
        
        # Response time performance
        if response_time <= scenario["expected_response_time"]:
            score += 0.3
            strengths.append(f"Response time target met ({response_time:.2f}s)")
        else:
            issues.append(f"Response time exceeded ({response_time:.2f}s > {scenario['expected_response_time']}s)")
        
        # Response quality
        response = result.get("response", "")
        if len(response) > 100:
            score += 0.2
        else:
            issues.append("Response too short")
        
        # Confidence level
        confidence = result.get("confidence", 0.0)
        if confidence > 0.7:
            score += 0.2
        else:
            issues.append(f"Low confidence ({confidence:.2f})")
        
        # Sources provided
        if result.get("sources"):
            score += 0.1
        else:
            issues.append("No sources provided")
        
        return {
            "score": min(score, 1.0),
            "issues": issues,
            "strengths": strengths,
            "overall_success": score > 0.6
        }
    
    def _calculate_performance_metrics(self, scenario_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            scenario_results: All scenario execution results
            
        Returns:
            Performance metrics summary
        """
        successful_scenarios = [r for r in scenario_results if r.get("success_evaluation", {}).get("overall_success", False)]
        response_times = [r.get("response_time", 0) for r in scenario_results if "response_time" in r]
        confidences = [r.get("confidence", 0) for r in scenario_results if "confidence" in r]
        
        return {
            "total_scenarios": len(scenario_results),
            "successful_scenarios": len(successful_scenarios),
            "success_rate": len(successful_scenarios) / len(scenario_results),
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "scenarios_under_2s": sum(1 for t in response_times if t <= 2.0),
            "scenarios_over_2s": sum(1 for t in response_times if t > 2.0),
            "performance_target_met": sum(1 for t in response_times if t <= 2.0) >= len(scenario_results) * 0.8
        }
    
    def _analyze_routing_accuracy(self, scenario_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze agent routing accuracy.
        
        Args:
            scenario_results: All scenario execution results
            
        Returns:
            Routing accuracy analysis
        """
        correct_routing = sum(1 for r in scenario_results 
                           if r.get("actual_agent") == r.get("expected_agent"))
        
        agent_performance = {}
        for result in scenario_results:
            expected = result.get("expected_agent")
            actual = result.get("actual_agent")
            
            if expected not in agent_performance:
                agent_performance[expected] = {"correct": 0, "total": 0}
            
            agent_performance[expected]["total"] += 1
            if expected == actual:
                agent_performance[expected]["correct"] += 1
        
        return {
            "overall_accuracy": correct_routing / len(scenario_results),
            "correct_routing": correct_routing,
            "total_routing": len(scenario_results),
            "agent_performance": agent_performance
        }
    
    def _analyze_response_times(self, scenario_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze response time performance.
        
        Args:
            scenario_results: All scenario execution results
            
        Returns:
            Response time analysis
        """
        response_times = [r.get("response_time", 0) for r in scenario_results if "response_time" in r]
        
        if not response_times:
            return {"error": "No response times available"}
        
        # Categorize response times
        under_1s = sum(1 for t in response_times if t < 1.0)
        under_2s = sum(1 for t in response_times if t < 2.0)
        over_2s = sum(1 for t in response_times if t >= 2.0)
        over_3s = sum(1 for t in response_times if t >= 3.0)
        
        return {
            "avg_response_time": sum(response_times) / len(response_times),
            "median_response_time": sorted(response_times)[len(response_times) // 2],
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "under_1s_count": under_1s,
            "under_2s_count": under_2s,
            "over_2s_count": over_2s,
            "over_3s_count": over_3s,
            "under_1s_percentage": under_1s / len(response_times),
            "under_2s_percentage": under_2s / len(response_times),
            "over_2s_percentage": over_2s / len(response_times),
            "performance_target_met": under_2s >= len(response_times) * 0.8
        }
    
    def _generate_overall_assessment(self, demo_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate overall assessment of the system.
        
        Args:
            demo_results: Complete demo results
            
        Returns:
            Overall system assessment
        """
        performance = demo_results.get("performance_metrics", {})
        routing = demo_results.get("agent_routing_accuracy", {})
        response_times = demo_results.get("response_time_analysis", {})
        
        # Calculate overall score
        overall_score = 0.0
        
        # Success rate (40% weight)
        success_rate = performance.get("success_rate", 0.0)
        overall_score += success_rate * 0.4
        
        # Routing accuracy (30% weight)
        routing_accuracy = routing.get("overall_accuracy", 0.0)
        overall_score += routing_accuracy * 0.3
        
        # Response time performance (30% weight)
        under_2s_percentage = response_times.get("under_2s_percentage", 0.0)
        overall_score += under_2s_percentage * 0.3
        
        # Determine status
        if overall_score >= 0.9:
            status = "EXCELLENT"
            recommendation = "System ready for production deployment"
        elif overall_score >= 0.8:
            status = "GOOD"
            recommendation = "System ready with minor optimizations"
        elif overall_score >= 0.7:
            status = "ACCEPTABLE"
            recommendation = "System needs performance improvements before production"
        else:
            status = "NEEDS WORK"
            recommendation = "System requires significant improvements"
        
        return {
            "overall_score": overall_score,
            "status": status,
            "recommendation": recommendation,
            "key_metrics": {
                "success_rate": success_rate,
                "routing_accuracy": routing_accuracy,
                "response_time_performance": under_2s_percentage,
                "avg_response_time": performance.get("avg_response_time", 0.0)
            },
            "production_readiness": overall_score >= 0.8
        }
    
    async def generate_demo_report(self, demo_results: Dict[str, Any]) -> str:
        """
        Generate formatted demo report.
        
        Args:
            demo_results: Complete demo results
            
        Returns:
            Formatted demo report
        """
        report = f"""
# FDA-AI Production Demo Report

## Executive Summary
- **Overall Score**: {demo_results['overall_assessment']['overall_score']:.2f}
- **Status**: {demo_results['overall_assessment']['status']}
- **Production Ready**: {demo_results['overall_assessment']['production_readiness']}
- **Recommendation**: {demo_results['overall_assessment']['recommendation']}

## Performance Metrics
- **Success Rate**: {demo_results['performance_metrics']['success_rate']:.2%}
- **Average Response Time**: {demo_results['performance_metrics']['avg_response_time']:.2f}s
- **Scenarios Under 2s**: {demo_results['performance_metrics']['scenarios_under_2s']}/{demo_results['performance_metrics']['total_scenarios']}
- **Performance Target Met**: {demo_results['performance_metrics']['performance_target_met']}

## Agent Routing Accuracy
- **Overall Accuracy**: {demo_results['agent_routing_accuracy']['overall_accuracy']:.2%}
- **Correct Routing**: {demo_results['agent_routing_accuracy']['correct_routing']}/{demo_results['agent_routing_accuracy']['total_routing']}

## Scenario Results
"""
        
        for scenario in demo_results['scenario_results']:
            report += f"""
### {scenario['scenario_name']}
- **Query**: {scenario['query']}
- **Expected Agent**: {scenario['expected_agent']}
- **Actual Agent**: {scenario['actual_agent']}
- **Response Time**: {scenario['response_time']:.2f}s
- **Performance Met**: {scenario['performance_met']}
- **Score**: {scenario['success_evaluation']['score']:.2f}
- **Strengths**: {', '.join(scenario['success_evaluation']['strengths'])}
- **Issues**: {', '.join(scenario['success_evaluation']['issues'])}
"""
        
        return report


# Global production demo instance
production_demo = ProductionDemo()
