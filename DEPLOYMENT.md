# Deployment Guide for bestmua-data Crawler

This guide covers deploying the bestmua-data crawler to a VPS with MySQL database integration and automated crawling via systemd timers.

## Server Information

- **SSH**: 194.233.71.21
- **User**: root
- **Password**: j4MREvDinip6H663Wwbul8HyxEBh
- **MySQL User**: root
- **MySQL Password**: 889d1879cd75f315
- **Database**: crawler_mediamart

## Quick Deployment

### 1. Initial Setup

```bash
# Connect to server
ssh root@194.233.71.21

# Download and run deployment script
wget https://raw.githubusercontent.com/BeeTech-Group/bestmua-data/main/deploy_setup.sh
chmod +x deploy_setup.sh
./deploy_setup.sh
```

### 2. Test the Installation

```bash
cd /opt/bestmua-data/bestmua-data
source venv/bin/activate

# Test database connectivity
python -m bestmua_data.cli --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart init-db

# Run test crawl (2 categories, 2 products each)
python -m bestmua_data.cli --verbose --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart crawl --max-categories 2 --max-products 2 --workers 1 --delay 3.0

# Check statistics
python -m bestmua_data.cli --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart stats
```

### 3. Setup Automated Crawling

```bash
# Setup systemd timers for automated crawling
bash scripts/setup_cronjobs.sh

# Check timer status
systemctl status bestmua-full-crawl.timer
systemctl status bestmua-incremental-crawl.timer
```

## Manual Operations

### Database Management

```bash
# Initialize/reset database
python -m bestmua_data.cli --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart init-db

# Show database statistics
python -m bestmua_data.cli --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart stats

# Export data to SQL files
python -m bestmua_data.cli --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart export
```

### Crawling Operations

```bash
# Full site crawl
python -m bestmua_data.cli --verbose --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart crawl --workers 2 --delay 2.0

# Limited test crawl
python -m bestmua_data.cli --verbose --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart crawl --max-categories 3 --max-products 5 --workers 1 --delay 3.0

# Incremental crawl (update existing data)
python -m bestmua_data.cli --verbose --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart incremental --since-days 1 --workers 2 --delay 2.0

# Crawl specific category
python -m bestmua_data.cli --database-url mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart crawl-category son-moi --max-products 10
```

### Service Management

```bash
# Start services manually
systemctl start bestmua-full-crawl.service
systemctl start bestmua-incremental-crawl.service

# Check service logs
journalctl -u bestmua-full-crawl.service -f
journalctl -u bestmua-incremental-crawl.service -f

# Monitor crawler health
bash /opt/bestmua-data/bestmua-data/scripts/monitor_crawler.sh
```

## Automated Schedule

- **Full Crawl**: Runs weekly (complete site crawl)
- **Incremental Crawl**: Runs daily (updates for recent changes)
- **Logs**: Stored in `/opt/bestmua-data/logs/`
- **Exports**: Stored in `/opt/bestmua-data/exports/`

## Configuration

Environment variables are stored in `/opt/bestmua-data/bestmua-data/.env`:

```bash
# Database configuration
BESTMUA_DATABASE_URL=mysql+pymysql://root:889d1879cd75f315@localhost:3306/crawler_mediamart
BESTMUA_EXPORT_DIR=/opt/bestmua-data/exports
BESTMUA_LOG_LEVEL=INFO

# Crawler settings
BESTMUA_BASE_URL=https://bestmua.vn
BESTMUA_MAX_WORKERS=2
BESTMUA_DELAY_BETWEEN_REQUESTS=2.0
```

## Troubleshooting

### Common Issues

1. **MySQL Connection Errors**
   ```bash
   # Check MySQL service
   systemctl status mysql
   
   # Test connection
   mysql -u root -p889d1879cd75f315 -e "SHOW DATABASES;"
   ```

2. **Permission Issues**
   ```bash
   # Fix permissions
   chown -R root:root /opt/bestmua-data
   chmod +x /opt/bestmua-data/bestmua-data/scripts/*.sh
   ```

3. **Network Issues**
   ```bash
   # Test website connectivity
   curl -I https://bestmua.vn
   
   # Check network delays
   ping bestmua.vn
   ```

### Log Files

- Full crawl logs: `/opt/bestmua-data/logs/full-crawl.log`
- Incremental crawl logs: `/opt/bestmua-data/logs/incremental-crawl.log`
- Error logs: `/opt/bestmua-data/logs/*-error.log`
- System logs: `journalctl -u bestmua-*.service`

### Performance Tuning

1. **Adjust worker count** based on server resources
2. **Increase delays** if getting rate-limited
3. **Run during off-peak hours** for better performance
4. **Monitor database size** and clean up old data regularly

## Database Schema

The crawler creates the following tables:
- `categories`: Product categories
- `brands`: Product brands
- `products`: Main product data
- `crawl_sessions`: Crawl audit trail

## Security

- Database credentials are stored in environment files
- Logs are rotated automatically
- Services run with minimal privileges
- Network requests include appropriate delays to respect the target site