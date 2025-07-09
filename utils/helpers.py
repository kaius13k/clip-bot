"""
Helper utilities for YouTube Clip Pipeline
"""

import os
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

def setup_logging(log_level: str = "INFO", log_file: str = "pipeline.log"):
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Setup log file path
    if not log_file.startswith("logs/"):
        log_file = f"logs/{log_file}"
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('moviepy').setLevel(logging.WARNING)
    logging.getLogger('whisper').setLevel(logging.WARNING)
    logging.getLogger('yt_dlp').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('google_auth_httplib2').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging setup complete - Level: {log_level}, File: {log_file}")

def ensure_directories():
    """Ensure all required directories exist"""
    required_dirs = [
        "downloads",
        "clips", 
        "config",
        "logs",
        "finished_clips"
    ]
    
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
        
    logger = logging.getLogger(__name__)
    logger.info(f"Created directories: {', '.join(required_dirs)}")

def validate_credentials() -> bool:
    """Validate Google API credentials"""
    credentials_path = "config/credentials.json"
    
    if not os.path.exists(credentials_path):
        logger = logging.getLogger(__name__)
        logger.warning(f"Google API credentials missing at {credentials_path}")
        logger.info("To setup Google API credentials:")
        logger.info("1. Go to https://console.cloud.google.com/")
        logger.info("2. Create a new project or select existing")
        logger.info("3. Enable YouTube Data API v3 and Google Drive API")
        logger.info("4. Create OAuth 2.0 credentials (Desktop Application)")
        logger.info("5. Download credentials.json to config/ directory")
        return False
    
    try:
        import json
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
            
        # Basic validation
        if 'installed' not in creds:
            raise ValueError("Invalid credentials format")
            
        required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
        for field in required_fields:
            if field not in creds['installed']:
                raise ValueError(f"Missing required field: {field}")
                
        logger = logging.getLogger(__name__)
        logger.info("Google API credentials validated successfully")
        return True
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Invalid credentials file: {e}")
        return False

def load_config(config_path: str = "youtube_config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Configuration loaded from {config_path}")
        return config
        
    except FileNotFoundError:
        logger = logging.getLogger(__name__)
        logger.warning(f"Config file {config_path} not found, using defaults")
        
        # Return default config
        from config.settings import DEFAULT_CONFIG
        return DEFAULT_CONFIG
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading config: {e}")
        raise

def save_config(config: Dict[str, Any], config_path: str = "youtube_config.yaml"):
    """Save configuration to YAML file"""
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Configuration saved to {config_path}")
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error saving config: {e}")
        raise

def check_disk_space(min_gb: float = 1.0) -> bool:
    """Check available disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_gb = free / (1024**3)
        
        logger = logging.getLogger(__name__)
        logger.debug(f"Available disk space: {free_gb:.2f} GB")
        
        if free_gb < min_gb:
            logger.warning(f"Low disk space: {free_gb:.2f} GB < {min_gb} GB")
            return False
        
        return True
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error checking disk space: {e}")
        return True  # Assume OK if we can't check

def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are available"""
    dependencies = {}
    
    # Check core dependencies
    try:
        import yt_dlp
        dependencies['yt_dlp'] = True
    except ImportError:
        dependencies['yt_dlp'] = False
    
    try:
        import whisper
        dependencies['whisper'] = True
    except ImportError:
        dependencies['whisper'] = False
    
    try:
        import moviepy
        dependencies['moviepy'] = True
    except ImportError:
        dependencies['moviepy'] = False
    
    # Check optional dependencies
    try:
        from google.oauth2.credentials import Credentials
        dependencies['google_apis'] = True
    except ImportError:
        dependencies['google_apis'] = False
    
    try:
        import torch
        dependencies['torch'] = True
    except ImportError:
        dependencies['torch'] = False
    
    try:
        import transformers
        dependencies['transformers'] = True
    except ImportError:
        dependencies['transformers'] = False
    
    # Check system dependencies
    dependencies['ffmpeg'] = check_ffmpeg()
    
    logger = logging.getLogger(__name__)
    missing = [name for name, available in dependencies.items() if not available]
    
    if missing:
        logger.warning(f"Missing dependencies: {', '.join(missing)}")
    else:
        logger.info("All dependencies available")
    
    return dependencies

def check_ffmpeg() -> bool:
    """Check if FFmpeg is available"""
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False

def get_system_info() -> Dict[str, Any]:
    """Get system information for debugging"""
    import platform
    import psutil
    
    try:
        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "available_memory_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "disk_free_gb": round(psutil.disk_usage('.').free / (1024**3), 2),
            "timestamp": datetime.now().isoformat()
        }
        
        return info
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting system info: {e}")
        return {"error": str(e)}

def cleanup_old_files(directory: str, max_age_days: int = 7, pattern: str = "*"):
    """Clean up old files in a directory"""
    try:
        from pathlib import Path
        import time
        
        path = Path(directory)
        if not path.exists():
            return
        
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        cleaned_count = 0
        cleaned_size = 0
        
        for file_path in path.glob(pattern):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_size = file_path.stat().st_size
                file_path.unlink()
                cleaned_count += 1
                cleaned_size += file_size
        
        if cleaned_count > 0:
            logger = logging.getLogger(__name__)
            logger.info(f"Cleaned up {cleaned_count} files ({cleaned_size / (1024**2):.1f} MB) from {directory}")
        
        return {"files_cleaned": cleaned_count, "size_freed_mb": cleaned_size / (1024**2)}
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error during cleanup: {e}")
        return {"error": str(e)}

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def format_file_size(bytes_size: int) -> str:
    """Format file size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

def safe_filename(filename: str) -> str:
    """Make a filename safe for filesystem"""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename.strip()

def get_video_info(file_path: str) -> Dict[str, Any]:
    """Get basic video information"""
    try:
        from moviepy.editor import VideoFileClip
        
        with VideoFileClip(file_path) as video:
            info = {
                "duration": video.duration,
                "fps": video.fps,
                "size": video.size,
                "width": video.w,
                "height": video.h,
                "file_size": os.path.getsize(file_path),
                "format": os.path.splitext(file_path)[1].lower()
            }
        
        return info
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting video info for {file_path}: {e}")
        return {"error": str(e)}