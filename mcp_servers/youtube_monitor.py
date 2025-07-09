"""
YouTube Monitor MCP Server
Monitors YouTube channels for new videos and triggers processing
"""

import asyncio
import yt_dlp as youtube_dl
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from .mcp_framework import AutoMCPServer, expose

logger = logging.getLogger(__name__)

class YouTubeMonitor(AutoMCPServer):
    """Monitors YouTube channels for new content"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("YouTubeMonitor")
        self.config = config
        self.youtube_config = config.get('youtube_automation', {})
        self.channel_id = self.youtube_config.get('channels', ["UCddg_live"])[0] if self.youtube_config.get('channels') else "UCddg_live"
        self.last_checked = {}
        self.poll_interval = self.youtube_config.get('check_interval_minutes', 5) * 60
        self.max_videos = self.youtube_config.get('max_videos_per_check', 10)
        self.keywords = self.youtube_config.get('keywords', [])
        
        # Ensure downloads directory exists
        self.downloads_dir = "downloads"
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        self.ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f'{self.downloads_dir}/%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'audioformat': 'mp3',
            'embed_subs': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
        }
        
        self.monitoring_task = None
    
    @expose
    async def start_monitoring(self):
        """Start monitoring YouTube channels"""
        if self.monitoring_task is None or self.monitoring_task.done():
            logger.info(f"Starting YouTube monitoring for channels: {self.channel_id}")
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        return {"status": "monitoring_started"}
    
    @expose
    async def stop_monitoring(self):
        """Stop monitoring YouTube channels"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("YouTube monitoring stopped")
        return {"status": "monitoring_stopped"}
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self.check_new_videos()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def check_new_videos(self):
        """Check for new videos on monitored channels"""
        logger.info("Checking for new videos...")
        
        try:
            # Check for live streams
            await self._check_live_streams()
            
            # Check for recent uploads
            await self._check_recent_uploads()
            
        except Exception as e:
            logger.error(f"Error checking videos: {e}")
    
    async def _check_live_streams(self):
        """Check for active live streams"""
        try:
            live_url = f"https://www.youtube.com/channel/{self.channel_id}/live"
            
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(live_url, download=False)
                    
                    if info and 'entries' in info:
                        for entry in info['entries'][:self.max_videos]:
                            if entry and entry.get('is_live'):
                                await self._process_new_video(entry, is_live=True)
                    elif info and info.get('is_live'):
                        await self._process_new_video(info, is_live=True)
                        
                except Exception as e:
                    logger.debug(f"No live stream found or error: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking live streams: {e}")
    
    async def _check_recent_uploads(self):
        """Check for recent uploads"""
        try:
            channel_url = f"https://www.youtube.com/channel/{self.channel_id}/videos"
            
            with youtube_dl.YoutubeDL({**self.ydl_opts, 'playlistend': self.max_videos}) as ydl:
                try:
                    info = ydl.extract_info(channel_url, download=False)
                    
                    if info and 'entries' in info:
                        for entry in info['entries']:
                            if entry:
                                await self._process_new_video(entry, is_live=False)
                                
                except Exception as e:
                    logger.debug(f"Error checking recent uploads: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking recent uploads: {e}")
    
    async def _process_new_video(self, video: Dict[str, Any], is_live: bool = False):
        """Process a newly found video"""
        video_id = video.get('id')
        video_title = video.get('title', 'Unknown Title')
        
        if not video_id:
            return
        
        # Check if we've already processed this video
        if video_id in self.last_checked:
            return
        
        # Apply keyword filtering if specified
        if self.keywords and not any(keyword.lower() in video_title.lower() for keyword in self.keywords):
            logger.debug(f"Video '{video_title}' doesn't match keywords, skipping")
            return
        
        logger.info(f"New video detected: {video_title} (ID: {video_id})")
        
        # Mark as processed
        self.last_checked[video_id] = datetime.now()
        
        # Clean up old entries to prevent memory bloat
        cutoff_time = datetime.now() - timedelta(days=7)
        self.last_checked = {
            vid_id: timestamp for vid_id, timestamp in self.last_checked.items()
            if timestamp > cutoff_time
        }
        
        try:
            # Download the video
            video_path = await self._download_video(video)
            
            if video_path and os.path.exists(video_path):
                # Send to video processor
                await self.call(
                    "VideoProcessor",
                    "process_video",
                    video_path=video_path,
                    metadata={
                        'id': video_id,
                        'title': video_title,
                        'url': video.get('webpage_url', ''),
                        'channel': self.channel_id,
                        'upload_date': video.get('upload_date'),
                        'duration': video.get('duration'),
                        'view_count': video.get('view_count'),
                        'is_live': is_live
                    }
                )
            else:
                logger.error(f"Failed to download video: {video_id}")
                
        except Exception as e:
            logger.error(f"Error processing video {video_id}: {e}")
    
    async def _download_video(self, video: Dict[str, Any]) -> Optional[str]:
        """Download a video and return the file path"""
        video_id = video.get('id')
        video_url = video.get('webpage_url', f"https://www.youtube.com/watch?v={video_id}")
        
        try:
            logger.info(f"Downloading video: {video_id}")
            
            # Run download in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._download_sync, video_url)
            
            if result:
                expected_path = f"{self.downloads_dir}/{video_id}.mp4"
                if os.path.exists(expected_path):
                    logger.info(f"Successfully downloaded: {expected_path}")
                    return expected_path
                else:
                    # Try to find the downloaded file
                    for ext in ['mp4', 'webm', 'mkv']:
                        potential_path = f"{self.downloads_dir}/{video_id}.{ext}"
                        if os.path.exists(potential_path):
                            logger.info(f"Successfully downloaded: {potential_path}")
                            return potential_path
            
            logger.error(f"Download failed or file not found for video: {video_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading video {video_id}: {e}")
            return None
    
    def _download_sync(self, url: str) -> bool:
        """Synchronous download function"""
        try:
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([url])
                return True
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False
    
    @expose
    async def get_status(self):
        """Get monitoring status"""
        return {
            "running": self.running,
            "monitoring": self.monitoring_task is not None and not self.monitoring_task.done(),
            "channel_id": self.channel_id,
            "poll_interval": self.poll_interval,
            "videos_tracked": len(self.last_checked),
            "keywords": self.keywords
        }