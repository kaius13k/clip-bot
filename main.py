#!/usr/bin/env python3
"""
Main entry point for the Autonomous AI Agent System
"""

import asyncio
import logging
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.agent import AutoAgent
from src.web.app import AgentWebInterface


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('agent.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Autonomous AI Agent System')
    parser.add_argument('--mode', choices=['agent', 'web', 'both'], default='both',
                        help='Run mode: agent only, web interface only, or both')
    parser.add_argument('--config', default='config.yaml',
                        help='Configuration file path')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Web interface host')
    parser.add_argument('--port', type=int, default=8000,
                        help='Web interface port')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger('main')
    
    logger.info("Starting Autonomous AI Agent System")
    
    if args.mode in ['web', 'both']:
        # Start web interface
        logger.info(f"Starting web interface on {args.host}:{args.port}")
        interface = AgentWebInterface(args.config)
        
        if args.mode == 'web':
            # Web interface only
            interface.run(args.host, args.port)
        else:
            # Both agent and web interface
            try:
                interface.run(args.host, args.port)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
    
    elif args.mode == 'agent':
        # Agent only (CLI mode)
        async def run_agent():
            import yaml
            
            try:
                with open(args.config, 'r') as f:
                    config = yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return
            
            agent = AutoAgent(config)
            
            try:
                # Add some initial tasks for demonstration
                await agent.add_task("Analyze system performance and create a report", priority=5)
                await agent.add_task("Search for the latest AI developments", priority=3)
                await agent.add_task("Create a simple data visualization", priority=2)
                
                # Start the agent
                await agent.start()
                
            except KeyboardInterrupt:
                logger.info("Stopping agent...")
                await agent.stop()
        
        # Run agent in CLI mode
        asyncio.run(run_agent())


if __name__ == "__main__":
    main()