"""Unit tests for category discovery module."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup

from bestmua_data.category_discovery import CategoryDiscovery
from fixtures.sample_data import SAMPLE_CATEGORY_PAGE_HTML


class TestCategoryDiscovery(unittest.TestCase):
    """Test cases for CategoryDiscovery class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=requests.Session)
        self.discovery = CategoryDiscovery(
            base_url="https://bestmua.vn",
            session=self.mock_session
        )
    
    def test_init(self):
        """Test CategoryDiscovery initialization."""
        discovery = CategoryDiscovery()
        self.assertEqual(discovery.base_url, "https://bestmua.vn")
        self.assertIsNotNone(discovery.session)
        
        # Test with custom parameters
        custom_session = Mock()
        custom_discovery = CategoryDiscovery(
            base_url="https://example.com",
            session=custom_session
        )
        self.assertEqual(custom_discovery.base_url, "https://example.com")
        self.assertEqual(custom_discovery.session, custom_session)
    
    @patch('requests.Session.get')
    def test_discover_categories_success(self, mock_get):
        """Test successful category discovery."""
        # Mock response
        mock_response = Mock()
        mock_response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Run discovery
        categories = self.discovery.discover_categories()
        
        # Verify results
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)
        
        # Check category structure
        for category in categories:
            self.assertIn('name', category)
            self.assertIn('slug', category)
            self.assertIn('url', category)
            self.assertIn('full_url', category)
    
    @patch('requests.Session.get')
    def test_discover_categories_network_error(self, mock_get):
        """Test category discovery with network error."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        categories = self.discovery.discover_categories()
        
        # Should return empty list on error
        self.assertEqual(categories, [])
    
    def test_extract_categories_from_links(self):
        """Test extracting categories from HTML links."""
        soup = BeautifulSoup(SAMPLE_CATEGORY_PAGE_HTML, 'html.parser')
        links = soup.select('nav.main-menu a')
        
        categories = self.discovery._extract_categories_from_links(links)
        
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)
        
        # Check first category
        first_category = categories[0]
        self.assertIn('name', first_category)
        self.assertIn('slug', first_category)
        self.assertIn('url', first_category)
        self.assertEqual(first_category['name'], 'Son môi')
        self.assertEqual(first_category['slug'], 'son-moi')
        self.assertEqual(first_category['url'], '/danh-muc/son-moi')
    
    def test_generate_slug(self):
        """Test slug generation from Vietnamese text."""
        test_cases = [
            ('Son môi', 'son-moi'),
            ('Kem nền', 'kem-nen'),
            ('Phấn mắt', 'phan-mat'),
            ('Son môi L\'Oréal', 'son-moi-loreal'),
            ('  Extra  Spaces  ', 'extra-spaces'),
            ('Special!@#$%^&*()Characters', 'specialcharacters'),
            ('', 'unknown')
        ]
        
        for input_text, expected_slug in test_cases:
            with self.subTest(input_text=input_text):
                result = self.discovery._generate_slug(input_text)
                self.assertEqual(result, expected_slug)
    
    def test_generate_slug_vietnamese_chars(self):
        """Test Vietnamese character conversion in slug generation."""
        vietnamese_text = "Sản phẩm làm đẹp từ thiên nhiên"
        expected_slug = "san-pham-lam-dep-tu-thien-nhien"
        
        result = self.discovery._generate_slug(vietnamese_text)
        self.assertEqual(result, expected_slug)
    
    @patch('requests.Session.get')
    def test_get_main_navigation_categories(self, mock_get):
        """Test extraction of main navigation categories."""
        mock_response = Mock()
        mock_response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        categories = self.discovery._get_main_navigation_categories()
        
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)
        
        # Check that we found the expected categories
        category_names = [cat['name'] for cat in categories]
        self.assertIn('Son môi', category_names)
        self.assertIn('Kem nền', category_names)
    
    @patch('requests.Session.get')
    def test_get_subcategories(self, mock_get):
        """Test subcategory extraction."""
        # Mock empty subcategory response (no subcategories found)
        mock_response = Mock()
        mock_response.content = "<html><body><div class='content'>No subcategories</div></body></html>".encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        subcategories = self.discovery._get_subcategories('/danh-muc/son-moi')
        
        self.assertIsInstance(subcategories, list)
        # Should be empty for this test case
        self.assertEqual(len(subcategories), 0)
    
    @patch('requests.Session.get')
    def test_get_subcategories_with_error(self, mock_get):
        """Test subcategory extraction with network error."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        subcategories = self.discovery._get_subcategories('/danh-muc/son-moi')
        
        self.assertEqual(subcategories, [])
    
    def test_extract_categories_from_links_empty(self):
        """Test extracting categories from empty links list."""
        categories = self.discovery._extract_categories_from_links([])
        self.assertEqual(categories, [])
    
    def test_extract_categories_from_links_invalid(self):
        """Test extracting categories from invalid links."""
        # Create mock links with invalid data
        mock_link1 = Mock()
        mock_link1.get.side_effect = lambda attr, default=None: {
            'href': 'javascript:void(0)',
            'text': 'Invalid Link'
        }.get(attr, default)
        mock_link1.get_text.return_value = 'Invalid Link'
        
        mock_link2 = Mock()
        mock_link2.get.side_effect = lambda attr, default=None: {
            'href': '',
            'text': ''
        }.get(attr, default)
        mock_link2.get_text.return_value = ''
        
        categories = self.discovery._extract_categories_from_links([mock_link1, mock_link2])
        
        # Should filter out invalid links
        self.assertEqual(len(categories), 0)


if __name__ == '__main__':
    unittest.main()