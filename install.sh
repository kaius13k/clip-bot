#!/bin/bash

# YouTube Clip Pipeline Installation Script
# This script automates the setup process for the AI-powered YouTube clip pipeline

set -e  # Exit on any error

echo "🎬 YouTube Clip Pipeline Installation"
echo "======================================"

# Check Python version
echo "🐍 Checking Python version..."
python3 --version || {
    echo "❌ Python 3 is required but not found"
    echo "Please install Python 3.8+ and try again"
    exit 1
}

# Check if pip is available
echo "📦 Checking pip..."
python3 -m pip --version || {
    echo "❌ pip is required but not found"
    echo "Please install pip and try again"
    exit 1
}

# Install FFmpeg if not present
echo "🎥 Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found. Attempting to install..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        elif command -v yum &> /dev/null; then
            sudo yum install -y ffmpeg
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y ffmpeg
        else
            echo "❌ Could not auto-install FFmpeg. Please install manually:"
            echo "https://ffmpeg.org/download.html"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "❌ Homebrew not found. Please install FFmpeg manually:"
            echo "brew install ffmpeg"
            exit 1
        fi
    else
        echo "❌ Unsupported OS. Please install FFmpeg manually:"
        echo "https://ffmpeg.org/download.html"
        exit 1
    fi
else
    echo "✅ FFmpeg found"
fi

# Install Python dependencies
echo "📚 Installing Python dependencies..."
python3 -m pip install --upgrade pip

# Install core dependencies
python3 -m pip install yt-dlp>=2023.11.16
python3 -m pip install openai-whisper>=20231117
python3 -m pip install moviepy>=1.0.3
python3 -m pip install pyyaml
python3 -m pip install asyncio
python3 -m pip install aiofiles

# Install optional dependencies
echo "🤖 Installing AI/ML dependencies..."
python3 -m pip install torch>=2.0.0 --index-url https://download.pytorch.org/whl/cpu
python3 -m pip install transformers>=4.35.0

# Install Google API dependencies (optional)
echo "📤 Installing Google API dependencies..."
python3 -m pip install google-api-python-client>=2.108.0 || echo "⚠️  Google API install failed (optional)"
python3 -m pip install google-auth-oauthlib>=1.2.0 || echo "⚠️  Google Auth install failed (optional)"
python3 -m pip install google-auth-httplib2>=0.2.0 || echo "⚠️  Google HTTP Auth install failed (optional)"

# Install utility dependencies
echo "🛠️  Installing utility dependencies..."
python3 -m pip install psutil>=5.9.6
python3 -m pip install python-dotenv>=1.0.0
python3 -m pip install aiohttp

# Create required directories
echo "📁 Creating directories..."
mkdir -p downloads
mkdir -p clips
mkdir -p config
mkdir -p logs
mkdir -p finished_clips

# Set permissions
chmod +x youtube_clip_pipeline.py

# Check installations
echo "🔍 Verifying installations..."

# Test imports
python3 -c "
import yt_dlp
import whisper
import moviepy
print('✅ Core dependencies verified')
" || {
    echo "❌ Core dependency verification failed"
    exit 1
}

# Test optional imports
python3 -c "
try:
    import torch
    import transformers
    print('✅ AI/ML dependencies verified')
except ImportError as e:
    print(f'⚠️  Some AI/ML dependencies missing: {e}')
" || echo "⚠️  AI/ML dependencies partially missing"

python3 -c "
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    print('✅ Google API dependencies verified')
except ImportError as e:
    print(f'⚠️  Google API dependencies missing: {e}')
" || echo "⚠️  Google API dependencies missing (optional)"

# Download Whisper model
echo "🎤 Pre-downloading Whisper model..."
python3 -c "
import whisper
try:
    whisper.load_model('medium')
    print('✅ Whisper medium model downloaded')
except Exception as e:
    print(f'⚠️  Whisper model download failed: {e}')
    print('Model will be downloaded on first use')
"

# Create sample configuration if it doesn't exist
if [ ! -f "youtube_config.yaml" ]; then
    echo "⚙️  Creating sample configuration..."
    cat > youtube_config.yaml << 'EOF'
# YouTube Content Automation Configuration

youtube_automation:
  # How often to check for new content (in minutes)
  check_interval_minutes: 5
  
  # Maximum videos to process per check
  max_videos_per_check: 10
  
  # Keywords to monitor for (leave empty to monitor all)
  keywords:
    - "breaking"
    - "news"
    - "live"
    - "update"
  
  # Specific channels to monitor (YouTube channel IDs)
  channels:
    - "UCddg_live"  # Replace with actual channel ID

# Video Clipping Service Configuration
clipping_service:
  service_type: "ffmpeg"
  default_clip_duration: 60
  max_clip_duration: 300
  output_quality: "1080p"

# Clip Delivery Configuration
clip_page:
  delivery_method: "local"
  local:
    directory: "./finished_clips"
    organize_by_date: true

# Advanced Settings
advanced:
  use_ai_analysis: true
  max_concurrent_clips: 3
  max_daily_clips: 50
  min_video_duration: 30
  max_video_duration: 3600
  max_storage_gb: 10

# Whisper model configuration
whisper_model: "medium"

# AI settings
ai_settings:
  use_engagement_scoring: true
  analyze_transcripts: true
  keyword_boost: true
  confidence_threshold: 0.8

# Upload settings
upload_settings:
  cleanup_after_upload: false
  retry_attempts: 3
  retry_delay: 5

# Notification settings  
notifications:
  log_level: "INFO"
  enable_webhooks: false
  enable_email: false
  enable_discord: false
EOF
    echo "✅ Sample configuration created: youtube_config.yaml"
else
    echo "✅ Configuration file already exists"
fi

# Create .env template if it doesn't exist
if [ ! -f ".env.template" ]; then
    cat > .env.template << 'EOF'
# Environment Variables Template
# Copy this to .env and fill in your values

# YouTube API Configuration
YOUTUBE_API_KEY=your_youtube_api_key_here

# Google Cloud Configuration  
GOOGLE_APPLICATION_CREDENTIALS=config/credentials.json

# Custom API Configuration
CUSTOM_API_ENDPOINT=https://your-api.com/upload
CUSTOM_API_KEY=your_api_key_here

# Notification Configuration
DISCORD_WEBHOOK_URL=your_discord_webhook_url
SLACK_WEBHOOK_URL=your_slack_webhook_url
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Performance Configuration
MAX_WORKERS=3
CHUNK_SIZE=1048576
MEMORY_LIMIT_GB=8
EOF
    echo "✅ Environment template created: .env.template"
fi

# Display completion message
echo ""
echo "🎉 Installation Complete!"
echo "======================="
echo ""
echo "Next steps:"
echo "1. 📝 Edit youtube_config.yaml to configure your channels"
echo "2. 🔑 (Optional) Setup Google API credentials:"
echo "   - Go to https://console.cloud.google.com/"
echo "   - Enable YouTube Data API v3 and Google Drive API"
echo "   - Create OAuth 2.0 credentials"
echo "   - Download credentials.json to config/ directory"
echo "3. 🚀 Run the pipeline:"
echo "   python3 youtube_clip_pipeline.py"
echo ""
echo "For detailed configuration options, see:"
echo "📖 YOUTUBE_CLIP_PIPELINE_README.md"
echo ""
echo "Test the installation:"
echo "python3 youtube_clip_pipeline.py --help"
echo ""

# Run a quick test
echo "🧪 Running quick test..."
python3 -c "
import sys
sys.path.insert(0, '.')
from utils.helpers import check_dependencies, get_system_info

print('System Info:')
info = get_system_info()
for key, value in info.items():
    if key != 'timestamp':
        print(f'  {key}: {value}')

print('\nDependency Check:')
deps = check_dependencies()
for name, available in deps.items():
    status = '✅' if available else '❌'
    print(f'  {status} {name}')
"

echo ""
echo "✨ Ready to start clipping! ✨"