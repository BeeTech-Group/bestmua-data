"""Command-line interface for bestmua-data crawler."""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

import click

from .crawler import BestmuaCrawler
from .database import DatabaseManager
from .exporter import SQLExporter


def setup_logging(verbose: bool = False, log_file: str = None):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Reduce noise from requests library
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--log-file', help='Log file path')
@click.option('--database-url', default='sqlite:///bestmua_data.db', 
              help='Database URL (default: sqlite:///bestmua_data.db)')
@click.option('--base-url', default='https://bestmua.vn',
              help='Base URL to crawl (default: https://bestmua.vn)')
@click.option('--export-dir', default='exports',
              help='Export directory (default: exports)')
@click.pass_context
def cli(ctx, verbose, log_file, database_url, base_url, export_dir):
    """bestmua-data: Web scraper for bestmua.vn product data."""
    setup_logging(verbose, log_file)
    
    # Store configuration in context
    ctx.ensure_object(dict)
    ctx.obj['database_url'] = database_url
    ctx.obj['base_url'] = base_url
    ctx.obj['export_dir'] = export_dir
    ctx.obj['verbose'] = verbose


@cli.command()
@click.option('--max-categories', type=int, help='Maximum categories to crawl')
@click.option('--max-products', type=int, help='Maximum products per category')
@click.option('--skip-details', is_flag=True, help='Skip detailed product parsing (faster)')
@click.option('--workers', type=int, default=4, help='Number of concurrent workers')
@click.option('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
@click.pass_context
def crawl(ctx, max_categories, max_products, skip_details, workers, delay):
    """Perform a full crawl of bestmua.vn."""
    click.echo("Starting full crawl of bestmua.vn...")
    click.echo(f"Database: {ctx.obj['database_url']}")
    click.echo(f"Export directory: {ctx.obj['export_dir']}")
    
    try:
        crawler = BestmuaCrawler(
            base_url=ctx.obj['base_url'],
            database_url=ctx.obj['database_url'],
            export_dir=ctx.obj['export_dir'],
            max_workers=workers,
            delay_between_requests=delay
        )
        
        stats = crawler.full_crawl(
            max_categories=max_categories,
            max_products_per_category=max_products,
            skip_detail_parsing=skip_details
        )
        
        click.echo("\nCrawl completed successfully!")
        click.echo(f"Categories found: {stats['categories_found']}")
        click.echo(f"Products found: {stats['products_found']}")
        click.echo(f"Products processed: {stats['products_processed']}")
        click.echo(f"Products created: {stats['products_created']}")
        click.echo(f"Products updated: {stats['products_updated']}")
        click.echo(f"Duration: {stats.get('duration_seconds', 0):.2f} seconds")
        
        if stats['errors'] > 0:
            click.echo(f"Errors encountered: {stats['errors']}", err=True)
        
    except Exception as e:
        click.echo(f"Crawl failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--since-days', type=int, default=1, help='Days back to check for changes')
@click.option('--workers', type=int, default=4, help='Number of concurrent workers')
@click.option('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
@click.pass_context
def incremental(ctx, since_days, workers, delay):
    """Perform an incremental crawl to update existing data."""
    click.echo(f"Starting incremental crawl (checking last {since_days} days)...")
    
    try:
        crawler = BestmuaCrawler(
            base_url=ctx.obj['base_url'],
            database_url=ctx.obj['database_url'],
            export_dir=ctx.obj['export_dir'],
            max_workers=workers,
            delay_between_requests=delay
        )
        
        stats = crawler.incremental_crawl(since_days=since_days)
        
        click.echo("\nIncremental crawl completed!")
        click.echo(f"Products processed: {stats['products_processed']}")
        click.echo(f"Products created: {stats['products_created']}")
        click.echo(f"Products updated: {stats['products_updated']}")
        click.echo(f"Duration: {stats.get('duration_seconds', 0):.2f} seconds")
        
        if stats['errors'] > 0:
            click.echo(f"Errors encountered: {stats['errors']}", err=True)
        
    except Exception as e:
        click.echo(f"Incremental crawl failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('category_slug')
@click.option('--max-products', type=int, help='Maximum products to crawl')
@click.option('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
@click.pass_context
def crawl_category(ctx, category_slug, max_products, delay):
    """Crawl a specific category by slug."""
    click.echo(f"Crawling category: {category_slug}")
    
    try:
        crawler = BestmuaCrawler(
            base_url=ctx.obj['base_url'],
            database_url=ctx.obj['database_url'],
            export_dir=ctx.obj['export_dir'],
            delay_between_requests=delay
        )
        
        stats = crawler.crawl_category(category_slug, max_products)
        
        click.echo(f"\nCategory crawl completed!")
        click.echo(f"Products found: {stats['products_found']}")
        click.echo(f"Products processed: {stats['products_processed']}")
        click.echo(f"Products created: {stats['products_created']}")
        click.echo(f"Products updated: {stats['products_updated']}")
        
        if stats['errors'] > 0:
            click.echo(f"Errors encountered: {stats['errors']}", err=True)
        
    except Exception as e:
        click.echo(f"Category crawl failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--category', help='Export specific category by slug')
@click.pass_context
def export(ctx, category):
    """Export data to SQL files."""
    click.echo("Exporting data to SQL files...")
    
    try:
        db_manager = DatabaseManager(ctx.obj['database_url'])
        exporter = SQLExporter(db_manager, ctx.obj['export_dir'])
        
        if category:
            # Export specific category
            stats = exporter.export_category_sql(category)
            click.echo(f"Exported category '{category}':")
            click.echo(f"Products: {stats['products_exported']}")
            click.echo(f"File: {stats['file_path']}")
            click.echo(f"Size: {stats['file_size']:,} bytes")
        else:
            # Export all categories
            stats = exporter.export_all_categories()
            click.echo(f"Export completed:")
            click.echo(f"Categories processed: {stats['categories_processed']}")
            click.echo(f"Files created: {stats['files_created']}")
            click.echo(f"Total products: {stats['total_products']}")
            
            if stats['errors']:
                click.echo(f"Errors: {len(stats['errors'])}", err=True)
                for error in stats['errors']:
                    click.echo(f"  - {error}", err=True)
        
        # Create summary
        summary_file = exporter.create_export_summary()
        click.echo(f"Export summary: {summary_file}")
        
    except Exception as e:
        click.echo(f"Export failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate exported SQL files."""
    click.echo("Validating exported SQL files...")
    
    try:
        db_manager = DatabaseManager(ctx.obj['database_url'])
        exporter = SQLExporter(db_manager, ctx.obj['export_dir'])
        
        # Use crawler's validate method
        crawler = BestmuaCrawler(
            database_url=ctx.obj['database_url'],
            export_dir=ctx.obj['export_dir']
        )
        
        results = crawler.validate_exports()
        
        click.echo(f"Validation completed:")
        click.echo(f"Total files: {results['total_files']}")
        click.echo(f"Valid files: {results['valid_files']}")
        click.echo(f"Invalid files: {results['invalid_files']}")
        click.echo(f"Total records: {results['total_records']:,}")
        
        if results['invalid_files'] > 0:
            click.echo("\nInvalid files:")
            for file_result in results['file_results']:
                if not file_result['is_valid']:
                    click.echo(f"  - {file_result['file']}: {file_result['errors']}")
        
    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database and crawl statistics."""
    try:
        db_manager = DatabaseManager(ctx.obj['database_url'])
        stats = db_manager.get_database_stats()
        
        click.echo("Database Statistics:")
        click.echo("=" * 40)
        click.echo(f"Categories: {stats['categories']:,}")
        click.echo(f"Brands: {stats['brands']:,}")
        click.echo(f"Products: {stats['products']:,}")
        click.echo(f"Crawl sessions: {stats['crawl_sessions']:,}")
        click.echo()
        click.echo("Product Statistics:")
        click.echo("-" * 20)
        click.echo(f"Products with images: {stats['products_with_images']:,}")
        click.echo(f"Products with prices: {stats['products_with_prices']:,}")
        click.echo(f"Products with ratings: {stats['products_with_ratings']:,}")
        
        # Show export directory info
        export_dir = Path(ctx.obj['export_dir'])
        if export_dir.exists():
            export_files = list(export_dir.glob("*.sql"))
            total_size = sum(f.stat().st_size for f in export_files)
            
            click.echo()
            click.echo("Export Statistics:")
            click.echo("-" * 20)
            click.echo(f"Export directory: {export_dir}")
            click.echo(f"SQL files: {len(export_files)}")
            click.echo(f"Total size: {total_size:,} bytes")
        
    except Exception as e:
        click.echo(f"Error getting statistics: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--days', type=int, default=30, help='Remove sessions older than N days')
@click.pass_context
def cleanup(ctx, days):
    """Clean up old data and files."""
    click.echo(f"Cleaning up data older than {days} days...")
    
    try:
        db_manager = DatabaseManager(ctx.obj['database_url'])
        exporter = SQLExporter(db_manager, ctx.obj['export_dir'])
        
        # Clean up old crawl sessions
        db_manager.cleanup_old_sessions(days)
        
        # Clean up old export files
        exporter.cleanup_old_exports(days)
        
        click.echo("Cleanup completed successfully!")
        
    except Exception as e:
        click.echo(f"Cleanup failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def init_db(ctx):
    """Initialize the database schema."""
    click.echo("Initializing database...")
    
    try:
        db_manager = DatabaseManager(ctx.obj['database_url'])
        click.echo(f"Database initialized: {ctx.obj['database_url']}")
        
        stats = db_manager.get_database_stats()
        if stats['products'] > 0:
            click.echo(f"Existing data found: {stats['products']} products")
        else:
            click.echo("Empty database ready for crawling")
        
    except Exception as e:
        click.echo(f"Database initialization failed: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()