"""Test fixtures and sample data."""

# Sample HTML content for testing parsers
SAMPLE_CATEGORY_PAGE_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Danh mục sản phẩm - BestMUA</title>
</head>
<body>
    <nav class="main-menu">
        <a href="/danh-muc/son-moi">Son môi</a>
        <a href="/danh-muc/kem-nen">Kem nền</a>
        <a href="/danh-muc/mascara">Mascara</a>
        <a href="/danh-muc/phan-mat">Phấn mắt</a>
    </nav>
    
    <div class="products-grid">
        <div class="product-item">
            <a href="/san-pham/son-moi-maybelline-super-stay" class="product-title">
                Son môi Maybelline Super Stay Matte Ink Liquid Lipstick
            </a>
            <div class="product-price">
                <span class="price-current">299,000đ</span>
                <span class="price-original">399,000đ</span>
            </div>
            <div class="product-image">
                <img src="/images/maybelline-lipstick.jpg" alt="Son môi Maybelline">
            </div>
            <div class="rating">
                <span data-rating="4.5">★★★★☆</span>
                <span class="review-count">(123 đánh giá)</span>
            </div>
            <div class="badges">
                <span class="badge sale">Sale</span>
                <span class="badge hot">Hot</span>
            </div>
        </div>
        
        <div class="product-item">
            <a href="/san-pham/kem-nen-loreal-true-match" class="product-title">
                Kem nền L'Oreal True Match Foundation
            </a>
            <div class="product-price">
                <span class="price-current">450,000đ</span>
            </div>
            <div class="product-image">
                <img src="/images/loreal-foundation.jpg" alt="Kem nền L'Oreal">
            </div>
            <div class="rating">
                <span data-rating="4.2">★★★★☆</span>
                <span class="review-count">(89 đánh giá)</span>
            </div>
            <div class="badges">
                <span class="badge new">New</span>
            </div>
        </div>
    </div>
</body>
</html>
'''

SAMPLE_PRODUCT_DETAIL_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Son môi Maybelline Super Stay - BestMUA</title>
</head>
<body>
    <div class="product-detail">
        <h1 class="product-title">Son môi Maybelline Super Stay Matte Ink Liquid Lipstick</h1>
        
        <div class="product-gallery">
            <img src="/images/maybelline-lipstick-main.jpg" class="main-image" alt="Son môi Maybelline">
            <div class="thumbnails">
                <img src="/images/maybelline-lipstick-2.jpg" alt="Màu son">
                <img src="/images/maybelline-lipstick-3.jpg" alt="Texture">
            </div>
        </div>
        
        <div class="product-info">
            <div class="price-box">
                <span class="price-current">299,000đ</span>
                <span class="price-original">399,000đ</span>
                <span class="discount">-25%</span>
            </div>
            
            <div class="product-meta">
                <div class="sku">Mã sản phẩm: MLB-SS-001</div>
                <div class="brand">Thương hiệu: Maybelline</div>
                <div class="availability in-stock">Còn hàng</div>
            </div>
            
            <div class="rating-summary">
                <div class="stars" data-rating="4.5">★★★★☆</div>
                <span class="review-count">123 đánh giá</span>
            </div>
            
            <div class="product-description">
                <h3>Mô tả sản phẩm</h3>
                <p>Son môi lâu trôi với công nghệ SuperStay độc quyền, giữ màu đến 16 giờ. 
                Kết cấu mịn màng, không gây khô môi.</p>
            </div>
            
            <div class="ingredients">
                <h3>Thành phần</h3>
                <p>Dimethicone, Trimethylsiloxysilicate, Polybutene, Petrolatum...</p>
            </div>
            
            <div class="usage-instructions">
                <h3>Hướng dẫn sử dụng</h3>
                <p>Thoa đều lên môi từ trong ra ngoài. Chờ khô hoàn toàn trước khi ăn uống.</p>
            </div>
        </div>
    </div>
    
    <script type="application/ld+json">
    {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Son môi Maybelline Super Stay Matte Ink Liquid Lipstick",
        "image": [
            "/images/maybelline-lipstick-main.jpg",
            "/images/maybelline-lipstick-2.jpg",
            "/images/maybelline-lipstick-3.jpg"
        ],
        "description": "Son môi lâu trôi với công nghệ SuperStay độc quyền",
        "sku": "MLB-SS-001",
        "brand": {
            "@type": "Brand",
            "name": "Maybelline"
        },
        "offers": {
            "@type": "Offer",
            "url": "/san-pham/son-moi-maybelline-super-stay",
            "priceCurrency": "VND",
            "price": "299000",
            "availability": "https://schema.org/InStock"
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.5",
            "reviewCount": "123"
        }
    }
    </script>
</body>
</html>
'''

# Sample data structures
SAMPLE_RAW_CATEGORY = {
    'name': 'Son môi',
    'slug': 'son-moi',
    'url': '/danh-muc/son-moi',
    'full_url': 'https://bestmua.vn/danh-muc/son-moi',
    'description': 'Bộ sưu tập son môi đa dạng'
}

SAMPLE_RAW_PRODUCT = {
    'name': 'Son môi Maybelline Super Stay Matte Ink Liquid Lipstick',
    'slug': 'son-moi-maybelline-super-stay',
    'url': '/san-pham/son-moi-maybelline-super-stay',
    'price': 299000.0,
    'original_price': 399000.0,
    'discount_percentage': 25.0,
    'sku': 'MLB-SS-001',
    'brand_name': 'Maybelline',
    'category_name': 'Son môi',
    'availability': 'in_stock',
    'rating': 4.5,
    'review_count': 123,
    'image_url': '/images/maybelline-lipstick-main.jpg',
    'images': '["\/images\/maybelline-lipstick-main.jpg", "\/images\/maybelline-lipstick-2.jpg"]',
    'description': 'Son môi lâu trôi với công nghệ SuperStay độc quyền, giữ màu đến 16 giờ.',
    'ingredients': 'Dimethicone, Trimethylsiloxysilicate, Polybutene, Petrolatum...',
    'usage_instructions': 'Thoa đều lên môi từ trong ra ngoài. Chờ khô hoàn toàn trước khi ăn uống.',
    'is_featured': False,
    'is_bestseller': True,
    'is_new': False,
    'is_sale': True
}

SAMPLE_NORMALIZED_PRODUCT = {
    'name': 'Son môi Maybelline Super Stay Matte Ink Liquid Lipstick',
    'slug': 'son-moi-maybelline-super-stay',
    'url': '/san-pham/son-moi-maybelline-super-stay',
    'description': 'Son môi lâu trôi với công nghệ SuperStay độc quyền, giữ màu đến 16 giờ.',
    'price': 299000.0,
    'original_price': 399000.0,
    'discount_percentage': 25.0,
    'sku': 'MLB-SS-001',
    'availability': 'in_stock',
    'rating': 4.5,
    'review_count': 123,
    'image_url': '/images/maybelline-lipstick-main.jpg',
    'images': '["/images/maybelline-lipstick-main.jpg", "/images/maybelline-lipstick-2.jpg"]',
    'ingredients': 'Dimethicone, Trimethylsiloxysilicate, Polybutene, Petrolatum...',
    'usage_instructions': 'Thoa đều lên môi từ trong ra ngoài. Chờ khô hoàn toàn trước khi ăn uống.',
    'brand_name': 'Maybelline',
    'category_name': 'Son môi',
    'is_featured': False,
    'is_bestseller': True,
    'is_new': False,
    'is_sale': True
}

SAMPLE_RAW_BRAND = {
    'name': 'Maybelline',
    'slug': 'maybelline',
    'url': '/thuong-hieu/maybelline',
    'description': 'Thương hiệu mỹ phẩm nổi tiếng từ Mỹ'
}

# Test data for edge cases
EDGE_CASE_PRODUCT_DATA = {
    'empty_strings': {
        'name': '',
        'slug': '',
        'url': '',
        'price': None,
        'rating': None
    },
    'special_characters': {
        'name': 'Son môi L\'Oréal "Rouge" & Màu <đỏ>',
        'description': 'Mô tả có ký tự đặc biệt: <script>alert("test")</script>',
        'price': '299,000đ'
    },
    'invalid_data_types': {
        'price': 'invalid',
        'rating': 'not_a_number',
        'review_count': 'abc',
        'discount_percentage': 'N/A'
    }
}

# Database test data
DATABASE_TEST_CATEGORIES = [
    {
        'name': 'Son môi',
        'slug': 'son-moi',
        'url': '/danh-muc/son-moi',
        'description': 'Bộ sưu tập son môi'
    },
    {
        'name': 'Son lì',
        'slug': 'son-li',
        'url': '/danh-muc/son-moi/son-li',
        'description': 'Son môi dạng lì',
        'parent_slug': 'son-moi'
    }
]

DATABASE_TEST_BRANDS = [
    {
        'name': 'Maybelline',
        'slug': 'maybelline',
        'url': '/thuong-hieu/maybelline',
        'description': 'Thương hiệu mỹ phẩm từ Mỹ'
    },
    {
        'name': 'L\'Oréal',
        'slug': 'loreal',
        'url': '/thuong-hieu/loreal',
        'description': 'Thương hiệu mỹ phẩm từ Pháp'
    }
]

DATABASE_TEST_PRODUCTS = [
    {
        'name': 'Son môi Maybelline Super Stay',
        'slug': 'son-moi-maybelline-super-stay',
        'url': '/san-pham/son-moi-maybelline-super-stay',
        'description': 'Son môi lâu trôi',
        'price': 299000.0,
        'sku': 'MLB-SS-001',
        'brand_name': 'Maybelline',
        'category_name': 'Son môi',
        'availability': 'in_stock',
        'rating': 4.5,
        'review_count': 123
    },
    {
        'name': 'Kem nền L\'Oréal True Match',
        'slug': 'kem-nen-loreal-true-match',
        'url': '/san-pham/kem-nen-loreal-true-match',
        'description': 'Kem nền che phủ tự nhiên',
        'price': 450000.0,
        'sku': 'LOR-TM-002',
        'brand_name': 'L\'Oréal',
        'category_name': 'Kem nền',
        'availability': 'in_stock',
        'rating': 4.2,
        'review_count': 89
    }
]