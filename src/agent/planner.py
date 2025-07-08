"""
Task Planning System for AI Agent
Breaks down complex tasks into executable steps using AI reasoning
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .llm import LLMInterface
from .memory import MemoryManager


class TaskPlanner:
    """
    Intelligent task planner that breaks down complex tasks into manageable steps
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = LLMInterface(config)
        self.memory = MemoryManager(config.get('database', {}))
        self.logger = logging.getLogger('TaskPlanner')
        
    async def create_plan(self, task_description: str, analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a detailed execution plan for a task"""
        
        # Get similar tasks for context
        similar_tasks = await self.memory.find_similar_tasks(task_description, limit=3)
        
        # Get learned patterns
        learned_patterns = await self.memory.get_learned_patterns(min_confidence=0.6)
        
        # Create planning prompt
        prompt = self._create_planning_prompt(task_description, analysis, similar_tasks, learned_patterns)
        
        # Generate plan using LLM
        plan_response = await self.llm.generate(prompt)
        
        try:
            plan = json.loads(plan_response)
            
            # Validate and enhance the plan
            plan = await self._validate_and_enhance_plan(plan, task_description)
            
            # Store successful planning pattern
            await self._store_planning_pattern(task_description, plan, analysis)
            
            return plan
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse plan JSON: {e}")
            # Fallback to simple plan
            return self._create_fallback_plan(task_description, analysis)
    
    def _create_planning_prompt(self, task_description: str, analysis: Dict[str, Any], 
                              similar_tasks: List[Dict], learned_patterns: List[Dict]) -> str:
        """Create a comprehensive planning prompt"""
        
        similar_context = ""
        if similar_tasks:
            similar_context = "Similar past tasks:\n"
            for i, similar in enumerate(similar_tasks[:3]):
                task = similar['task']
                similar_context += f"{i+1}. {task.description} (Status: {task.status.value}, Similarity: {similar['similarity']:.2f})\n"
        
        patterns_context = ""
        if learned_patterns:
            patterns_context = "Learned patterns:\n"
            for pattern in learned_patterns[:3]:
                patterns_context += f"- {pattern['pattern_type']}: {pattern['confidence']:.2f} confidence\n"
        
        return f"""
        You are an expert task planner for an AI agent. Create a detailed, executable plan for the following task.
        
        TASK: {task_description}
        
        ANALYSIS: {json.dumps(analysis, indent=2) if analysis else 'No analysis provided'}
        
        {similar_context}
        
        {patterns_context}
        
        Available tools:
        - web_search: Search the internet for information
        - file_operations: Read, write, create, delete files
        - code_execution: Execute Python code safely
        - data_analysis: Analyze data and create visualizations
        - api_calls: Make HTTP requests to external APIs
        - llm_reasoning: Use AI reasoning for complex decisions
        
        Create a JSON plan with the following structure:
        {{
            "plan_id": "unique-plan-id",
            "task_description": "original task description",
            "estimated_duration_minutes": 30,
            "complexity_score": 5,
            "prerequisites": ["list of prerequisites"],
            "steps": [
                {{
                    "step_id": 1,
                    "description": "detailed step description",
                    "tool": "tool_name_or_null",
                    "parameters": {{"key": "value"}},
                    "expected_output": "what this step should produce",
                    "success_criteria": "how to know this step succeeded",
                    "estimated_duration_minutes": 5,
                    "dependencies": [0],
                    "risk_level": "low|medium|high",
                    "fallback_options": ["alternative approaches if this fails"]
                }}
            ],
            "success_criteria": "overall success criteria for the task",
            "fallback_plan": "what to do if the main plan fails",
            "learning_opportunities": "what can be learned from this task"
        }}
        
        IMPORTANT:
        - Break complex tasks into smaller, manageable steps
        - Each step should be atomic and testable
        - Consider dependencies between steps
        - Include error handling and fallback options
        - Make the plan as detailed and actionable as possible
        - Ensure all tool parameters are realistic and valid
        """
    
    async def _validate_and_enhance_plan(self, plan: Dict[str, Any], task_description: str) -> Dict[str, Any]:
        """Validate and enhance the generated plan"""
        
        # Ensure required fields
        if 'steps' not in plan:
            plan['steps'] = []
        
        if 'plan_id' not in plan:
            plan['plan_id'] = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate and enhance steps
        enhanced_steps = []
        for i, step in enumerate(plan.get('steps', [])):
            enhanced_step = await self._enhance_step(step, i)
            enhanced_steps.append(enhanced_step)
        
        plan['steps'] = enhanced_steps
        
        # Add metadata
        plan['created_at'] = datetime.now().isoformat()
        plan['planner_version'] = "1.0"
        
        return plan
    
    async def _enhance_step(self, step: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """Enhance a single step with validation and defaults"""
        
        # Set defaults
        step.setdefault('step_id', step_index + 1)
        step.setdefault('estimated_duration_minutes', 5)
        step.setdefault('risk_level', 'medium')
        step.setdefault('dependencies', [])
        step.setdefault('fallback_options', [])
        step.setdefault('parameters', {})
        
        # Validate tool exists
        available_tools = ['web_search', 'file_operations', 'code_execution', 
                          'data_analysis', 'api_calls', 'llm_reasoning']
        
        if step.get('tool') and step['tool'] not in available_tools:
            step['tool'] = 'llm_reasoning'  # Fallback to LLM reasoning
        
        return step
    
    def _create_fallback_plan(self, task_description: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a simple fallback plan if LLM planning fails"""
        return {
            "plan_id": f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "task_description": task_description,
            "estimated_duration_minutes": 15,
            "complexity_score": analysis.get('complexity', 5) if analysis else 5,
            "prerequisites": [],
            "steps": [
                {
                    "step_id": 1,
                    "description": f"Analyze and understand the task: {task_description}",
                    "tool": "llm_reasoning",
                    "parameters": {"query": task_description},
                    "expected_output": "Task analysis and approach",
                    "success_criteria": "Clear understanding of what needs to be done",
                    "estimated_duration_minutes": 5,
                    "dependencies": [],
                    "risk_level": "low",
                    "fallback_options": ["Manual review required"]
                },
                {
                    "step_id": 2,
                    "description": f"Execute the task: {task_description}",
                    "tool": "llm_reasoning",
                    "parameters": {"query": f"How to complete: {task_description}"},
                    "expected_output": "Task completion",
                    "success_criteria": "Task objectives met",
                    "estimated_duration_minutes": 10,
                    "dependencies": [1],
                    "risk_level": "medium",
                    "fallback_options": ["Break into smaller subtasks"]
                }
            ],
            "success_criteria": "Task completed successfully",
            "fallback_plan": "Manual intervention required",
            "learning_opportunities": "Learn from task execution patterns",
            "created_at": datetime.now().isoformat(),
            "planner_version": "1.0_fallback"
        }
    
    async def _store_planning_pattern(self, task_description: str, plan: Dict[str, Any], analysis: Dict[str, Any]):
        """Store successful planning patterns for future use"""
        pattern_data = {
            "task_type": analysis.get('task_type') if analysis else 'general',
            "complexity": analysis.get('complexity') if analysis else plan.get('complexity_score', 5),
            "step_count": len(plan.get('steps', [])),
            "tools_used": [step.get('tool') for step in plan.get('steps', []) if step.get('tool')],
            "estimated_duration": plan.get('estimated_duration_minutes', 0),
            "plan_structure": {
                "has_prerequisites": bool(plan.get('prerequisites')),
                "has_fallback": bool(plan.get('fallback_plan')),
                "step_dependencies": any(step.get('dependencies') for step in plan.get('steps', []))
            }
        }
        
        await self.memory.store_learned_pattern(
            pattern_type="planning_pattern",
            pattern_data=pattern_data,
            confidence=0.7  # Initial confidence for new patterns
        )
    
    async def optimize_plan(self, plan: Dict[str, Any], execution_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize a plan based on execution feedback"""
        
        optimization_prompt = f"""
        Optimize this execution plan based on the feedback received:
        
        ORIGINAL PLAN:
        {json.dumps(plan, indent=2)}
        
        EXECUTION FEEDBACK:
        {json.dumps(execution_feedback, indent=2)}
        
        Please provide an optimized version of the plan that addresses:
        1. Any failed steps
        2. Efficiency improvements
        3. Better error handling
        4. Reduced complexity where possible
        
        Return the optimized plan in the same JSON format.
        """
        
        try:
            optimized_response = await self.llm.generate(optimization_prompt)
            optimized_plan = json.loads(optimized_response)
            
            # Store optimization pattern
            await self.memory.store_learned_pattern(
                pattern_type="plan_optimization",
                pattern_data={
                    "original_complexity": plan.get('complexity_score', 5),
                    "feedback_type": execution_feedback.get('type', 'general'),
                    "optimization_applied": True
                },
                confidence=0.8
            )
            
            return optimized_plan
            
        except Exception as e:
            self.logger.error(f"Failed to optimize plan: {e}")
            return plan  # Return original plan if optimization fails
    
    async def estimate_plan_success_probability(self, plan: Dict[str, Any]) -> float:
        """Estimate the probability of plan success based on learned patterns"""
        
        # Get similar past plans
        similar_tasks = await self.memory.find_similar_tasks(plan.get('task_description', ''))
        
        if not similar_tasks:
            return 0.5  # Default probability
        
        # Calculate success rate of similar tasks
        successful_tasks = sum(1 for task in similar_tasks if task['task'].status.value == 'completed')
        success_rate = successful_tasks / len(similar_tasks)
        
        # Adjust based on plan complexity
        complexity_factor = max(0.1, 1.0 - (plan.get('complexity_score', 5) - 1) * 0.1)
        
        # Adjust based on available tools
        tool_factor = 1.0
        if plan.get('steps'):
            tools_with_none = [step.get('tool') for step in plan['steps']]
            none_tools = sum(1 for tool in tools_with_none if tool is None)
            if none_tools > 0:
                tool_factor = max(0.3, 1.0 - (none_tools / len(tools_with_none)) * 0.5)
        
        estimated_probability = success_rate * complexity_factor * tool_factor
        return min(1.0, max(0.1, estimated_probability))