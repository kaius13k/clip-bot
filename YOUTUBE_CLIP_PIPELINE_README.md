# 🎬 AI-Powered YouTube Clip Pipeline

A complete, autonomous YouTube monitoring and clip generation system using AI-powered content curation. This pipeline monitors YouTube channels 24/7, automatically downloads new videos, uses OpenAI Whisper for transcription, creates AI-curated clips, and uploads them to your preferred platform.

## ✨ Features

- 🔍 **24/7 YouTube Monitoring** - Continuously monitors specified channels for new content
- 🤖 **AI Transcription** - Uses OpenAI Whisper for accurate speech-to-text conversion  
- 📊 **Engagement Prediction** - AI-powered scoring to identify the most engaging segments
- ✂️ **Automatic Clip Creation** - Creates short clips from the most interesting parts
- 📤 **Multi-Platform Upload** - Supports YouTube, Google Drive, custom APIs, or local storage
- 🏗️ **MCP Architecture** - Modular, fault-tolerant design with automatic restart capabilities
- 📈 **Real-time Monitoring** - Live status updates and comprehensive logging
- ⚙️ **Configurable Everything** - Extensive customization options via YAML configuration

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd youtube-clip-pipeline

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (required for video processing)
# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/download.html
```

### 2. Configuration

Copy and edit the configuration file:

```bash
cp youtube_config.yaml my_config.yaml
```

Edit `my_config.yaml` to configure your channels and settings:

```yaml
youtube_automation:
  check_interval_minutes: 5
  channels:
    - "UCddg_live"  # Replace with your target channel ID
  keywords:
    - "breaking"
    - "news" 
    - "live"

clipping_service:
  default_clip_duration: 60  # seconds
  max_clip_duration: 300
  output_quality: "1080p"

clip_page:
  delivery_method: "local"  # or "youtube", "drive", "api"
  local:
    directory: "./finished_clips"
```

### 3. Run the Pipeline

```bash
# Start the pipeline
python youtube_clip_pipeline.py --config my_config.yaml

# Run in daemon mode (background)
python youtube_clip_pipeline.py --config my_config.yaml --daemon

# Debug mode with verbose logging
python youtube_clip_pipeline.py --log-level DEBUG
```

## 📋 Prerequisites

### Required Dependencies
- Python 3.8+
- FFmpeg
- yt-dlp
- OpenAI Whisper
- moviepy

### Optional Dependencies (for advanced features)
- Google API libraries (for YouTube/Drive upload)
- transformers + torch (for AI engagement prediction)
- aiohttp (for custom API uploads)

### System Requirements
- **CPU**: Multi-core recommended (Whisper is CPU-intensive)
- **RAM**: 4GB+ (8GB+ recommended for larger models)
- **Storage**: 10GB+ free space for video processing
- **Network**: Stable internet connection for YouTube monitoring

## 🔧 Configuration Guide

### YouTube Monitoring

```yaml
youtube_automation:
  check_interval_minutes: 5        # How often to check for new videos
  max_videos_per_check: 10         # Limit videos processed per check
  keywords:                        # Filter videos by keywords (optional)
    - "breaking news"
    - "live update"
  channels:                        # YouTube channel IDs to monitor
    - "UCddg_live"
    - "UC_x5XG1OV2P6uZZ5FSM9Ttw"  # Google Developers
```

### Video Processing

```yaml
clipping_service:
  service_type: "ffmpeg"           # Processing method
  default_clip_duration: 60       # Default clip length in seconds
  max_clip_duration: 300          # Maximum allowed clip length
  output_quality: "1080p"         # Video quality

advanced:
  max_concurrent_clips: 3          # Parallel processing limit
  min_video_duration: 30          # Skip videos shorter than this
  max_video_duration: 3600        # Skip videos longer than this (1 hour)
  use_ai_analysis: true           # Enable AI engagement scoring
```

### Upload Configuration

```yaml
clip_page:
  delivery_method: "local"         # Options: local, youtube, drive, api
  
  # Local storage
  local:
    directory: "./finished_clips"
    organize_by_date: true
  
  # YouTube upload
  youtube:
    privacy_status: "private"      # private, unlisted, public
    category_id: "22"             # People & Blogs
  
  # Google Drive
  drive:
    folder_id: "your-folder-id"   # Optional: specific folder
  
  # Custom API
  api:
    endpoint: "https://your-api.com/upload"
    api_key: "your-api-key"
```

## 🎯 Usage Examples

### Basic Monitoring

Monitor DDG's channel for any new content:

```python
# Use default configuration
python youtube_clip_pipeline.py
```

### Keyword-Filtered Monitoring

Monitor specific types of content:

```yaml
youtube_automation:
  channels: ["UCddg_live"]
  keywords:
    - "breaking"
    - "urgent"
    - "live update"
    - "news flash"
```

### High-Quality Processing

For better results with more resources:

```yaml
whisper_model: "large"           # Better transcription accuracy
clipping_service:
  default_clip_duration: 90     # Longer clips
  output_quality: "1440p"       # Higher quality
advanced:
  max_concurrent_clips: 1       # Reduce load
  use_ai_analysis: true         # Enable AI scoring
```

### YouTube Channel Upload

Automatically upload clips to your YouTube channel:

```yaml
clip_page:
  delivery_method: "youtube"
```

**Setup Google API credentials:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials (Desktop Application)
5. Download `credentials.json` to `config/` directory
6. Run the pipeline - it will guide you through OAuth authentication

## 🏗️ Architecture Overview

The pipeline uses a modular MCP (Message Coordination Protocol) architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  YouTube        │    │  Video           │    │  Upload         │
│  Monitor        │───▶│  Processor       │───▶│  Manager        │
│                 │    │                  │    │                 │
│ • Channel scan  │    │ • Whisper AI     │    │ • YouTube API   │
│ • Video download│    │ • Clip creation  │    │ • Google Drive  │
│ • Change detect │    │ • AI curation    │    │ • Local storage │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────────┐
                    │  MCP Coordinator    │
                    │                     │
                    │ • Message routing   │
                    │ • Error handling    │
                    │ • Status monitoring │
                    └─────────────────────┘
```

### Components

1. **YouTube Monitor**: Watches channels for new videos
2. **Video Processor**: Downloads, transcribes, and creates clips  
3. **Upload Manager**: Handles clip delivery to various platforms
4. **Engagement Predictor**: AI-powered content scoring (optional)
5. **MCP Coordinator**: Manages communication between components

## 📊 Monitoring & Status

### Live Status

The pipeline provides real-time status updates:

```
📊 Pipeline Status:
   📺 Monitor: 🟢 (15 videos tracked)
   🎬 Processor: 🟢 (2 queued, 3 workers)
   📤 Uploader: 🟢 (0 queued, method: local)
```

### Logs

Comprehensive logging to files and console:

- `logs/youtube_pipeline.log` - Main pipeline log
- `logs/youtube_monitor.log` - YouTube monitoring details
- `logs/video_processor.log` - Processing and AI logs
- `logs/upload_manager.log` - Upload activity

### Status API

Get programmatic status (when running with web interface):

```bash
curl http://localhost:8000/status
```

## 🤖 AI Features

### Engagement Prediction

The pipeline includes AI-powered engagement prediction using:

- **Keyword Analysis**: Identifies high-engagement terms
- **Sentiment Analysis**: Evaluates emotional content
- **Structural Analysis**: Considers questions, urgency, etc.
- **Metadata Integration**: Uses view counts, live status, etc.

### Whisper Models

Choose transcription quality vs. speed:

- `tiny` - Fastest, least accurate
- `base` - Good balance for testing
- `small` - Better accuracy, still fast
- `medium` - **Recommended** - good accuracy/speed balance
- `large` - Best accuracy, slower

### Custom Engagement Models

You can integrate custom engagement prediction models:

```python
# In mcp_servers/engagement_predictor.py
# Replace the placeholder model with your trained model
self.engagement_model = pipeline(
    "text-classification",
    model="your-custom-engagement-model",
    return_all_scores=True
)
```

## 🔒 Security & Privacy

### Data Handling
- Videos are processed locally and can be automatically deleted
- No video content is sent to external APIs (except chosen upload targets)
- Transcripts are processed locally with Whisper

### API Keys & Credentials
- Store credentials securely in `config/credentials.json`
- Use environment variables for sensitive configuration
- OAuth tokens are encrypted and stored locally

### YouTube Terms of Service
- Ensure compliance with YouTube's Terms of Service
- Respect copyright and fair use guidelines
- Consider adding attribution to generated clips

## 🛠️ Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# Install FFmpeg
sudo apt install ffmpeg  # Ubuntu/Debian
brew install ffmpeg      # macOS
```

**Whisper model download fails:**
```bash
# Pre-download models
python -c "import whisper; whisper.load_model('medium')"
```

**Google API authentication fails:**
```bash
# Ensure credentials.json is in config/ directory
# Run interactive authentication first:
python youtube_clip_pipeline.py --log-level DEBUG
```

**Out of disk space:**
```bash
# Clean up old files
python -c "from utils.helpers import cleanup_old_files; cleanup_old_files('downloads', 1)"
```

### Performance Optimization

**For low-resource systems:**
```yaml
whisper_model: "base"              # Faster model
advanced:
  max_concurrent_clips: 1          # Reduce parallel processing
clipping_service:
  output_quality: "720p"           # Lower quality
```

**For high-performance systems:**
```yaml
whisper_model: "large"             # Best accuracy
advanced:
  max_concurrent_clips: 6          # More parallel processing
  use_ai_analysis: true           # Enable AI features
```

## 📈 Scaling & Production

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y ffmpeg
RUN pip install -r requirements.txt

CMD ["python", "youtube_clip_pipeline.py", "--daemon"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: youtube-clip-pipeline
spec:
  replicas: 1
  selector:
    matchLabels:
      app: clip-pipeline
  template:
    metadata:
      labels:
        app: clip-pipeline
    spec:
      containers:
      - name: pipeline
        image: your-registry/clip-pipeline:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "8Gi"
            cpu: "4"
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: storage
          mountPath: /app/finished_clips
      volumes:
      - name: config
        configMap:
          name: pipeline-config
      - name: storage
        persistentVolumeClaim:
          claimName: clip-storage
```

### Monitoring Integration

**Prometheus metrics:**
```python
# Add to main pipeline
from prometheus_client import start_http_server, Counter, Gauge

videos_processed = Counter('videos_processed_total', 'Total videos processed')
clips_created = Counter('clips_created_total', 'Total clips created')
pipeline_status = Gauge('pipeline_running', 'Pipeline running status')

start_http_server(9090)  # Metrics endpoint
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 mcp_servers/ utils/
black mcp_servers/ utils/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for excellent speech recognition
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for robust YouTube downloading
- [MoviePy](https://github.com/Zulko/moviepy) for video processing
- [Transformers](https://huggingface.co/transformers/) for AI model integration

## 📞 Support

- 📖 Check the documentation above
- 🐛 Report bugs via GitHub Issues
- 💬 Join discussions in GitHub Discussions
- 📧 Email support: [your-email@domain.com]

---

**Happy Clipping!** 🎬✨