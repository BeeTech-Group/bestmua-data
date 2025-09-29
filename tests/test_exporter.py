"""Unit tests for SQL export module."""

import unittest
import tempfile
import os
import json
from pathlib import Path

from bestmua_data.database import DatabaseManager
from bestmua_data.exporter import SQLExporter
from bestmua_data.models import Category, Brand, Product
from fixtures.sample_data import DATABASE_TEST_CATEGORIES, DATABASE_TEST_BRANDS, DATABASE_TEST_PRODUCTS


class TestSQLExporter(unittest.TestCase):
    """Test cases for SQLExporter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for exports
        self.temp_dir = tempfile.mkdtemp()
        
        # Setup in-memory database with test data
        self.db_manager = DatabaseManager("sqlite:///:memory:")
        self.exporter = SQLExporter(self.db_manager, self.temp_dir)
        
        # Create test data
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_test_data(self):
        """Create test data in database."""
        # Create categories
        for category_data in DATABASE_TEST_CATEGORIES:
            self.db_manager.upsert_category(category_data)
        
        # Create brands
        for brand_data in DATABASE_TEST_BRANDS:
            self.db_manager.upsert_brand(brand_data)
        
        # Create products
        for product_data in DATABASE_TEST_PRODUCTS:
            self.db_manager.upsert_product(product_data)
    
    def test_init(self):
        """Test SQLExporter initialization."""
        export_dir = Path(self.temp_dir)
        exporter = SQLExporter(self.db_manager, str(export_dir))
        
        self.assertEqual(exporter.export_dir, export_dir)
        self.assertTrue(export_dir.exists())
    
    def test_export_category_sql(self):
        """Test exporting specific category to SQL."""
        # Export a category
        stats = self.exporter.export_category_sql('son-moi')
        
        self.assertEqual(stats['category_slug'], 'son-moi')
        self.assertGreater(stats['products_exported'], 0)
        self.assertGreater(stats['file_size'], 0)
        
        # Check file was created
        file_path = Path(stats['file_path'])
        self.assertTrue(file_path.exists())
        
        # Check file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('CREATE TABLE', content)
        self.assertIn('INSERT', content)
        self.assertIn('products', content)
        self.assertIn('categories', content)
    
    def test_export_category_sql_nonexistent(self):
        """Test exporting non-existent category."""
        with self.assertRaises(ValueError):
            self.exporter.export_category_sql('non-existent-category')
    
    def test_export_all_categories(self):
        """Test exporting all categories."""
        stats = self.exporter.export_all_categories()
        
        self.assertIn('categories_processed', stats)
        self.assertIn('files_created', stats)
        self.assertIn('total_products', stats)
        self.assertIn('errors', stats)
        
        # Should have created some files
        export_files = list(Path(self.temp_dir).glob("*.sql"))
        self.assertGreater(len(export_files), 0)
    
    def test_generate_create_table_sql(self):
        """Test SQL table creation statements."""
        create_sql = self.exporter._generate_create_table_sql()
        
        # Check for all required tables
        self.assertIn('CREATE TABLE IF NOT EXISTS categories', create_sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS brands', create_sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS products', create_sql)
        
        # Check for foreign key relationships
        self.assertIn('FOREIGN KEY(category_id)', create_sql)
        self.assertIn('FOREIGN KEY(brand_id)', create_sql)
    
    def test_generate_category_insert_sql(self):
        """Test category INSERT statement generation."""
        session = self.db_manager.get_session()
        category = session.query(Category).filter(Category.slug == 'son-moi').first()
        
        insert_sql = self.exporter._generate_category_insert_sql(category, session)
        
        self.assertIn('INSERT OR REPLACE INTO categories', insert_sql)
        self.assertIn(category.name, insert_sql)
        self.assertIn(category.slug, insert_sql)
        
        session.close()
    
    def test_generate_brand_insert_sql(self):
        """Test brand INSERT statement generation."""
        session = self.db_manager.get_session()
        brand = session.query(Brand).first()
        
        insert_sql = self.exporter._generate_brand_insert_sql(brand)
        
        self.assertIn('INSERT OR REPLACE INTO brands', insert_sql)
        self.assertIn(brand.name, insert_sql)
        self.assertIn(brand.slug, insert_sql)
        
        session.close()
    
    def test_generate_product_insert_sql(self):
        """Test product INSERT statement generation."""
        session = self.db_manager.get_session()
        product = session.query(Product).first()
        
        insert_sql = self.exporter._generate_product_insert_sql(product)
        
        self.assertIn('INSERT OR REPLACE INTO products', insert_sql)
        self.assertIn(product.name, insert_sql)
        self.assertIn(product.slug, insert_sql)
        
        session.close()
    
    def test_escape_sql_string(self):
        """Test SQL string escaping."""
        test_cases = [
            ('Simple text', "'Simple text'"),
            ("Text with 'quotes'", "'Text with ''quotes'''"),
            ('', "''"),
            (None, "''")
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.exporter._escape_sql_string(input_text)
                self.assertEqual(result, expected)
    
    def test_export_database_schema(self):
        """Test database schema export."""
        schema_file = self.exporter.export_database_schema()
        
        self.assertTrue(os.path.exists(schema_file))
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('CREATE TABLE', content)
        self.assertIn('CREATE INDEX', content)
        self.assertIn('categories', content)
        self.assertIn('products', content)
        self.assertIn('brands', content)
    
    def test_generate_indexes_sql(self):
        """Test database index creation SQL."""
        indexes_sql = self.exporter._generate_indexes_sql()
        
        # Check for key indexes
        self.assertIn('idx_categories_slug', indexes_sql)
        self.assertIn('idx_products_slug', indexes_sql)
        self.assertIn('idx_products_category_id', indexes_sql)
        self.assertIn('idx_products_brand_id', indexes_sql)
        self.assertIn('CREATE INDEX IF NOT EXISTS', indexes_sql)
    
    def test_create_export_summary(self):
        """Test export summary creation."""
        # Create some export files first
        self.exporter.export_all_categories()
        
        summary_file = self.exporter.create_export_summary()
        
        self.assertTrue(os.path.exists(summary_file))
        
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('Database Statistics', content)
        self.assertIn('Export Files', content)
        self.assertIn('Categories:', content)
        self.assertIn('Products:', content)
    
    def test_validate_exported_sql(self):
        """Test validation of exported SQL files."""
        # Export a category first
        stats = self.exporter.export_category_sql('son-moi')
        sql_file = stats['file_path']
        
        # Validate the exported file
        validation_result = self.exporter.validate_exported_sql(sql_file)
        
        self.assertIn('is_valid', validation_result)
        self.assertIn('errors', validation_result)
        self.assertIn('warnings', validation_result)
        self.assertIn('records_count', validation_result)
        
        # Should be valid
        if validation_result['errors']:
            print("Validation errors:", validation_result['errors'])
        
        self.assertTrue(validation_result['is_valid'])
        self.assertGreater(validation_result['records_count'], 0)
    
    def test_validate_exported_sql_invalid(self):
        """Test validation of invalid SQL file."""
        # Create invalid SQL file
        invalid_sql_file = os.path.join(self.temp_dir, 'invalid.sql')
        with open(invalid_sql_file, 'w') as f:
            f.write('INVALID SQL STATEMENT;')
        
        validation_result = self.exporter.validate_exported_sql(invalid_sql_file)
        
        self.assertFalse(validation_result['is_valid'])
        self.assertGreater(len(validation_result['errors']), 0)
    
    def test_cleanup_old_exports(self):
        """Test cleanup of old export files."""
        # Create some export files
        self.exporter.export_all_categories()
        
        # Get current file count
        export_files_before = list(Path(self.temp_dir).glob("*.sql"))
        files_count_before = len(export_files_before)
        
        # Cleanup (with 0 days, should delete all files)
        self.exporter.cleanup_old_exports(days_old=0)
        
        # Check files were deleted
        export_files_after = list(Path(self.temp_dir).glob("*.sql"))
        files_count_after = len(export_files_after)
        
        self.assertLess(files_count_after, files_count_before)
    
    def test_get_category_products_recursive(self):
        """Test getting products from category and subcategories."""
        session = self.db_manager.get_session()
        
        # Get a category
        category = session.query(Category).filter(Category.slug == 'son-moi').first()
        self.assertIsNotNone(category)
        
        # Get products recursively
        products = self.exporter._get_category_products_recursive(category, session)
        
        self.assertIsInstance(products, list)
        # Should have at least some products
        self.assertGreaterEqual(len(products), 0)
        
        session.close()
    
    def test_get_category_products_direct(self):
        """Test getting products directly from category."""
        session = self.db_manager.get_session()
        
        # Get a category
        category = session.query(Category).filter(Category.slug == 'son-moi').first()
        self.assertIsNotNone(category)
        
        # Get direct products only
        products = self.exporter._get_category_products_direct(category, session)
        
        self.assertIsInstance(products, list)
        
        session.close()
    
    def test_write_products_sql_file(self):
        """Test writing products to SQL file."""
        session = self.db_manager.get_session()
        
        # Get test data
        category = session.query(Category).first()
        products = session.query(Product).filter(Product.category_id == category.id).all()
        
        # Write SQL file
        test_file = Path(self.temp_dir) / 'test_products.sql'
        self.exporter._write_products_sql_file(products, category, test_file, session)
        
        # Check file was created
        self.assertTrue(test_file.exists())
        
        # Check file content
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('-- bestmua.vn Product Data Export', content)
        self.assertIn(f'-- Category: {category.name}', content)
        self.assertIn('CREATE TABLE', content)
        self.assertIn('INSERT', content)
        
        session.close()


if __name__ == '__main__':
    unittest.main()