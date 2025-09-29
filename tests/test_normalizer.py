"""Unit tests for data normalization module."""

import unittest
import json

from bestmua_data.normalizer import DataNormalizer
from fixtures.sample_data import SAMPLE_RAW_PRODUCT, EDGE_CASE_PRODUCT_DATA


class TestDataNormalizer(unittest.TestCase):
    """Test cases for DataNormalizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = DataNormalizer()
    
    def test_init(self):
        """Test DataNormalizer initialization."""
        normalizer = DataNormalizer()
        self.assertIsNotNone(normalizer.vietnamese_chars_map)
        self.assertIn('á', normalizer.vietnamese_chars_map)
        self.assertEqual(normalizer.vietnamese_chars_map['á'], 'a')
    
    def test_normalize_product_complete(self):
        """Test product normalization with complete data."""
        normalized = self.normalizer.normalize_product(SAMPLE_RAW_PRODUCT)
        
        # Check all required fields are present
        required_fields = ['name', 'slug', 'url', 'price', 'brand_name', 'category_name']
        for field in required_fields:
            self.assertIn(field, normalized)
        
        # Check specific values
        self.assertEqual(normalized['name'], SAMPLE_RAW_PRODUCT['name'])
        self.assertEqual(normalized['slug'], SAMPLE_RAW_PRODUCT['slug'])
        self.assertEqual(normalized['price'], SAMPLE_RAW_PRODUCT['price'])
        self.assertEqual(normalized['rating'], SAMPLE_RAW_PRODUCT['rating'])
        self.assertEqual(normalized['review_count'], SAMPLE_RAW_PRODUCT['review_count'])
        
        # Check boolean flags
        self.assertIsInstance(normalized['is_sale'], bool)
        self.assertIsInstance(normalized['is_new'], bool)
        self.assertIsInstance(normalized['is_bestseller'], bool)
        self.assertIsInstance(normalized['is_featured'], bool)
    
    def test_normalize_product_empty(self):
        """Test product normalization with empty data."""
        empty_product = {}
        normalized = self.normalizer.normalize_product(empty_product)
        
        # Should have default values
        self.assertEqual(normalized['name'], '')
        self.assertEqual(normalized['slug'], '')
        self.assertEqual(normalized['url'], '')
        self.assertIsNone(normalized['price'])
        self.assertEqual(normalized['review_count'], 0)
        self.assertFalse(normalized['is_sale'])
    
    def test_normalize_category(self):
        """Test category normalization."""
        raw_category = {
            'name': 'Son môi',
            'slug': 'son-moi',
            'url': '/danh-muc/son-moi',
            'description': 'Bộ sưu tập son môi đa dạng',
            'parent_slug': 'my-pham'
        }
        
        normalized = self.normalizer.normalize_category(raw_category)
        
        self.assertEqual(normalized['name'], 'Son môi')
        self.assertEqual(normalized['slug'], 'son-moi')
        self.assertEqual(normalized['url'], '/danh-muc/son-moi')
        self.assertEqual(normalized['description'], 'Bộ sưu tập son môi đa dạng')
        self.assertEqual(normalized['parent_slug'], 'my-pham')
    
    def test_normalize_brand(self):
        """Test brand normalization."""
        raw_brand = {
            'name': 'L\'Oréal Paris',
            'slug': 'loreal-paris',
            'url': '/thuong-hieu/loreal-paris',
            'description': 'Thương hiệu mỹ phẩm từ Pháp'
        }
        
        normalized = self.normalizer.normalize_brand(raw_brand)
        
        self.assertEqual(normalized['name'], 'L\'Oréal Paris')
        self.assertEqual(normalized['slug'], 'loreal-paris')
        self.assertEqual(normalized['url'], '/thuong-hieu/loreal-paris')
        self.assertEqual(normalized['description'], 'Thương hiệu mỹ phẩm từ Pháp')
    
    def test_normalize_text(self):
        """Test text normalization."""
        test_cases = [
            ('Normal text', 'Normal text'),
            ('  Extra   spaces  ', 'Extra spaces'),
            ('<p>HTML content</p>', 'HTML content'),
            ('Text with\n\nnewlines', 'Text with newlines'),
            ('', ''),
            (None, ''),
            (123, '123'),
            ('"Smart quotes"', '"Smart quotes"'),
            (''curly quotes'', "'curly quotes'")
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.normalizer.normalize_text(input_text)
                self.assertEqual(result, expected)
    
    def test_normalize_slug(self):
        """Test slug normalization."""
        test_cases = [
            ('Son môi', 'son-moi'),
            ('Phấn mắt 3CE', 'phan-mat-3ce'),
            ('L\'Oréal Paris', 'loreal-paris'),
            ('  Extra  Spaces  ', 'extra-spaces'),
            ('Special!@#$%Characters', 'specialcharacters'),
            ('', 'unknown'),
            (None, 'unknown'),
            ('Sản phẩm làm đẹp', 'san-pham-lam-dep')
        ]
        
        for input_slug, expected in test_cases:
            with self.subTest(input_slug=input_slug):
                result = self.normalizer.normalize_slug(input_slug)
                self.assertEqual(result, expected)
    
    def test_normalize_url(self):
        """Test URL normalization."""
        test_cases = [
            ('/san-pham/test', '/san-pham/test'),
            ('https://example.com/test', 'https://example.com/test'),
            ('san-pham/test', '/san-pham/test'),
            ('', ''),
            (None, ''),
            ('  /test  ', '/test')
        ]
        
        for input_url, expected in test_cases:
            with self.subTest(input_url=input_url):
                result = self.normalizer.normalize_url(input_url)
                self.assertEqual(result, expected)
    
    def test_normalize_price(self):
        """Test price normalization."""
        test_cases = [
            (299000, 299000.0),
            (299000.0, 299000.0),
            ('299000', 299000.0),
            ('299,000', 299000.0),
            ('299.000', 299000.0),
            ('invalid', None),
            ('', None),
            (None, None),
            (-100, None),  # Negative prices should be None
            (0, 0.0)
        ]
        
        for input_price, expected in test_cases:
            with self.subTest(input_price=input_price):
                result = self.normalizer.normalize_price(input_price)
                self.assertEqual(result, expected)
    
    def test_normalize_percentage(self):
        """Test percentage normalization."""
        test_cases = [
            (25, 25.0),
            (25.5, 25.5),
            ('25', 25.0),
            ('25%', 25.0),
            ('25.5%', 25.5),
            (150, None),  # > 100%
            (-10, None),  # < 0%
            ('invalid', None),
            ('', None),
            (None, None)
        ]
        
        for input_percentage, expected in test_cases:
            with self.subTest(input_percentage=input_percentage):
                result = self.normalizer.normalize_percentage(input_percentage)
                self.assertEqual(result, expected)
    
    def test_normalize_rating(self):
        """Test rating normalization."""
        test_cases = [
            (4.5, 4.5),
            (5, 5.0),
            (0, 0.0),
            ('4.5', 4.5),
            (6, None),  # > 5
            (-1, None),  # < 0
            ('invalid', None),
            ('', None),
            (None, None)
        ]
        
        for input_rating, expected in test_cases:
            with self.subTest(input_rating=input_rating):
                result = self.normalizer.normalize_rating(input_rating)
                self.assertEqual(result, expected)
    
    def test_normalize_integer(self):
        """Test integer normalization."""
        test_cases = [
            (123, 123),
            (123.7, 123),
            ('123', 123),
            ('1,234', 1234),
            ('invalid', 0),
            ('', 0),
            (None, 0),
            (-10, 0)  # Negative should become 0
        ]
        
        for input_int, expected in test_cases:
            with self.subTest(input_int=input_int):
                result = self.normalizer.normalize_integer(input_int)
                self.assertEqual(result, expected)
    
    def test_normalize_boolean(self):
        """Test boolean normalization."""
        test_cases = [
            (True, True),
            (False, False),
            ('true', True),
            ('True', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('active', True),
            ('false', False),
            ('0', False),
            ('no', False),
            ('', False),
            (1, True),
            (0, False),
            (123, True),  # Non-zero numbers are True
            (None, False)
        ]
        
        for input_bool, expected in test_cases:
            with self.subTest(input_bool=input_bool):
                result = self.normalizer.normalize_boolean(input_bool)
                self.assertEqual(result, expected)
    
    def test_normalize_sku(self):
        """Test SKU normalization."""
        test_cases = [
            ('MLB-SS-001', 'MLB-SS-001'),
            ('mlb-ss-001', 'MLB-SS-001'),  # Should be uppercase
            ('MLB SS 001', 'MLBSS001'),  # Remove spaces
            ('MLB@SS#001', 'MLBSS001'),  # Remove special chars
            ('', ''),
            (None, ''),
            (123, '123')
        ]
        
        for input_sku, expected in test_cases:
            with self.subTest(input_sku=input_sku):
                result = self.normalizer.normalize_sku(input_sku)
                self.assertEqual(result, expected)
    
    def test_normalize_availability(self):
        """Test availability normalization."""
        test_cases = [
            ('in_stock', 'in_stock'),
            ('instock', 'in_stock'),
            ('available', 'in_stock'),
            ('có sẵn', 'in_stock'),
            ('còn hàng', 'in_stock'),
            ('out_of_stock', 'out_of_stock'),
            ('outofstock', 'out_of_stock'),
            ('hết hàng', 'out_of_stock'),
            ('pre_order', 'pre_order'),
            ('đặt trước', 'pre_order'),
            ('unknown_status', 'unknown'),
            ('', 'unknown'),
            (None, 'unknown')
        ]
        
        for input_availability, expected in test_cases:
            with self.subTest(input_availability=input_availability):
                result = self.normalizer.normalize_availability(input_availability)
                self.assertEqual(result, expected)
    
    def test_normalize_images(self):
        """Test images normalization."""
        # Test JSON array string
        json_array = '["image1.jpg", "image2.jpg"]'
        result = self.normalizer.normalize_images(json_array)
        parsed_result = json.loads(result)
        self.assertIsInstance(parsed_result, list)
        self.assertEqual(len(parsed_result), 2)
        
        # Test single URL string
        single_url = "/images/product.jpg"
        result = self.normalizer.normalize_images(single_url)
        parsed_result = json.loads(result)
        self.assertEqual(parsed_result, ["/images/product.jpg"])
        
        # Test Python list
        url_list = ["/image1.jpg", "/image2.jpg"]
        result = self.normalizer.normalize_images(url_list)
        parsed_result = json.loads(result)
        self.assertEqual(parsed_result, ["/image1.jpg", "/image2.jpg"])
        
        # Test empty input
        result = self.normalizer.normalize_images("")
        self.assertEqual(result, '')
        
        result = self.normalizer.normalize_images(None)
        self.assertEqual(result, '')
    
    def test_normalize_product_with_edge_cases(self):
        """Test product normalization with edge case data."""
        # Test with empty strings
        empty_product = EDGE_CASE_PRODUCT_DATA['empty_strings']
        normalized = self.normalizer.normalize_product(empty_product)
        
        self.assertEqual(normalized['name'], '')
        self.assertEqual(normalized['slug'], '')
        self.assertIsNone(normalized['price'])
        self.assertIsNone(normalized['rating'])
        
        # Test with special characters
        special_product = EDGE_CASE_PRODUCT_DATA['special_characters']
        normalized = self.normalizer.normalize_product(special_product)
        
        # Should clean HTML and special characters
        self.assertNotIn('<script>', normalized['description'])
        self.assertNotIn('&', normalized['name'])
        
        # Test with invalid data types
        invalid_product = EDGE_CASE_PRODUCT_DATA['invalid_data_types']
        normalized = self.normalizer.normalize_product(invalid_product)
        
        self.assertIsNone(normalized['price'])
        self.assertIsNone(normalized['rating'])
        self.assertEqual(normalized['review_count'], 0)
        self.assertIsNone(normalized['discount_percentage'])
    
    def test_validate_normalized_product(self):
        """Test product validation."""
        # Valid product
        valid_product = {
            'name': 'Test Product',
            'slug': 'test-product',
            'url': '/product/test',
            'price': 100.0,
            'rating': 4.5
        }
        
        validation_result = self.normalizer.validate_normalized_product(valid_product)
        
        self.assertTrue(validation_result['is_valid'])
        self.assertEqual(len(validation_result['errors']), 0)
        
        # Invalid product - missing required fields
        invalid_product = {
            'description': 'Test description'
        }
        
        validation_result = self.normalizer.validate_normalized_product(invalid_product)
        
        self.assertFalse(validation_result['is_valid'])
        self.assertGreater(len(validation_result['errors']), 0)
        
        # Product with warnings
        warning_product = {
            'name': 'Test Product',
            'slug': 'test-product',
            'url': '/product/test',
            'price': -100.0,  # Invalid price
            'rating': 10.0  # Invalid rating
        }
        
        validation_result = self.normalizer.validate_normalized_product(warning_product)
        
        self.assertTrue(validation_result['is_valid'])  # Still valid (warnings don't fail validation)
        self.assertGreater(len(validation_result['warnings']), 0)
    
    def test_is_valid_url(self):
        """Test URL validation."""
        test_cases = [
            ('https://example.com', True),
            ('http://example.com/path', True),
            ('/relative/path', True),
            ('ftp://example.com', False),
            ('invalid-url', False),
            ('', False)
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                result = self.normalizer._is_valid_url(url)
                self.assertEqual(result, expected)
    
    def test_vietnamese_chars_map(self):
        """Test Vietnamese character mapping."""
        vietnamese_chars_map = self.normalizer._build_vietnamese_chars_map()
        
        # Test some specific mappings
        self.assertEqual(vietnamese_chars_map['á'], 'a')
        self.assertEqual(vietnamese_chars_map['ế'], 'e')
        self.assertEqual(vietnamese_chars_map['ộ'], 'o')
        self.assertEqual(vietnamese_chars_map['ư'], 'u')
        self.assertEqual(vietnamese_chars_map['đ'], 'd')
        
        # Test uppercase
        self.assertEqual(vietnamese_chars_map['Á'], 'A')
        self.assertEqual(vietnamese_chars_map['Đ'], 'D')


if __name__ == '__main__':
    unittest.main()