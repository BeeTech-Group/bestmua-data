"""Unit tests for database operations module."""

import unittest
import tempfile
import os
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bestmua_data.database import DatabaseManager
from bestmua_data.models import Category, Brand, Product, CrawlSession, Base
from fixtures.sample_data import DATABASE_TEST_CATEGORIES, DATABASE_TEST_BRANDS, DATABASE_TEST_PRODUCTS


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class."""
    
    def setUp(self):
        """Set up test fixtures with in-memory SQLite database."""
        # Use in-memory SQLite for testing
        self.test_db_url = "sqlite:///:memory:"
        self.db_manager = DatabaseManager(self.test_db_url)
    
    def test_init(self):
        """Test DatabaseManager initialization."""
        self.assertIsNotNone(self.db_manager.engine)
        
        # Test with custom database URL
        custom_db_manager = DatabaseManager("sqlite:///test.db")
        self.assertIsNotNone(custom_db_manager.engine)
    
    def test_get_session(self):
        """Test database session creation."""
        session = self.db_manager.get_session()
        self.assertIsNotNone(session)
        session.close()
    
    def test_upsert_category_create(self):
        """Test category creation via upsert."""
        category_data = DATABASE_TEST_CATEGORIES[0].copy()
        
        category, was_created = self.db_manager.upsert_category(category_data)
        
        self.assertTrue(was_created)
        self.assertIsNotNone(category.id)
        self.assertEqual(category.name, category_data['name'])
        self.assertEqual(category.slug, category_data['slug'])
        self.assertEqual(category.url, category_data['url'])
        self.assertIsNotNone(category.created_at)
    
    def test_upsert_category_update(self):
        """Test category update via upsert."""
        category_data = DATABASE_TEST_CATEGORIES[0].copy()
        
        # Create category first
        category, was_created = self.db_manager.upsert_category(category_data)
        self.assertTrue(was_created)
        original_updated_at = category.updated_at
        
        # Update category
        category_data['description'] = 'Updated description'
        updated_category, was_created = self.db_manager.upsert_category(category_data)
        
        self.assertFalse(was_created)
        self.assertEqual(updated_category.id, category.id)
        self.assertEqual(updated_category.description, 'Updated description')
        self.assertGreater(updated_category.updated_at, original_updated_at)
    
    def test_upsert_category_with_parent(self):
        """Test category creation with parent relationship."""
        # Create parent category first
        parent_data = DATABASE_TEST_CATEGORIES[0].copy()
        parent_category, _ = self.db_manager.upsert_category(parent_data)
        
        # Create child category
        child_data = DATABASE_TEST_CATEGORIES[1].copy()
        child_category, was_created = self.db_manager.upsert_category(child_data)
        
        self.assertTrue(was_created)
        self.assertEqual(child_category.parent_id, parent_category.id)
        self.assertEqual(child_category.parent, parent_category)
    
    def test_upsert_brand_create(self):
        """Test brand creation via upsert."""
        brand_data = DATABASE_TEST_BRANDS[0].copy()
        
        brand, was_created = self.db_manager.upsert_brand(brand_data)
        
        self.assertTrue(was_created)
        self.assertIsNotNone(brand.id)
        self.assertEqual(brand.name, brand_data['name'])
        self.assertEqual(brand.slug, brand_data['slug'])
    
    def test_upsert_brand_update(self):
        """Test brand update via upsert."""
        brand_data = DATABASE_TEST_BRANDS[0].copy()
        
        # Create brand first
        brand, was_created = self.db_manager.upsert_brand(brand_data)
        self.assertTrue(was_created)
        
        # Update brand
        brand_data['description'] = 'Updated brand description'
        updated_brand, was_created = self.db_manager.upsert_brand(brand_data)
        
        self.assertFalse(was_created)
        self.assertEqual(updated_brand.id, brand.id)
        self.assertEqual(updated_brand.description, 'Updated brand description')
    
    def test_upsert_product_create(self):
        """Test product creation via upsert."""
        # Create category and brand first
        category_data = {'name': 'Test Category', 'slug': 'test-category', 'url': '/test'}
        brand_data = {'name': 'Test Brand', 'slug': 'test-brand', 'url': '/brand/test'}
        
        category, _ = self.db_manager.upsert_category(category_data)
        brand, _ = self.db_manager.upsert_brand(brand_data)
        
        # Create product
        product_data = DATABASE_TEST_PRODUCTS[0].copy()
        product_data['category_name'] = 'Test Category'
        product_data['brand_name'] = 'Test Brand'
        
        product, was_created = self.db_manager.upsert_product(product_data)
        
        self.assertTrue(was_created)
        self.assertIsNotNone(product.id)
        self.assertEqual(product.name, product_data['name'])
        self.assertEqual(product.category_id, category.id)
        self.assertEqual(product.brand_id, brand.id)
    
    def test_upsert_product_update(self):
        """Test product update via upsert."""
        # Setup category and brand
        category_data = {'name': 'Test Category', 'slug': 'test-category', 'url': '/test'}
        brand_data = {'name': 'Test Brand', 'slug': 'test-brand', 'url': '/brand/test'}
        
        self.db_manager.upsert_category(category_data)
        self.db_manager.upsert_brand(brand_data)
        
        # Create product
        product_data = DATABASE_TEST_PRODUCTS[0].copy()
        product_data['category_name'] = 'Test Category'
        product_data['brand_name'] = 'Test Brand'
        
        product, was_created = self.db_manager.upsert_product(product_data)
        self.assertTrue(was_created)
        
        # Update product
        product_data['price'] = 350000.0
        product_data['description'] = 'Updated description'
        
        updated_product, was_created = self.db_manager.upsert_product(product_data)
        
        self.assertFalse(was_created)
        self.assertEqual(updated_product.id, product.id)
        self.assertEqual(updated_product.price, 350000.0)
        self.assertEqual(updated_product.description, 'Updated description')
    
    def test_get_or_create_category_by_name(self):
        """Test getting or creating category by name."""
        session = self.db_manager.get_session()
        
        # Create new category
        category_name = "New Category"
        category = self.db_manager._get_or_create_category_by_name(category_name, session)
        
        self.assertIsNotNone(category)
        self.assertEqual(category.name, category_name)
        self.assertEqual(category.slug, 'new-category')
        
        # Get existing category
        existing_category = self.db_manager._get_or_create_category_by_name(category_name, session)
        
        self.assertEqual(existing_category.id, category.id)
        
        session.close()
    
    def test_get_or_create_brand_by_name(self):
        """Test getting or creating brand by name."""
        session = self.db_manager.get_session()
        
        # Create new brand
        brand_name = "New Brand"
        brand = self.db_manager._get_or_create_brand_by_name(brand_name, session)
        
        self.assertIsNotNone(brand)
        self.assertEqual(brand.name, brand_name)
        self.assertEqual(brand.slug, 'new-brand')
        
        # Get existing brand
        existing_brand = self.db_manager._get_or_create_brand_by_name(brand_name, session)
        
        self.assertEqual(existing_brand.id, brand.id)
        
        session.close()
    
    def test_bulk_upsert_products(self):
        """Test bulk product upsert operation."""
        # Setup categories and brands
        for category_data in DATABASE_TEST_CATEGORIES:
            self.db_manager.upsert_category(category_data)
        
        for brand_data in DATABASE_TEST_BRANDS:
            self.db_manager.upsert_brand(brand_data)
        
        # Prepare products data
        products_data = []
        for product_data in DATABASE_TEST_PRODUCTS:
            product_copy = product_data.copy()
            products_data.append(product_copy)
        
        # Bulk upsert
        stats = self.db_manager.bulk_upsert_products(products_data)
        
        self.assertEqual(stats['total'], len(products_data))
        self.assertEqual(stats['created'], len(products_data))
        self.assertEqual(stats['updated'], 0)
        self.assertEqual(stats['errors'], 0)
    
    def test_start_and_finish_crawl_session(self):
        """Test crawl session management."""
        # Start crawl session
        crawl_session = self.db_manager.start_crawl_session()
        
        self.assertIsNotNone(crawl_session.id)
        self.assertEqual(crawl_session.status, 'running')
        self.assertIsNotNone(crawl_session.started_at)
        self.assertIsNone(crawl_session.finished_at)
        
        # Finish crawl session
        stats = {
            'categories_found': 10,
            'products_found': 100,
            'products_created': 80,
            'products_updated': 20
        }
        
        self.db_manager.finish_crawl_session(
            crawl_session.id,
            status='completed',
            stats=stats,
            errors='Some error messages'
        )
        
        # Verify session was updated
        session = self.db_manager.get_session()
        updated_session = session.query(CrawlSession).get(crawl_session.id)
        
        self.assertEqual(updated_session.status, 'completed')
        self.assertIsNotNone(updated_session.finished_at)
        self.assertEqual(updated_session.categories_found, 10)
        self.assertEqual(updated_session.products_found, 100)
        self.assertEqual(updated_session.products_created, 80)
        self.assertEqual(updated_session.products_updated, 20)
        self.assertEqual(updated_session.errors, 'Some error messages')
        
        session.close()
    
    def test_get_categories(self):
        """Test getting categories."""
        # Create test categories
        for category_data in DATABASE_TEST_CATEGORIES:
            self.db_manager.upsert_category(category_data)
        
        # Get all categories
        all_categories = self.db_manager.get_categories()
        
        self.assertGreaterEqual(len(all_categories), len(DATABASE_TEST_CATEGORIES))
        
        # Get root categories (no parent)
        root_categories = self.db_manager.get_categories(parent_id=None)
        
        # Should have at least one root category
        self.assertGreater(len(root_categories), 0)
    
    def test_get_products_by_category(self):
        """Test getting products by category."""
        # Setup test data
        category_data = DATABASE_TEST_CATEGORIES[0].copy()
        category, _ = self.db_manager.upsert_category(category_data)
        
        product_data = DATABASE_TEST_PRODUCTS[0].copy()
        product_data['category_name'] = category.name
        self.db_manager.upsert_product(product_data)
        
        # Get products by category
        products = self.db_manager.get_products_by_category(category.id)
        
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].category_id, category.id)
        
        # Test with limit
        products_limited = self.db_manager.get_products_by_category(category.id, limit=1)
        
        self.assertEqual(len(products_limited), 1)
    
    def test_get_database_stats(self):
        """Test database statistics retrieval."""
        # Create some test data
        category_data = DATABASE_TEST_CATEGORIES[0].copy()
        category, _ = self.db_manager.upsert_category(category_data)
        
        brand_data = DATABASE_TEST_BRANDS[0].copy()
        brand, _ = self.db_manager.upsert_brand(brand_data)
        
        product_data = DATABASE_TEST_PRODUCTS[0].copy()
        product_data['category_name'] = category.name
        product_data['brand_name'] = brand.name
        self.db_manager.upsert_product(product_data)
        
        # Get stats
        stats = self.db_manager.get_database_stats()
        
        self.assertIn('categories', stats)
        self.assertIn('brands', stats)
        self.assertIn('products', stats)
        self.assertIn('products_with_images', stats)
        self.assertIn('products_with_prices', stats)
        self.assertIn('products_with_ratings', stats)
        
        self.assertEqual(stats['categories'], 1)
        self.assertEqual(stats['brands'], 1)
        self.assertEqual(stats['products'], 1)
    
    def test_check_product_exists(self):
        """Test product existence check."""
        # Product doesn't exist initially
        exists = self.db_manager.check_product_exists('non-existent-product')
        self.assertFalse(exists)
        
        # Create product
        product_data = DATABASE_TEST_PRODUCTS[0].copy()
        product, _ = self.db_manager.upsert_product(product_data)
        
        # Product should exist now
        exists = self.db_manager.check_product_exists(product.slug)
        self.assertTrue(exists)
    
    def test_get_products_modified_since(self):
        """Test getting products modified since a date."""
        # Create product
        product_data = DATABASE_TEST_PRODUCTS[0].copy()
        product, _ = self.db_manager.upsert_product(product_data)
        
        # Get products modified since yesterday
        yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_products = self.db_manager.get_products_modified_since(yesterday)
        
        self.assertGreaterEqual(len(recent_products), 1)
        self.assertIn(product, recent_products)
    
    def test_get_category_by_slug(self):
        """Test getting category by slug."""
        # Category doesn't exist initially
        category = self.db_manager.get_category_by_slug('non-existent')
        self.assertIsNone(category)
        
        # Create category
        category_data = DATABASE_TEST_CATEGORIES[0].copy()
        created_category, _ = self.db_manager.upsert_category(category_data)
        
        # Get category by slug
        found_category = self.db_manager.get_category_by_slug(created_category.slug)
        self.assertIsNotNone(found_category)
        self.assertEqual(found_category.id, created_category.id)
    
    def test_get_brand_by_slug(self):
        """Test getting brand by slug."""
        # Brand doesn't exist initially
        brand = self.db_manager.get_brand_by_slug('non-existent')
        self.assertIsNone(brand)
        
        # Create brand
        brand_data = DATABASE_TEST_BRANDS[0].copy()
        created_brand, _ = self.db_manager.upsert_brand(brand_data)
        
        # Get brand by slug
        found_brand = self.db_manager.get_brand_by_slug(created_brand.slug)
        self.assertIsNotNone(found_brand)
        self.assertEqual(found_brand.id, created_brand.id)
    
    def test_cleanup_old_sessions(self):
        """Test cleanup of old crawl sessions."""
        # Create a crawl session
        crawl_session = self.db_manager.start_crawl_session()
        
        # Manually set an old date
        session = self.db_manager.get_session()
        old_session = session.query(CrawlSession).get(crawl_session.id)
        old_session.started_at = datetime(2020, 1, 1)  # Very old date
        session.commit()
        session.close()
        
        # Cleanup old sessions
        self.db_manager.cleanup_old_sessions(days_old=30)
        
        # Session should be deleted
        session = self.db_manager.get_session()
        deleted_session = session.query(CrawlSession).get(crawl_session.id)
        self.assertIsNone(deleted_session)
        session.close()


if __name__ == '__main__':
    unittest.main()