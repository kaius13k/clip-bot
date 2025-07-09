"""
Video Processor MCP Server
Handles AI transcription and clip creation
"""

import os
import asyncio
import logging
import whisper
from moviepy import VideoFileClip
from typing import Dict, Any, List, Optional
from datetime import datetime
from .mcp_framework import AutoMCPServer, expose

logger = logging.getLogger(__name__)

class VideoProcessor(AutoMCPServer):
    """Processes videos to create AI-curated clips"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("VideoProcessor")
        self.config = config
        self.clipping_config = config.get('clipping_service', {})
        
        # Load Whisper model
        self.whisper_model_name = config.get('whisper_model', 'medium')
        self.model = None
        
        # Clip settings
        self.clip_length = self.clipping_config.get('default_clip_duration', 60)
        self.max_clip_duration = self.clipping_config.get('max_clip_duration', 300)
        self.output_quality = self.clipping_config.get('output_quality', '1080p')
        
        # Processing limits
        self.advanced_config = config.get('advanced', {})
        self.max_concurrent_clips = self.advanced_config.get('max_concurrent_clips', 3)
        self.min_video_duration = self.advanced_config.get('min_video_duration', 30)
        self.max_video_duration = self.advanced_config.get('max_video_duration', 3600)
        
        # Ensure clips directory exists
        self.clips_dir = "clips"
        os.makedirs(self.clips_dir, exist_ok=True)
        
        # Processing queue
        self.processing_queue = asyncio.Queue()
        self.processing_tasks = []
        
    async def start(self):
        """Start the video processor"""
        await super().start()
        
        # Load Whisper model
        try:
            logger.info(f"Loading Whisper model: {self.whisper_model_name}")
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(None, self._load_whisper_model)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
        
        # Start processing workers
        for i in range(self.max_concurrent_clips):
            task = asyncio.create_task(self._processing_worker(f"worker-{i}"))
            self.processing_tasks.append(task)
        
        logger.info(f"Started {self.max_concurrent_clips} processing workers")
    
    async def stop(self):
        """Stop the video processor"""
        await super().stop()
        
        # Cancel processing tasks
        for task in self.processing_tasks:
            task.cancel()
        
        await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        self.processing_tasks.clear()
        
        logger.info("Video processor stopped")
    
    def _load_whisper_model(self) -> whisper.Whisper:
        """Load Whisper model synchronously"""
        return whisper.load_model(self.whisper_model_name)
    
    @expose
    async def process_video(self, video_path: str, metadata: Dict[str, Any]):
        """Process a video to create clips"""
        logger.info(f"Queuing video for processing: {video_path}")
        
        # Add to processing queue
        await self.processing_queue.put({
            'video_path': video_path,
            'metadata': metadata,
            'timestamp': datetime.now()
        })
        
        return {"status": "queued", "video_path": video_path}
    
    async def _processing_worker(self, worker_name: str):
        """Worker to process videos from the queue"""
        logger.info(f"Started processing worker: {worker_name}")
        
        while self.running:
            try:
                # Wait for work
                work_item = await asyncio.wait_for(
                    self.processing_queue.get(), timeout=1.0
                )
                
                video_path = work_item['video_path']
                metadata = work_item['metadata']
                
                logger.info(f"{worker_name}: Processing {video_path}")
                
                try:
                    await self._process_video_internal(video_path, metadata)
                    logger.info(f"{worker_name}: Completed processing {video_path}")
                except Exception as e:
                    logger.error(f"{worker_name}: Error processing {video_path}: {e}")
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{worker_name}: Unexpected error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Processing worker stopped: {worker_name}")
    
    async def _process_video_internal(self, video_path: str, metadata: Dict[str, Any]):
        """Internal video processing logic"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Get video duration
        loop = asyncio.get_event_loop()
        duration = await loop.run_in_executor(None, self._get_video_duration, video_path)
        
        # Apply duration filters
        if duration < self.min_video_duration:
            logger.info(f"Video too short ({duration}s), skipping: {video_path}")
            return
        
        if duration > self.max_video_duration:
            logger.info(f"Video too long ({duration}s), skipping: {video_path}")
            return
        
        logger.info(f"Processing video: {video_path} (duration: {duration}s)")
        
        # Transcribe audio
        logger.info("Transcribing audio...")
        result = await loop.run_in_executor(None, self._transcribe_video, video_path)
        
        if not result:
            logger.error("Transcription failed")
            return
        
        # Find interesting segments
        logger.info("Finding interesting segments...")
        segments = self.find_interesting_segments(result['segments'])
        
        if not segments:
            logger.info("No interesting segments found")
            return
        
        logger.info(f"Found {len(segments)} interesting segments")
        
        # Create clips
        clip_paths = await self._create_clips(video_path, segments, metadata)
        
        if clip_paths:
            # Send to upload manager
            await self.call(
                "UploadManager",
                "upload_clips",
                clip_paths=clip_paths,
                metadata=metadata
            )
        
        # Clean up original video file if configured
        # TODO: Add configuration option for this
        # os.remove(video_path)
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration"""
        try:
            with VideoFileClip(video_path) as video:
                return video.duration
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
            return 0.0
    
    def _transcribe_video(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Transcribe video using Whisper"""
        try:
            if not self.model:
                logger.error("Whisper model not loaded")
                return None
            
            result = self.model.transcribe(video_path)
            return result
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def find_interesting_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find interesting segments based on various criteria
        This implements a simple algorithm - can be enhanced with more sophisticated AI
        """
        if not segments:
            return []
        
        interesting_segments = []
        
        for segment in segments:
            # Filter by speech probability (remove silent segments)
            if segment.get('no_speech_prob', 1.0) > 0.5:
                continue
            
            # Filter by confidence (avg_logprob)
            if segment.get('avg_logprob', -10) < -1.0:
                continue
            
            # Filter by minimum duration
            duration = segment.get('end', 0) - segment.get('start', 0)
            if duration < 10:  # Minimum 10 seconds
                continue
            
            # Look for keywords that indicate interesting content
            text = segment.get('text', '').lower()
            interesting_keywords = [
                'breaking', 'news', 'important', 'exclusive', 'amazing', 
                'incredible', 'shocking', 'must see', 'viral', 'trending',
                'announcement', 'reveal', 'launch', 'new', 'first time',
                'question', 'answer', 'explain', 'how to', 'tutorial'
            ]
            
            keyword_score = sum(1 for keyword in interesting_keywords if keyword in text)
            
            # Add engagement score
            engagement_score = (
                -segment.get('avg_logprob', -10) * 0.1 +  # Confidence score
                keyword_score * 0.3 +  # Keyword relevance
                min(duration / 60, 2) * 0.2  # Duration bonus (capped at 2 minutes)
            )
            
            segment['engagement_score'] = engagement_score
            interesting_segments.append(segment)
        
        # Sort by engagement score and return top segments
        interesting_segments.sort(key=lambda x: x['engagement_score'], reverse=True)
        return interesting_segments[:5]  # Top 5 segments
    
    async def _create_clips(self, video_path: str, segments: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[str]:
        """Create video clips from interesting segments"""
        clip_paths = []
        video_id = metadata.get('id', 'unknown')
        
        loop = asyncio.get_event_loop()
        
        for i, segment in enumerate(segments):
            try:
                start_time = segment['start']
                end_time = min(segment['end'], start_time + self.clip_length)
                
                clip_filename = f"{video_id}_clip_{i+1}_{int(start_time)}s.mp4"
                clip_path = os.path.join(self.clips_dir, clip_filename)
                
                logger.info(f"Creating clip {i+1}: {start_time:.1f}s - {end_time:.1f}s")
                
                # Create clip in executor
                success = await loop.run_in_executor(
                    None, 
                    self._create_clip_sync, 
                    video_path, start_time, end_time, clip_path
                )
                
                if success and os.path.exists(clip_path):
                    clip_paths.append(clip_path)
                    logger.info(f"Created clip: {clip_path}")
                else:
                    logger.error(f"Failed to create clip: {clip_path}")
                
            except Exception as e:
                logger.error(f"Error creating clip {i+1}: {e}")
        
        return clip_paths
    
    def _create_clip_sync(self, video_path: str, start_time: float, end_time: float, output_path: str) -> bool:
        """Create a video clip synchronously"""
        try:
            with VideoFileClip(video_path) as video:
                clip = video.subclip(start_time, end_time)
                
                # Apply quality settings
                codec = "libx264"
                audio_codec = "aac"
                
                clip.write_videofile(
                    output_path,
                    codec=codec,
                    audio_codec=audio_codec,
                    temp_audiofile="temp-audio.m4a",
                    remove_temp=True,
                    verbose=False,
                    logger=None
                )
                
                clip.close()
                return True
                
        except Exception as e:
            logger.error(f"Error creating clip: {e}")
            return False
    
    @expose
    async def get_status(self):
        """Get processor status"""
        return {
            "running": self.running,
            "model_loaded": self.model is not None,
            "model_name": self.whisper_model_name,
            "queue_size": self.processing_queue.qsize(),
            "active_workers": len([t for t in self.processing_tasks if not t.done()]),
            "clip_length": self.clip_length,
            "max_concurrent": self.max_concurrent_clips
        }
    
    @expose
    async def update_settings(self, **kwargs):
        """Update processor settings"""
        if 'clip_length' in kwargs:
            self.clip_length = max(10, min(kwargs['clip_length'], self.max_clip_duration))
        
        if 'max_concurrent_clips' in kwargs:
            # TODO: Implement dynamic worker scaling
            pass
        
        return await self.get_status()