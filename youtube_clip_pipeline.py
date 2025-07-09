#!/usr/bin/env python3
"""
AI-Powered YouTube Clip Pipeline
Main entry point for the complete YouTube monitoring, processing, and upload system
"""

import asyncio
import logging
import argparse
import signal
import sys
from typing import Dict, Any
from datetime import datetime

# Add utils to path for imports
sys.path.insert(0, '.')

from mcp_servers.mcp_framework import MCPCoordinator
from mcp_servers.youtube_monitor import YouTubeMonitor
from mcp_servers.video_processor import VideoProcessor
from mcp_servers.upload_manager import UploadManager
from utils.helpers import (
    setup_logging, ensure_directories, validate_credentials,
    load_config, check_dependencies, get_system_info, check_disk_space
)

class YouTubeClipPipeline:
    """Main pipeline coordinator"""
    
    def __init__(self, config_path: str = "youtube_config.yaml"):
        self.config_path = config_path
        self.config = None
        self.coordinator = None
        self.running = False
        
    async def initialize(self):
        """Initialize the pipeline"""
        logger = logging.getLogger(__name__)
        logger.info("🚀 Initializing YouTube Clip Pipeline")
        
        # Setup directories
        ensure_directories()
        
        # Load configuration
        self.config = load_config(self.config_path)
        
        # Check system requirements
        await self._check_system_requirements()
        
        # Setup MCP coordinator
        self.coordinator = MCPCoordinator()
        
        # Create and register MCP servers
        youtube_monitor = YouTubeMonitor(self.config)
        video_processor = VideoProcessor(self.config)
        upload_manager = UploadManager(self.config)
        
        self.coordinator.register_server(youtube_monitor)
        self.coordinator.register_server(video_processor)
        self.coordinator.register_server(upload_manager)
        
        logger.info("✅ Pipeline initialization complete")
    
    async def _check_system_requirements(self):
        """Check system requirements and dependencies"""
        logger = logging.getLogger(__name__)
        logger.info("🔍 Checking system requirements...")
        
        # Check dependencies
        deps = check_dependencies()
        critical_deps = ['yt_dlp', 'whisper', 'moviepy', 'ffmpeg']
        missing_critical = [dep for dep in critical_deps if not deps.get(dep, False)]
        
        if missing_critical:
            logger.error(f"❌ Missing critical dependencies: {', '.join(missing_critical)}")
            logger.error("Please install missing dependencies:")
            logger.error("pip install yt-dlp openai-whisper moviepy")
            if 'ffmpeg' in missing_critical:
                logger.error("Please install FFmpeg: https://ffmpeg.org/download.html")
            raise RuntimeError("Missing critical dependencies")
        
        # Check disk space
        min_space = self.config.get('advanced', {}).get('max_storage_gb', 10)
        if not check_disk_space(min_space):
            logger.warning(f"⚠️  Low disk space (minimum {min_space} GB recommended)")
        
        # Validate credentials if using Google APIs
        delivery_method = self.config.get('clip_page', {}).get('delivery_method', 'local')
        if delivery_method in ['youtube', 'drive', 'api']:
            if not validate_credentials():
                logger.warning("⚠️  Google API credentials not configured - falling back to local delivery")
                # Update config to use local delivery
                if 'clip_page' not in self.config:
                    self.config['clip_page'] = {}
                self.config['clip_page']['delivery_method'] = 'local'
        
        # Log system info
        system_info = get_system_info()
        logger.info(f"💻 System: {system_info.get('platform', 'Unknown')}")
        logger.info(f"🐍 Python: {system_info.get('python_version', 'Unknown')}")
        logger.info(f"💾 Memory: {system_info.get('available_memory_gb', 0):.1f} GB available")
        logger.info(f"💽 Disk: {system_info.get('disk_free_gb', 0):.1f} GB free")
        
        logger.info("✅ System requirements check complete")
    
    async def start(self):
        """Start the pipeline"""
        logger = logging.getLogger(__name__)
        logger.info("🎬 Starting YouTube Clip Pipeline")
        
        try:
            # Start MCP coordinator and all servers
            await self.coordinator.start()
            
            # Start YouTube monitoring
            await self.coordinator.route_message(
                type('', (), {
                    'sender': 'Pipeline',
                    'target': 'YouTubeMonitor', 
                    'method': 'start_monitoring',
                    'data': {}
                })()
            )
            
            self.running = True
            logger.info("🎯 Pipeline started successfully!")
            logger.info("📺 Monitoring YouTube channels...")
            
            # Log configuration summary
            await self._log_configuration_summary()
            
        except Exception as e:
            logger.error(f"❌ Failed to start pipeline: {e}")
            raise
    
    async def stop(self):
        """Stop the pipeline"""
        logger = logging.getLogger(__name__)
        logger.info("🛑 Stopping YouTube Clip Pipeline")
        
        self.running = False
        
        if self.coordinator:
            try:
                # Stop YouTube monitoring
                await self.coordinator.route_message(
                    type('', (), {
                        'sender': 'Pipeline',
                        'target': 'YouTubeMonitor',
                        'method': 'stop_monitoring', 
                        'data': {}
                    })()
                )
            except Exception as e:
                logger.warning(f"Error stopping YouTube monitor: {e}")
            
            # Stop coordinator
            await self.coordinator.stop()
        
        logger.info("✅ Pipeline stopped")
    
    async def _log_configuration_summary(self):
        """Log current configuration summary"""
        logger = logging.getLogger(__name__)
        
        youtube_config = self.config.get('youtube_automation', {})
        clip_config = self.config.get('clipping_service', {})
        upload_config = self.config.get('clip_page', {})
        
        logger.info("📋 Configuration Summary:")
        logger.info(f"   📺 Channels: {youtube_config.get('channels', ['UCddg_live'])}")
        logger.info(f"   ⏱️  Check Interval: {youtube_config.get('check_interval_minutes', 5)} minutes")
        logger.info(f"   🎞️  Clip Duration: {clip_config.get('default_clip_duration', 60)} seconds")
        logger.info(f"   📤 Delivery Method: {upload_config.get('delivery_method', 'local')}")
        logger.info(f"   🤖 Whisper Model: {self.config.get('whisper_model', 'medium')}")
        
        keywords = youtube_config.get('keywords', [])
        if keywords:
            logger.info(f"   🔍 Keywords: {', '.join(keywords[:3])}{'...' if len(keywords) > 3 else ''}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get pipeline status"""
        if not self.coordinator:
            return {"status": "not_initialized"}
        
        try:
            # Get status from all servers
            monitor_status = await self.coordinator.route_message(
                type('', (), {
                    'sender': 'Pipeline',
                    'target': 'YouTubeMonitor',
                    'method': 'get_status',
                    'data': {}
                })()
            )
            
            processor_status = await self.coordinator.route_message(
                type('', (), {
                    'sender': 'Pipeline', 
                    'target': 'VideoProcessor',
                    'method': 'get_status',
                    'data': {}
                })()
            )
            
            upload_status = await self.coordinator.route_message(
                type('', (), {
                    'sender': 'Pipeline',
                    'target': 'UploadManager', 
                    'method': 'get_status',
                    'data': {}
                })()
            )
            
            return {
                "pipeline_running": self.running,
                "timestamp": datetime.now().isoformat(),
                "monitor": monitor_status,
                "processor": processor_status,
                "uploader": upload_status
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI-Powered YouTube Clip Pipeline')
    parser.add_argument('--config', default='youtube_config.yaml',
                       help='Configuration file path')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--status-interval', type=int, default=300,
                       help='Status logging interval in seconds')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (no interactive status)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, "youtube_pipeline.log")
    logger = logging.getLogger(__name__)
    
    # Create and initialize pipeline
    pipeline = YouTubeClipPipeline(args.config)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(pipeline.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and start pipeline
        await pipeline.initialize()
        await pipeline.start()
        
        # Status logging task
        async def status_logger():
            while pipeline.running:
                try:
                    status = await pipeline.get_status()
                    monitor = status.get('monitor', {})
                    processor = status.get('processor', {})
                    uploader = status.get('uploader', {})
                    
                    logger.info("📊 Pipeline Status:")
                    logger.info(f"   📺 Monitor: {'🟢' if monitor.get('monitoring') else '🔴'} "
                              f"({monitor.get('videos_tracked', 0)} videos tracked)")
                    logger.info(f"   🎬 Processor: {'🟢' if processor.get('running') else '🔴'} "
                              f"({processor.get('queue_size', 0)} queued, "
                              f"{processor.get('active_workers', 0)} workers)")
                    logger.info(f"   📤 Uploader: {'🟢' if uploader.get('running') else '🔴'} "
                              f"({uploader.get('queue_size', 0)} queued, "
                              f"method: {uploader.get('delivery_method', 'unknown')})")
                    
                    await asyncio.sleep(args.status_interval)
                except Exception as e:
                    logger.error(f"Error in status logger: {e}")
                    await asyncio.sleep(60)
        
        # Start status logger
        status_task = asyncio.create_task(status_logger())
        
        if not args.daemon:
            # Interactive mode
            logger.info("💬 Interactive mode - press Ctrl+C to stop")
            logger.info("💡 Use --daemon flag to run in background")
        
        # Keep pipeline running
        try:
            await status_task
        except asyncio.CancelledError:
            pass
        
    except KeyboardInterrupt:
        logger.info("👋 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}")
        raise
    finally:
        await pipeline.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)