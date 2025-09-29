#!/bin/bash

# Setup cronjobs for automated crawling
# This script creates systemd timers and services for reliable crawling

set -e

echo "Setting up cronjobs for bestmua-data crawler..."

APP_DIR="/opt/bestmua-data/bestmua-data"
VENV_PATH="$APP_DIR/venv"

# Create systemd service for full crawl
cat > /etc/systemd/system/bestmua-full-crawl.service << EOF
[Unit]
Description=Bestmua Full Site Crawler
After=network.target mysql.service

[Service]
Type=oneshot
User=root
WorkingDirectory=$APP_DIR
Environment=PATH=$VENV_PATH/bin
ExecStart=$VENV_PATH/bin/python -m bestmua_data.cli --verbose --log-file /opt/bestmua-data/logs/full-crawl.log --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart crawl --workers 2 --delay 2.0
StandardOutput=append:/opt/bestmua-data/logs/full-crawl.log
StandardError=append:/opt/bestmua-data/logs/full-crawl-error.log
EOF

# Create systemd timer for full crawl (weekly)
cat > /etc/systemd/system/bestmua-full-crawl.timer << EOF
[Unit]
Description=Run Bestmua Full Crawl Weekly
Requires=bestmua-full-crawl.service

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Create systemd service for incremental crawl
cat > /etc/systemd/system/bestmua-incremental-crawl.service << EOF
[Unit]
Description=Bestmua Incremental Crawler
After=network.target mysql.service

[Service]
Type=oneshot
User=root
WorkingDirectory=$APP_DIR
Environment=PATH=$VENV_PATH/bin
ExecStart=$VENV_PATH/bin/python -m bestmua_data.cli --verbose --log-file /opt/bestmua-data/logs/incremental-crawl.log --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart incremental --since-days 1 --workers 2 --delay 2.0
StandardOutput=append:/opt/bestmua-data/logs/incremental-crawl.log
StandardError=append:/opt/bestmua-data/logs/incremental-crawl-error.log
EOF

# Create systemd timer for incremental crawl (daily)
cat > /etc/systemd/system/bestmua-incremental-crawl.timer << EOF
[Unit]
Description=Run Bestmua Incremental Crawl Daily
Requires=bestmua-incremental-crawl.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Create monitoring script
cat > $APP_DIR/scripts/monitor_crawler.sh << 'EOF'
#!/bin/bash

# Simple monitoring script for crawler health
LOG_DIR="/opt/bestmua-data/logs"
TODAY=$(date +%Y-%m-%d)

echo "=== Crawler Status Report - $TODAY ==="

# Check if crawler services are active
echo "Service Status:"
systemctl is-active bestmua-full-crawl.timer || echo "Full crawl timer: INACTIVE"
systemctl is-active bestmua-incremental-crawl.timer || echo "Incremental crawl timer: INACTIVE"

# Check recent log activity
echo -e "\nRecent Activity:"
if [ -f "$LOG_DIR/incremental-crawl.log" ]; then
    echo "Last incremental crawl:"
    tail -n 5 "$LOG_DIR/incremental-crawl.log" | head -n 1
fi

if [ -f "$LOG_DIR/full-crawl.log" ]; then
    echo "Last full crawl:"
    tail -n 5 "$LOG_DIR/full-crawl.log" | head -n 1
fi

# Check for errors
echo -e "\nRecent Errors:"
if [ -f "$LOG_DIR/incremental-crawl-error.log" ]; then
    echo "Incremental crawl errors (last 24h):"
    find "$LOG_DIR/incremental-crawl-error.log" -mtime -1 -exec tail -n 10 {} \;
fi

if [ -f "$LOG_DIR/full-crawl-error.log" ]; then
    echo "Full crawl errors (last 7 days):"
    find "$LOG_DIR/full-crawl-error.log" -mtime -7 -exec tail -n 10 {} \;
fi

# Database stats
echo -e "\nDatabase Statistics:"
cd /opt/bestmua-data/bestmua-data
source venv/bin/activate
python -m bestmua_data.cli --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart stats 2>/dev/null || echo "Failed to get database stats"
EOF

chmod +x $APP_DIR/scripts/monitor_crawler.sh

# Reload systemd and enable timers
echo "Reloading systemd and enabling timers..."
systemctl daemon-reload
systemctl enable bestmua-full-crawl.timer
systemctl enable bestmua-incremental-crawl.timer
systemctl start bestmua-full-crawl.timer
systemctl start bestmua-incremental-crawl.timer

# Setup log rotation
cat > /etc/logrotate.d/bestmua-crawler << EOF
/opt/bestmua-data/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

echo "Cronjob setup complete!"
echo "Services created:"
echo "- bestmua-full-crawl.service (runs weekly)"
echo "- bestmua-incremental-crawl.service (runs daily)"
echo ""
echo "To check status:"
echo "systemctl status bestmua-full-crawl.timer"
echo "systemctl status bestmua-incremental-crawl.timer"
echo ""
echo "To monitor crawler:"
echo "bash $APP_DIR/scripts/monitor_crawler.sh"
echo ""
echo "To run manual crawl:"
echo "systemctl start bestmua-full-crawl.service"
echo "systemctl start bestmua-incremental-crawl.service"