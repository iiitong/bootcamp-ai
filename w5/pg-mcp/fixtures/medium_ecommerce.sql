-- =============================================================================
-- Medium Database: E-Commerce Platform
-- Tables: 15 | Views: 5 | Custom Types: 6 | Indexes: ~25
-- Data: 100-500 rows per table
-- =============================================================================

-- Drop existing objects
DROP SCHEMA IF EXISTS ecommerce CASCADE;
CREATE SCHEMA ecommerce;
SET search_path TO ecommerce;

-- =============================================================================
-- Custom Types
-- =============================================================================

CREATE TYPE order_status AS ENUM ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded');
CREATE TYPE payment_status AS ENUM ('pending', 'authorized', 'captured', 'failed', 'refunded');
CREATE TYPE payment_method AS ENUM ('credit_card', 'debit_card', 'paypal', 'bank_transfer', 'crypto');
CREATE TYPE shipping_method AS ENUM ('standard', 'express', 'overnight', 'pickup');
CREATE TYPE product_status AS ENUM ('draft', 'active', 'out_of_stock', 'discontinued');
CREATE TYPE address_type AS ENUM ('billing', 'shipping', 'both');

-- =============================================================================
-- Tables
-- =============================================================================

-- Categories (hierarchical)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    image_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE categories IS 'Product categories with hierarchical structure';

-- Suppliers
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    contact_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    country VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE suppliers IS 'Product suppliers and vendors';

-- Products
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    sku VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(12, 2) NOT NULL CHECK (price >= 0),
    cost_price DECIMAL(12, 2) CHECK (cost_price >= 0),
    compare_at_price DECIMAL(12, 2) CHECK (compare_at_price >= 0),
    weight_kg DECIMAL(8, 3),
    status product_status NOT NULL DEFAULT 'draft',
    is_featured BOOLEAN DEFAULT FALSE,
    meta_title VARCHAR(255),
    meta_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE products IS 'Product catalog';
COMMENT ON COLUMN products.compare_at_price IS 'Original price for showing discounts';

-- Product Variants (size, color, etc.)
CREATE TABLE product_variants (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    price_modifier DECIMAL(12, 2) DEFAULT 0,
    weight_modifier DECIMAL(8, 3) DEFAULT 0,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Inventory
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id INTEGER REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    reorder_level INTEGER DEFAULT 10,
    reorder_quantity INTEGER DEFAULT 50,
    warehouse_location VARCHAR(50),
    last_restock_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, variant_id)
);

COMMENT ON TABLE inventory IS 'Stock levels for products and variants';

-- Customers
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(50),
    date_of_birth DATE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    accepts_marketing BOOLEAN DEFAULT FALSE,
    total_orders INTEGER DEFAULT 0,
    total_spent DECIMAL(12, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE customers IS 'Registered customers';

-- Customer Addresses
CREATE TABLE addresses (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    address_type address_type NOT NULL DEFAULT 'both',
    is_default BOOLEAN DEFAULT FALSE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company VARCHAR(200),
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) NOT NULL,
    phone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    status order_status NOT NULL DEFAULT 'pending',
    subtotal DECIMAL(12, 2) NOT NULL,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    shipping_amount DECIMAL(12, 2) DEFAULT 0,
    discount_amount DECIMAL(12, 2) DEFAULT 0,
    total_amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    shipping_address_id INTEGER REFERENCES addresses(id),
    billing_address_id INTEGER REFERENCES addresses(id),
    shipping_method shipping_method,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    shipped_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE orders IS 'Customer orders';

-- Order Items
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL,
    product_name VARCHAR(255) NOT NULL,
    variant_name VARCHAR(100),
    sku VARCHAR(100),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(12, 2) NOT NULL,
    total_price DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Payments
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    payment_method payment_method NOT NULL,
    status payment_status NOT NULL DEFAULT 'pending',
    amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    transaction_id VARCHAR(255),
    gateway_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Shipping
CREATE TABLE shipments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    carrier VARCHAR(100),
    tracking_number VARCHAR(255),
    shipping_method shipping_method NOT NULL,
    estimated_delivery DATE,
    actual_delivery DATE,
    weight_kg DECIMAL(8, 3),
    shipping_cost DECIMAL(12, 2),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    shipped_at TIMESTAMP WITH TIME ZONE
);

-- Coupons
CREATE TABLE coupons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('percentage', 'fixed_amount')),
    discount_value DECIMAL(12, 2) NOT NULL,
    min_order_amount DECIMAL(12, 2),
    max_uses INTEGER,
    used_count INTEGER DEFAULT 0,
    starts_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Order Coupons (applied coupons)
CREATE TABLE order_coupons (
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    coupon_id INTEGER NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
    discount_applied DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (order_id, coupon_id)
);

-- Product Reviews
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(255),
    content TEXT,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Shopping Cart
CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 days')
);

-- Cart Items
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id INTEGER REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Categories
CREATE INDEX idx_categories_parent_id ON categories(parent_id);
CREATE INDEX idx_categories_is_active ON categories(is_active);

-- Products
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_supplier_id ON products(supplier_id);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_is_featured ON products(is_featured) WHERE is_featured = TRUE;
CREATE INDEX idx_products_created_at ON products(created_at DESC);
CREATE INDEX idx_products_name_search ON products USING GIN (to_tsvector('english', name));

-- Product Variants
CREATE INDEX idx_product_variants_product_id ON product_variants(product_id);

-- Inventory
CREATE INDEX idx_inventory_product_id ON inventory(product_id);
CREATE INDEX idx_inventory_low_stock ON inventory(quantity) WHERE quantity <= reorder_level;

-- Customers
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_created_at ON customers(created_at);

-- Addresses
CREATE INDEX idx_addresses_customer_id ON addresses(customer_id);

-- Orders
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_orders_order_number ON orders(order_number);

-- Order Items
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

-- Payments
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);

-- Reviews
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
CREATE INDEX idx_reviews_customer_id ON reviews(customer_id);
CREATE INDEX idx_reviews_rating ON reviews(rating);

-- Carts
CREATE INDEX idx_carts_customer_id ON carts(customer_id);
CREATE INDEX idx_carts_session_id ON carts(session_id);

-- =============================================================================
-- Views
-- =============================================================================

-- Product catalog with inventory and reviews
CREATE VIEW product_catalog AS
SELECT
    p.id,
    p.sku,
    p.name,
    p.description,
    p.price,
    p.compare_at_price,
    p.status,
    p.is_featured,
    c.name AS category_name,
    c.slug AS category_slug,
    s.name AS supplier_name,
    COALESCE(i.quantity, 0) - COALESCE(i.reserved_quantity, 0) AS available_stock,
    COALESCE(r.avg_rating, 0) AS avg_rating,
    COALESCE(r.review_count, 0) AS review_count
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN suppliers s ON p.supplier_id = s.id
LEFT JOIN (
    SELECT product_id, SUM(quantity) AS quantity, SUM(reserved_quantity) AS reserved_quantity
    FROM inventory GROUP BY product_id
) i ON p.id = i.product_id
LEFT JOIN (
    SELECT product_id, AVG(rating)::DECIMAL(3,2) AS avg_rating, COUNT(*) AS review_count
    FROM reviews WHERE is_approved = TRUE GROUP BY product_id
) r ON p.id = r.product_id
WHERE p.status = 'active';

-- Customer order summary
CREATE VIEW customer_orders_summary AS
SELECT
    c.id AS customer_id,
    c.email,
    c.first_name,
    c.last_name,
    COUNT(DISTINCT o.id) AS order_count,
    SUM(o.total_amount) AS lifetime_value,
    AVG(o.total_amount) AS avg_order_value,
    MAX(o.created_at) AS last_order_date,
    MIN(o.created_at) AS first_order_date
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id AND o.status NOT IN ('cancelled', 'refunded')
GROUP BY c.id, c.email, c.first_name, c.last_name;

-- Daily sales report
CREATE VIEW daily_sales AS
SELECT
    DATE(o.created_at) AS order_date,
    COUNT(DISTINCT o.id) AS order_count,
    SUM(o.subtotal) AS gross_sales,
    SUM(o.discount_amount) AS total_discounts,
    SUM(o.tax_amount) AS total_tax,
    SUM(o.shipping_amount) AS total_shipping,
    SUM(o.total_amount) AS net_sales,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(oi.quantity) AS items_sold
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY DATE(o.created_at)
ORDER BY order_date DESC;

-- Top selling products
CREATE VIEW top_products AS
SELECT
    p.id,
    p.sku,
    p.name,
    c.name AS category,
    SUM(oi.quantity) AS total_sold,
    SUM(oi.total_price) AS total_revenue,
    COUNT(DISTINCT oi.order_id) AS order_count
FROM products p
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id AND o.status NOT IN ('cancelled', 'refunded')
LEFT JOIN categories c ON p.category_id = c.id
GROUP BY p.id, p.sku, p.name, c.name
ORDER BY total_sold DESC;

-- Low stock alert
CREATE VIEW low_stock_products AS
SELECT
    p.id,
    p.sku,
    p.name,
    p.status,
    s.name AS supplier_name,
    s.email AS supplier_email,
    i.quantity AS current_stock,
    i.reserved_quantity,
    i.reorder_level,
    i.reorder_quantity,
    i.warehouse_location
FROM products p
JOIN inventory i ON p.id = i.product_id
LEFT JOIN suppliers s ON p.supplier_id = s.id
WHERE i.quantity <= i.reorder_level
  AND p.status = 'active'
ORDER BY i.quantity ASC;

-- =============================================================================
-- Sample Data Generation Functions
-- =============================================================================

-- Generate sample data
DO $$
DECLARE
    i INTEGER;
    j INTEGER;
    customer_count INTEGER := 200;
    product_count INTEGER := 150;
    order_count INTEGER := 500;
    v_category_id INTEGER;
    v_supplier_id INTEGER;
    v_product_id INTEGER;
    v_customer_id INTEGER;
    v_order_id INTEGER;
    v_address_id INTEGER;
    v_order_total DECIMAL;
    v_item_count INTEGER;
    v_random_status order_status;
BEGIN
    -- Insert Categories
    INSERT INTO categories (name, slug, description, sort_order) VALUES
    ('Electronics', 'electronics', 'Electronic devices and accessories', 1),
    ('Clothing', 'clothing', 'Apparel and fashion', 2),
    ('Home & Garden', 'home-garden', 'Home improvement and garden supplies', 3),
    ('Sports', 'sports', 'Sports equipment and outdoor gear', 4),
    ('Books', 'books', 'Books and educational materials', 5);

    -- Subcategories
    INSERT INTO categories (parent_id, name, slug, description, sort_order) VALUES
    (1, 'Smartphones', 'smartphones', 'Mobile phones and accessories', 1),
    (1, 'Laptops', 'laptops', 'Notebook computers', 2),
    (1, 'Audio', 'audio', 'Headphones and speakers', 3),
    (1, 'Cameras', 'cameras', 'Digital cameras', 4),
    (2, 'Men', 'men-clothing', 'Men''s clothing', 1),
    (2, 'Women', 'women-clothing', 'Women''s clothing', 2),
    (2, 'Kids', 'kids-clothing', 'Children''s clothing', 3),
    (3, 'Furniture', 'furniture', 'Home furniture', 1),
    (3, 'Kitchen', 'kitchen', 'Kitchen appliances', 2),
    (3, 'Garden', 'garden', 'Garden tools and plants', 3),
    (4, 'Fitness', 'fitness', 'Gym and fitness equipment', 1),
    (4, 'Outdoor', 'outdoor', 'Camping and hiking gear', 2),
    (5, 'Fiction', 'fiction', 'Fiction books', 1),
    (5, 'Non-Fiction', 'non-fiction', 'Educational and reference', 2);

    -- Insert Suppliers
    INSERT INTO suppliers (name, code, contact_name, email, phone, country) VALUES
    ('TechWorld Inc.', 'TECH001', 'John Smith', 'john@techworld.com', '+1-555-0101', 'USA'),
    ('FashionHub Ltd.', 'FASH001', 'Emma Wilson', 'emma@fashionhub.com', '+1-555-0102', 'USA'),
    ('HomeGoods Co.', 'HOME001', 'Michael Brown', 'michael@homegoods.com', '+1-555-0103', 'USA'),
    ('SportsPro', 'SPRT001', 'Sarah Davis', 'sarah@sportspro.com', '+1-555-0104', 'USA'),
    ('BookMasters', 'BOOK001', 'David Lee', 'david@bookmasters.com', '+1-555-0105', 'USA'),
    ('Global Electronics', 'GLBL001', 'Lisa Chen', 'lisa@globalelec.com', '+86-755-1234', 'China'),
    ('EuroFashion', 'EURO001', 'Pierre Martin', 'pierre@eurofashion.com', '+33-1-2345', 'France'),
    ('Tokyo Tech', 'TOKY001', 'Yuki Tanaka', 'yuki@tokyotech.com', '+81-3-5678', 'Japan');

    -- Insert Products
    FOR i IN 1..product_count LOOP
        v_category_id := 6 + (i % 14);  -- Subcategories (6-19)
        v_supplier_id := 1 + (i % 8);

        INSERT INTO products (category_id, supplier_id, sku, name, description, price, cost_price, compare_at_price, weight_kg, status, is_featured)
        VALUES (
            v_category_id,
            v_supplier_id,
            'SKU-' || LPAD(i::TEXT, 6, '0'),
            'Product ' || i || ' - ' || CASE (i % 10)
                WHEN 0 THEN 'Premium Edition'
                WHEN 1 THEN 'Standard'
                WHEN 2 THEN 'Pro Series'
                WHEN 3 THEN 'Basic Model'
                WHEN 4 THEN 'Deluxe'
                WHEN 5 THEN 'Limited Edition'
                WHEN 6 THEN 'Classic'
                WHEN 7 THEN 'Sport'
                WHEN 8 THEN 'Essential'
                ELSE 'Value Pack'
            END,
            'High quality product with excellent features. Product number ' || i || '.',
            (random() * 500 + 10)::DECIMAL(12,2),
            (random() * 200 + 5)::DECIMAL(12,2),
            CASE WHEN random() > 0.7 THEN (random() * 600 + 20)::DECIMAL(12,2) ELSE NULL END,
            (random() * 10 + 0.1)::DECIMAL(8,3),
            CASE (i % 20) WHEN 0 THEN 'out_of_stock'::product_status WHEN 1 THEN 'draft'::product_status ELSE 'active'::product_status END,
            (i % 15 = 0)
        )
        RETURNING id INTO v_product_id;

        -- Add inventory
        INSERT INTO inventory (product_id, quantity, reserved_quantity, reorder_level, reorder_quantity, warehouse_location)
        VALUES (
            v_product_id,
            (random() * 200)::INTEGER,
            (random() * 20)::INTEGER,
            10 + (random() * 20)::INTEGER,
            50 + (random() * 100)::INTEGER,
            'WH-' || (1 + (i % 5))::TEXT || '-' || CHR(65 + (i % 26)) || (1 + (i % 10))::TEXT
        );
    END LOOP;

    -- Insert Customers
    FOR i IN 1..customer_count LOOP
        INSERT INTO customers (email, password_hash, first_name, last_name, phone, is_verified, is_active, accepts_marketing)
        VALUES (
            'customer' || i || '@example.com',
            '$2b$12$hash' || i,
            CASE (i % 20)
                WHEN 0 THEN 'James' WHEN 1 THEN 'Mary' WHEN 2 THEN 'John' WHEN 3 THEN 'Patricia'
                WHEN 4 THEN 'Robert' WHEN 5 THEN 'Jennifer' WHEN 6 THEN 'Michael' WHEN 7 THEN 'Linda'
                WHEN 8 THEN 'William' WHEN 9 THEN 'Elizabeth' WHEN 10 THEN 'David' WHEN 11 THEN 'Barbara'
                WHEN 12 THEN 'Richard' WHEN 13 THEN 'Susan' WHEN 14 THEN 'Joseph' WHEN 15 THEN 'Jessica'
                WHEN 16 THEN 'Thomas' WHEN 17 THEN 'Sarah' WHEN 18 THEN 'Charles' ELSE 'Karen'
            END,
            CASE (i % 15)
                WHEN 0 THEN 'Smith' WHEN 1 THEN 'Johnson' WHEN 2 THEN 'Williams' WHEN 3 THEN 'Brown'
                WHEN 4 THEN 'Jones' WHEN 5 THEN 'Garcia' WHEN 6 THEN 'Miller' WHEN 7 THEN 'Davis'
                WHEN 8 THEN 'Rodriguez' WHEN 9 THEN 'Martinez' WHEN 10 THEN 'Hernandez' WHEN 11 THEN 'Lopez'
                WHEN 12 THEN 'Gonzalez' WHEN 13 THEN 'Wilson' ELSE 'Anderson'
            END,
            '+1-555-' || LPAD((1000 + i)::TEXT, 4, '0'),
            (random() > 0.2),
            (random() > 0.05),
            (random() > 0.5)
        )
        RETURNING id INTO v_customer_id;

        -- Add addresses
        FOR j IN 1..LEAST(2, 1 + (i % 3)) LOOP
            INSERT INTO addresses (customer_id, address_type, is_default, first_name, last_name, address_line1, city, state, postal_code, country)
            VALUES (
                v_customer_id,
                CASE j WHEN 1 THEN 'both'::address_type ELSE 'shipping'::address_type END,
                (j = 1),
                (SELECT first_name FROM customers WHERE id = v_customer_id),
                (SELECT last_name FROM customers WHERE id = v_customer_id),
                (100 + (i * j)) || ' Main Street',
                CASE (i % 10)
                    WHEN 0 THEN 'New York' WHEN 1 THEN 'Los Angeles' WHEN 2 THEN 'Chicago'
                    WHEN 3 THEN 'Houston' WHEN 4 THEN 'Phoenix' WHEN 5 THEN 'Philadelphia'
                    WHEN 6 THEN 'San Antonio' WHEN 7 THEN 'San Diego' WHEN 8 THEN 'Dallas' ELSE 'Seattle'
                END,
                CASE (i % 5)
                    WHEN 0 THEN 'NY' WHEN 1 THEN 'CA' WHEN 2 THEN 'IL' WHEN 3 THEN 'TX' ELSE 'WA'
                END,
                LPAD(((10000 + i * j) % 99999)::TEXT, 5, '0'),
                'USA'
            );
        END LOOP;
    END LOOP;

    -- Insert Coupons
    INSERT INTO coupons (code, description, discount_type, discount_value, min_order_amount, max_uses, starts_at, expires_at) VALUES
    ('WELCOME10', 'Welcome discount 10%', 'percentage', 10, 50, 1000, NOW() - INTERVAL '30 days', NOW() + INTERVAL '365 days'),
    ('SUMMER20', 'Summer sale 20% off', 'percentage', 20, 100, 500, NOW() - INTERVAL '10 days', NOW() + INTERVAL '60 days'),
    ('FLAT25', '$25 off orders over $150', 'fixed_amount', 25, 150, 200, NOW() - INTERVAL '5 days', NOW() + INTERVAL '30 days'),
    ('VIP15', 'VIP member discount', 'percentage', 15, 0, NULL, NOW() - INTERVAL '60 days', NOW() + INTERVAL '300 days'),
    ('FREESHIP', 'Free shipping (min $75)', 'fixed_amount', 10, 75, 1000, NOW(), NOW() + INTERVAL '90 days');

    -- Insert Orders
    FOR i IN 1..order_count LOOP
        v_customer_id := 1 + (i % customer_count);

        SELECT id INTO v_address_id FROM addresses WHERE customer_id = v_customer_id AND is_default = TRUE LIMIT 1;

        v_random_status := (ARRAY['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']::order_status[])
                           [1 + (i % 6)];

        INSERT INTO orders (customer_id, order_number, status, subtotal, tax_amount, shipping_amount, discount_amount, total_amount, shipping_address_id, billing_address_id, shipping_method, created_at)
        VALUES (
            v_customer_id,
            'ORD-' || TO_CHAR(NOW() - (i || ' hours')::INTERVAL, 'YYYYMMDD') || '-' || LPAD(i::TEXT, 5, '0'),
            v_random_status,
            0, 0, (random() * 15)::DECIMAL(12,2), 0, 0,
            v_address_id, v_address_id,
            (ARRAY['standard', 'express', 'overnight', 'pickup']::shipping_method[])[1 + (i % 4)],
            NOW() - ((i * 2) || ' hours')::INTERVAL
        )
        RETURNING id INTO v_order_id;

        -- Add 1-5 items per order
        v_item_count := 1 + (i % 5);
        v_order_total := 0;

        FOR j IN 1..v_item_count LOOP
            DECLARE
                v_prod_id INTEGER;
                v_prod_price DECIMAL;
                v_qty INTEGER;
                v_line_total DECIMAL;
            BEGIN
                v_prod_id := 1 + ((i + j * 17) % product_count);
                SELECT price INTO v_prod_price FROM products WHERE id = v_prod_id;
                v_qty := 1 + (j % 3);
                v_line_total := v_prod_price * v_qty;

                INSERT INTO order_items (order_id, product_id, product_name, sku, quantity, unit_price, total_price)
                SELECT v_order_id, id, name, sku, v_qty, price, v_line_total
                FROM products WHERE id = v_prod_id;

                v_order_total := v_order_total + v_line_total;
            END;
        END LOOP;

        -- Update order totals
        UPDATE orders SET
            subtotal = v_order_total,
            tax_amount = (v_order_total * 0.08)::DECIMAL(12,2),
            total_amount = v_order_total + (v_order_total * 0.08) + shipping_amount - discount_amount
        WHERE id = v_order_id;

        -- Add payment
        INSERT INTO payments (order_id, payment_method, status, amount)
        SELECT id, (ARRAY['credit_card', 'debit_card', 'paypal']::payment_method[])[1 + (i % 3)],
               CASE status
                   WHEN 'cancelled' THEN 'failed'::payment_status
                   WHEN 'pending' THEN 'pending'::payment_status
                   ELSE 'captured'::payment_status
               END,
               total_amount
        FROM orders WHERE id = v_order_id;

        -- Add shipment for shipped/delivered orders
        IF v_random_status IN ('shipped', 'delivered') THEN
            INSERT INTO shipments (order_id, carrier, tracking_number, shipping_method, status, shipped_at)
            SELECT id, CASE (i % 4) WHEN 0 THEN 'UPS' WHEN 1 THEN 'FedEx' WHEN 2 THEN 'USPS' ELSE 'DHL' END,
                   'TRK' || LPAD(i::TEXT, 12, '0'),
                   shipping_method,
                   CASE status WHEN 'delivered' THEN 'delivered' ELSE 'in_transit' END,
                   created_at + INTERVAL '1 day'
            FROM orders WHERE id = v_order_id;
        END IF;

        -- Update customer stats
        IF v_random_status NOT IN ('cancelled', 'refunded') THEN
            UPDATE customers SET
                total_orders = total_orders + 1,
                total_spent = total_spent + (SELECT total_amount FROM orders WHERE id = v_order_id)
            WHERE id = v_customer_id;
        END IF;
    END LOOP;

    -- Insert Reviews (about 30% of delivered orders)
    INSERT INTO reviews (product_id, customer_id, order_id, rating, title, content, is_verified_purchase, is_approved)
    SELECT DISTINCT ON (oi.product_id, o.customer_id)
        oi.product_id,
        o.customer_id,
        o.id,
        1 + (random() * 4)::INTEGER,
        CASE (oi.product_id % 5)
            WHEN 0 THEN 'Great product!' WHEN 1 THEN 'Very satisfied' WHEN 2 THEN 'Good value'
            WHEN 3 THEN 'As expected' ELSE 'Highly recommend'
        END,
        'This product met my expectations. Quality is ' ||
        CASE (oi.product_id % 4)
            WHEN 0 THEN 'excellent' WHEN 1 THEN 'very good' WHEN 2 THEN 'decent' ELSE 'as described'
        END || '.',
        TRUE,
        (random() > 0.1)
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.id
    WHERE o.status = 'delivered' AND random() < 0.3
    LIMIT 150;

    -- Insert active carts
    FOR i IN 1..50 LOOP
        INSERT INTO carts (customer_id, session_id)
        VALUES (
            CASE WHEN random() > 0.3 THEN 1 + (i % customer_count) ELSE NULL END,
            'sess_' || md5(i::TEXT || random()::TEXT)
        )
        RETURNING id INTO v_order_id;

        -- Add 1-4 items to cart
        FOR j IN 1..LEAST(4, 1 + (i % 4)) LOOP
            INSERT INTO cart_items (cart_id, product_id, quantity)
            VALUES (v_order_id, 1 + ((i + j * 13) % product_count), 1 + (j % 3))
            ON CONFLICT DO NOTHING;
        END LOOP;
    END LOOP;

END $$;
