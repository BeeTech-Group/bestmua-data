"""Unit tests for product detail parsing module."""

import unittest
from unittest.mock import Mock, patch
import json
from bs4 import BeautifulSoup

from bestmua_data.detail_parser import ProductDetailParser
from fixtures.sample_data import SAMPLE_PRODUCT_DETAIL_HTML


class TestProductDetailParser(unittest.TestCase):
    """Test cases for ProductDetailParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.parser = ProductDetailParser(
            base_url="https://bestmua.vn",
            session=self.mock_session
        )
    
    def test_init(self):
        """Test ProductDetailParser initialization."""
        parser = ProductDetailParser()
        self.assertEqual(parser.base_url, "https://bestmua.vn")
        self.assertIsNotNone(parser.session)
    
    @patch('requests.Session.get')
    def test_parse_product_detail_success(self, mock_get):
        """Test successful product detail parsing."""
        mock_response = Mock()
        mock_response.content = SAMPLE_PRODUCT_DETAIL_HTML.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        product_url = "https://bestmua.vn/san-pham/son-moi-maybelline-super-stay"
        product = self.parser.parse_product_detail(product_url)
        
        self.assertIsNotNone(product)
        self.assertIn('name', product)
        self.assertIn('url', product)
        self.assertIn('slug', product)
        self.assertEqual(product['url'], product_url)
        self.assertEqual(product['slug'], 'son-moi-maybelline-super-stay')
    
    @patch('requests.Session.get')
    def test_parse_product_detail_network_error(self, mock_get):
        """Test product detail parsing with network error."""
        mock_get.side_effect = Exception("Network error")
        
        product = self.parser.parse_product_detail("https://bestmua.vn/test")
        
        self.assertIsNone(product)
    
    def test_extract_from_structured_data(self):
        """Test extraction from JSON-LD structured data."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        product = self.parser._extract_from_structured_data(soup)
        
        self.assertIsNotNone(product)
        self.assertEqual(product['name'], 'Son môi Maybelline Super Stay Matte Ink Liquid Lipstick')
        self.assertEqual(product['sku'], 'MLB-SS-001')
        self.assertEqual(product['brand_name'], 'Maybelline')
        self.assertEqual(product['price'], 299000.0)
        self.assertEqual(product['rating'], 4.5)
        self.assertEqual(product['review_count'], 123)
        self.assertIn('availability', product)
    
    def test_extract_from_html(self):
        """Test extraction from HTML elements."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        product = self.parser._extract_from_html(soup)
        
        self.assertIsNotNone(product)
        self.assertIn('name', product)
        self.assertIn('description', product)
        self.assertIn('price', product)
        self.assertIn('brand_name', product)
    
    def test_extract_product_name(self):
        """Test product name extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        name = self.parser._extract_product_name(soup)
        
        self.assertEqual(name, 'Son môi Maybelline Super Stay Matte Ink Liquid Lipstick')
    
    def test_extract_product_name_missing(self):
        """Test product name extraction when missing."""
        html = '<html><body><div>No title</div></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        name = self.parser._extract_product_name(soup)
        
        self.assertEqual(name, '')
    
    def test_extract_description(self):
        """Test description extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        description = self.parser._extract_description(soup)
        
        self.assertIn('Son môi lâu trôi', description)
        self.assertIn('SuperStay', description)
    
    def test_extract_price_info(self):
        """Test price information extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        price_info = self.parser._extract_price_info(soup)
        
        self.assertEqual(price_info['price'], 299000.0)
        self.assertEqual(price_info['original_price'], 399000.0)
        self.assertIn('discount_percentage', price_info)
    
    def test_parse_price(self):
        """Test price parsing from text."""
        test_cases = [
            ('299,000đ', 299000.0),
            ('450.000 VND', 450000.0),
            ('1,234.56', 1234.56),
            ('invalid', None),
            ('', None),
            (None, None)
        ]
        
        for price_text, expected in test_cases:
            with self.subTest(price_text=price_text):
                result = self.parser._parse_price(price_text)
                self.assertEqual(result, expected)
    
    def test_extract_images(self):
        """Test image extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        image_info = self.parser._extract_images(soup)
        
        self.assertIn('image_url', image_info)
        self.assertIn('images', image_info)
        
        # Parse images JSON
        images = json.loads(image_info['images'])
        self.assertIsInstance(images, list)
        self.assertGreater(len(images), 0)
    
    def test_extract_sku(self):
        """Test SKU extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        sku = self.parser._extract_sku(soup)
        
        self.assertEqual(sku, 'MLB-SS-001')
    
    def test_extract_sku_missing(self):
        """Test SKU extraction when missing."""
        html = '<html><body><div>No SKU</div></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        sku = self.parser._extract_sku(soup)
        
        self.assertEqual(sku, '')
    
    def test_extract_brand(self):
        """Test brand extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        brand = self.parser._extract_brand(soup)
        
        self.assertEqual(brand, 'Maybelline')
    
    def test_extract_availability(self):
        """Test availability extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        availability = self.parser._extract_availability(soup)
        
        self.assertEqual(availability, 'in_stock')
    
    def test_extract_availability_out_of_stock(self):
        """Test availability extraction for out of stock."""
        html = '''
        <html>
        <body>
        <div class="availability">Hết hàng</div>
        </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        availability = self.parser._extract_availability(soup)
        
        self.assertEqual(availability, 'out_of_stock')
    
    def test_extract_rating_info(self):
        """Test rating information extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        rating_info = self.parser._extract_rating_info(soup)
        
        self.assertEqual(rating_info['rating'], 4.5)
        self.assertEqual(rating_info['review_count'], 123)
    
    def test_parse_rating(self):
        """Test rating parsing."""
        # Test with data attribute
        html = '<div class="rating" data-rating="4.5">Stars</div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.rating')
        
        rating = self.parser._parse_rating(element)
        self.assertEqual(rating, 4.5)
        
        # Test with text content
        html = '<div class="rating">Rating: 4.2/5</div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.rating')
        
        rating = self.parser._parse_rating(element)
        self.assertEqual(rating, 4.2)
        
        # Test with no rating
        html = '<div class="rating">No rating</div>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one('.rating')
        
        rating = self.parser._parse_rating(element)
        self.assertIsNone(rating)
    
    def test_parse_review_count(self):
        """Test review count parsing."""
        test_cases = [
            ('123 đánh giá', 123),
            ('1,234 reviews', 1234),
            ('(89)', 89),
            ('No reviews', None),
            ('', None)
        ]
        
        for review_text, expected in test_cases:
            with self.subTest(review_text=review_text):
                result = self.parser._parse_review_count(review_text)
                self.assertEqual(result, expected)
    
    def test_extract_additional_info(self):
        """Test additional information extraction."""
        soup = BeautifulSoup(SAMPLE_PRODUCT_DETAIL_HTML, 'html.parser')
        
        additional_info = self.parser._extract_additional_info(soup)
        
        self.assertIn('ingredients', additional_info)
        self.assertIn('usage_instructions', additional_info)
        self.assertIn('Dimethicone', additional_info['ingredients'])
        self.assertIn('Thoa đều', additional_info['usage_instructions'])
    
    def test_extract_product_flags(self):
        """Test product flags extraction."""
        html = '''
        <html>
        <body>
        <div class="badges">
            <span class="badge sale">Sale</span>
            <span class="badge new">New</span>
        </div>
        </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        flags = self.parser._extract_product_flags(soup)
        
        self.assertTrue(flags['is_sale'])
        self.assertTrue(flags['is_new'])
        self.assertFalse(flags['is_featured'])
        self.assertFalse(flags['is_bestseller'])
    
    def test_make_absolute_url(self):
        """Test URL conversion to absolute."""
        test_cases = [
            ('https://example.com/image.jpg', 'https://example.com/image.jpg'),
            ('/images/product.jpg', 'https://bestmua.vn/images/product.jpg'),
            ('image.jpg', 'image.jpg')  # Relative URLs without / are returned as-is
        ]
        
        for input_url, expected_url in test_cases:
            with self.subTest(input_url=input_url):
                result = self.parser._make_absolute_url(input_url)
                self.assertEqual(result, expected_url)
    
    def test_extract_slug_from_url(self):
        """Test slug extraction from URL."""
        test_cases = [
            ('https://bestmua.vn/san-pham/son-moi-maybelline', 'son-moi-maybelline'),
            ('/product/test-product', 'test-product'),
            ('invalid-url', 'unknown'),
            ('', 'unknown')
        ]
        
        for url, expected_slug in test_cases:
            with self.subTest(url=url):
                result = self.parser._extract_slug_from_url(url)
                self.assertEqual(result, expected_slug)
    
    def test_parse_structured_product(self):
        """Test parsing structured product data."""
        structured_data = {
            "@type": "Product",
            "name": "Test Product",
            "description": "Test description",
            "sku": "TEST-001",
            "brand": {"name": "Test Brand"},
            "offers": {
                "price": "299000",
                "priceCurrency": "VND",
                "availability": "https://schema.org/InStock"
            },
            "image": ["/image1.jpg", "/image2.jpg"],
            "aggregateRating": {
                "ratingValue": "4.5",
                "reviewCount": "100"
            },
            "category": "Test Category"
        }
        
        product = self.parser._parse_structured_product(structured_data)
        
        self.assertEqual(product['name'], 'Test Product')
        self.assertEqual(product['description'], 'Test description')
        self.assertEqual(product['sku'], 'TEST-001')
        self.assertEqual(product['brand_name'], 'Test Brand')
        self.assertEqual(product['price'], 299000.0)
        self.assertEqual(product['availability'], 'instock')
        self.assertEqual(product['currency'], 'VND')
        self.assertEqual(product['rating'], 4.5)
        self.assertEqual(product['review_count'], 100)
        self.assertEqual(product['category_name'], 'Test Category')
        
        # Test images
        images = json.loads(product['images'])
        self.assertEqual(len(images), 2)
        self.assertIn('/image1.jpg', images)


if __name__ == '__main__':
    unittest.main()