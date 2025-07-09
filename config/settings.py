"""
Configuration settings for YouTube Clip Pipeline
"""

# YouTube and API configurations
YOUTUBE_CONFIG = {
    "channel_id": "UCddg_live",
    "poll_interval": 300,  # 5 minutes
    "clip_length": 60,     # 60-second clips
    "upload_method": "local"  # or "youtube", "drive", "api"
}

# Whisper model configuration
WHISPER_MODEL = "medium"  # Options: tiny, base, small, medium, large

# Path configurations
PATHS = {
    "downloads": "downloads",
    "clips": "clips", 
    "credentials": "config/credentials.json",
    "logs": "logs"
}

# Processing limits
PROCESSING_LIMITS = {
    "max_concurrent_clips": 3,
    "max_daily_clips": 50,
    "min_video_duration": 30,     # seconds
    "max_video_duration": 3600,   # 1 hour
    "min_view_count": 1000,
    "max_storage_gb": 10
}

# Clip quality settings
CLIP_SETTINGS = {
    "default_duration": 60,       # seconds
    "max_duration": 300,          # 5 minutes
    "output_quality": "1080p",
    "format": "mp4",
    "codec": "libx264",
    "audio_codec": "aac"
}

# AI Analysis settings
AI_SETTINGS = {
    "use_engagement_scoring": True,
    "analyze_comments": False,    # Not implemented yet
    "analyze_transcripts": True,
    "keyword_boost": True,
    "confidence_threshold": 0.8
}

# Upload settings
UPLOAD_SETTINGS = {
    "cleanup_after_upload": True,
    "retry_attempts": 3,
    "retry_delay": 5,  # seconds
    "chunk_size": 1024 * 1024,  # 1MB chunks
}

# Notification settings
NOTIFICATIONS = {
    "log_level": "INFO",
    "enable_webhooks": False,
    "enable_email": False,
    "enable_discord": False
}

# Default configuration for easy loading
DEFAULT_CONFIG = {
    "youtube_automation": {
        "check_interval_minutes": 5,
        "max_videos_per_check": 10,
        "keywords": [
            "breaking", "news", "live", "update", "announcement"
        ],
        "channels": ["UCddg_live"]
    },
    "clipping_service": {
        "service_type": "ffmpeg",
        "default_clip_duration": CLIP_SETTINGS["default_duration"],
        "max_clip_duration": CLIP_SETTINGS["max_duration"],
        "output_quality": CLIP_SETTINGS["output_quality"]
    },
    "clip_page": {
        "delivery_method": "local",
        "local": {
            "directory": "./finished_clips",
            "organize_by_date": True
        }
    },
    "advanced": PROCESSING_LIMITS,
    "whisper_model": WHISPER_MODEL,
    "ai_settings": AI_SETTINGS,
    "upload_settings": UPLOAD_SETTINGS,
    "notifications": NOTIFICATIONS
}