"""Data normalization module for bestmua product data."""

import re
import json
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalizes raw scraped data into consistent format."""
    
    def __init__(self):
        self.vietnamese_chars_map = self._build_vietnamese_chars_map()
    
    def normalize_product(self, raw_product: Dict) -> Dict:
        """
        Normalize a product dictionary.
        
        Args:
            raw_product: Raw product data from scrapers
            
        Returns:
            Normalized product data
        """
        try:
            normalized = {}
            
            # Basic information
            normalized['name'] = self.normalize_text(raw_product.get('name', ''))
            normalized['slug'] = self.normalize_slug(raw_product.get('slug', ''))
            normalized['url'] = self.normalize_url(raw_product.get('url', ''))
            normalized['description'] = self.normalize_text(raw_product.get('description', ''))
            
            # Price information
            normalized['price'] = self.normalize_price(raw_product.get('price'))
            normalized['original_price'] = self.normalize_price(raw_product.get('original_price'))
            normalized['discount_percentage'] = self.normalize_percentage(raw_product.get('discount_percentage'))
            
            # Product identification
            normalized['sku'] = self.normalize_sku(raw_product.get('sku', ''))
            
            # Availability
            normalized['availability'] = self.normalize_availability(raw_product.get('availability', 'unknown'))
            
            # Rating and reviews
            normalized['rating'] = self.normalize_rating(raw_product.get('rating'))
            normalized['review_count'] = self.normalize_integer(raw_product.get('review_count', 0))
            
            # Images
            normalized['image_url'] = self.normalize_url(raw_product.get('image_url', ''))
            normalized['images'] = self.normalize_images(raw_product.get('images'))
            
            # Additional information
            normalized['ingredients'] = self.normalize_text(raw_product.get('ingredients', ''))
            normalized['usage_instructions'] = self.normalize_text(raw_product.get('usage_instructions', ''))
            
            # Brand information
            normalized['brand_name'] = self.normalize_text(raw_product.get('brand_name', ''))
            
            # Boolean flags
            normalized['is_featured'] = self.normalize_boolean(raw_product.get('is_featured', False))
            normalized['is_bestseller'] = self.normalize_boolean(raw_product.get('is_bestseller', False))
            normalized['is_new'] = self.normalize_boolean(raw_product.get('is_new', False))
            normalized['is_sale'] = self.normalize_boolean(raw_product.get('is_sale', False))
            
            # Category information (for reference, will be resolved later)
            normalized['category_name'] = self.normalize_text(raw_product.get('category_name', ''))
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing product: {e}")
            logger.error(f"Raw product data: {raw_product}")
            return {}
    
    def normalize_category(self, raw_category: Dict) -> Dict:
        """
        Normalize a category dictionary.
        
        Args:
            raw_category: Raw category data from scraper
            
        Returns:
            Normalized category data
        """
        try:
            normalized = {}
            
            normalized['name'] = self.normalize_text(raw_category.get('name', ''))
            normalized['slug'] = self.normalize_slug(raw_category.get('slug', ''))
            normalized['url'] = self.normalize_url(raw_category.get('url', ''))
            normalized['description'] = self.normalize_text(raw_category.get('description', ''))
            
            # Parent category information
            normalized['parent_slug'] = self.normalize_slug(raw_category.get('parent_slug', ''))
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing category: {e}")
            return {}
    
    def normalize_brand(self, raw_brand: Dict) -> Dict:
        """
        Normalize a brand dictionary.
        
        Args:
            raw_brand: Raw brand data
            
        Returns:
            Normalized brand data
        """
        try:
            normalized = {}
            
            normalized['name'] = self.normalize_text(raw_brand.get('name', ''))
            normalized['slug'] = self.normalize_slug(raw_brand.get('slug', ''))
            normalized['url'] = self.normalize_url(raw_brand.get('url', ''))
            normalized['description'] = self.normalize_text(raw_brand.get('description', ''))
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing brand: {e}")
            return {}
    
    def normalize_text(self, text: Any) -> str:
        """Normalize text fields."""
        if not text:
            return ''
        
        try:
            # Convert to string
            text_str = str(text).strip()
            
            # Remove excessive whitespace
            text_str = re.sub(r'\s+', ' ', text_str)
            
            # Remove HTML tags
            text_str = re.sub(r'<[^>]+>', '', text_str)
            
            # Decode HTML entities
            import html
            text_str = html.unescape(text_str)
            
            # Normalize quotes
            text_str = text_str.replace('"', '"').replace('"', '"')
            text_str = text_str.replace(''', "'").replace(''', "'")
            
            return text_str.strip()
            
        except Exception as e:
            logger.warning(f"Error normalizing text '{text}': {e}")
            return ''
    
    def normalize_slug(self, slug: Any) -> str:
        """Normalize slug fields."""
        if not slug:
            return ''
        
        try:
            slug_str = str(slug).strip().lower()
            
            # Remove leading/trailing slashes and spaces
            slug_str = slug_str.strip('/ ')
            
            # Convert Vietnamese characters
            for vn_char, en_char in self.vietnamese_chars_map.items():
                slug_str = slug_str.replace(vn_char, en_char)
            
            # Replace spaces and special characters with hyphens
            slug_str = re.sub(r'[^\w\s-]', '', slug_str)
            slug_str = re.sub(r'[-\s]+', '-', slug_str)
            
            # Remove leading/trailing hyphens
            slug_str = slug_str.strip('-')
            
            return slug_str or 'unknown'
            
        except Exception as e:
            logger.warning(f"Error normalizing slug '{slug}': {e}")
            return 'unknown'
    
    def normalize_url(self, url: Any) -> str:
        """Normalize URL fields."""
        if not url:
            return ''
        
        try:
            url_str = str(url).strip()
            
            # Basic URL validation
            if url_str and not url_str.startswith(('http://', 'https://', '/')):
                url_str = '/' + url_str
            
            return url_str
            
        except Exception as e:
            logger.warning(f"Error normalizing URL '{url}': {e}")
            return ''
    
    def normalize_price(self, price: Any) -> Optional[float]:
        """Normalize price fields."""
        if price is None or price == '':
            return None
        
        try:
            # If already a number
            if isinstance(price, (int, float)):
                return float(price) if price >= 0 else None
            
            # If string, clean and parse
            if isinstance(price, str):
                # Remove currency symbols and formatting
                price_clean = re.sub(r'[^\d.,]', '', price.replace(',', ''))
                
                if not price_clean:
                    return None
                
                # Handle different decimal formats
                try:
                    return float(price_clean)
                except ValueError:
                    return None
            
            return None
            
        except Exception as e:
            logger.warning(f"Error normalizing price '{price}': {e}")
            return None
    
    def normalize_percentage(self, percentage: Any) -> Optional[float]:
        """Normalize percentage fields."""
        if percentage is None or percentage == '':
            return None
        
        try:
            if isinstance(percentage, (int, float)):
                # Ensure percentage is between 0 and 100
                perc = float(percentage)
                return perc if 0 <= perc <= 100 else None
            
            if isinstance(percentage, str):
                # Remove % symbol and spaces
                perc_clean = percentage.replace('%', '').strip()
                try:
                    perc = float(perc_clean)
                    return perc if 0 <= perc <= 100 else None
                except ValueError:
                    return None
            
            return None
            
        except Exception as e:
            logger.warning(f"Error normalizing percentage '{percentage}': {e}")
            return None
    
    def normalize_rating(self, rating: Any) -> Optional[float]:
        """Normalize rating fields."""
        if rating is None or rating == '':
            return None
        
        try:
            if isinstance(rating, (int, float)):
                # Ensure rating is between 0 and 5
                rating_val = float(rating)
                return rating_val if 0 <= rating_val <= 5 else None
            
            if isinstance(rating, str):
                try:
                    rating_val = float(rating.strip())
                    return rating_val if 0 <= rating_val <= 5 else None
                except ValueError:
                    return None
            
            return None
            
        except Exception as e:
            logger.warning(f"Error normalizing rating '{rating}': {e}")
            return None
    
    def normalize_integer(self, value: Any) -> int:
        """Normalize integer fields."""
        if value is None or value == '':
            return 0
        
        try:
            if isinstance(value, int):
                return max(0, value)
            
            if isinstance(value, (float, str)):
                try:
                    int_val = int(float(str(value).replace(',', '')))
                    return max(0, int_val)
                except ValueError:
                    return 0
            
            return 0
            
        except Exception as e:
            logger.warning(f"Error normalizing integer '{value}': {e}")
            return 0
    
    def normalize_boolean(self, value: Any) -> bool:
        """Normalize boolean fields."""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'active')
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return False
    
    def normalize_sku(self, sku: Any) -> str:
        """Normalize SKU fields."""
        if not sku:
            return ''
        
        try:
            sku_str = str(sku).strip().upper()
            
            # Remove special characters but keep alphanumeric and common separators
            sku_str = re.sub(r'[^A-Z0-9\-_]', '', sku_str)
            
            return sku_str
            
        except Exception as e:
            logger.warning(f"Error normalizing SKU '{sku}': {e}")
            return ''
    
    def normalize_availability(self, availability: Any) -> str:
        """Normalize availability status."""
        if not availability:
            return 'unknown'
        
        try:
            avail_str = str(availability).strip().lower()
            
            # Map common availability values
            availability_map = {
                'in_stock': 'in_stock',
                'instock': 'in_stock',
                'available': 'in_stock',
                'có sẵn': 'in_stock',
                'còn hàng': 'in_stock',
                'out_of_stock': 'out_of_stock',
                'outofstock': 'out_of_stock',
                'unavailable': 'out_of_stock',
                'hết hàng': 'out_of_stock',
                'ngừng bán': 'out_of_stock',
                'pre_order': 'pre_order',
                'preorder': 'pre_order',
                'đặt trước': 'pre_order'
            }
            
            # Check for exact matches first
            if avail_str in availability_map:
                return availability_map[avail_str]
            
            # Check for partial matches
            for key, value in availability_map.items():
                if key in avail_str:
                    return value
            
            return 'unknown'
            
        except Exception as e:
            logger.warning(f"Error normalizing availability '{availability}': {e}")
            return 'unknown'
    
    def normalize_images(self, images: Any) -> str:
        """Normalize images field (should be JSON string of URLs)."""
        if not images:
            return ''
        
        try:
            if isinstance(images, str):
                # Try to parse as JSON
                try:
                    parsed = json.loads(images)
                    if isinstance(parsed, list):
                        # Validate and normalize URLs
                        normalized_urls = [self.normalize_url(url) for url in parsed if url]
                        return json.dumps(normalized_urls)
                    else:
                        # Single URL as string
                        normalized_url = self.normalize_url(images)
                        return json.dumps([normalized_url] if normalized_url else [])
                except json.JSONDecodeError:
                    # Not JSON, treat as single URL
                    normalized_url = self.normalize_url(images)
                    return json.dumps([normalized_url] if normalized_url else [])
            
            elif isinstance(images, list):
                # List of URLs
                normalized_urls = [self.normalize_url(url) for url in images if url]
                return json.dumps(normalized_urls)
            
            else:
                # Try to convert to string and normalize as URL
                normalized_url = self.normalize_url(str(images))
                return json.dumps([normalized_url] if normalized_url else [])
            
        except Exception as e:
            logger.warning(f"Error normalizing images '{images}': {e}")
            return ''
    
    def _build_vietnamese_chars_map(self) -> Dict[str, str]:
        """Build mapping of Vietnamese characters to ASCII equivalents."""
        return {
            'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
            'ă': 'a', 'ắ': 'a', 'ằ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
            'â': 'a', 'ấ': 'a', 'ầ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
            'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
            'ê': 'e', 'ế': 'e', 'ề': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
            'í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
            'ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
            'ô': 'o', 'ố': 'o', 'ồ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
            'ơ': 'o', 'ớ': 'o', 'ờ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
            'ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
            'ư': 'u', 'ứ': 'u', 'ừ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
            'ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
            'đ': 'd',
            # Uppercase versions
            'Á': 'A', 'À': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
            'Ă': 'A', 'Ắ': 'A', 'Ằ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
            'Â': 'A', 'Ấ': 'A', 'Ầ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
            'É': 'E', 'È': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
            'Ê': 'E', 'Ế': 'E', 'Ề': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
            'Í': 'I', 'Ì': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
            'Ó': 'O', 'Ò': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
            'Ô': 'O', 'Ố': 'O', 'Ồ': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
            'Ơ': 'O', 'Ớ': 'O', 'Ờ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
            'Ú': 'U', 'Ù': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
            'Ư': 'U', 'Ứ': 'U', 'Ừ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
            'Ý': 'Y', 'Ỳ': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
            'Đ': 'D'
        }
    
    def validate_normalized_product(self, product: Dict) -> Dict:
        """
        Validate normalized product data and return validation results.
        
        Args:
            product: Normalized product data
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Required fields
        required_fields = ['name', 'slug', 'url']
        for field in required_fields:
            if not product.get(field):
                validation_result['errors'].append(f"Missing required field: {field}")
                validation_result['is_valid'] = False
        
        # URL validation
        if product.get('url') and not self._is_valid_url(product['url']):
            validation_result['errors'].append(f"Invalid URL: {product['url']}")
            validation_result['is_valid'] = False
        
        # Price validation
        if product.get('price') is not None:
            if not isinstance(product['price'], (int, float)) or product['price'] < 0:
                validation_result['warnings'].append(f"Invalid price: {product['price']}")
        
        # Rating validation
        if product.get('rating') is not None:
            if not isinstance(product['rating'], (int, float)) or not (0 <= product['rating'] <= 5):
                validation_result['warnings'].append(f"Invalid rating: {product['rating']}")
        
        return validation_result
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme in ('http', 'https') or url.startswith('/'), result.netloc or url.startswith('/')])
        except Exception:
            return False