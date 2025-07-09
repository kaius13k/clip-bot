"""
Simple MCP (Message Coordination Protocol) Framework
Provides basic coordination between YouTube pipeline components
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MCPMessage:
    sender: str
    target: str
    method: str
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class MCPServer:
    """Base class for MCP servers/components"""
    
    def __init__(self, name: str):
        self.name = name
        self.coordinator = None
        self.exposed_methods = {}
        self.running = False
        
    def expose(self, method: Callable):
        """Decorator to expose methods for MCP calls"""
        self.exposed_methods[method.__name__] = method
        return method
    
    async def handle_message(self, message: MCPMessage) -> Any:
        """Handle incoming MCP messages"""
        if message.method in self.exposed_methods:
            try:
                method = self.exposed_methods[message.method]
                if asyncio.iscoroutinefunction(method):
                    result = await method(**message.data)
                else:
                    result = method(**message.data)
                return result
            except Exception as e:
                logger.error(f"Error handling message {message.method}: {e}")
                raise
        else:
            raise ValueError(f"Method {message.method} not found in {self.name}")
    
    async def call(self, target: str, method: str, **kwargs) -> Any:
        """Call a method on another MCP server"""
        if self.coordinator:
            message = MCPMessage(
                sender=self.name,
                target=target,
                method=method,
                data=kwargs
            )
            return await self.coordinator.route_message(message)
        else:
            raise RuntimeError("No coordinator available")
    
    async def start(self):
        """Start the server"""
        self.running = True
        logger.info(f"Started MCP server: {self.name}")
    
    async def stop(self):
        """Stop the server"""
        self.running = False
        logger.info(f"Stopped MCP server: {self.name}")

class MCPCoordinator:
    """Coordinates messages between MCP servers"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.message_queue = asyncio.Queue()
        self.running = False
        
    def register_server(self, server: MCPServer):
        """Register a server with the coordinator"""
        self.servers[server.name] = server
        server.coordinator = self
        logger.info(f"Registered MCP server: {server.name}")
    
    async def route_message(self, message: MCPMessage) -> Any:
        """Route a message to the target server"""
        if message.target in self.servers:
            target_server = self.servers[message.target]
            return await target_server.handle_message(message)
        else:
            raise ValueError(f"Target server {message.target} not found")
    
    async def start(self):
        """Start the coordinator and all registered servers"""
        self.running = True
        logger.info("Starting MCP Coordinator")
        
        # Start all servers
        for server in self.servers.values():
            await server.start()
        
        logger.info("All MCP servers started")
    
    async def stop(self):
        """Stop the coordinator and all servers"""
        self.running = False
        logger.info("Stopping MCP Coordinator")
        
        # Stop all servers
        for server in self.servers.values():
            await server.stop()
        
        logger.info("All MCP servers stopped")

# Convenience decorator for method exposure
def expose(func):
    """Decorator to mark methods for MCP exposure"""
    func._mcp_exposed = True
    return func

# Auto-exposure metaclass
class MCPServerMeta(type):
    """Metaclass to automatically expose decorated methods"""
    
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        
        # Auto-register exposed methods
        if hasattr(new_class, '__init__'):
            original_init = new_class.__init__
            
            def enhanced_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                
                # Auto-expose decorated methods
                for attr_name in dir(self):
                    attr = getattr(self, attr_name)
                    if hasattr(attr, '_mcp_exposed'):
                        self.exposed_methods[attr_name] = attr
            
            new_class.__init__ = enhanced_init
        
        return new_class

class AutoMCPServer(MCPServer, metaclass=MCPServerMeta):
    """MCP Server with automatic method exposure"""
    pass