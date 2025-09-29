#!/bin/bash

# Test crawler functionality with MySQL database
# This script runs a small test to verify everything works

set -e

APP_DIR="/opt/bestmua-data/bestmua-data"
cd $APP_DIR

# Source virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    source .env
fi

# Set MySQL connection for testing
export DATABASE_URL="mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart"

echo "=== Testing bestmua-data crawler ==="
echo "Database URL: $DATABASE_URL"

# Test 1: Initialize database
echo "Step 1: Testing database initialization..."
python -m bestmua_data.cli --database-url $DATABASE_URL init-db

# Test 2: Test limited crawl
echo "Step 2: Testing limited crawl (2 categories, 2 products each)..."
python -m bestmua_data.cli --verbose --database-url $DATABASE_URL crawl --max-categories 2 --max-products 2 --workers 1 --delay 3.0

# Test 3: Show statistics
echo "Step 3: Showing database statistics..."
python -m bestmua_data.cli --database-url $DATABASE_URL stats

# Test 4: Export data
echo "Step 4: Testing data export..."
python -m bestmua_data.cli --database-url $DATABASE_URL export

echo "=== Test completed successfully! ==="
echo "The crawler is working properly with MySQL database."
echo "You can now run the full deployment."