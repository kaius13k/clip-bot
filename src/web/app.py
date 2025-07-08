"""
Web Interface for AI Agent
FastAPI-based dashboard for monitoring and controlling the agent
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import yaml

from src.agent import AutoAgent, Task, TaskStatus


# Pydantic models
class TaskRequest(BaseModel):
    description: str
    priority: int = 1

class TaskResponse(BaseModel):
    id: str
    description: str
    status: str
    priority: int
    created_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

class AgentStatus(BaseModel):
    agent_id: str
    is_running: bool
    active_tasks: int
    total_tasks: int
    uptime_seconds: float


class AgentWebInterface:
    """
    Web interface for the AI Agent
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.agent: Optional[AutoAgent] = None
        self.agent_task: Optional[asyncio.Task] = None
        
        # FastAPI app
        self.app = FastAPI(
            title="AI Agent Dashboard",
            description="Monitor and control your autonomous AI agent",
            version="1.0.0"
        )
        
        # Setup templates and static files
        self.templates = Jinja2Templates(directory="src/web/templates")
        
        # WebSocket connections for real-time updates
        self.active_connections: List[WebSocket] = []
        
        # Setup routes
        self._setup_routes()
        
        # Setup logging
        self.logger = logging.getLogger('AgentWebInterface')
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            # Fallback configuration
            return {
                'agent': {'name': 'AutoAgent', 'model': 'gpt-4'},
                'web_interface': {'host': '0.0.0.0', 'port': 8000},
                'database': {'url': 'sqlite:///agent_memory.db'},
                'autonomous_mode': {'enabled': True}
            }
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard page"""
            return self.templates.TemplateResponse(
                "dashboard.html", 
                {"request": request, "agent_name": self.config.get('agent', {}).get('name', 'AutoAgent')}
            )
        
        @self.app.get("/api/status", response_model=AgentStatus)
        async def get_status():
            """Get agent status"""
            if not self.agent:
                raise HTTPException(status_code=404, detail="Agent not initialized")
            
            status = self.agent.get_status()
            return AgentStatus(
                agent_id=status['agent_id'],
                is_running=status['is_running'],
                active_tasks=status['active_tasks'],
                total_tasks=status['total_tasks'],
                uptime_seconds=getattr(self.agent, 'uptime_seconds', 0)
            )
        
        @self.app.post("/api/start")
        async def start_agent():
            """Start the autonomous agent"""
            if self.agent and self.agent.is_running:
                raise HTTPException(status_code=400, detail="Agent already running")
            
            try:
                self.agent = AutoAgent(self.config)
                self.agent_task = asyncio.create_task(self.agent.start())
                
                await self._broadcast_status_update()
                return {"message": "Agent started successfully", "agent_id": self.agent.agent_id}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")
        
        @self.app.post("/api/stop")
        async def stop_agent():
            """Stop the autonomous agent"""
            if not self.agent or not self.agent.is_running:
                raise HTTPException(status_code=400, detail="Agent not running")
            
            try:
                await self.agent.stop()
                if self.agent_task:
                    self.agent_task.cancel()
                
                await self._broadcast_status_update()
                return {"message": "Agent stopped successfully"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to stop agent: {str(e)}")
        
        @self.app.post("/api/tasks", response_model=TaskResponse)
        async def create_task(task_request: TaskRequest):
            """Create a new task for the agent"""
            if not self.agent:
                raise HTTPException(status_code=404, detail="Agent not initialized")
            
            try:
                task_id = await self.agent.add_task(
                    description=task_request.description,
                    priority=task_request.priority
                )
                
                task = self.agent.tasks.get(task_id)
                if not task:
                    raise HTTPException(status_code=500, detail="Failed to create task")
                
                await self._broadcast_task_update(task)
                
                return TaskResponse(
                    id=task.id,
                    description=task.description,
                    status=task.status.value,
                    priority=task.priority,
                    created_at=task.created_at.isoformat() if task.created_at else None
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")
        
        @self.app.get("/api/tasks", response_model=List[TaskResponse])
        async def get_tasks():
            """Get all tasks"""
            if not self.agent:
                raise HTTPException(status_code=404, detail="Agent not initialized")
            
            tasks = []
            for task in self.agent.tasks.values():
                tasks.append(TaskResponse(
                    id=task.id,
                    description=task.description,
                    status=task.status.value,
                    priority=task.priority,
                    created_at=task.created_at.isoformat() if task.created_at else None,
                    result=task.result,
                    error=task.error
                ))
            
            return tasks
        
        @self.app.get("/api/tasks/{task_id}", response_model=TaskResponse)
        async def get_task(task_id: str):
            """Get a specific task"""
            if not self.agent:
                raise HTTPException(status_code=404, detail="Agent not initialized")
            
            task = self.agent.tasks.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return TaskResponse(
                id=task.id,
                description=task.description,
                status=task.status.value,
                priority=task.priority,
                created_at=task.created_at.isoformat() if task.created_at else None,
                result=task.result,
                error=task.error
            )
        
        @self.app.delete("/api/tasks/{task_id}")
        async def cancel_task(task_id: str):
            """Cancel a task"""
            if not self.agent:
                raise HTTPException(status_code=404, detail="Agent not initialized")
            
            try:
                await self.agent._cancel_task(task_id)
                return {"message": f"Task {task_id} cancelled"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                while True:
                    # Send periodic status updates
                    if self.agent:
                        status = self.agent.get_status()
                        await websocket.send_json({
                            "type": "status",
                            "data": status
                        })
                    
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
            finally:
                self.active_connections.remove(websocket)
        
        @self.app.get("/api/memory/stats")
        async def get_memory_stats():
            """Get memory usage statistics"""
            if not self.agent:
                raise HTTPException(status_code=404, detail="Agent not initialized")
            
            try:
                stats = await self.agent.memory.get_usage_stats()
                return stats
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get memory stats: {str(e)}")
        
        @self.app.get("/api/config")
        async def get_config():
            """Get current configuration"""
            # Return config without sensitive information
            safe_config = {
                'agent': self.config.get('agent', {}),
                'autonomous_mode': self.config.get('autonomous_mode', {}),
                'tools': self.config.get('tools', {})
            }
            return safe_config
        
        @self.app.post("/api/config")
        async def update_config(new_config: Dict[str, Any]):
            """Update configuration"""
            try:
                # Merge with existing config
                self.config.update(new_config)
                
                # Save to file
                with open('config.yaml', 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False)
                
                return {"message": "Configuration updated successfully"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")
    
    async def _broadcast_status_update(self):
        """Broadcast status update to all connected WebSocket clients"""
        if not self.active_connections or not self.agent:
            return
        
        status = self.agent.get_status()
        message = {
            "type": "status_update",
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected clients
        for connection in self.active_connections[:]:  # Copy list to avoid modification during iteration
            try:
                await connection.send_json(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)
    
    async def _broadcast_task_update(self, task: Task):
        """Broadcast task update to all connected WebSocket clients"""
        if not self.active_connections:
            return
        
        message = {
            "type": "task_update",
            "data": {
                "id": task.id,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority,
                "created_at": task.created_at.isoformat() if task.created_at else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected clients
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except:
                self.active_connections.remove(connection)
    
    def run(self, host: str = None, port: int = None):
        """Run the web interface"""
        host = host or self.config.get('web_interface', {}).get('host', '0.0.0.0')
        port = port or self.config.get('web_interface', {}).get('port', 8000)
        
        uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    interface = AgentWebInterface()
    interface.run()