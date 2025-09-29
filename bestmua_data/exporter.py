"""SQL export module for bestmua data."""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import Category, Brand, Product, CrawlSession
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLExporter:
    """Exports database data to SQL dump files."""
    
    def __init__(self, db_manager: DatabaseManager, export_dir: str = "exports"):
        self.db_manager = db_manager
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        logger.info(f"SQL Exporter initialized with export directory: {self.export_dir}")
    
    def export_all_categories(self) -> Dict:
        """
        Export all categories to per-category SQL files.
        
        Returns:
            Dictionary with export statistics
        """
        stats = {
            'categories_processed': 0,
            'files_created': 0,
            'total_products': 0,
            'errors': []
        }
        
        session = self.db_manager.get_session()
        try:
            # Get all root categories (no parent)
            root_categories = session.query(Category).filter(
                Category.parent_id.is_(None)
            ).all()
            
            for category in root_categories:
                try:
                    category_stats = self._export_category_with_subcategories(category, session)
                    stats['categories_processed'] += category_stats['categories_processed']
                    stats['files_created'] += category_stats['files_created']
                    stats['total_products'] += category_stats['products_exported']
                    
                except Exception as e:
                    error_msg = f"Error exporting category {category.slug}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            logger.info(f"Export completed: {stats}")
            return stats
            
        finally:
            session.close()
    
    def export_category_sql(self, category_slug: str) -> Dict:
        """
        Export a specific category to SQL file.
        
        Args:
            category_slug: Slug of the category to export
            
        Returns:
            Export statistics
        """
        stats = {
            'category_slug': category_slug,
            'products_exported': 0,
            'file_path': '',
            'file_size': 0
        }
        
        session = self.db_manager.get_session()
        try:
            category = session.query(Category).filter(
                Category.slug == category_slug
            ).first()
            
            if not category:
                raise ValueError(f"Category '{category_slug}' not found")
            
            # Get all products in this category and its subcategories
            products = self._get_category_products_recursive(category, session)
            
            if not products:
                logger.warning(f"No products found for category: {category_slug}")
                return stats
            
            # Generate SQL file
            file_path = self.export_dir / f"{category_slug}_products.sql"
            self._write_products_sql_file(products, category, file_path, session)
            
            stats['products_exported'] = len(products)
            stats['file_path'] = str(file_path)
            stats['file_size'] = file_path.stat().st_size if file_path.exists() else 0
            
            logger.info(f"Exported {len(products)} products for category '{category_slug}' to {file_path}")
            return stats
            
        finally:
            session.close()
    
    def _export_category_with_subcategories(self, category: Category, session: Session) -> Dict:
        """Export a category and all its subcategories."""
        stats = {
            'categories_processed': 0,
            'files_created': 0,
            'products_exported': 0
        }
        
        try:
            # Export current category
            products = self._get_category_products_direct(category, session)
            
            if products:
                file_path = self.export_dir / f"{category.slug}_products.sql"
                self._write_products_sql_file(products, category, file_path, session)
                
                stats['files_created'] += 1
                stats['products_exported'] += len(products)
                logger.debug(f"Exported {len(products)} products for category: {category.slug}")
            
            stats['categories_processed'] += 1
            
            # Export subcategories recursively
            for subcategory in category.children:
                sub_stats = self._export_category_with_subcategories(subcategory, session)
                stats['categories_processed'] += sub_stats['categories_processed']
                stats['files_created'] += sub_stats['files_created']
                stats['products_exported'] += sub_stats['products_exported']
            
            return stats
            
        except Exception as e:
            logger.error(f"Error exporting category {category.slug}: {e}")
            raise
    
    def _get_category_products_recursive(self, category: Category, session: Session) -> List[Product]:
        """Get all products in category and its subcategories recursively."""
        products = []
        
        # Get direct products
        direct_products = session.query(Product).filter(
            Product.category_id == category.id
        ).all()
        products.extend(direct_products)
        
        # Get products from subcategories
        for subcategory in category.children:
            sub_products = self._get_category_products_recursive(subcategory, session)
            products.extend(sub_products)
        
        return products
    
    def _get_category_products_direct(self, category: Category, session: Session) -> List[Product]:
        """Get products directly in this category (not subcategories)."""
        return session.query(Product).filter(
            Product.category_id == category.id
        ).all()
    
    def _write_products_sql_file(self, products: List[Product], category: Category, 
                                file_path: Path, session: Session):
        """Write products to SQL file with complete schema."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"-- bestmua.vn Product Data Export\n")
                f.write(f"-- Category: {category.name} ({category.slug})\n")
                f.write(f"-- Exported at: {datetime.utcnow().isoformat()}\n")
                f.write(f"-- Total products: {len(products)}\n\n")
                
                # Write schema creation
                f.write("-- Create tables if they don't exist\n")
                f.write(self._generate_create_table_sql())
                f.write("\n\n")
                
                # Write category data
                f.write("-- Insert category data\n")
                f.write(self._generate_category_insert_sql(category, session))
                f.write("\n\n")
                
                # Write brand data for products
                brands = set()
                for product in products:
                    if product.brand:
                        brands.add(product.brand)
                
                if brands:
                    f.write("-- Insert brand data\n")
                    for brand in brands:
                        f.write(self._generate_brand_insert_sql(brand))
                    f.write("\n\n")
                
                # Write product data
                f.write("-- Insert product data\n")
                for product in products:
                    f.write(self._generate_product_insert_sql(product))
                
                f.write("\n-- End of export\n")
            
            logger.debug(f"Created SQL file: {file_path}")
            
        except Exception as e:
            logger.error(f"Error writing SQL file {file_path}: {e}")
            raise
    
    def _generate_create_table_sql(self) -> str:
        """Generate CREATE TABLE statements."""
        return """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL UNIQUE,
    url VARCHAR(500) NOT NULL,
    parent_id INTEGER,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(parent_id) REFERENCES categories (id)
);

CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL UNIQUE,
    slug VARCHAR(200) NOT NULL UNIQUE,
    url VARCHAR(500),
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(500) NOT NULL,
    slug VARCHAR(500) NOT NULL UNIQUE,
    url VARCHAR(500) NOT NULL UNIQUE,
    description TEXT,
    price REAL,
    original_price REAL,
    discount_percentage REAL,
    sku VARCHAR(100),
    availability VARCHAR(50),
    rating REAL,
    review_count INTEGER DEFAULT 0,
    image_url VARCHAR(500),
    images TEXT,
    ingredients TEXT,
    usage_instructions TEXT,
    category_id INTEGER NOT NULL,
    brand_id INTEGER,
    is_featured BOOLEAN DEFAULT 0,
    is_bestseller BOOLEAN DEFAULT 0,
    is_new BOOLEAN DEFAULT 0,
    is_sale BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories (id),
    FOREIGN KEY(brand_id) REFERENCES brands (id)
);
"""
    
    def _generate_category_insert_sql(self, category: Category, session: Session) -> str:
        """Generate INSERT statement for category and its parents."""
        sql_statements = []
        
        # Collect all parent categories
        categories_to_insert = []
        current = category
        while current:
            categories_to_insert.insert(0, current)  # Insert at beginning to maintain order
            current = current.parent
        
        # Generate INSERT statements
        for cat in categories_to_insert:
            parent_id = cat.parent.id if cat.parent else 'NULL'
            
            sql = f"""INSERT OR REPLACE INTO categories (id, name, slug, url, parent_id, description, created_at, updated_at) VALUES (
    {cat.id},
    {self._escape_sql_string(cat.name)},
    {self._escape_sql_string(cat.slug)},
    {self._escape_sql_string(cat.url)},
    {parent_id},
    {self._escape_sql_string(cat.description or '')},
    '{cat.created_at.isoformat()}',
    '{cat.updated_at.isoformat()}'
);\n"""
            sql_statements.append(sql)
        
        return ''.join(sql_statements)
    
    def _generate_brand_insert_sql(self, brand: Brand) -> str:
        """Generate INSERT statement for brand."""
        return f"""INSERT OR REPLACE INTO brands (id, name, slug, url, description, created_at, updated_at) VALUES (
    {brand.id},
    {self._escape_sql_string(brand.name)},
    {self._escape_sql_string(brand.slug)},
    {self._escape_sql_string(brand.url or '')},
    {self._escape_sql_string(brand.description or '')},
    '{brand.created_at.isoformat()}',
    '{brand.updated_at.isoformat()}'
);
"""
    
    def _generate_product_insert_sql(self, product: Product) -> str:
        """Generate INSERT statement for product."""
        brand_id = product.brand_id if product.brand_id else 'NULL'
        price = product.price if product.price is not None else 'NULL'
        original_price = product.original_price if product.original_price is not None else 'NULL'
        discount_percentage = product.discount_percentage if product.discount_percentage is not None else 'NULL'
        rating = product.rating if product.rating is not None else 'NULL'
        
        return f"""INSERT OR REPLACE INTO products (id, name, slug, url, description, price, original_price, discount_percentage, sku, availability, rating, review_count, image_url, images, ingredients, usage_instructions, category_id, brand_id, is_featured, is_bestseller, is_new, is_sale, created_at, updated_at) VALUES (
    {product.id},
    {self._escape_sql_string(product.name)},
    {self._escape_sql_string(product.slug)},
    {self._escape_sql_string(product.url)},
    {self._escape_sql_string(product.description or '')},
    {price},
    {original_price},
    {discount_percentage},
    {self._escape_sql_string(product.sku or '')},
    {self._escape_sql_string(product.availability)},
    {rating},
    {product.review_count},
    {self._escape_sql_string(product.image_url or '')},
    {self._escape_sql_string(product.images or '')},
    {self._escape_sql_string(product.ingredients or '')},
    {self._escape_sql_string(product.usage_instructions or '')},
    {product.category_id},
    {brand_id},
    {1 if product.is_featured else 0},
    {1 if product.is_bestseller else 0},
    {1 if product.is_new else 0},
    {1 if product.is_sale else 0},
    '{product.created_at.isoformat()}',
    '{product.updated_at.isoformat()}'
);
"""
    
    def _escape_sql_string(self, value: str) -> str:
        """Escape SQL string value."""
        if not value:
            return "''"
        
        # Escape single quotes by doubling them
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    
    def export_database_schema(self) -> str:
        """Export complete database schema to SQL file."""
        schema_file = self.export_dir / "schema.sql"
        
        try:
            with open(schema_file, 'w', encoding='utf-8') as f:
                f.write("-- bestmua.vn Database Schema\n")
                f.write(f"-- Generated at: {datetime.utcnow().isoformat()}\n\n")
                f.write(self._generate_create_table_sql())
                f.write("\n-- Create indexes for performance\n")
                f.write(self._generate_indexes_sql())
            
            logger.info(f"Database schema exported to: {schema_file}")
            return str(schema_file)
            
        except Exception as e:
            logger.error(f"Error exporting schema: {e}")
            raise
    
    def _generate_indexes_sql(self) -> str:
        """Generate CREATE INDEX statements."""
        return """
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);
CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_brands_slug ON brands(slug);
CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_brand_id ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating);
CREATE INDEX IF NOT EXISTS idx_products_availability ON products(availability);
CREATE INDEX IF NOT EXISTS idx_products_flags ON products(is_featured, is_bestseller, is_new, is_sale);
"""
    
    def create_export_summary(self) -> str:
        """Create a summary file of all exports."""
        summary_file = self.export_dir / "export_summary.txt"
        
        try:
            # Get database stats
            stats = self.db_manager.get_database_stats()
            
            # List all export files
            export_files = list(self.export_dir.glob("*.sql"))
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("bestmua.vn Data Export Summary\n")
                f.write("=" * 40 + "\n\n")
                f.write(f"Export Date: {datetime.utcnow().isoformat()}\n")
                f.write(f"Export Directory: {self.export_dir}\n\n")
                
                f.write("Database Statistics:\n")
                f.write(f"- Categories: {stats['categories']}\n")
                f.write(f"- Brands: {stats['brands']}\n")
                f.write(f"- Products: {stats['products']}\n")
                f.write(f"- Products with images: {stats['products_with_images']}\n")
                f.write(f"- Products with prices: {stats['products_with_prices']}\n")
                f.write(f"- Products with ratings: {stats['products_with_ratings']}\n\n")
                
                f.write("Export Files:\n")
                for export_file in sorted(export_files):
                    file_size = export_file.stat().st_size
                    f.write(f"- {export_file.name} ({file_size:,} bytes)\n")
                
                if not export_files:
                    f.write("- No export files found\n")
            
            logger.info(f"Export summary created: {summary_file}")
            return str(summary_file)
            
        except Exception as e:
            logger.error(f"Error creating export summary: {e}")
            raise
    
    def validate_exported_sql(self, sql_file_path: str) -> Dict:
        """
        Validate an exported SQL file by attempting to re-import it.
        
        Args:
            sql_file_path: Path to SQL file to validate
            
        Returns:
            Validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'records_count': 0
        }
        
        try:
            # Create a temporary in-memory database
            from sqlalchemy import create_engine
            temp_engine = create_engine("sqlite:///:memory:")
            
            # Read and execute SQL file
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            with temp_engine.connect() as connection:
                # Execute the SQL statements
                statements = sql_content.split(';')
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            connection.execute(text(statement))
                        except Exception as e:
                            validation_result['errors'].append(f"SQL Error: {e}")
                            validation_result['is_valid'] = False
                
                # Count records if successful
                if validation_result['is_valid']:
                    try:
                        result = connection.execute(text("SELECT COUNT(*) FROM products"))
                        validation_result['records_count'] = result.scalar()
                    except Exception:
                        validation_result['warnings'].append("Could not count records")
            
            logger.info(f"SQL validation completed for {sql_file_path}: {validation_result}")
            return validation_result
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {e}")
            logger.error(f"Error validating SQL file {sql_file_path}: {e}")
            return validation_result
    
    def cleanup_old_exports(self, days_old: int = 7):
        """Clean up old export files."""
        try:
            from datetime import timedelta
            import time
            
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            deleted_count = 0
            
            for export_file in self.export_dir.glob("*.sql"):
                if export_file.stat().st_mtime < cutoff_time:
                    export_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old export file: {export_file}")
            
            logger.info(f"Cleaned up {deleted_count} old export files")
            
        except Exception as e:
            logger.error(f"Error cleaning up old exports: {e}")