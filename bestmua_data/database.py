"""Database operations module for bestmua data."""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, or_

from .models import Category, Brand, Product, CrawlSession, create_database_engine, create_tables, get_session

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations with upsert capabilities."""
    
    def __init__(self, database_url: str = "sqlite:///bestmua_data.db"):
        self.engine = create_database_engine(database_url)
        create_tables(self.engine)
        logger.info(f"Database initialized: {database_url}")
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return get_session(self.engine)
    
    def upsert_category(self, category_data: Dict, session: Optional[Session] = None) -> Tuple[Category, bool]:
        """
        Insert or update a category.
        
        Args:
            category_data: Normalized category data
            session: Database session (optional)
            
        Returns:
            Tuple of (Category object, was_created)
        """
        close_session = session is None
        if session is None:
            session = self.get_session()
        
        try:
            # Check if category exists by slug
            existing_category = session.query(Category).filter(
                Category.slug == category_data['slug']
            ).first()
            
            if existing_category:
                # Update existing category
                for key, value in category_data.items():
                    if key != 'slug' and value:  # Don't update slug, skip empty values
                        setattr(existing_category, key, value)
                
                existing_category.updated_at = datetime.utcnow()
                session.commit()
                logger.debug(f"Updated category: {existing_category.name}")
                return existing_category, False
            
            else:
                # Create new category
                # Handle parent relationship
                parent = None
                if category_data.get('parent_slug'):
                    parent = session.query(Category).filter(
                        Category.slug == category_data['parent_slug']
                    ).first()
                
                category = Category(
                    name=category_data['name'],
                    slug=category_data['slug'],
                    url=category_data['url'],
                    description=category_data.get('description', ''),
                    parent=parent
                )
                
                session.add(category)
                session.commit()
                session.refresh(category)
                logger.debug(f"Created category: {category.name}")
                return category, True
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error upserting category {category_data.get('slug', 'unknown')}: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def upsert_brand(self, brand_data: Dict, session: Optional[Session] = None) -> Tuple[Brand, bool]:
        """
        Insert or update a brand.
        
        Args:
            brand_data: Normalized brand data
            session: Database session (optional)
            
        Returns:
            Tuple of (Brand object, was_created)
        """
        close_session = session is None
        if session is None:
            session = self.get_session()
        
        try:
            # Check if brand exists by slug
            existing_brand = session.query(Brand).filter(
                Brand.slug == brand_data['slug']
            ).first()
            
            if existing_brand:
                # Update existing brand
                for key, value in brand_data.items():
                    if key != 'slug' and value:  # Don't update slug, skip empty values
                        setattr(existing_brand, key, value)
                
                existing_brand.updated_at = datetime.utcnow()
                session.commit()
                logger.debug(f"Updated brand: {existing_brand.name}")
                return existing_brand, False
            
            else:
                # Create new brand
                brand = Brand(
                    name=brand_data['name'],
                    slug=brand_data['slug'],
                    url=brand_data.get('url', ''),
                    description=brand_data.get('description', '')
                )
                
                session.add(brand)
                session.commit()
                session.refresh(brand)
                logger.debug(f"Created brand: {brand.name}")
                return brand, True
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error upserting brand {brand_data.get('slug', 'unknown')}: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def upsert_product(self, product_data: Dict, session: Optional[Session] = None) -> Tuple[Product, bool]:
        """
        Insert or update a product.
        
        Args:
            product_data: Normalized product data
            session: Database session (optional)
            
        Returns:
            Tuple of (Product object, was_created)
        """
        close_session = session is None
        if session is None:
            session = self.get_session()
        
        try:
            # Check if product exists by slug or URL
            existing_product = session.query(Product).filter(
                or_(
                    Product.slug == product_data['slug'],
                    Product.url == product_data['url']
                )
            ).first()
            
            if existing_product:
                # Update existing product
                for key, value in product_data.items():
                    if key not in ['slug', 'category_id', 'brand_id'] and value is not None:
                        setattr(existing_product, key, value)
                
                # Handle category relationship
                if product_data.get('category_name'):
                    category = self._get_or_create_category_by_name(
                        product_data['category_name'], session
                    )
                    if category:
                        existing_product.category_id = category.id
                
                # Handle brand relationship
                if product_data.get('brand_name'):
                    brand = self._get_or_create_brand_by_name(
                        product_data['brand_name'], session
                    )
                    if brand:
                        existing_product.brand_id = brand.id
                
                existing_product.updated_at = datetime.utcnow()
                session.commit()
                logger.debug(f"Updated product: {existing_product.name}")
                return existing_product, False
            
            else:
                # Create new product
                # Get or create category
                category = None
                if product_data.get('category_name'):
                    category = self._get_or_create_category_by_name(
                        product_data['category_name'], session
                    )
                
                # Get or create brand
                brand = None
                if product_data.get('brand_name'):
                    brand = self._get_or_create_brand_by_name(
                        product_data['brand_name'], session
                    )
                
                product = Product(
                    name=product_data['name'],
                    slug=product_data['slug'],
                    url=product_data['url'],
                    description=product_data.get('description', ''),
                    price=product_data.get('price'),
                    original_price=product_data.get('original_price'),
                    discount_percentage=product_data.get('discount_percentage'),
                    sku=product_data.get('sku', ''),
                    availability=product_data.get('availability', 'unknown'),
                    rating=product_data.get('rating'),
                    review_count=product_data.get('review_count', 0),
                    image_url=product_data.get('image_url', ''),
                    images=product_data.get('images', ''),
                    ingredients=product_data.get('ingredients', ''),
                    usage_instructions=product_data.get('usage_instructions', ''),
                    category_id=category.id if category else None,
                    brand_id=brand.id if brand else None,
                    is_featured=product_data.get('is_featured', False),
                    is_bestseller=product_data.get('is_bestseller', False),
                    is_new=product_data.get('is_new', False),
                    is_sale=product_data.get('is_sale', False)
                )
                
                session.add(product)
                session.commit()
                session.refresh(product)
                logger.debug(f"Created product: {product.name}")
                return product, True
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error upserting product {product_data.get('slug', 'unknown')}: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    def _get_or_create_category_by_name(self, category_name: str, session: Session) -> Optional[Category]:
        """Get or create a category by name."""
        if not category_name:
            return None
        
        try:
            # First try to find by exact name
            category = session.query(Category).filter(
                Category.name == category_name
            ).first()
            
            if category:
                return category
            
            # Create category with generated slug
            from .normalizer import DataNormalizer
            normalizer = DataNormalizer()
            
            category_data = {
                'name': category_name,
                'slug': normalizer.normalize_slug(category_name),
                'url': '',
                'description': ''
            }
            
            category, _ = self.upsert_category(category_data, session)
            return category
            
        except Exception as e:
            logger.warning(f"Error getting/creating category '{category_name}': {e}")
            return None
    
    def _get_or_create_brand_by_name(self, brand_name: str, session: Session) -> Optional[Brand]:
        """Get or create a brand by name."""
        if not brand_name:
            return None
        
        try:
            # First try to find by exact name
            brand = session.query(Brand).filter(
                Brand.name == brand_name
            ).first()
            
            if brand:
                return brand
            
            # Create brand with generated slug
            from .normalizer import DataNormalizer
            normalizer = DataNormalizer()
            
            brand_data = {
                'name': brand_name,
                'slug': normalizer.normalize_slug(brand_name),
                'url': '',
                'description': ''
            }
            
            brand, _ = self.upsert_brand(brand_data, session)
            return brand
            
        except Exception as e:
            logger.warning(f"Error getting/creating brand '{brand_name}': {e}")
            return None
    
    def bulk_upsert_products(self, products_data: List[Dict]) -> Dict:
        """
        Bulk upsert multiple products efficiently.
        
        Args:
            products_data: List of normalized product data
            
        Returns:
            Dictionary with operation statistics
        """
        stats = {
            'total': len(products_data),
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        session = self.get_session()
        try:
            for product_data in products_data:
                try:
                    _, was_created = self.upsert_product(product_data, session)
                    if was_created:
                        stats['created'] += 1
                    else:
                        stats['updated'] += 1
                        
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error bulk upserting product {product_data.get('slug', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Bulk upsert completed: {stats}")
            return stats
            
        finally:
            session.close()
    
    def start_crawl_session(self) -> CrawlSession:
        """Start a new crawl session."""
        session = self.get_session()
        try:
            crawl_session = CrawlSession()
            session.add(crawl_session)
            session.commit()
            session.refresh(crawl_session)
            logger.info(f"Started crawl session: {crawl_session.id}")
            return crawl_session
        finally:
            session.close()
    
    def finish_crawl_session(self, crawl_session_id: int, status: str = 'completed', 
                           stats: Optional[Dict] = None, errors: Optional[str] = None):
        """Finish a crawl session with statistics."""
        session = self.get_session()
        try:
            crawl_session = session.query(CrawlSession).get(crawl_session_id)
            if crawl_session:
                crawl_session.finished_at = datetime.utcnow()
                crawl_session.status = status
                
                if stats:
                    crawl_session.categories_found = stats.get('categories_found', 0)
                    crawl_session.products_found = stats.get('products_found', 0)
                    crawl_session.products_created = stats.get('products_created', 0)
                    crawl_session.products_updated = stats.get('products_updated', 0)
                
                if errors:
                    crawl_session.errors = errors
                
                session.commit()
                logger.info(f"Finished crawl session {crawl_session_id} with status: {status}")
            
        except Exception as e:
            logger.error(f"Error finishing crawl session {crawl_session_id}: {e}")
        finally:
            session.close()
    
    def get_categories(self, parent_id: Optional[int] = None) -> List[Category]:
        """Get categories, optionally filtered by parent."""
        session = self.get_session()
        try:
            query = session.query(Category)
            if parent_id is not None:
                query = query.filter(Category.parent_id == parent_id)
            
            return query.all()
        finally:
            session.close()
    
    def get_products_by_category(self, category_id: int, limit: Optional[int] = None) -> List[Product]:
        """Get products in a specific category."""
        session = self.get_session()
        try:
            query = session.query(Product).filter(Product.category_id == category_id)
            if limit:
                query = query.limit(limit)
            
            return query.all()
        finally:
            session.close()
    
    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        session = self.get_session()
        try:
            stats = {
                'categories': session.query(Category).count(),
                'brands': session.query(Brand).count(),
                'products': session.query(Product).count(),
                'crawl_sessions': session.query(CrawlSession).count()
            }
            
            # Additional product stats
            stats['products_with_images'] = session.query(Product).filter(
                Product.image_url != ''
            ).count()
            
            stats['products_with_prices'] = session.query(Product).filter(
                Product.price.isnot(None)
            ).count()
            
            stats['products_with_ratings'] = session.query(Product).filter(
                Product.rating.isnot(None)
            ).count()
            
            return stats
            
        finally:
            session.close()
    
    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up old crawl sessions."""
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            deleted_count = session.query(CrawlSession).filter(
                CrawlSession.started_at < cutoff_date
            ).delete()
            
            session.commit()
            logger.info(f"Cleaned up {deleted_count} old crawl sessions")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up old sessions: {e}")
        finally:
            session.close()
    
    def check_product_exists(self, slug: str) -> bool:
        """Check if a product exists by slug."""
        session = self.get_session()
        try:
            exists = session.query(Product.id).filter(Product.slug == slug).first() is not None
            return exists
        finally:
            session.close()
    
    def get_products_modified_since(self, since_date: datetime) -> List[Product]:
        """Get products modified since a specific date (for incremental crawls)."""
        session = self.get_session()
        try:
            return session.query(Product).filter(
                Product.updated_at >= since_date
            ).all()
        finally:
            session.close()
    
    def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug."""
        session = self.get_session()
        try:
            return session.query(Category).filter(Category.slug == slug).first()
        finally:
            session.close()
    
    def get_brand_by_slug(self, slug: str) -> Optional[Brand]:
        """Get brand by slug."""
        session = self.get_session()
        try:
            return session.query(Brand).filter(Brand.slug == slug).first()
        finally:
            session.close()