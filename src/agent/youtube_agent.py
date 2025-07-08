"""
YouTube Content Automation Agent
Monitors YouTube for new content, automatically clips videos, and delivers to user's clip page
"""

import asyncio
import logging
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import aiohttp
from bs4 import BeautifulSoup
import re

@dataclass
class VideoData:
    video_id: str
    title: str
    channel: str
    url: str
    duration: str
    upload_time: str
    view_count: str
    video_type: str  # 'video' or 'short'

@dataclass
class ClipJob:
    video_id: str
    clip_start: float
    clip_end: float
    title: str
    output_url: str = None
    status: str = "pending"  # pending, processing, completed, failed

class YouTubeContentAgent:
    """
    Specialized agent for YouTube content monitoring and automated clipping
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('YouTubeContentAgent')
        
        # Configuration
        self.youtube_config = config.get('youtube_automation', {})
        self.clip_config = config.get('clipping_service', {})
        
        # Monitoring settings
        self.check_interval = self.youtube_config.get('check_interval_minutes', 5)
        self.max_videos_per_check = self.youtube_config.get('max_videos_per_check', 10)
        
        # Clipping settings
        self.clip_duration = self.clip_config.get('default_clip_duration', 60)  # seconds
        self.clip_service_api = self.clip_config.get('api_endpoint')
        self.clip_service_key = self.clip_config.get('api_key')
        
        # User's clip page settings
        self.clip_page_url = config.get('clip_page', {}).get('url')
        self.clip_page_api = config.get('clip_page', {}).get('api_endpoint')
        
        # Storage
        self.monitored_channels = set()
        self.processed_videos = set()
        self.active_clip_jobs = {}
        
        self.is_monitoring = False
        
    async def start_monitoring(self, channels: List[str] = None, keywords: List[str] = None):
        """Start monitoring YouTube for new content"""
        self.logger.info("Starting YouTube content monitoring...")
        
        if channels:
            self.monitored_channels.update(channels)
            
        self.keywords = keywords or []
        self.is_monitoring = True
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
        
        return {
            "status": "started",
            "monitoring_channels": list(self.monitored_channels),
            "keywords": self.keywords,
            "check_interval": self.check_interval
        }
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        self.logger.info("YouTube monitoring stopped")
        
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Check for new content
                new_videos = await self._check_for_new_content()
                
                if new_videos:
                    self.logger.info(f"Found {len(new_videos)} new videos")
                    
                    # Process each video
                    for video in new_videos:
                        await self._process_new_video(video)
                
                # Check status of active clip jobs
                await self._check_clip_jobs()
                
                # Wait before next check
                await asyncio.sleep(self.check_interval * 60)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _check_for_new_content(self) -> List[VideoData]:
        """Check DDG/YouTube for new content"""
        new_videos = []
        
        try:
            # Method 1: Search YouTube via DDG
            ddg_results = await self._search_ddg_youtube()
            new_videos.extend(ddg_results)
            
            # Method 2: Direct channel monitoring (if APIs available)
            if self.monitored_channels:
                channel_results = await self._check_channels_direct()
                new_videos.extend(channel_results)
                
        except Exception as e:
            self.logger.error(f"Error checking for new content: {e}")
        
        # Filter out already processed videos
        truly_new = [v for v in new_videos if v.video_id not in self.processed_videos]
        
        # Mark as processed
        for video in truly_new:
            self.processed_videos.add(video.video_id)
        
        return truly_new
    
    async def _search_ddg_youtube(self) -> List[VideoData]:
        """Search YouTube content via DuckDuckGo"""
        videos = []
        
        try:
            # Build search query
            search_terms = []
            if self.keywords:
                search_terms.extend(self.keywords)
            if self.monitored_channels:
                search_terms.extend([f"site:youtube.com {channel}" for channel in self.monitored_channels])
            
            # If no specific terms, search for trending/recent
            if not search_terms:
                search_terms = ["site:youtube.com recent videos", "site:youtube.com trending"]
            
            async with aiohttp.ClientSession() as session:
                for search_term in search_terms[:3]:  # Limit searches
                    url = f"https://duckduckgo.com/html/?q={search_term} after:{(datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d')}"
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    async with session.get(url, headers=headers) as response:
                        html = await response.text()
                        videos.extend(self._parse_ddg_results(html))
                    
                    await asyncio.sleep(2)  # Rate limiting
                        
        except Exception as e:
            self.logger.error(f"Error searching DDG: {e}")
        
        return videos[:self.max_videos_per_check]
    
    async def _check_channels_direct(self) -> List[VideoData]:
        """Check channels directly using RSS/API if available"""
        videos = []
        
        try:
            async with aiohttp.ClientSession() as session:
                for channel in self.monitored_channels:
                    # Try RSS feed first
                    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel}"
                    
                    try:
                        async with session.get(rss_url) as response:
                            xml_content = await response.text()
                            channel_videos = self._parse_rss_feed(xml_content)
                            videos.extend(channel_videos)
                    except Exception as e:
                        self.logger.warning(f"RSS check failed for {channel}: {e}")
                    
                    await asyncio.sleep(1)  # Rate limiting
        
        except Exception as e:
            self.logger.error(f"Error checking channels: {e}")
        
        return videos
    
    def _parse_ddg_results(self, html: str) -> List[VideoData]:
        """Parse DuckDuckGo search results for YouTube videos"""
        videos = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find YouTube links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if 'youtube.com/watch' in href or 'youtube.com/shorts' in href:
                    video_data = self._extract_video_info(link, href)
                    if video_data:
                        videos.append(video_data)
                        
        except Exception as e:
            self.logger.error(f"Error parsing DDG results: {e}")
        
        return videos
    
    def _parse_rss_feed(self, xml_content: str) -> List[VideoData]:
        """Parse YouTube RSS feed"""
        videos = []
        
        try:
            soup = BeautifulSoup(xml_content, 'xml')
            
            for entry in soup.find_all('entry'):
                video_id = entry.find('yt:videoId').text if entry.find('yt:videoId') else None
                title = entry.find('title').text if entry.find('title') else 'Unknown'
                channel = entry.find('name').text if entry.find('name') else 'Unknown'
                published = entry.find('published').text if entry.find('published') else datetime.now().isoformat()
                
                if video_id:
                    video = VideoData(
                        video_id=video_id,
                        title=title,
                        channel=channel,
                        url=f"https://youtube.com/watch?v={video_id}",
                        duration="Unknown",
                        upload_time=published,
                        view_count="Unknown",
                        video_type="video"
                    )
                    videos.append(video)
                    
        except Exception as e:
            self.logger.error(f"Error parsing RSS: {e}")
        
        return videos
    
    def _extract_video_info(self, link_element, href: str) -> Optional[VideoData]:
        """Extract video information from link"""
        try:
            # Extract video ID
            if '/watch?v=' in href:
                video_id = href.split('/watch?v=')[1].split('&')[0]
                video_type = "video"
            elif '/shorts/' in href:
                video_id = href.split('/shorts/')[1].split('?')[0]
                video_type = "short"
            else:
                return None
            
            # Extract title and other info from link text/parent
            title_element = link_element.find('b') or link_element
            title = title_element.get_text(strip=True) if title_element else 'Unknown'
            
            return VideoData(
                video_id=video_id,
                title=title,
                channel="Unknown",
                url=href,
                duration="Unknown",
                upload_time=datetime.now().isoformat(),
                view_count="Unknown",
                video_type=video_type
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting video info: {e}")
            return None
    
    async def _process_new_video(self, video: VideoData):
        """Process a newly found video"""
        self.logger.info(f"Processing video: {video.title} ({video.video_id})")
        
        try:
            # Analyze video for clipping potential
            clip_segments = await self._analyze_for_clipping(video)
            
            if clip_segments:
                # Create clip jobs
                for segment in clip_segments:
                    clip_job = ClipJob(
                        video_id=video.video_id,
                        clip_start=segment['start'],
                        clip_end=segment['end'],
                        title=f"{video.title} - {segment['title']}"
                    )
                    
                    # Submit to clipping service
                    await self._submit_clip_job(video, clip_job)
                    
        except Exception as e:
            self.logger.error(f"Error processing video {video.video_id}: {e}")
    
    async def _analyze_for_clipping(self, video: VideoData) -> List[Dict[str, Any]]:
        """Analyze video to determine best clips"""
        
        # For shorts, clip the entire thing
        if video.video_type == "short":
            return [{
                'start': 0,
                'end': 60,  # Max short duration
                'title': 'Full Short',
                'confidence': 1.0
            }]
        
        # For regular videos, use AI to find interesting segments
        # This would integrate with your LLM to analyze transcripts/titles
        segments = []
        
        # Simple heuristic: create clips from beginning
        segments.append({
            'start': 0,
            'end': min(self.clip_duration, 300),  # Up to 5 minutes
            'title': 'Opening Segment',
            'confidence': 0.8
        })
        
        # TODO: Add more sophisticated analysis
        # - Transcript analysis for highlight moments
        # - Audio analysis for excitement peaks
        # - Comment analysis for popular timestamps
        
        return segments
    
    async def _submit_clip_job(self, video: VideoData, clip_job: ClipJob):
        """Submit clip job to clipping service"""
        
        if not self.clip_service_api:
            self.logger.warning("No clipping service configured")
            return
        
        try:
            # Different APIs you could use:
            
            # Option 1: Clipchamp API (if available)
            # Option 2: RunwayML API
            # Option 3: Replicate.com for video processing
            # Option 4: FFmpeg-based service
            
            # Example with a generic video processing API:
            payload = {
                'video_url': video.url,
                'start_time': clip_job.clip_start,
                'end_time': clip_job.clip_end,
                'output_format': 'mp4',
                'quality': 'high',
                'title': clip_job.title
            }
            
            headers = {
                'Authorization': f'Bearer {self.clip_service_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.clip_service_api, 
                                      json=payload, 
                                      headers=headers) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        clip_job.status = "processing"
                        clip_job.output_url = result.get('job_id')  # Or direct URL
                        
                        self.active_clip_jobs[result.get('job_id')] = clip_job
                        self.logger.info(f"Clip job submitted: {clip_job.title}")
                    else:
                        self.logger.error(f"Clip submission failed: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error submitting clip job: {e}")
    
    async def _check_clip_jobs(self):
        """Check status of active clip jobs"""
        
        completed_jobs = []
        
        for job_id, clip_job in self.active_clip_jobs.items():
            try:
                status = await self._check_clip_status(job_id)
                
                if status == 'completed':
                    clip_job.status = 'completed'
                    await self._deliver_clip(clip_job)
                    completed_jobs.append(job_id)
                elif status == 'failed':
                    clip_job.status = 'failed'
                    completed_jobs.append(job_id)
                    
            except Exception as e:
                self.logger.error(f"Error checking clip job {job_id}: {e}")
        
        # Clean up completed jobs
        for job_id in completed_jobs:
            del self.active_clip_jobs[job_id]
    
    async def _check_clip_status(self, job_id: str) -> str:
        """Check status of a specific clip job"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.clip_service_api}/status/{job_id}") as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('status', 'unknown')
                        
        except Exception as e:
            self.logger.error(f"Error checking status for {job_id}: {e}")
        
        return 'unknown'
    
    async def _deliver_clip(self, clip_job: ClipJob):
        """Deliver completed clip to user's clip page"""
        
        try:
            if self.clip_page_api:
                # Send directly to clip page API
                await self._send_to_clip_page(clip_job)
            else:
                # Save locally first, then deliver
                local_path = await self._save_clip_locally(clip_job)
                if local_path:
                    await self._upload_to_clip_page(local_path, clip_job)
                    
        except Exception as e:
            self.logger.error(f"Error delivering clip: {e}")
    
    async def _send_to_clip_page(self, clip_job: ClipJob):
        """Send clip directly to user's clip page"""
        
        payload = {
            'title': clip_job.title,
            'video_url': clip_job.output_url,
            'source': 'youtube_automation',
            'timestamp': datetime.now().isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.clip_page_api, json=payload) as response:
                if response.status == 200:
                    self.logger.info(f"Clip delivered: {clip_job.title}")
                else:
                    self.logger.error(f"Failed to deliver clip: {response.status}")
    
    async def _save_clip_locally(self, clip_job: ClipJob) -> Optional[str]:
        """Save clip locally before uploading"""
        
        try:
            # Download the clip
            async with aiohttp.ClientSession() as session:
                async with session.get(clip_job.output_url) as response:
                    if response.status == 200:
                        filename = f"clips/{clip_job.video_id}_{int(time.time())}.mp4"
                        
                        # Ensure clips directory exists
                        import os
                        os.makedirs('clips', exist_ok=True)
                        
                        with open(filename, 'wb') as f:
                            f.write(await response.read())
                        
                        return filename
                        
        except Exception as e:
            self.logger.error(f"Error saving clip locally: {e}")
        
        return None
    
    async def _upload_to_clip_page(self, local_path: str, clip_job: ClipJob):
        """Upload local clip file to clip page"""
        
        try:
            # This would depend on your clip page's upload API
            # Example for a generic file upload endpoint
            
            async with aiohttp.ClientSession() as session:
                with open(local_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=f"{clip_job.title}.mp4")
                    data.add_field('title', clip_job.title)
                    
                    async with session.post(f"{self.clip_page_api}/upload", 
                                          data=data) as response:
                        if response.status == 200:
                            self.logger.info(f"Clip uploaded: {clip_job.title}")
                            
                            # Clean up local file
                            import os
                            os.remove(local_path)
                        else:
                            self.logger.error(f"Upload failed: {response.status}")
                            
        except Exception as e:
            self.logger.error(f"Error uploading clip: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the YouTube agent"""
        
        return {
            'is_monitoring': self.is_monitoring,
            'monitored_channels': list(self.monitored_channels),
            'processed_videos_count': len(self.processed_videos),
            'active_clip_jobs': len(self.active_clip_jobs),
            'check_interval_minutes': self.check_interval,
            'last_check': datetime.now().isoformat()
        }