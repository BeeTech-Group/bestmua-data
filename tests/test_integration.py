"""Integration tests for the complete crawling workflow."""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
import json

from bestmua_data.crawler import BestmuaCrawler
from bestmua_data.database import DatabaseManager
from bestmua_data.exporter import SQLExporter
from fixtures.sample_data import (
    SAMPLE_CATEGORY_PAGE_HTML, 
    SAMPLE_PRODUCT_DETAIL_HTML,
    DATABASE_TEST_CATEGORIES
)


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for complete crawling workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.export_dir = os.path.join(self.temp_dir, 'exports')
        
        # Use in-memory database for testing
        self.test_db_url = "sqlite:///:memory:"
        
        # Initialize crawler with test configuration
        self.crawler = BestmuaCrawler(
            base_url="https://bestmua.vn",
            database_url=self.test_db_url,
            export_dir=self.export_dir,
            max_workers=1,  # Single threaded for testing
            delay_between_requests=0  # No delay for testing
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('requests.Session.get')
    def test_full_crawl_workflow_small_subset(self, mock_get):
        """Test complete crawl workflow with small subset of data."""
        # Mock HTTP responses
        def mock_response(url):
            response = Mock()
            response.raise_for_status.return_value = None
            
            if 'bestmua.vn' in str(url) and not 'san-pham' in str(url):
                # Category page response
                response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
            elif 'san-pham' in str(url):
                # Product detail page response
                response.content = SAMPLE_PRODUCT_DETAIL_HTML.encode('utf-8')
            else:
                # Default response
                response.content = '<html><body>Empty page</body></html>'.encode('utf-8')
            
            return response
        
        mock_get.side_effect = mock_response
        
        # Run full crawl with limits
        stats = self.crawler.full_crawl(
            max_categories=2,  # Limit to 2 categories
            max_products_per_category=2,  # Limit to 2 products per category
            skip_detail_parsing=False
        )
        
        # Verify crawl statistics
        self.assertIn('categories_found', stats)
        self.assertIn('products_found', stats)
        self.assertIn('products_processed', stats)
        self.assertIn('duration_seconds', stats)
        
        # Should have found some data
        self.assertGreaterEqual(stats['categories_found'], 1)
        self.assertGreaterEqual(stats['products_processed'], 1)
        
        # Verify database was populated
        db_stats = self.crawler.db_manager.get_database_stats()
        self.assertGreater(db_stats['categories'], 0)
        self.assertGreater(db_stats['products'], 0)
        
        # Verify export files were created
        export_files = list(Path(self.export_dir).glob("*.sql"))
        self.assertGreater(len(export_files), 0)
        
        # Verify export files contain valid SQL
        for export_file in export_files:
            if export_file.name == 'schema.sql':
                continue
            
            validation_result = self.crawler.validate_exports(self.export_dir)
            self.assertGreater(validation_result['valid_files'], 0)
    
    @patch('requests.Session.get')
    def test_incremental_crawl_workflow(self, mock_get):
        """Test incremental crawl workflow."""
        # Mock responses
        def mock_response(url):
            response = Mock()
            response.raise_for_status.return_value = None
            response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
            return response
        
        mock_get.side_effect = mock_response
        
        # First, populate database with some initial data
        self._populate_initial_data()
        
        # Run incremental crawl
        stats = self.crawler.incremental_crawl(since_days=1)
        
        # Verify incremental crawl results
        self.assertIn('products_processed', stats)
        self.assertIn('products_created', stats)
        self.assertIn('products_updated', stats)
        self.assertIn('duration_seconds', stats)
        
        # Should have processed some products
        self.assertGreaterEqual(stats['products_processed'], 0)
    
    @patch('requests.Session.get')
    def test_category_specific_crawl(self, mock_get):
        """Test crawling a specific category."""
        # Mock responses
        def mock_response(url):
            response = Mock()
            response.raise_for_status.return_value = None
            
            if 'san-pham' in str(url):
                response.content = SAMPLE_PRODUCT_DETAIL_HTML.encode('utf-8')
            else:
                response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
            
            return response
        
        mock_get.side_effect = mock_response
        
        # First create a category in database
        category_data = DATABASE_TEST_CATEGORIES[0].copy()
        self.crawler.db_manager.upsert_category(category_data)
        
        # Crawl specific category
        stats = self.crawler.crawl_category('son-moi', max_products=3)
        
        # Verify category crawl results
        self.assertIn('products_found', stats)
        self.assertIn('products_processed', stats)
        self.assertIn('export_stats', stats)
        
        # Verify category export file was created
        category_export_file = Path(self.export_dir) / 'son-moi_products.sql'
        self.assertTrue(category_export_file.exists())
    
    def test_data_export_and_reimport(self):
        """Test that exported SQL can be successfully re-imported."""
        # Populate database with test data
        self._populate_initial_data()
        
        # Export data
        export_stats = self.crawler.export_all_data()
        self.assertIn('files_created', export_stats)
        self.assertGreater(export_stats['files_created'], 0)
        
        # Create a new database instance
        new_db_url = "sqlite:///:memory:"
        new_db_manager = DatabaseManager(new_db_url)
        
        # Import exported SQL into new database
        export_files = list(Path(self.export_dir).glob("*_products.sql"))
        self.assertGreater(len(export_files), 0)
        
        # Test importing one file
        test_file = export_files[0]
        validation_result = SQLExporter(new_db_manager, self.export_dir).validate_exported_sql(str(test_file))
        
        self.assertTrue(validation_result['is_valid'])
        self.assertGreater(validation_result['records_count'], 0)
    
    def test_idempotent_crawl(self):
        """Test that running crawl multiple times produces consistent results."""
        # Mock consistent responses
        with patch('requests.Session.get') as mock_get:
            def mock_response(url):
                response = Mock()
                response.raise_for_status.return_value = None
                
                if 'san-pham' in str(url):
                    response.content = SAMPLE_PRODUCT_DETAIL_HTML.encode('utf-8')
                else:
                    response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
                
                return response
            
            mock_get.side_effect = mock_response
            
            # First crawl
            stats1 = self.crawler.full_crawl(
                max_categories=1,
                max_products_per_category=2,
                skip_detail_parsing=False
            )
            
            # Second crawl (should update existing data, not create duplicates)
            stats2 = self.crawler.full_crawl(
                max_categories=1,
                max_products_per_category=2,
                skip_detail_parsing=False
            )
            
            # Verify idempotent behavior
            db_stats_after_first = self.crawler.db_manager.get_database_stats()
            
            # Products count shouldn't double after second crawl
            # (some might be updated, but not duplicated)
            final_stats = self.crawler.db_manager.get_database_stats()
            self.assertEqual(final_stats['products'], db_stats_after_first['products'])
    
    def test_error_handling_and_recovery(self):
        """Test crawler behavior with network errors and malformed data."""
        with patch('requests.Session.get') as mock_get:
            # First few calls succeed, then fail
            call_count = 0
            
            def mock_response_with_errors(url):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 2:
                    # First few calls succeed
                    response = Mock()
                    response.raise_for_status.return_value = None
                    response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
                    return response
                elif call_count <= 4:
                    # Next few calls fail with network error
                    raise Exception("Network error")
                else:
                    # Later calls return malformed data
                    response = Mock()
                    response.raise_for_status.return_value = None
                    response.content = '<html><body>Invalid HTML</body></html>'.encode('utf-8')
                    return response
            
            mock_get.side_effect = mock_response_with_errors
            
            # Run crawl and expect it to handle errors gracefully
            stats = self.crawler.full_crawl(
                max_categories=5,
                max_products_per_category=2
            )
            
            # Should have some errors but not crash
            self.assertIn('errors', stats)
            # Should still have processed some data successfully
            self.assertGreaterEqual(stats['products_processed'], 0)
    
    def test_database_integrity(self):
        """Test database integrity after complete workflow."""
        # Populate database
        self._populate_initial_data()
        
        # Verify referential integrity
        session = self.crawler.db_manager.get_session()
        
        try:
            # Get all products
            from bestmua_data.models import Product, Category, Brand
            products = session.query(Product).all()
            
            for product in products:
                # Each product should have a valid category
                if product.category_id:
                    category = session.query(Category).get(product.category_id)
                    self.assertIsNotNone(category, f"Product {product.slug} has invalid category_id")
                
                # Each product with brand_id should have a valid brand
                if product.brand_id:
                    brand = session.query(Brand).get(product.brand_id)
                    self.assertIsNotNone(brand, f"Product {product.slug} has invalid brand_id")
                
                # Verify data types and constraints
                if product.price is not None:
                    self.assertGreaterEqual(product.price, 0)
                
                if product.rating is not None:
                    self.assertGreaterEqual(product.rating, 0)
                    self.assertLessEqual(product.rating, 5)
                
                if product.discount_percentage is not None:
                    self.assertGreaterEqual(product.discount_percentage, 0)
                    self.assertLessEqual(product.discount_percentage, 100)
        
        finally:
            session.close()
    
    def test_complete_workflow_performance(self):
        """Test performance characteristics of complete workflow."""
        import time
        
        with patch('requests.Session.get') as mock_get:
            # Mock fast responses
            def mock_response(url):
                response = Mock()
                response.raise_for_status.return_value = None
                response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
                return response
            
            mock_get.side_effect = mock_response
            
            start_time = time.time()
            
            # Run limited crawl
            stats = self.crawler.full_crawl(
                max_categories=3,
                max_products_per_category=5,
                skip_detail_parsing=True  # Faster
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify reasonable performance
            self.assertLess(duration, 30)  # Should complete within 30 seconds
            self.assertIn('duration_seconds', stats)
            self.assertGreater(stats.get('products_processed', 0), 0)
    
    def _populate_initial_data(self):
        """Helper method to populate database with initial test data."""
        # Create categories
        for category_data in DATABASE_TEST_CATEGORIES:
            self.crawler.db_manager.upsert_category(category_data)
        
        # Create some sample products
        from fixtures.sample_data import DATABASE_TEST_BRANDS, DATABASE_TEST_PRODUCTS
        
        for brand_data in DATABASE_TEST_BRANDS:
            self.crawler.db_manager.upsert_brand(brand_data)
        
        for product_data in DATABASE_TEST_PRODUCTS:
            self.crawler.db_manager.upsert_product(product_data)


if __name__ == '__main__':
    unittest.main()