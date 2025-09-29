#!/bin/bash

# Deployment script for bestmua-data crawler on VPS
# This script sets up the environment and installs dependencies

set -e

echo "Starting deployment setup for bestmua-data crawler..."

# Update system packages
echo "Updating system packages..."
apt update && apt upgrade -y

# Install required system packages
echo "Installing system dependencies..."
apt install -y python3 python3-pip python3-venv git mysql-client cron

# Create application directory
APP_DIR="/opt/bestmua-data"
echo "Creating application directory: $APP_DIR"
mkdir -p $APP_DIR
cd $APP_DIR

# Clone repository (if not already present)
if [ ! -d "bestmua-data" ]; then
    echo "Cloning repository..."
    git clone https://github.com/BeeTech-Group/bestmua-data.git
fi

cd bestmua-data

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create environment configuration
echo "Creating environment configuration..."
cat > .env << EOF
# Database configuration
BESTMUA_DATABASE_URL=mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart
BESTMUA_EXPORT_DIR=/opt/bestmua-data/exports
BESTMUA_LOG_LEVEL=INFO

# Crawler settings
BESTMUA_BASE_URL=https://bestmua.vn
BESTMUA_MAX_WORKERS=2
BESTMUA_DELAY_BETWEEN_REQUESTS=2.0

# Production settings
BESTMUA_PRODUCTION=true
EOF

# Create exports directory
mkdir -p /opt/bestmua-data/exports

# Create logs directory
mkdir -p /opt/bestmua-data/logs

# Set proper permissions
chown -R root:root /opt/bestmua-data
chmod +x /opt/bestmua-data/bestmua-data/scripts/*.sh

echo "Environment setup complete!"
echo "Next steps:"
echo "1. Test database connectivity: cd $APP_DIR/bestmua-data && source venv/bin/activate && python -m bestmua_data.cli init-db"
echo "2. Run test crawl: python -m bestmua_data.cli crawl --max-categories 2 --max-products 2"
echo "3. Setup cronjobs: bash scripts/setup_cronjobs.sh"