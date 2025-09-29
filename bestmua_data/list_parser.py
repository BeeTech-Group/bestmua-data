"""Product list parsing module for bestmua.vn."""

import re
import json
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ProductListParser:
    """Parses product listings from category pages."""
    
    def __init__(self, base_url: str = "https://bestmua.vn", session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def parse_category_page(self, category_url: str, max_pages: Optional[int] = None) -> List[Dict]:
        """
        Parse all products from a category page, handling pagination.
        
        Args:
            category_url: URL of the category page
            max_pages: Maximum number of pages to crawl (None for all)
            
        Returns:
            List of product dictionaries with basic info
        """
        products = []
        current_page = 1
        
        try:
            while True:
                page_url = self._get_page_url(category_url, current_page)
                logger.info(f"Parsing page {current_page}: {page_url}")
                
                page_products = self._parse_single_page(page_url)
                
                if not page_products:
                    logger.info(f"No products found on page {current_page}, stopping")
                    break
                
                products.extend(page_products)
                logger.info(f"Found {len(page_products)} products on page {current_page}")
                
                # Check if we should continue to next page
                if max_pages and current_page >= max_pages:
                    logger.info(f"Reached max pages limit: {max_pages}")
                    break
                
                if not self._has_next_page(page_url):
                    logger.info("No more pages found")
                    break
                
                current_page += 1
            
            logger.info(f"Total products found in category: {len(products)}")
            return products
            
        except Exception as e:
            logger.error(f"Error parsing category page {category_url}: {e}")
            return products
    
    def _parse_single_page(self, page_url: str) -> List[Dict]:
        """Parse products from a single page."""
        products = []
        
        try:
            response = self.session.get(page_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try different common product listing selectors
            product_selectors = [
                '.product-item',
                '.product',
                '.product-card',
                '.item-product',
                '.product-list-item',
                '.grid-item',
                '.product-grid-item',
                '[data-product-id]',
                '.woocommerce-product-list .product'
            ]
            
            product_elements = []
            for selector in product_selectors:
                elements = soup.select(selector)
                if elements:
                    product_elements = elements
                    logger.debug(f"Found products using selector: {selector}")
                    break
            
            if not product_elements:
                # Fallback: look for structured data
                products_from_json = self._extract_from_structured_data(soup)
                if products_from_json:
                    return products_from_json
                
                logger.warning(f"No product elements found on page: {page_url}")
                return []
            
            for element in product_elements:
                product = self._extract_product_from_element(element)
                if product:
                    products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error parsing single page {page_url}: {e}")
            return []
    
    def _extract_product_from_element(self, element) -> Optional[Dict]:
        """Extract product information from a product element."""
        try:
            product = {}
            
            # Extract product name
            name_selectors = [
                '.product-title a',
                '.product-name a',
                'h3 a',
                'h2 a',
                '.title a',
                'a[title]'
            ]
            
            name_element = None
            for selector in name_selectors:
                name_element = element.select_one(selector)
                if name_element:
                    break
            
            if not name_element:
                # Try to find any link with text
                name_element = element.find('a', string=True)
            
            if not name_element:
                return None
            
            product['name'] = name_element.get_text().strip()
            product['url'] = name_element.get('href', '')
            
            # Make URL absolute
            if product['url'].startswith('/'):
                product['url'] = urljoin(self.base_url, product['url'])
            
            # Extract product slug from URL
            product['slug'] = self._extract_slug_from_url(product['url'])
            
            # Extract price
            price_info = self._extract_price_info(element)
            product.update(price_info)
            
            # Extract image URL
            image_url = self._extract_image_url(element)
            if image_url:
                product['image_url'] = image_url
            
            # Extract rating and reviews
            rating_info = self._extract_rating_info(element)
            product.update(rating_info)
            
            # Extract additional attributes
            product['sku'] = self._extract_sku(element)
            product['availability'] = self._extract_availability(element)
            
            # Extract flags (new, sale, bestseller, etc.)
            flags = self._extract_product_flags(element)
            product.update(flags)
            
            return product
            
        except Exception as e:
            logger.warning(f"Error extracting product from element: {e}")
            return None
    
    def _extract_price_info(self, element) -> Dict:
        """Extract price information from product element."""
        price_info = {}
        
        try:
            # Common price selectors
            price_selectors = [
                '.price',
                '.product-price',
                '.price-current',
                '.current-price',
                '.sale-price'
            ]
            
            original_price_selectors = [
                '.price-original',
                '.original-price',
                '.old-price',
                '.regular-price',
                '.price-old'
            ]
            
            # Extract current price
            for selector in price_selectors:
                price_element = element.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    price = self._parse_price(price_text)
                    if price:
                        price_info['price'] = price
                        break
            
            # Extract original price
            for selector in original_price_selectors:
                price_element = element.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    price = self._parse_price(price_text)
                    if price:
                        price_info['original_price'] = price
                        break
            
            # Calculate discount percentage
            if 'price' in price_info and 'original_price' in price_info:
                discount = ((price_info['original_price'] - price_info['price']) / 
                           price_info['original_price']) * 100
                price_info['discount_percentage'] = round(discount, 2)
            
            return price_info
            
        except Exception as e:
            logger.warning(f"Error extracting price info: {e}")
            return {}
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text string."""
        if not price_text:
            return None
            
        # Remove common currency symbols and formatting
        price_clean = re.sub(r'[^\d.,]', '', price_text.replace(',', ''))
        
        # Handle different decimal formats
        if '.' in price_clean:
            try:
                return float(price_clean)
            except ValueError:
                pass
        
        try:
            return float(price_clean)
        except ValueError:
            return None
    
    def _extract_image_url(self, element) -> Optional[str]:
        """Extract product image URL."""
        try:
            img_selectors = [
                '.product-image img',
                '.product-img img',
                '.thumb img',
                'img.product-image',
                'img'
            ]
            
            for selector in img_selectors:
                img_element = element.select_one(selector)
                if img_element:
                    # Try data-src first (lazy loading), then src
                    img_url = (img_element.get('data-src') or 
                             img_element.get('src') or 
                             img_element.get('data-original'))
                    
                    if img_url:
                        # Make URL absolute
                        if img_url.startswith('/'):
                            img_url = urljoin(self.base_url, img_url)
                        return img_url
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting image URL: {e}")
            return None
    
    def _extract_rating_info(self, element) -> Dict:
        """Extract rating and review information."""
        rating_info = {}
        
        try:
            # Look for star ratings
            star_selectors = [
                '.stars',
                '.rating',
                '.star-rating',
                '.product-rating'
            ]
            
            for selector in star_selectors:
                rating_element = element.select_one(selector)
                if rating_element:
                    # Try to extract rating from different formats
                    rating = self._parse_rating(rating_element)
                    if rating:
                        rating_info['rating'] = rating
                        break
            
            # Look for review count
            review_selectors = [
                '.review-count',
                '.reviews',
                '.num-reviews',
                '.review-num'
            ]
            
            for selector in review_selectors:
                review_element = element.select_one(selector)
                if review_element:
                    review_text = review_element.get_text().strip()
                    review_count = self._parse_review_count(review_text)
                    if review_count is not None:
                        rating_info['review_count'] = review_count
                        break
            
            return rating_info
            
        except Exception as e:
            logger.warning(f"Error extracting rating info: {e}")
            return {}
    
    def _parse_rating(self, rating_element) -> Optional[float]:
        """Parse rating from rating element."""
        try:
            # Try data attributes first
            rating_attrs = ['data-rating', 'data-score', 'data-stars']
            for attr in rating_attrs:
                rating_value = rating_element.get(attr)
                if rating_value:
                    try:
                        return float(rating_value)
                    except ValueError:
                        pass
            
            # Try to parse from text
            rating_text = rating_element.get_text().strip()
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                return float(rating_match.group(1))
            
            # Try to count filled stars
            filled_stars = len(rating_element.select('.star.filled, .star-filled, .fa-star, .glyphicon-star'))
            if filled_stars > 0:
                return float(filled_stars)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing rating: {e}")
            return None
    
    def _parse_review_count(self, review_text: str) -> Optional[int]:
        """Parse review count from text."""
        if not review_text:
            return None
        
        # Extract numbers from text
        numbers = re.findall(r'\d+', review_text.replace(',', ''))
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                pass
        
        return None
    
    def _extract_sku(self, element) -> Optional[str]:
        """Extract product SKU."""
        try:
            sku_selectors = [
                '[data-sku]',
                '.sku',
                '.product-sku',
                '.product-code'
            ]
            
            for selector in sku_selectors:
                sku_element = element.select_one(selector)
                if sku_element:
                    sku = sku_element.get('data-sku') or sku_element.get_text().strip()
                    if sku:
                        return sku
            
            return None
            
        except Exception:
            return None
    
    def _extract_availability(self, element) -> Optional[str]:
        """Extract product availability status."""
        try:
            # Look for availability indicators
            availability_selectors = [
                '.availability',
                '.stock-status',
                '.in-stock',
                '.out-of-stock'
            ]
            
            for selector in availability_selectors:
                avail_element = element.select_one(selector)
                if avail_element:
                    return avail_element.get_text().strip()
            
            # Check for common classes
            if element.select_one('.in-stock, .available'):
                return 'in_stock'
            elif element.select_one('.out-of-stock, .unavailable'):
                return 'out_of_stock'
            
            return 'unknown'
            
        except Exception:
            return 'unknown'
    
    def _extract_product_flags(self, element) -> Dict:
        """Extract product flags (new, sale, bestseller, etc.)."""
        flags = {
            'is_featured': False,
            'is_bestseller': False,
            'is_new': False,
            'is_sale': False
        }
        
        try:
            # Look for badge/flag elements
            badge_selectors = [
                '.badge',
                '.label',
                '.flag',
                '.tag'
            ]
            
            for selector in badge_selectors:
                badges = element.select(selector)
                for badge in badges:
                    badge_text = badge.get_text().strip().lower()
                    
                    if any(word in badge_text for word in ['new', 'mới']):
                        flags['is_new'] = True
                    elif any(word in badge_text for word in ['sale', 'giảm', 'khuyến mãi']):
                        flags['is_sale'] = True
                    elif any(word in badge_text for word in ['bestseller', 'bán chạy', 'hot']):
                        flags['is_bestseller'] = True
                    elif any(word in badge_text for word in ['featured', 'nổi bật']):
                        flags['is_featured'] = True
            
            # Check for CSS classes
            element_classes = ' '.join(element.get('class', []))
            if any(cls in element_classes for cls in ['featured', 'bestseller', 'hot']):
                flags['is_featured'] = True
            
            return flags
            
        except Exception:
            return flags
    
    def _extract_slug_from_url(self, url: str) -> str:
        """Extract product slug from URL."""
        try:
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.split('/') if part]
            
            if path_parts:
                # Usually the last part is the product slug
                return path_parts[-1]
            
            return 'unknown'
            
        except Exception:
            return 'unknown'
    
    def _get_page_url(self, base_url: str, page: int) -> str:
        """Generate URL for specific page number."""
        if page == 1:
            return base_url
        
        # Common pagination URL patterns
        if '?' in base_url:
            return f"{base_url}&page={page}"
        else:
            return f"{base_url}?page={page}"
    
    def _has_next_page(self, current_url: str) -> bool:
        """Check if there's a next page available."""
        try:
            response = self.session.get(current_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for next page indicators
            next_selectors = [
                '.next',
                '.pagination-next',
                'a[rel="next"]',
                '.page-next'
            ]
            
            for selector in next_selectors:
                if soup.select_one(selector):
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking for next page: {e}")
            return False
    
    def _extract_from_structured_data(self, soup) -> List[Dict]:
        """Extract products from JSON-LD structured data."""
        products = []
        
        try:
            # Look for JSON-LD scripts
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Handle different structured data formats
                    if isinstance(data, list):
                        for item in data:
                            product = self._parse_structured_product(item)
                            if product:
                                products.append(product)
                    elif isinstance(data, dict):
                        if data.get('@type') == 'Product':
                            product = self._parse_structured_product(data)
                            if product:
                                products.append(product)
                        elif 'itemListElement' in data:
                            # Product list
                            for item in data['itemListElement']:
                                product = self._parse_structured_product(item)
                                if product:
                                    products.append(product)
                
                except json.JSONDecodeError:
                    continue
            
            return products
            
        except Exception as e:
            logger.warning(f"Error extracting from structured data: {e}")
            return []
    
    def _parse_structured_product(self, data: Dict) -> Optional[Dict]:
        """Parse product from structured data."""
        try:
            if not isinstance(data, dict):
                return None
            
            product = {}
            
            # Extract name
            if 'name' in data:
                product['name'] = data['name']
            
            # Extract URL
            if 'url' in data:
                product['url'] = data['url']
                product['slug'] = self._extract_slug_from_url(data['url'])
            
            # Extract price
            if 'offers' in data and isinstance(data['offers'], dict):
                offers = data['offers']
                if 'price' in offers:
                    try:
                        product['price'] = float(offers['price'])
                    except (ValueError, TypeError):
                        pass
            
            # Extract image
            if 'image' in data:
                if isinstance(data['image'], list) and data['image']:
                    product['image_url'] = data['image'][0]
                elif isinstance(data['image'], str):
                    product['image_url'] = data['image']
            
            # Extract rating
            if 'aggregateRating' in data:
                rating_data = data['aggregateRating']
                if 'ratingValue' in rating_data:
                    try:
                        product['rating'] = float(rating_data['ratingValue'])
                    except (ValueError, TypeError):
                        pass
                if 'reviewCount' in rating_data:
                    try:
                        product['review_count'] = int(rating_data['reviewCount'])
                    except (ValueError, TypeError):
                        pass
            
            return product if 'name' in product else None
            
        except Exception as e:
            logger.warning(f"Error parsing structured product: {e}")
            return None