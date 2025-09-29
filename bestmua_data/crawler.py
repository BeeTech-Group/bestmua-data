"""Main crawler orchestrator for bestmua.vn."""

import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .category_discovery import CategoryDiscovery
from .list_parser import ProductListParser
from .detail_parser import ProductDetailParser
from .normalizer import DataNormalizer
from .database import DatabaseManager
from .exporter import SQLExporter

logger = logging.getLogger(__name__)


class BestmuaCrawler:
    """Main crawler orchestrator for bestmua.vn."""
    
    def __init__(self, 
                 base_url: str = "https://bestmua.vn",
                 database_url: str = "sqlite:///bestmua_data.db",
                 export_dir: str = "exports",
                 max_workers: int = 4,
                 delay_between_requests: float = 1.0):
        """
        Initialize the crawler.
        
        Args:
            base_url: Base URL of the website
            database_url: Database connection URL
            export_dir: Directory for SQL exports
            max_workers: Number of concurrent workers
            delay_between_requests: Delay between HTTP requests (seconds)
        """
        self.base_url = base_url
        self.delay_between_requests = delay_between_requests
        self.max_workers = max_workers
        
        # Initialize session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Initialize components
        self.category_discovery = CategoryDiscovery(base_url, self.session)
        self.list_parser = ProductListParser(base_url, self.session)
        self.detail_parser = ProductDetailParser(base_url, self.session)
        self.normalizer = DataNormalizer()
        self.db_manager = DatabaseManager(database_url)
        self.exporter = SQLExporter(self.db_manager, export_dir)
        
        # State tracking
        self.crawl_session_id = None
        self.stats = {
            'categories_found': 0,
            'categories_processed': 0,
            'products_found': 0,
            'products_processed': 0,
            'products_created': 0,
            'products_updated': 0,
            'errors': 0
        }
        
        logger.info(f"BestmuaCrawler initialized for {base_url}")
    
    def full_crawl(self, max_categories: Optional[int] = None, 
                   max_products_per_category: Optional[int] = None,
                   skip_detail_parsing: bool = False) -> Dict:
        """
        Perform a full crawl of the website.
        
        Args:
            max_categories: Maximum number of categories to crawl (None for all)
            max_products_per_category: Maximum products per category (None for all)
            skip_detail_parsing: Skip detailed product parsing (faster but less data)
            
        Returns:
            Crawl statistics
        """
        start_time = datetime.utcnow()
        logger.info("Starting full crawl")
        
        # Start crawl session
        crawl_session = self.db_manager.start_crawl_session()
        self.crawl_session_id = crawl_session.id
        
        try:
            # Step 1: Discover categories
            logger.info("Step 1: Discovering categories")
            categories = self._discover_and_save_categories()
            self.stats['categories_found'] = len(categories)
            
            if max_categories:
                categories = categories[:max_categories]
            
            # Step 2: Crawl products from categories
            logger.info(f"Step 2: Crawling products from {len(categories)} categories")
            self._crawl_categories(categories, max_products_per_category, skip_detail_parsing)
            
            # Step 3: Export data
            logger.info("Step 3: Exporting data to SQL files")
            export_stats = self.exporter.export_all_categories()
            self.stats['export_stats'] = export_stats
            
            # Finish crawl session
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.stats['duration_seconds'] = duration
            
            self.db_manager.finish_crawl_session(
                self.crawl_session_id, 
                'completed', 
                self.stats
            )
            
            logger.info(f"Full crawl completed in {duration:.2f} seconds")
            logger.info(f"Final stats: {self.stats}")
            
            return self.stats
            
        except Exception as e:
            # Mark crawl session as failed
            self.db_manager.finish_crawl_session(
                self.crawl_session_id,
                'failed',
                self.stats,
                str(e)
            )
            logger.error(f"Full crawl failed: {e}")
            raise
    
    def incremental_crawl(self, since_days: int = 1) -> Dict:
        """
        Perform an incremental crawl, updating only changed products.
        
        Args:
            since_days: Number of days back to check for changes
            
        Returns:
            Crawl statistics
        """
        start_time = datetime.utcnow()
        since_date = start_time - timedelta(days=since_days)
        
        logger.info(f"Starting incremental crawl (since {since_date.isoformat()})")
        
        # Start crawl session
        crawl_session = self.db_manager.start_crawl_session()
        self.crawl_session_id = crawl_session.id
        
        try:
            # Get existing products that might need updating
            existing_products = self.db_manager.get_products_modified_since(since_date)
            
            logger.info(f"Found {len(existing_products)} products to check for updates")
            
            # Check and update products
            updated_count = self._update_existing_products(existing_products)
            self.stats['products_updated'] = updated_count
            
            # Also check for new categories and products
            categories = self._discover_and_save_categories()
            new_products_count = 0
            
            for category_data in categories:
                category = self.db_manager.get_category_by_slug(category_data['slug'])
                if category:
                    # Get first page of products to check for new ones
                    products_data = self.list_parser.parse_category_page(
                        category_data['url'], max_pages=1
                    )
                    
                    for product_data in products_data:
                        normalized_product = self.normalizer.normalize_product(product_data)
                        if not self.db_manager.check_product_exists(normalized_product['slug']):
                            # Get detailed data for new products
                            detailed_product = self.detail_parser.parse_product_detail(
                                product_data['url']
                            )
                            if detailed_product:
                                detailed_normalized = self.normalizer.normalize_product(detailed_product)
                                self.db_manager.upsert_product(detailed_normalized)
                                new_products_count += 1
                    
                    time.sleep(self.delay_between_requests)
            
            self.stats['products_created'] = new_products_count
            self.stats['products_processed'] = updated_count + new_products_count
            
            # Finish crawl session
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.stats['duration_seconds'] = duration
            
            self.db_manager.finish_crawl_session(
                self.crawl_session_id,
                'completed',
                self.stats
            )
            
            logger.info(f"Incremental crawl completed: {self.stats}")
            return self.stats
            
        except Exception as e:
            self.db_manager.finish_crawl_session(
                self.crawl_session_id,
                'failed',
                self.stats,
                str(e)
            )
            logger.error(f"Incremental crawl failed: {e}")
            raise
    
    def crawl_category(self, category_slug: str, max_products: Optional[int] = None) -> Dict:
        """
        Crawl a specific category.
        
        Args:
            category_slug: Slug of the category to crawl
            max_products: Maximum number of products to crawl
            
        Returns:
            Crawl statistics
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting category crawl: {category_slug}")
        
        # Start crawl session
        crawl_session = self.db_manager.start_crawl_session()
        self.crawl_session_id = crawl_session.id
        
        try:
            # Get category from database
            category = self.db_manager.get_category_by_slug(category_slug)
            if not category:
                raise ValueError(f"Category '{category_slug}' not found in database")
            
            # Crawl products from category
            products_data = self.list_parser.parse_category_page(category.url)
            
            if max_products:
                products_data = products_data[:max_products]
            
            self.stats['products_found'] = len(products_data)
            
            # Process products
            processed_products = self._process_products_batch(products_data)
            
            self.stats['products_processed'] = len(processed_products)
            self.stats['products_created'] = sum(1 for _, created in processed_products if created)
            self.stats['products_updated'] = sum(1 for _, created in processed_products if not created)
            
            # Export category data
            export_stats = self.exporter.export_category_sql(category_slug)
            self.stats['export_stats'] = export_stats
            
            # Finish crawl session
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.stats['duration_seconds'] = duration
            
            self.db_manager.finish_crawl_session(
                self.crawl_session_id,
                'completed',
                self.stats
            )
            
            logger.info(f"Category crawl completed: {self.stats}")
            return self.stats
            
        except Exception as e:
            self.db_manager.finish_crawl_session(
                self.crawl_session_id,
                'failed',
                self.stats,
                str(e)
            )
            logger.error(f"Category crawl failed: {e}")
            raise
    
    def _discover_and_save_categories(self) -> List[Dict]:
        """Discover and save categories to database."""
        try:
            categories_data = self.category_discovery.discover_categories()
            
            for category_data in categories_data:
                try:
                    normalized_category = self.normalizer.normalize_category(category_data)
                    self.db_manager.upsert_category(normalized_category)
                except Exception as e:
                    logger.error(f"Error saving category {category_data.get('slug', 'unknown')}: {e}")
                    self.stats['errors'] += 1
            
            logger.info(f"Discovered and saved {len(categories_data)} categories")
            return categories_data
            
        except Exception as e:
            logger.error(f"Error discovering categories: {e}")
            self.stats['errors'] += 1
            return []
    
    def _crawl_categories(self, categories: List[Dict], max_products_per_category: Optional[int] = None,
                         skip_detail_parsing: bool = False):
        """Crawl products from multiple categories."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_category = {
                executor.submit(
                    self._crawl_single_category,
                    category,
                    max_products_per_category,
                    skip_detail_parsing
                ): category for category in categories
            }
            
            # Process completed tasks
            for future in as_completed(future_to_category):
                category = future_to_category[future]
                try:
                    category_stats = future.result()
                    self.stats['categories_processed'] += 1
                    self.stats['products_found'] += category_stats.get('products_found', 0)
                    self.stats['products_processed'] += category_stats.get('products_processed', 0)
                    self.stats['products_created'] += category_stats.get('products_created', 0)
                    self.stats['products_updated'] += category_stats.get('products_updated', 0)
                    self.stats['errors'] += category_stats.get('errors', 0)
                    
                except Exception as e:
                    logger.error(f"Error crawling category {category.get('slug', 'unknown')}: {e}")
                    self.stats['errors'] += 1
                
                # Add delay between category processing
                time.sleep(self.delay_between_requests)
    
    def _crawl_single_category(self, category_data: Dict, max_products: Optional[int] = None,
                              skip_detail_parsing: bool = False) -> Dict:
        """Crawl products from a single category."""
        category_stats = {
            'products_found': 0,
            'products_processed': 0,
            'products_created': 0,
            'products_updated': 0,
            'errors': 0
        }
        
        try:
            logger.info(f"Crawling category: {category_data['slug']}")
            
            # Get products list
            products_data = self.list_parser.parse_category_page(
                category_data['url'],
                max_pages=None
            )
            
            if max_products:
                products_data = products_data[:max_products]
            
            category_stats['products_found'] = len(products_data)
            
            # Process products
            if not skip_detail_parsing:
                # Get detailed data for each product
                detailed_products = []
                for product_data in products_data:
                    try:
                        detailed_product = self.detail_parser.parse_product_detail(
                            product_data['url']
                        )
                        if detailed_product:
                            # Merge list data with detail data
                            merged_product = {**product_data, **detailed_product}
                            detailed_products.append(merged_product)
                        
                        time.sleep(self.delay_between_requests)
                        
                    except Exception as e:
                        logger.error(f"Error getting product details for {product_data.get('url', 'unknown')}: {e}")
                        category_stats['errors'] += 1
                
                products_data = detailed_products
            
            # Normalize and save products
            processed_products = self._process_products_batch(products_data)
            
            category_stats['products_processed'] = len(processed_products)
            category_stats['products_created'] = sum(1 for _, created in processed_products if created)
            category_stats['products_updated'] = sum(1 for _, created in processed_products if not created)
            
            logger.info(f"Completed category {category_data['slug']}: {category_stats}")
            return category_stats
            
        except Exception as e:
            logger.error(f"Error crawling category {category_data.get('slug', 'unknown')}: {e}")
            category_stats['errors'] += 1
            return category_stats
    
    def _process_products_batch(self, products_data: List[Dict]) -> List[Tuple]:
        """Process a batch of products."""
        processed_products = []
        
        for product_data in products_data:
            try:
                # Add category name for reference
                product_data['category_name'] = product_data.get('category_name', '')
                
                # Normalize product data
                normalized_product = self.normalizer.normalize_product(product_data)
                
                # Validate normalized data
                validation_result = self.normalizer.validate_normalized_product(normalized_product)
                if not validation_result['is_valid']:
                    logger.warning(f"Product validation failed for {normalized_product.get('slug', 'unknown')}: {validation_result['errors']}")
                    continue
                
                # Save to database
                product, was_created = self.db_manager.upsert_product(normalized_product)
                processed_products.append((product, was_created))
                
            except Exception as e:
                logger.error(f"Error processing product {product_data.get('slug', 'unknown')}: {e}")
                self.stats['errors'] += 1
                continue
        
        return processed_products
    
    def _update_existing_products(self, products: List) -> int:
        """Update existing products by re-parsing their details."""
        updated_count = 0
        
        for product in products:
            try:
                # Re-parse product details
                detailed_product = self.detail_parser.parse_product_detail(product.url)
                
                if detailed_product:
                    # Normalize and update
                    normalized_product = self.normalizer.normalize_product(detailed_product)
                    self.db_manager.upsert_product(normalized_product)
                    updated_count += 1
                    
                    logger.debug(f"Updated product: {product.slug}")
                
                time.sleep(self.delay_between_requests)
                
            except Exception as e:
                logger.error(f"Error updating product {product.slug}: {e}")
                self.stats['errors'] += 1
                continue
        
        return updated_count
    
    def get_crawl_stats(self) -> Dict:
        """Get current crawl statistics."""
        db_stats = self.db_manager.get_database_stats()
        return {
            'crawl_stats': self.stats,
            'database_stats': db_stats
        }
    
    def export_all_data(self) -> Dict:
        """Export all data to SQL files."""
        try:
            export_stats = self.exporter.export_all_categories()
            
            # Create schema file
            schema_file = self.exporter.export_database_schema()
            
            # Create summary
            summary_file = self.exporter.create_export_summary()
            
            export_stats['schema_file'] = schema_file
            export_stats['summary_file'] = summary_file
            
            logger.info(f"Data export completed: {export_stats}")
            return export_stats
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            raise
    
    def validate_exports(self, export_dir: Optional[str] = None) -> Dict:
        """Validate all exported SQL files."""
        import os
        from pathlib import Path
        
        if export_dir:
            export_path = Path(export_dir)
        else:
            export_path = self.exporter.export_dir
        
        validation_results = {
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'total_records': 0,
            'file_results': []
        }
        
        try:
            sql_files = list(export_path.glob("*.sql"))
            validation_results['total_files'] = len(sql_files)
            
            for sql_file in sql_files:
                if sql_file.name == 'schema.sql':
                    continue  # Skip schema file
                
                file_validation = self.exporter.validate_exported_sql(str(sql_file))
                validation_results['file_results'].append({
                    'file': sql_file.name,
                    'is_valid': file_validation['is_valid'],
                    'records_count': file_validation['records_count'],
                    'errors': file_validation['errors']
                })
                
                if file_validation['is_valid']:
                    validation_results['valid_files'] += 1
                    validation_results['total_records'] += file_validation['records_count']
                else:
                    validation_results['invalid_files'] += 1
            
            logger.info(f"Export validation completed: {validation_results}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating exports: {e}")
            raise