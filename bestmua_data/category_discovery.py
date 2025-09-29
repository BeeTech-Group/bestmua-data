"""Category discovery module for bestmua.vn."""

import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import Category

logger = logging.getLogger(__name__)


class CategoryDiscovery:
    """Discovers product categories from bestmua.vn."""
    
    def __init__(self, base_url: str = "https://bestmua.vn", session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def discover_categories(self) -> List[Dict]:
        """
        Discover all product categories from the main navigation and category pages.
        
        Returns:
            List of category dictionaries with name, slug, url, and parent info
        """
        categories = []
        
        try:
            # Get main page to discover primary navigation categories
            main_categories = self._get_main_navigation_categories()
            categories.extend(main_categories)
            
            # For each main category, discover subcategories
            for main_category in main_categories:
                subcategories = self._get_subcategories(main_category['url'])
                for subcat in subcategories:
                    subcat['parent_slug'] = main_category['slug']
                categories.extend(subcategories)
            
            logger.info(f"Discovered {len(categories)} categories")
            return categories
            
        except Exception as e:
            logger.error(f"Error discovering categories: {e}")
            return []
    
    def _get_main_navigation_categories(self) -> List[Dict]:
        """Extract categories from main navigation menu."""
        categories = []
        
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for common navigation selectors
            nav_selectors = [
                'nav .menu a',
                '.main-menu a',
                '.navigation a',
                '.navbar a',
                '.category-menu a',
                'header nav a',
                '.header-menu a'
            ]
            
            for selector in nav_selectors:
                nav_links = soup.select(selector)
                if nav_links:
                    categories.extend(self._extract_categories_from_links(nav_links))
                    break
                    
            # Fallback: look for any links that appear to be category links
            if not categories:
                all_links = soup.find_all('a', href=True)
                category_patterns = [
                    r'/danh-muc/',
                    r'/category/',
                    r'/categories/',
                    r'/c/',
                    r'/san-pham/',
                    r'/products/'
                ]
                
                for link in all_links:
                    href = link.get('href', '')
                    if any(pattern in href for pattern in category_patterns):
                        categories.extend(self._extract_categories_from_links([link]))
            
            # Remove duplicates
            seen = set()
            unique_categories = []
            for cat in categories:
                key = cat['slug']
                if key not in seen:
                    seen.add(key)
                    unique_categories.append(cat)
            
            return unique_categories
            
        except Exception as e:
            logger.error(f"Error getting main navigation categories: {e}")
            return []
    
    def _get_subcategories(self, category_url: str) -> List[Dict]:
        """Extract subcategories from a category page."""
        subcategories = []
        
        try:
            full_url = urljoin(self.base_url, category_url)
            response = self.session.get(full_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for subcategory navigation
            subcat_selectors = [
                '.subcategory-menu a',
                '.sub-categories a',
                '.category-sidebar a',
                '.filter-categories a',
                '.sub-nav a'
            ]
            
            for selector in subcat_selectors:
                subcat_links = soup.select(selector)
                if subcat_links:
                    subcategories.extend(self._extract_categories_from_links(subcat_links))
                    break
            
            return subcategories
            
        except Exception as e:
            logger.error(f"Error getting subcategories from {category_url}: {e}")
            return []
    
    def _extract_categories_from_links(self, links) -> List[Dict]:
        """Extract category information from link elements."""
        categories = []
        
        for link in links:
            try:
                href = link.get('href', '')
                text = link.get_text().strip()
                
                if not href or not text or len(text) > 200:
                    continue
                
                # Skip non-category links
                skip_patterns = [
                    'javascript:',
                    'mailto:',
                    'tel:',
                    '#',
                    '/search',
                    '/contact',
                    '/about',
                    '/blog',
                    '/news'
                ]
                
                if any(pattern in href.lower() for pattern in skip_patterns):
                    continue
                
                # Generate slug from text
                slug = self._generate_slug(text)
                
                # Make URL absolute
                full_url = urljoin(self.base_url, href)
                
                category = {
                    'name': text,
                    'slug': slug,
                    'url': href,
                    'full_url': full_url
                }
                
                categories.append(category)
                
            except Exception as e:
                logger.warning(f"Error extracting category from link: {e}")
                continue
        
        return categories
    
    def _generate_slug(self, text: str) -> str:
        """Generate URL-friendly slug from category name."""
        # Convert to lowercase
        slug = text.lower()
        
        # Remove Vietnamese diacritics (basic conversion)
        vietnamese_chars = {
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
            'đ': 'd'
        }
        
        for vn_char, en_char in vietnamese_chars.items():
            slug = slug.replace(vn_char, en_char)
        
        # Replace spaces and special characters with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        return slug or 'unknown'