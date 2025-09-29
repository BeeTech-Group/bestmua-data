"""Unit tests for product list parsing module."""

import unittest
from unittest.mock import Mock, patch
import json
from bs4 import BeautifulSoup

from bestmua_data.list_parser import ProductListParser
from fixtures.sample_data import SAMPLE_CATEGORY_PAGE_HTML


class TestProductListParser(unittest.TestCase):
    """Test cases for ProductListParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.parser = ProductListParser(
            base_url="https://bestmua.vn",
            session=self.mock_session
        )
    
    def test_init(self):
        """Test ProductListParser initialization."""
        parser = ProductListParser()
        self.assertEqual(parser.base_url, "https://bestmua.vn")
        self.assertIsNotNone(parser.session)
    
    @patch('requests.Session.get')
    def test_parse_single_page_success(self, mock_get):
        """Test successful parsing of a single page."""
        mock_response = Mock()
        mock_response.content = SAMPLE_CATEGORY_PAGE_HTML.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        products = self.parser._parse_single_page("https://bestmua.vn/danh-muc/son-moi")
        
        self.assertIsInstance(products, list)
        self.assertGreater(len(products), 0)
        
        # Check product structure
        first_product = products[0]
        self.assertIn('name', first_product)
        self.assertIn('url', first_product)
        self.assertIn('slug', first_product)
        self.assertIn('price', first_product)
    
    def test_extract_product_from_element(self):
        """Test product extraction from HTML element."""
        soup = BeautifulSoup(SAMPLE_CATEGORY_PAGE_HTML, 'html.parser')
        product_elements = soup.select('.product-item')
        
        self.assertGreater(len(product_elements), 0)
        
        # Test first product
        first_element = product_elements[0]
        product = self.parser._extract_product_from_element(first_element)
        
        self.assertIsNotNone(product)
        self.assertEqual(product['name'], 'Son môi Maybelline Super Stay Matte Ink Liquid Lipstick')
        self.assertEqual(product['url'], '/san-pham/son-moi-maybelline-super-stay')
        self.assertEqual(product['slug'], 'son-moi-maybelline-super-stay')
        self.assertEqual(product['price'], 299000.0)
        self.assertEqual(product['original_price'], 399000.0)
        self.assertEqual(product['rating'], 4.5)
        self.assertEqual(product['review_count'], 123)
        self.assertTrue(product['is_sale'])
        self.assertFalse(product['is_new'])
    
    def test_extract_product_from_element_minimal(self):
        """Test product extraction with minimal data."""
        # Create minimal HTML element
        html = '''
        <div class="product-item">
            <a href="/product/test" class="product-title">Test Product</a>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product-item')
        
        product = self.parser._extract_product_from_element(element)
        
        self.assertIsNotNone(product)
        self.assertEqual(product['name'], 'Test Product')
        self.assertEqual(product['url'], '/product/test')
        self.assertEqual(product['slug'], 'test')
    
    def test_extract_product_from_element_invalid(self):
        """Test product extraction from invalid element."""
        # Create element without required data
        html = '<div class="product-item">No product data</div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product-item')
        
        product = self.parser._extract_product_from_element(element)
        
        self.assertIsNone(product)
    
    def test_parse_price(self):
        """Test price parsing from various formats."""
        test_cases = [
            ('299,000đ', 299000.0),
            ('450.000 VND', 450000.0),
            ('1,234.56', 1234.56),
            ('$29.99', 29.99),
            ('invalid price', None),
            ('', None),
            (None, None)
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.parser._parse_price(price_text)
                self.assertEqual(result, expected)
    
    def test_extract_price_info(self):
        """Test price information extraction."""
        # Test with full price info
        html = '''
        <div class="product">
            <span class="price-current">299,000đ</span>
            <span class="price-original">399,000đ</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product')
        
        price_info = self.parser._extract_price_info(element)
        
        self.assertEqual(price_info['price'], 299000.0)
        self.assertEqual(price_info['original_price'], 399000.0)
        self.assertEqual(price_info['discount_percentage'], 25.06)  # Rounded
    
    def test_extract_image_url(self):
        """Test image URL extraction."""
        html = '''
        <div class="product">
            <img src="/images/product.jpg" alt="Product" class="product-image">
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product')
        
        image_url = self.parser._extract_image_url(element)
        
        self.assertEqual(image_url, 'https://bestmua.vn/images/product.jpg')
    
    def test_extract_image_url_lazy_loading(self):
        """Test image URL extraction with lazy loading."""
        html = '''
        <div class="product">
            <img data-src="/images/product.jpg" src="/images/placeholder.jpg" class="product-image">
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product')
        
        image_url = self.parser._extract_image_url(element)
        
        # Should prefer data-src over src
        self.assertEqual(image_url, 'https://bestmua.vn/images/product.jpg')
    
    def test_extract_rating_info(self):
        """Test rating information extraction."""
        html = '''
        <div class="product">
            <div class="rating" data-rating="4.5">★★★★☆</div>
            <span class="review-count">123 đánh giá</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product')
        
        rating_info = self.parser._extract_rating_info(element)
        
        self.assertEqual(rating_info['rating'], 4.5)
        self.assertEqual(rating_info['review_count'], 123)
    
    def test_parse_rating(self):
        """Test rating parsing from different formats."""
        # Test with data attribute
        html = '<div class="rating" data-rating="4.5">Stars</div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.rating')
        
        rating = self.parser._parse_rating(element)
        self.assertEqual(rating, 4.5)
        
        # Test with text content
        html = '<div class="rating">4.2 out of 5</div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.rating')
        
        rating = self.parser._parse_rating(element)
        self.assertEqual(rating, 4.2)
    
    def test_parse_review_count(self):
        """Test review count parsing."""
        test_cases = [
            ('123 đánh giá', 123),
            ('1,234 reviews', 1234),
            ('(89 reviews)', 89),
            ('No reviews', None),
            ('', None)
        ]
        
        for review_text, expected in test_cases:
            with self.subTest(review_text=review_text):
                result = self.parser._parse_review_count(review_text)
                self.assertEqual(result, expected)
    
    def test_extract_availability(self):
        """Test availability extraction."""
        # Test in stock
        html = '<div class="product"><div class="in-stock">Còn hàng</div></div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product')
        
        availability = self.parser._extract_availability(element)
        self.assertEqual(availability, 'in_stock')
        
        # Test out of stock
        html = '<div class="product"><div class="out-of-stock">Hết hàng</div></div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product')
        
        availability = self.parser._extract_availability(element)
        self.assertEqual(availability, 'out_of_stock')
    
    def test_extract_product_flags(self):
        """Test product flags extraction."""
        html = '''
        <div class="product">
            <span class="badge sale">Sale</span>
            <span class="badge hot">Hot</span>
            <span class="badge new">New</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.product')
        
        flags = self.parser._extract_product_flags(element)
        
        self.assertTrue(flags['is_sale'])
        self.assertTrue(flags['is_bestseller'])  # 'hot' maps to bestseller
        self.assertTrue(flags['is_new'])
        self.assertFalse(flags['is_featured'])
    
    def test_extract_slug_from_url(self):
        """Test slug extraction from URLs."""
        test_cases = [
            ('/san-pham/son-moi-maybelline', 'son-moi-maybelline'),
            ('https://bestmua.vn/category/makeup/lipstick', 'lipstick'),
            ('/product/test-product-name', 'test-product-name'),
            ('invalid-url', 'unknown'),
            ('', 'unknown')
        ]
        
        for url, expected_slug in test_cases:
            with self.subTest(url=url):
                result = self.parser._extract_slug_from_url(url)
                self.assertEqual(result, expected_slug)
    
    def test_get_page_url(self):
        """Test page URL generation."""
        base_url = "https://bestmua.vn/category/lipstick"
        
        # First page should return base URL
        page1_url = self.parser._get_page_url(base_url, 1)
        self.assertEqual(page1_url, base_url)
        
        # Subsequent pages should add page parameter
        page2_url = self.parser._get_page_url(base_url, 2)
        self.assertEqual(page2_url, base_url + "?page=2")
        
        # URL with existing parameters
        base_url_with_params = "https://bestmua.vn/category/lipstick?sort=price"
        page2_url = self.parser._get_page_url(base_url_with_params, 2)
        self.assertEqual(page2_url, base_url_with_params + "&page=2")
    
    def test_extract_from_structured_data(self):
        """Test product extraction from JSON-LD structured data."""
        structured_data_html = '''
        <html>
        <body>
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "Test Product",
            "url": "/product/test",
            "offers": {
                "price": "299000"
            },
            "image": ["/image1.jpg", "/image2.jpg"],
            "aggregateRating": {
                "ratingValue": "4.5",
                "reviewCount": "100"
            }
        }
        </script>
        </body>
        </html>
        '''
        
        soup = BeautifulSoup(structured_data_html, 'html.parser')
        products = self.parser._extract_from_structured_data(soup)
        
        self.assertEqual(len(products), 1)
        
        product = products[0]
        self.assertEqual(product['name'], 'Test Product')
        self.assertEqual(product['url'], '/product/test')
        self.assertEqual(product['price'], 299000.0)
        self.assertEqual(product['rating'], 4.5)
        self.assertEqual(product['review_count'], 100)
        self.assertEqual(product['image_url'], '/image1.jpg')
    
    @patch('requests.Session.get')
    def test_has_next_page_true(self, mock_get):
        """Test next page detection when next page exists."""
        html_with_next = '''
        <html>
        <body>
        <div class="pagination">
            <a class="next" href="/page/2">Next</a>
        </div>
        </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.content = html_with_next.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        has_next = self.parser._has_next_page("https://bestmua.vn/category/test")
        self.assertTrue(has_next)
    
    @patch('requests.Session.get')
    def test_has_next_page_false(self, mock_get):
        """Test next page detection when no next page exists."""
        html_without_next = '''
        <html>
        <body>
        <div class="pagination">
            <span class="current">1</span>
        </div>
        </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.content = html_without_next.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        has_next = self.parser._has_next_page("https://bestmua.vn/category/test")
        self.assertFalse(has_next)


if __name__ == '__main__':
    unittest.main()