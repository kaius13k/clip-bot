"""
Upload Manager MCP Server
Handles uploading clips to YouTube and Google Drive
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .mcp_framework import AutoMCPServer, expose

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    import pickle
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False
    logger.warning("Google API libraries not available. Upload functionality will be limited.")

logger = logging.getLogger(__name__)

class UploadManager(AutoMCPServer):
    """Manages uploading clips to various platforms"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("UploadManager")
        self.config = config
        self.clip_page_config = config.get('clip_page', {})
        
        # Services
        self.youtube_service = None
        self.drive_service = None
        
        # Upload settings
        self.delivery_method = self.clip_page_config.get('delivery_method', 'local')
        self.local_dir = self.clip_page_config.get('local', {}).get('directory', './finished_clips')
        
        # Ensure local directory exists
        os.makedirs(self.local_dir, exist_ok=True)
        
        # OAuth scopes
        self.youtube_scopes = ['https://www.googleapis.com/auth/youtube.upload']
        self.drive_scopes = ['https://www.googleapis.com/auth/drive.file']
        
        # Credentials file path
        self.credentials_file = "config/credentials.json"
        self.token_file = "config/token.pickle"
        
        # Upload queue
        self.upload_queue = asyncio.Queue()
        self.upload_task = None
    
    async def start(self):
        """Start the upload manager"""
        await super().start()
        
        if GOOGLE_APIS_AVAILABLE and self.delivery_method in ['api', 'youtube', 'drive']:
            try:
                await self._setup_google_services()
            except Exception as e:
                logger.error(f"Failed to setup Google services: {e}")
                logger.info("Falling back to local delivery method")
                self.delivery_method = 'local'
        
        # Start upload worker
        self.upload_task = asyncio.create_task(self._upload_worker())
        logger.info("Upload manager started")
    
    async def stop(self):
        """Stop the upload manager"""
        await super().stop()
        
        if self.upload_task:
            self.upload_task.cancel()
            try:
                await self.upload_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Upload manager stopped")
    
    async def _setup_google_services(self):
        """Setup Google API services"""
        if not GOOGLE_APIS_AVAILABLE:
            raise ImportError("Google API libraries not available")
        
        loop = asyncio.get_event_loop()
        
        # Setup YouTube service
        if self.delivery_method in ['api', 'youtube']:
            logger.info("Setting up YouTube API service...")
            self.youtube_service = await loop.run_in_executor(
                None, self._get_youtube_service
            )
            logger.info("YouTube API service ready")
        
        # Setup Drive service
        if self.delivery_method in ['drive']:
            logger.info("Setting up Google Drive API service...")
            self.drive_service = await loop.run_in_executor(
                None, self._get_drive_service
            )
            logger.info("Google Drive API service ready")
    
    def _get_credentials(self, scopes: List[str]):
        """Get Google API credentials"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Google API credentials not found at {self.credentials_file}. "
                        "Please download credentials.json from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, scopes
                )
                # For background agent, we can't run interactive flow
                # User needs to run this interactively first
                raise RuntimeError(
                    "OAuth flow required. Please run this interactively first to authenticate."
                )
            
            # Save credentials
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def _get_youtube_service(self):
        """Get YouTube API service"""
        creds = self._get_credentials(self.youtube_scopes)
        return build('youtube', 'v3', credentials=creds)
    
    def _get_drive_service(self):
        """Get Google Drive API service"""
        creds = self._get_credentials(self.drive_scopes)
        return build('drive', 'v3', credentials=creds)
    
    @expose
    async def upload_clips(self, clip_paths: List[str], metadata: Dict[str, Any]):
        """Upload clips using the configured method"""
        logger.info(f"Queuing {len(clip_paths)} clips for upload")
        
        # Add to upload queue
        await self.upload_queue.put({
            'clip_paths': clip_paths,
            'metadata': metadata,
            'timestamp': datetime.now()
        })
        
        return {"status": "queued", "clip_count": len(clip_paths)}
    
    async def _upload_worker(self):
        """Worker to handle uploads from the queue"""
        logger.info("Started upload worker")
        
        while self.running:
            try:
                # Wait for work
                work_item = await asyncio.wait_for(
                    self.upload_queue.get(), timeout=1.0
                )
                
                clip_paths = work_item['clip_paths']
                metadata = work_item['metadata']
                
                logger.info(f"Uploading {len(clip_paths)} clips")
                
                try:
                    await self._upload_clips_internal(clip_paths, metadata)
                    logger.info("Upload completed successfully")
                except Exception as e:
                    logger.error(f"Upload failed: {e}")
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in upload worker: {e}")
                await asyncio.sleep(1)
        
        logger.info("Upload worker stopped")
    
    async def _upload_clips_internal(self, clip_paths: List[str], metadata: Dict[str, Any]):
        """Internal upload logic"""
        uploaded_clips = []
        
        for clip_path in clip_paths:
            if not os.path.exists(clip_path):
                logger.error(f"Clip file not found: {clip_path}")
                continue
            
            try:
                result = await self._upload_single_clip(clip_path, metadata)
                if result:
                    uploaded_clips.append(result)
                    
                    # Clean up local clip file after successful upload
                    if self.delivery_method != 'local':
                        try:
                            os.remove(clip_path)
                            logger.debug(f"Cleaned up local file: {clip_path}")
                        except Exception as e:
                            logger.warning(f"Failed to clean up {clip_path}: {e}")
                
            except Exception as e:
                logger.error(f"Failed to upload {clip_path}: {e}")
        
        logger.info(f"Successfully uploaded {len(uploaded_clips)}/{len(clip_paths)} clips")
        return uploaded_clips
    
    async def _upload_single_clip(self, clip_path: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upload a single clip"""
        if self.delivery_method == 'local':
            return await self._save_local(clip_path, metadata)
        elif self.delivery_method == 'youtube':
            return await self._upload_to_youtube(clip_path, metadata)
        elif self.delivery_method == 'drive':
            return await self._upload_to_drive(clip_path, metadata)
        elif self.delivery_method == 'api':
            return await self._upload_via_api(clip_path, metadata)
        else:
            logger.error(f"Unknown delivery method: {self.delivery_method}")
            return None
    
    async def _save_local(self, clip_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Save clip to local directory"""
        try:
            filename = os.path.basename(clip_path)
            destination = os.path.join(self.local_dir, filename)
            
            # Copy file to destination
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._copy_file, clip_path, destination)
            
            logger.info(f"Saved clip locally: {destination}")
            return {
                "method": "local",
                "path": destination,
                "filename": filename
            }
        except Exception as e:
            logger.error(f"Failed to save locally: {e}")
            return None
    
    def _copy_file(self, src: str, dst: str):
        """Copy file synchronously"""
        import shutil
        shutil.copy2(src, dst)
    
    async def _upload_to_youtube(self, clip_path: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upload clip to YouTube"""
        if not self.youtube_service:
            logger.error("YouTube service not available")
            return None
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._upload_to_youtube_sync, clip_path, metadata
            )
            return result
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return None
    
    def _upload_to_youtube_sync(self, clip_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload to YouTube synchronously"""
        try:
            # Prepare video metadata
            video_title = f"{metadata.get('title', 'Unknown')} - Highlight"
            video_description = f"Clip from: {metadata.get('url', '')}"
            
            request_body = {
                "snippet": {
                    "title": video_title,
                    "description": video_description,
                    "categoryId": "22",  # People & Blogs
                    "tags": ["highlight", "clip", "ai-generated"]
                },
                "status": {
                    "privacyStatus": "private"  # Start as private
                }
            }
            
            # Upload video
            media = MediaFileUpload(
                clip_path,
                chunksize=-1,
                resumable=True,
                mimetype="video/mp4"
            )
            
            request = self.youtube_service.videos().insert(
                part="snippet,status",
                body=request_body,
                media_body=media
            )
            
            response = request.execute()
            video_id = response.get("id")
            
            logger.info(f"Uploaded to YouTube: {video_id}")
            return {
                "method": "youtube",
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": video_title
            }
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise
        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            raise
    
    async def _upload_to_drive(self, clip_path: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upload clip to Google Drive"""
        if not self.drive_service:
            logger.error("Drive service not available")
            return None
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._upload_to_drive_sync, clip_path, metadata
            )
            return result
        except Exception as e:
            logger.error(f"Drive upload failed: {e}")
            return None
    
    def _upload_to_drive_sync(self, clip_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload to Google Drive synchronously"""
        try:
            filename = os.path.basename(clip_path)
            
            file_metadata = {
                "name": filename,
                "description": f"AI-generated clip from {metadata.get('title', 'Unknown Video')}"
            }
            
            media = MediaFileUpload(
                clip_path,
                mimetype="video/mp4",
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id,name,webViewLink"
            ).execute()
            
            file_id = file.get('id')
            web_link = file.get('webViewLink')
            
            logger.info(f"Uploaded to Drive: {file_id}")
            return {
                "method": "drive",
                "file_id": file_id,
                "url": web_link,
                "filename": filename
            }
            
        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Drive upload error: {e}")
            raise
    
    async def _upload_via_api(self, clip_path: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upload via custom API endpoint"""
        api_endpoint = self.clip_page_config.get('api_endpoint')
        api_key = self.clip_page_config.get('api_key')
        
        if not api_endpoint:
            logger.error("API endpoint not configured")
            return None
        
        try:
            import aiohttp
            
            with open(clip_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=os.path.basename(clip_path))
                data.add_field('metadata', str(metadata))
                
                headers = {}
                if api_key:
                    headers['Authorization'] = f'Bearer {api_key}'
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_endpoint, data=data, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"Uploaded via API: {result}")
                            return {
                                "method": "api",
                                "response": result
                            }
                        else:
                            logger.error(f"API upload failed: {response.status}")
                            return None
        except Exception as e:
            logger.error(f"API upload error: {e}")
            return None
    
    @expose
    async def get_status(self):
        """Get upload manager status"""
        return {
            "running": self.running,
            "delivery_method": self.delivery_method,
            "queue_size": self.upload_queue.qsize(),
            "youtube_ready": self.youtube_service is not None,
            "drive_ready": self.drive_service is not None,
            "google_apis_available": GOOGLE_APIS_AVAILABLE
        }
    
    @expose
    async def change_delivery_method(self, method: str):
        """Change the delivery method"""
        valid_methods = ['local', 'youtube', 'drive', 'api']
        if method not in valid_methods:
            raise ValueError(f"Invalid method. Must be one of: {valid_methods}")
        
        self.delivery_method = method
        logger.info(f"Delivery method changed to: {method}")
        
        # Re-setup services if needed
        if method in ['youtube', 'drive'] and GOOGLE_APIS_AVAILABLE:
            try:
                await self._setup_google_services()
            except Exception as e:
                logger.error(f"Failed to setup services for {method}: {e}")
                self.delivery_method = 'local'
                return {"status": "fallback_to_local", "error": str(e)}
        
        return {"status": "success", "method": self.delivery_method}