#!/bin/bash

echo "🚀 Deploying AI Agent System to Production"
echo "=========================================="

# Configuration
APP_DIR="/opt/ai-agent-system"
SERVICE_NAME="ai-agent"
DOMAIN="your-domain.com"  # Change this to your domain

# Create application directory
echo "📁 Creating application directory..."
sudo mkdir -p $APP_DIR/{downloads,clips,temp_clips,finished_clips,logs}
sudo chown -R $USER:$USER $APP_DIR

# Copy our existing system to production location
echo "📋 Copying system files..."
cp -r . $APP_DIR/
cd $APP_DIR

# Create production environment file
echo "⚙️ Creating production environment..."
cat > .env << EOL
# Production Environment Configuration
OPENAI_API_KEY="your-openai-api-key-here"
ANTHROPIC_API_KEY="your-anthropic-api-key-here"

# YouTube Automation
YOUTUBE_API_KEY="your-youtube-api-key-here"
REPLICATE_API_KEY="your-replicate-api-key-here"

# Clip Page Integration
CLIP_PAGE_API_ENDPOINT="https://your-clip-page.com/api/upload"
CLIP_PAGE_API_KEY="your-clip-page-api-key"

# Production Settings
ENVIRONMENT="production"
LOG_LEVEL="INFO"
HOST="0.0.0.0"
PORT="8000"
EOL

# Set secure permissions
chmod 600 .env

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create systemd service
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOL
[Unit]
Description=AI Agent System
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/python main.py --mode both --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# Create nginx configuration
echo "🌐 Setting up Nginx..."
sudo tee /etc/nginx/sites-available/$SERVICE_NAME > /dev/null << EOL
server {
    listen 80;
    server_name $DOMAIN;

    # Static files
    location /static/ {
        alias $APP_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API and WebSocket
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # WebSocket specific
        proxy_set_header Sec-WebSocket-Extensions \$http_sec_websocket_extensions;
        proxy_set_header Sec-WebSocket-Key \$http_sec_websocket_key;
        proxy_set_header Sec-WebSocket-Version \$http_sec_websocket_version;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
EOL

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Set up SSL with Let's Encrypt
echo "🔒 Setting up SSL..."
sudo apt update && sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# Create log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/$SERVICE_NAME > /dev/null << EOL
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload $SERVICE_NAME
    endscript
}
EOL

# Create monitoring script
echo "📊 Creating monitoring script..."
cat > monitor.sh << 'EOL'
#!/bin/bash

SERVICE_NAME="ai-agent"
APP_DIR="/opt/ai-agent-system"

# Check service status
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "❌ Service $SERVICE_NAME is not running"
    sudo systemctl restart $SERVICE_NAME
    echo "🔄 Service restarted"
fi

# Check disk space
DISK_USAGE=$(df $APP_DIR | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "⚠️ Disk usage is at ${DISK_USAGE}%"
    # Clean up old clips
    find $APP_DIR/clips -type f -mtime +7 -delete
    find $APP_DIR/temp_clips -type f -mtime +1 -delete
fi

# Check API health
if ! curl -s http://localhost:8000/api/status > /dev/null; then
    echo "❌ API health check failed"
    sudo systemctl restart $SERVICE_NAME
fi

echo "✅ System check completed at $(date)"
EOL

chmod +x monitor.sh

# Set up cron job for monitoring
echo "⏰ Setting up monitoring cron job..."
(crontab -l 2>/dev/null; echo "*/5 * * * * $APP_DIR/monitor.sh >> $APP_DIR/logs/monitor.log 2>&1") | crontab -

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo "📊 Dashboard: https://$DOMAIN"
echo "📝 Logs: journalctl -u $SERVICE_NAME -f"
echo "📈 Status: systemctl status $SERVICE_NAME"
echo ""
echo "🔧 Next Steps:"
echo "1. Edit $APP_DIR/.env with your real API keys"
echo "2. Configure $APP_DIR/youtube_config.yaml"
echo "3. Restart service: sudo systemctl restart $SERVICE_NAME"
echo "4. Start making money! 💰"