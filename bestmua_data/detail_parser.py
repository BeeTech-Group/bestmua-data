"""Product detail parsing module for bestmua.vn."""

import re
import json
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ProductDetailParser:
    """Parses detailed product information from product pages."""
    
    def __init__(self, base_url: str = "https://bestmua.vn", session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def parse_product_detail(self, product_url: str) -> Optional[Dict]:
        """
        Parse detailed product information from a product page.
        
        Args:
            product_url: URL of the product page
            
        Returns:
            Dictionary with detailed product information
        """
        try:
            response = self.session.get(product_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to extract from structured data first
            product = self._extract_from_structured_data(soup)
            
            if not product:
                # Fallback to HTML parsing
                product = self._extract_from_html(soup)
            
            if product:
                product['url'] = product_url
                product['slug'] = self._extract_slug_from_url(product_url)
                logger.debug(f"Successfully parsed product: {product.get('name', 'Unknown')}")
            
            return product
            
        except Exception as e:
            logger.error(f"Error parsing product detail {product_url}: {e}")
            return None
    
    def _extract_from_structured_data(self, soup) -> Optional[Dict]:
        """Extract product data from JSON-LD structured data."""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Handle different data formats
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'Product':
                                return self._parse_structured_product(item)
                    elif isinstance(data, dict) and data.get('@type') == 'Product':
                        return self._parse_structured_product(data)
                        
                except json.JSONDecodeError:
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting from structured data: {e}")
            return None
    
    def _parse_structured_product(self, data: Dict) -> Dict:
        """Parse product from structured data."""
        product = {}
        
        try:
            # Basic information
            product['name'] = data.get('name', '')
            product['description'] = data.get('description', '')
            product['sku'] = data.get('sku', '')
            
            # Brand information
            if 'brand' in data:
                brand_data = data['brand']
                if isinstance(brand_data, dict):
                    product['brand_name'] = brand_data.get('name', '')
                elif isinstance(brand_data, str):
                    product['brand_name'] = brand_data
            
            # Price information
            if 'offers' in data:
                offers = data['offers']
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                
                if isinstance(offers, dict):
                    if 'price' in offers:
                        try:
                            product['price'] = float(offers['price'])
                        except (ValueError, TypeError):
                            pass
                    
                    product['availability'] = offers.get('availability', '').split('/')[-1].lower()
                    
                    # Currency
                    product['currency'] = offers.get('priceCurrency', 'VND')
            
            # Images
            if 'image' in data:
                images = data['image']
                if isinstance(images, list):
                    product['image_url'] = images[0] if images else ''
                    product['images'] = json.dumps(images)
                elif isinstance(images, str):
                    product['image_url'] = images
                    product['images'] = json.dumps([images])
            
            # Rating information
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
            
            # Category information
            if 'category' in data:
                product['category_name'] = data['category']
            
            return product
            
        except Exception as e:
            logger.warning(f"Error parsing structured product: {e}")
            return {}
    
    def _extract_from_html(self, soup) -> Optional[Dict]:
        """Extract product data from HTML elements."""
        product = {}
        
        try:
            # Extract product name
            product['name'] = self._extract_product_name(soup)
            
            # Extract description
            product['description'] = self._extract_description(soup)
            
            # Extract price information
            price_info = self._extract_price_info(soup)
            product.update(price_info)
            
            # Extract images
            image_info = self._extract_images(soup)
            product.update(image_info)
            
            # Extract SKU
            product['sku'] = self._extract_sku(soup)
            
            # Extract brand
            product['brand_name'] = self._extract_brand(soup)
            
            # Extract availability
            product['availability'] = self._extract_availability(soup)
            
            # Extract rating and reviews
            rating_info = self._extract_rating_info(soup)
            product.update(rating_info)
            
            # Extract additional details
            additional_info = self._extract_additional_info(soup)
            product.update(additional_info)
            
            # Extract product flags
            flags = self._extract_product_flags(soup)
            product.update(flags)
            
            return product if product.get('name') else None
            
        except Exception as e:
            logger.error(f"Error extracting from HTML: {e}")
            return None
    
    def _extract_product_name(self, soup) -> str:
        """Extract product name."""
        name_selectors = [
            'h1.product-title',
            'h1.product-name', 
            '.product-title h1',
            '.product-name h1',
            'h1',
            '.product-info h1',
            '.product-details h1'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text().strip()
                if name and len(name) > 5:  # Basic validation
                    return name
        
        return ''
    
    def _extract_description(self, soup) -> str:
        """Extract product description."""
        desc_selectors = [
            '.product-description',
            '.product-desc',
            '.product-detail',
            '.description',
            '.product-content',
            '.product-info .description',
            '[id*="description"]',
            '.tab-content .description'
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                # Remove script and style tags
                for tag in element(['script', 'style']):
                    tag.decompose()
                    
                desc = element.get_text().strip()
                if desc and len(desc) > 10:
                    return desc
        
        return ''
    
    def _extract_price_info(self, soup) -> Dict:
        """Extract price information."""
        price_info = {}
        
        # Current price selectors
        price_selectors = [
            '.price-current',
            '.current-price',
            '.sale-price',
            '.price.current',
            '.product-price .current',
            '.price-box .price'
        ]
        
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                price = self._parse_price(price_text)
                if price:
                    price_info['price'] = price
                    break
        
        # Original price selectors
        original_price_selectors = [
            '.price-original',
            '.original-price',
            '.old-price',
            '.regular-price',
            '.price.old',
            '.product-price .old',
            '.price-box .old-price'
        ]
        
        for selector in original_price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
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
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text."""
        if not price_text:
            return None
        
        # Remove currency symbols and spaces
        price_clean = re.sub(r'[^\d.,]', '', price_text.replace(',', ''))
        
        try:
            # Handle different decimal formats
            if '.' in price_clean and price_clean.count('.') == 1:
                return float(price_clean)
            else:
                # Assume no decimal point
                return float(price_clean)
        except ValueError:
            return None
    
    def _extract_images(self, soup) -> Dict:
        """Extract product images."""
        image_info = {}
        images = []
        
        # Main product image selectors
        main_img_selectors = [
            '.product-image img',
            '.product-img img',
            '.main-image img',
            '.product-gallery .main img',
            '.product-photo img'
        ]
        
        main_img = None
        for selector in main_img_selectors:
            element = soup.select_one(selector)
            if element:
                img_url = (element.get('data-src') or 
                          element.get('src') or 
                          element.get('data-original'))
                if img_url:
                    main_img = self._make_absolute_url(img_url)
                    break
        
        if main_img:
            image_info['image_url'] = main_img
            images.append(main_img)
        
        # Gallery images
        gallery_selectors = [
            '.product-gallery img',
            '.product-images img',
            '.product-thumbnails img',
            '.image-gallery img'
        ]
        
        for selector in gallery_selectors:
            elements = soup.select(selector)
            for element in elements:
                img_url = (element.get('data-src') or 
                          element.get('src') or 
                          element.get('data-original'))
                if img_url:
                    full_url = self._make_absolute_url(img_url)
                    if full_url and full_url not in images:
                        images.append(full_url)
        
        if images:
            image_info['images'] = json.dumps(images)
        
        return image_info
    
    def _extract_sku(self, soup) -> str:
        """Extract product SKU."""
        sku_selectors = [
            '[data-sku]',
            '.sku',
            '.product-sku',
            '.product-code',
            '.item-code'
        ]
        
        for selector in sku_selectors:
            element = soup.select_one(selector)
            if element:
                sku = element.get('data-sku') or element.get_text().strip()
                if sku:
                    return sku
        
        # Try to find SKU in product info table
        info_rows = soup.select('.product-info tr, .product-details tr')
        for row in info_rows:
            cells = row.select('td, th')
            if len(cells) >= 2:
                key = cells[0].get_text().strip().lower()
                if any(term in key for term in ['sku', 'mã', 'code']):
                    return cells[1].get_text().strip()
        
        return ''
    
    def _extract_brand(self, soup) -> str:
        """Extract product brand."""
        brand_selectors = [
            '.product-brand',
            '.brand',
            '.manufacturer',
            '.brand-name',
            '.product-manufacturer'
        ]
        
        for selector in brand_selectors:
            element = soup.select_one(selector)
            if element:
                brand = element.get_text().strip()
                if brand:
                    return brand
        
        # Try to find brand in product info
        info_rows = soup.select('.product-info tr, .product-details tr')
        for row in info_rows:
            cells = row.select('td, th')
            if len(cells) >= 2:
                key = cells[0].get_text().strip().lower()
                if any(term in key for term in ['brand', 'thương hiệu', 'hãng']):
                    return cells[1].get_text().strip()
        
        return ''
    
    def _extract_availability(self, soup) -> str:
        """Extract product availability."""
        availability_selectors = [
            '.availability',
            '.stock-status',
            '.product-availability',
            '.stock'
        ]
        
        for selector in availability_selectors:
            element = soup.select_one(selector)
            if element:
                status = element.get_text().strip().lower()
                if any(term in status for term in ['in stock', 'có sẵn', 'còn hàng']):
                    return 'in_stock'
                elif any(term in status for term in ['out of stock', 'hết hàng', 'ngừng bán']):
                    return 'out_of_stock'
                else:
                    return status
        
        # Check for add to cart button
        if soup.select_one('.add-to-cart, .btn-add-cart'):
            return 'in_stock'
        
        return 'unknown'
    
    def _extract_rating_info(self, soup) -> Dict:
        """Extract rating and review information."""
        rating_info = {}
        
        # Rating selectors
        rating_selectors = [
            '.rating',
            '.stars',
            '.star-rating',
            '.product-rating'
        ]
        
        for selector in rating_selectors:
            element = soup.select_one(selector)
            if element:
                rating = self._parse_rating(element)
                if rating:
                    rating_info['rating'] = rating
                    break
        
        # Review count selectors
        review_selectors = [
            '.review-count',
            '.reviews-count',
            '.num-reviews',
            '.total-reviews'
        ]
        
        for selector in review_selectors:
            element = soup.select_one(selector)
            if element:
                review_text = element.get_text().strip()
                count = self._parse_review_count(review_text)
                if count is not None:
                    rating_info['review_count'] = count
                    break
        
        return rating_info
    
    def _parse_rating(self, rating_element) -> Optional[float]:
        """Parse rating from element."""
        try:
            # Check data attributes
            rating_attrs = ['data-rating', 'data-score', 'data-stars']
            for attr in rating_attrs:
                rating_value = rating_element.get(attr)
                if rating_value:
                    try:
                        return float(rating_value)
                    except ValueError:
                        pass
            
            # Parse from text
            rating_text = rating_element.get_text().strip()
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                return float(rating_match.group(1))
            
            # Count filled stars
            filled_stars = len(rating_element.select('.star.filled, .star-filled, .fa-star'))
            if filled_stars > 0:
                return float(filled_stars)
            
            return None
            
        except Exception:
            return None
    
    def _parse_review_count(self, review_text: str) -> Optional[int]:
        """Parse review count from text."""
        if not review_text:
            return None
        
        numbers = re.findall(r'\d+', review_text.replace(',', ''))
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                pass
        
        return None
    
    def _extract_additional_info(self, soup) -> Dict:
        """Extract additional product information."""
        additional_info = {}
        
        # Extract ingredients
        ingredients_selectors = [
            '.ingredients',
            '.product-ingredients',
            '.composition',
            '.thành-phần'
        ]
        
        for selector in ingredients_selectors:
            element = soup.select_one(selector)
            if element:
                ingredients = element.get_text().strip()
                if ingredients:
                    additional_info['ingredients'] = ingredients
                    break
        
        # Extract usage instructions
        usage_selectors = [
            '.usage',
            '.instructions',
            '.how-to-use',
            '.cách-sử-dụng',
            '.hướng-dẫn'
        ]
        
        for selector in usage_selectors:
            element = soup.select_one(selector)
            if element:
                usage = element.get_text().strip()
                if usage:
                    additional_info['usage_instructions'] = usage
                    break
        
        return additional_info
    
    def _extract_product_flags(self, soup) -> Dict:
        """Extract product flags."""
        flags = {
            'is_featured': False,
            'is_bestseller': False,
            'is_new': False,
            'is_sale': False
        }
        
        # Look for badge elements
        badges = soup.select('.badge, .label, .flag, .tag')
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
        
        return flags
    
    def _make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute URL."""
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return urljoin(self.base_url, url)
        else:
            return url
    
    def _extract_slug_from_url(self, url: str) -> str:
        """Extract product slug from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.split('/') if part]
            
            if path_parts:
                return path_parts[-1]
            
            return 'unknown'
            
        except Exception:
            return 'unknown'