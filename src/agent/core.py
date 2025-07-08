"""
Core AI Agent Implementation
Fully autonomous agent with reasoning, planning, and execution capabilities
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from .types import Task, TaskStatus
from .memory import MemoryManager
from .planner import TaskPlanner
from .tools import ToolManager
from .llm import LLMInterface


class AutoAgent:
    """
    Fully Automated AI Agent with autonomous reasoning and task execution
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.is_running = False
        self.tasks = {}
        self.active_tasks = {}
        
        # Initialize components
        self.memory = MemoryManager(config.get('database', {}))
        self.planner = TaskPlanner(config)
        self.tools = ToolManager(config)
        self.llm = LLMInterface(config)
        
        # Setup logging
        self.logger = logging.getLogger(f"AutoAgent-{self.agent_id[:8]}")
        
        # Autonomous operation settings
        self.max_concurrent_tasks = config.get('autonomous_mode', {}).get('max_concurrent_tasks', 3)
        self.check_interval = config.get('autonomous_mode', {}).get('check_interval_seconds', 60)
        
    async def start(self):
        """Start the autonomous agent"""
        self.is_running = True
        self.logger.info(f"Starting AutoAgent {self.agent_id}")
        
        # Start main execution loop
        await self._main_loop()
    
    async def stop(self):
        """Stop the autonomous agent"""
        self.is_running = False
        self.logger.info(f"Stopping AutoAgent {self.agent_id}")
        
        # Cancel all active tasks
        for task_id in list(self.active_tasks.keys()):
            await self._cancel_task(task_id)
    
    async def add_task(self, description: str, priority: int = 1, parent_task_id: str = None) -> str:
        """Add a new task to the agent"""
        task = Task(
            id=str(uuid.uuid4()),
            description=description,
            priority=priority,
            parent_task_id=parent_task_id
        )
        
        self.tasks[task.id] = task
        await self.memory.store_task(task)
        
        self.logger.info(f"Added task: {task.description} (ID: {task.id})")
        return task.id
    
    async def _main_loop(self):
        """Main autonomous execution loop"""
        while self.is_running:
            try:
                # Check for pending tasks
                await self._process_pending_tasks()
                
                # Monitor active tasks
                await self._monitor_active_tasks()
                
                # Autonomous reasoning - generate new tasks if needed
                await self._autonomous_reasoning()
                
                # Wait before next iteration
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _process_pending_tasks(self):
        """Process pending tasks based on priority and capacity"""
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            return
        
        # Get pending tasks sorted by priority
        pending_tasks = [
            task for task in self.tasks.values() 
            if task.status == TaskStatus.PENDING
        ]
        pending_tasks.sort(key=lambda t: (-t.priority, t.created_at))
        
        # Start tasks up to capacity
        for task in pending_tasks[:self.max_concurrent_tasks - len(self.active_tasks)]:
            await self._start_task(task)
    
    async def _start_task(self, task: Task):
        """Start executing a task"""
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        
        self.active_tasks[task.id] = asyncio.create_task(self._execute_task(task))
        self.logger.info(f"Started task: {task.description}")
    
    async def _execute_task(self, task: Task):
        """Execute a single task with full AI reasoning"""
        try:
            self.logger.info(f"Executing task: {task.description}")
            
            # Step 1: Analyze the task
            analysis = await self._analyze_task(task)
            
            # Step 2: Create execution plan
            plan = await self.planner.create_plan(task.description, analysis)
            
            # Step 3: Execute the plan
            result = await self._execute_plan(task, plan)
            
            # Step 4: Validate and store results
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            await self.memory.update_task(task)
            self.logger.info(f"Completed task: {task.description}")
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            await self.memory.update_task(task)
            self.logger.error(f"Failed task: {task.description} - {e}")
        
        finally:
            # Remove from active tasks
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
    
    async def _analyze_task(self, task: Task) -> Dict[str, Any]:
        """Analyze a task to understand requirements and context"""
        prompt = f"""
        Analyze this task and provide a structured analysis:
        
        Task: {task.description}
        
        Please provide:
        1. Task type and category
        2. Required tools and resources
        3. Complexity estimation (1-10)
        4. Dependencies and prerequisites
        5. Success criteria
        6. Potential risks or challenges
        
        Format as JSON.
        """
        
        response = await self.llm.generate(prompt)
        try:
            return json.loads(response)
        except:
            return {"analysis": response, "complexity": 5}
    
    async def _execute_plan(self, task: Task, plan: Dict[str, Any]) -> Any:
        """Execute a plan using available tools"""
        results = []
        
        for step in plan.get('steps', []):
            step_result = await self._execute_step(step)
            results.append(step_result)
            
            # Store intermediate results in memory
            await self.memory.store_execution_step(task.id, step, step_result)
        
        return {
            'plan': plan,
            'steps_executed': len(results),
            'results': results,
            'success': True
        }
    
    async def _execute_step(self, step: Dict[str, Any]) -> Any:
        """Execute a single step of a plan"""
        tool_name = step.get('tool')
        parameters = step.get('parameters', {})
        
        if tool_name and hasattr(self.tools, tool_name):
            tool_func = getattr(self.tools, tool_name)
            return await tool_func(**parameters)
        else:
            # Fallback to LLM reasoning
            return await self.llm.generate(step.get('description', ''))
    
    async def _monitor_active_tasks(self):
        """Monitor and manage active tasks"""
        completed_tasks = []
        
        for task_id, task_future in self.active_tasks.items():
            if task_future.done():
                completed_tasks.append(task_id)
        
        # Clean up completed tasks
        for task_id in completed_tasks:
            del self.active_tasks[task_id]
    
    async def _autonomous_reasoning(self):
        """Autonomous reasoning to generate new tasks and goals"""
        if not self.config.get('autonomous_mode', {}).get('enabled', False):
            return
        
        # Get recent memory and context
        recent_tasks = await self.memory.get_recent_tasks(limit=10)
        system_state = await self._get_system_state()
        
        prompt = f"""
        You are an autonomous AI agent. Based on your recent activities and current state,
        determine if you should create any new tasks or goals.
        
        Recent tasks: {[task.description for task in recent_tasks]}
        System state: {system_state}
        Current time: {datetime.now()}
        
        Should you create any new tasks? If so, what tasks would be valuable?
        Consider:
        - Learning and improvement opportunities
        - Maintenance tasks
        - Optimization opportunities
        - User value creation
        
        Respond with JSON: {{"create_tasks": true/false, "tasks": [{"description": "...", "priority": 1-10}]}}
        """
        
        response = await self.llm.generate(prompt)
        try:
            reasoning = json.loads(response)
            if reasoning.get('create_tasks'):
                for task_data in reasoning.get('tasks', []):
                    await self.add_task(
                        task_data['description'],
                        task_data.get('priority', 1)
                    )
        except Exception as e:
            self.logger.warning(f"Error in autonomous reasoning: {e}")
    
    async def _get_system_state(self) -> Dict[str, Any]:
        """Get current system state for autonomous reasoning"""
        return {
            'active_tasks': len(self.active_tasks),
            'total_tasks': len(self.tasks),
            'completed_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
            'failed_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
            'uptime_hours': (datetime.now() - getattr(self, 'start_time', datetime.now())).total_seconds() / 3600,
            'memory_usage': await self.memory.get_usage_stats()
        }
    
    async def _cancel_task(self, task_id: str):
        """Cancel an active task"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            del self.active_tasks[task_id]
        
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            await self.memory.update_task(self.tasks[task_id])
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            'agent_id': self.agent_id,
            'is_running': self.is_running,
            'active_tasks': len(self.active_tasks),
            'total_tasks': len(self.tasks),
            'system_state': asyncio.create_task(self._get_system_state()) if self.is_running else {}
        }