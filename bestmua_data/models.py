"""Database models for bestmua product data."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Category(Base):
    """Product category model."""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(200), nullable=False, unique=True)
    url = Column(String(500), nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("Category", remote_side=[id])
    children = relationship("Category")
    products = relationship("Product", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Brand(Base):
    """Product brand model."""
    __tablename__ = 'brands'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(200), nullable=False, unique=True)
    url = Column(String(500))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = relationship("Product", back_populates="brand")
    
    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Product(Base):
    """Product model."""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, unique=True)
    url = Column(String(500), nullable=False, unique=True)
    description = Column(Text)
    price = Column(Float)
    original_price = Column(Float)
    discount_percentage = Column(Float)
    sku = Column(String(100))
    availability = Column(String(50))
    rating = Column(Float)
    review_count = Column(Integer, default=0)
    image_url = Column(String(500))
    images = Column(Text)  # JSON string of image URLs
    ingredients = Column(Text)
    usage_instructions = Column(Text)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=True)
    is_featured = Column(Boolean, default=False)
    is_bestseller = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)
    is_sale = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class CrawlSession(Base):
    """Crawl session tracking model."""
    __tablename__ = 'crawl_sessions'
    
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String(20), default='running')  # running, completed, failed
    categories_found = Column(Integer, default=0)
    products_found = Column(Integer, default=0)
    products_updated = Column(Integer, default=0)
    products_created = Column(Integer, default=0)
    errors = Column(Text)
    
    def __repr__(self):
        return f"<CrawlSession(id={self.id}, started_at='{self.started_at}', status='{self.status}')>"


def create_database_engine(database_url="sqlite:///bestmua_data.db"):
    """Create and return database engine."""
    engine = create_engine(database_url, echo=False)
    return engine


def create_tables(engine):
    """Create all tables."""
    Base.metadata.create_all(engine)


def get_session(engine):
    """Get database session."""
    Session = sessionmaker(bind=engine)
    return Session()