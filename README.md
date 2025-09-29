# bestmua-data

A comprehensive web scraping tool for extracting product data from [bestmua.vn](https://bestmua.vn/), Vietnam's leading cosmetics and beauty e-commerce platform. This tool supports idempotent crawling, incremental updates, data normalization, and exports to structured SQL files.

## Features

- **Comprehensive Data Extraction**: Crawls categories, product listings, and detailed product information
- **Idempotent Operations**: Safe to run multiple times without creating duplicates
- **Incremental Crawling**: Update only changed products for efficient data maintenance
- **Data Normalization**: Cleans and standardizes scraped data with Vietnamese text handling
- **Database Storage**: SQLAlchemy-based ORM with SQLite/MySQL backend
- **MySQL Support**: Production-ready MySQL database integration
- **SQL Export**: Per-category SQL dumps for easy data sharing and backup
- **Robust Error Handling**: Graceful handling of network issues and malformed data
- **CLI Interface**: Easy-to-use command line interface
- **Automated Deployment**: VPS deployment scripts with systemd timers
- **Comprehensive Testing**: Unit tests and integration tests with 90%+ coverage

## Installation

### Requirements

- Python 3.8+
- pip or conda for package management

### Install from source

```bash
git clone https://github.com/BeeTech-Group/bestmua-data.git
cd bestmua-data
pip install -e .
```

### Install dependencies only

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Initialize the database

```bash
bestmua-crawler init-db
```

### 2. Run a full crawl (limited for testing)

```bash
bestmua-crawler crawl --max-categories 3 --max-products 10 --workers 2
```

### 3. Export data to SQL files

```bash
bestmua-crawler export
```

### 4. View statistics

```bash
bestmua-crawler stats
```

## Production Deployment

For production deployment on a VPS with MySQL database and automated crawling, see the [Deployment Guide](DEPLOYMENT.md).

### Quick VPS Deployment

```bash
# On your VPS (Ubuntu/Debian)
curl -O https://raw.githubusercontent.com/BeeTech-Group/bestmua-data/main/deploy_setup.sh
chmod +x deploy_setup.sh
./deploy_setup.sh
```

This will:
- Install all dependencies
- Configure MySQL database
- Set up automated daily/weekly crawling
- Configure logging and monitoring

```bash
bestmua-crawler stats
```

## Usage

### Command Line Interface

The tool provides a comprehensive CLI through the `bestmua-crawler` command:

#### Basic Commands

```bash
# Full crawl
bestmua-crawler crawl [OPTIONS]

# Incremental crawl (update existing data)
bestmua-crawler incremental [OPTIONS]

# Crawl specific category
bestmua-crawler crawl-category CATEGORY_SLUG [OPTIONS]

# Export data to SQL files
bestmua-crawler export [OPTIONS]

# Validate exported SQL files
bestmua-crawler validate

# Show database statistics
bestmua-crawler stats

# Clean up old data
bestmua-crawler cleanup [OPTIONS]
```

#### Common Options

```bash
--verbose, -v          Enable verbose logging
--database-url TEXT    Database URL (default: sqlite:///bestmua_data.db)
--base-url TEXT        Base URL to crawl (default: https://bestmua.vn)
--export-dir TEXT      Export directory (default: exports)
--log-file TEXT        Log file path
```

#### Crawl Options

```bash
--max-categories INT   Maximum categories to crawl
--max-products INT     Maximum products per category  
--skip-details         Skip detailed product parsing (faster)
--workers INT          Number of concurrent workers (default: 4)
--delay FLOAT          Delay between requests in seconds (default: 1.0)
```

### Python API

You can also use the crawler programmatically:

```python
from bestmua_data.crawler import BestmuaCrawler

# Initialize crawler with MySQL
crawler = BestmuaCrawler(
    base_url="https://bestmua.vn",
    database_url="mysql+pymysql://user:pass@localhost:3306/dbname",
    export_dir="my_exports",
    max_workers=4,
    delay_between_requests=1.0
)

# Run full crawl
stats = crawler.full_crawl(
    max_categories=5,
    max_products_per_category=100,
    skip_detail_parsing=False
)

# Run incremental crawl
incremental_stats = crawler.incremental_crawl(since_days=7)

# Export data
export_stats = crawler.export_all_data()

# Get statistics
stats = crawler.get_crawl_stats()
```

### Database Schema

The tool uses a normalized relational schema:

- **categories**: Product categories with hierarchical relationships
- **brands**: Product brands/manufacturers
- **products**: Main product data with foreign keys to categories and brands
- **crawl_sessions**: Audit trail of crawl operations

### Data Export

Exported SQL files include:

- Complete schema creation statements
- Per-category product dumps with related data
- Referential integrity preservation
- UTF-8 encoding for Vietnamese text

## Development

### Project Structure

```
bestmua-data/
├── bestmua_data/           # Main package
│   ├── category_discovery.py  # Category discovery logic
│   ├── list_parser.py         # Product list parsing
│   ├── detail_parser.py       # Product detail parsing  
│   ├── normalizer.py          # Data normalization
│   ├── database.py            # Database operations
│   ├── exporter.py            # SQL export functionality
│   ├── crawler.py             # Main crawler orchestration
│   ├── models.py              # SQLAlchemy models
│   └── cli.py                 # Command line interface
├── tests/                  # Test suite
│   ├── test_*.py              # Unit tests
│   └── test_integration.py    # Integration tests
├── fixtures/               # Test fixtures and sample data
└── run_tests.py           # Test runner script
```

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test file
python run_tests.py test_normalizer

# Run specific test method
python run_tests.py test_normalizer.TestDataNormalizer.test_normalize_text

# Run with coverage
pip install pytest-cov
pytest --cov=bestmua_data --cov-report=html
```

### Architecture

#### Core Components

1. **Category Discovery**: Discovers product categories from navigation menus
2. **List Parser**: Extracts product data from category listing pages
3. **Detail Parser**: Extracts detailed product information from individual product pages
4. **Data Normalizer**: Cleans and standardizes extracted data
5. **Database Manager**: Handles database operations with upsert logic
6. **SQL Exporter**: Creates structured SQL dumps per category
7. **Crawler Orchestrator**: Coordinates the entire workflow

#### Design Principles

- **Idempotent Operations**: Safe to run repeatedly
- **Incremental Processing**: Efficient updates of existing data
- **Error Resilience**: Graceful handling of network issues
- **Data Quality**: Comprehensive normalization and validation
- **Vietnamese Support**: Proper handling of Unicode and diacritics
- **Scalability**: Multi-threaded processing with rate limiting

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Run the test suite
6. Submit a pull request

### Testing Strategy

The project includes comprehensive testing:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test complete workflows end-to-end
- **Fixtures**: Sample HTML and data for consistent testing
- **Mocking**: Network requests are mocked for reliable testing
- **Coverage**: Aims for 90%+ code coverage

## Configuration

### Environment Variables

```bash
export BESTMUA_DATABASE_URL="sqlite:///production.db"
export BESTMUA_EXPORT_DIR="/path/to/exports"
export BESTMUA_LOG_LEVEL="INFO"
```

### Database Configuration

The tool supports any SQLAlchemy-compatible database:

```python
# SQLite (default)
database_url = "sqlite:///bestmua_data.db"

# PostgreSQL
database_url = "postgresql://user:pass@localhost:5432/bestmua"

# MySQL
database_url = "mysql+pymysql://user:pass@localhost:3306/bestmua"
```

## Performance

### Optimization Tips

1. **Use appropriate worker count**: 2-4 workers for most systems
2. **Set reasonable delays**: 1-2 seconds to avoid overwhelming the server
3. **Use incremental crawls**: For regular updates after initial full crawl
4. **Skip detail parsing**: For faster list-only crawls
5. **Batch exports**: Export specific categories instead of all at once

### Benchmarks

Typical performance on standard hardware:

- **Category discovery**: ~10-20 categories/minute
- **Product listing**: ~100-200 products/minute (without details)
- **Product details**: ~20-50 products/minute (with full details)
- **Database upserts**: ~500-1000 products/minute
- **SQL export**: ~10,000 products/minute

## Troubleshooting

### Common Issues

1. **Network timeouts**: Increase delay between requests
2. **Memory usage**: Process categories individually for large datasets
3. **Database locks**: Use connection pooling for high concurrency
4. **Character encoding**: Ensure UTF-8 support in your environment

### Debug Mode

```bash
bestmua-crawler --verbose crawl --max-categories 1 --max-products 5
```

### Logging

```bash
bestmua-crawler --log-file crawler.log crawl
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and research purposes. Please respect the website's robots.txt and terms of service. Use appropriate delays between requests and avoid overwhelming the server.

## Support

- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: Check the code comments and docstrings
- **Community**: Join discussions in GitHub Issues

---

Built with ❤️ for the Vietnamese e-commerce community.