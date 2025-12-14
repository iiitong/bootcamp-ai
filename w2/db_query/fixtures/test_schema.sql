-- =============================================================================
-- Test Database Schema and Sample Data
-- Purpose: Create a comprehensive test database for DB Query Tool testing
-- =============================================================================

-- Drop existing tables if they exist (for clean re-runs)
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;

DROP VIEW IF EXISTS v_order_summary;
DROP VIEW IF EXISTS v_product_inventory;
DROP VIEW IF EXISTS v_employee_departments;

-- =============================================================================
-- DEPARTMENTS TABLE
-- =============================================================================
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    budget DECIMAL(15, 2) DEFAULT 0,
    location VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE departments IS 'Company departments';
COMMENT ON COLUMN departments.budget IS 'Annual department budget in USD';

-- =============================================================================
-- EMPLOYEES TABLE
-- =============================================================================
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    employee_code VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    hire_date DATE NOT NULL,
    salary DECIMAL(10, 2),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    manager_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE employees IS 'Company employees with hierarchical management structure';

-- =============================================================================
-- CATEGORIES TABLE
-- =============================================================================
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE categories IS 'Product categories with hierarchical structure';

-- =============================================================================
-- PRODUCTS TABLE
-- =============================================================================
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    name_cn VARCHAR(200),  -- Chinese name for i18n testing
    description TEXT,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    cost DECIMAL(10, 2) CHECK (cost >= 0),
    stock_quantity INTEGER DEFAULT 0 CHECK (stock_quantity >= 0),
    min_stock_level INTEGER DEFAULT 10,
    weight_kg DECIMAL(8, 3),
    dimensions JSONB,  -- {length, width, height}
    tags TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE products IS 'Product catalog with inventory tracking';
COMMENT ON COLUMN products.name_cn IS 'Chinese product name for i18n testing';
COMMENT ON COLUMN products.dimensions IS 'Product dimensions in JSON format';

-- Create index for common queries
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_tags ON products USING GIN(tags);

-- =============================================================================
-- CUSTOMERS TABLE
-- =============================================================================
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    customer_code VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(200),
    contact_name VARCHAR(100) NOT NULL,
    contact_name_cn VARCHAR(100),  -- Chinese name
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'China',
    postal_code VARCHAR(20),
    credit_limit DECIMAL(12, 2) DEFAULT 10000,
    customer_since DATE DEFAULT CURRENT_DATE,
    notes TEXT,
    preferences JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE customers IS 'Customer information with contact details';

-- =============================================================================
-- ORDERS TABLE
-- =============================================================================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(30) NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    required_date DATE,
    shipped_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled')),
    shipping_address TEXT,
    shipping_city VARCHAR(100),
    shipping_country VARCHAR(100),
    shipping_cost DECIMAL(10, 2) DEFAULT 0,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    discount_percent DECIMAL(5, 2) DEFAULT 0 CHECK (discount_percent >= 0 AND discount_percent <= 100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE orders IS 'Customer orders with shipping and status tracking';

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_date ON orders(order_date);

-- =============================================================================
-- ORDER_ITEMS TABLE
-- =============================================================================
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    discount_percent DECIMAL(5, 2) DEFAULT 0 CHECK (discount_percent >= 0 AND discount_percent <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, product_id)
);

COMMENT ON TABLE order_items IS 'Individual items within each order';

-- =============================================================================
-- AUDIT_LOGS TABLE
-- =============================================================================
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

COMMENT ON TABLE audit_logs IS 'System audit trail for data changes';

CREATE INDEX idx_audit_logs_table ON audit_logs(table_name);
CREATE INDEX idx_audit_logs_date ON audit_logs(changed_at);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Order summary view
CREATE VIEW v_order_summary AS
SELECT
    o.id AS order_id,
    o.order_number,
    c.company_name AS customer_name,
    c.contact_name,
    o.order_date,
    o.status,
    COUNT(oi.id) AS item_count,
    SUM(oi.quantity) AS total_quantity,
    SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS subtotal,
    o.shipping_cost,
    o.tax_amount,
    SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) + o.shipping_cost + o.tax_amount AS total_amount
FROM orders o
JOIN customers c ON o.customer_id = c.id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id, o.order_number, c.company_name, c.contact_name, o.order_date, o.status, o.shipping_cost, o.tax_amount;

COMMENT ON VIEW v_order_summary IS 'Aggregated order information with totals';

-- Product inventory view
CREATE VIEW v_product_inventory AS
SELECT
    p.id AS product_id,
    p.sku,
    p.name,
    p.name_cn,
    c.name AS category_name,
    p.price,
    p.cost,
    p.stock_quantity,
    p.min_stock_level,
    CASE
        WHEN p.stock_quantity <= 0 THEN 'Out of Stock'
        WHEN p.stock_quantity <= p.min_stock_level THEN 'Low Stock'
        ELSE 'In Stock'
    END AS stock_status,
    (p.price - COALESCE(p.cost, 0)) AS profit_margin,
    p.is_active
FROM products p
LEFT JOIN categories c ON p.category_id = c.id;

COMMENT ON VIEW v_product_inventory IS 'Product inventory status with stock levels';

-- Employee departments view
CREATE VIEW v_employee_departments AS
SELECT
    e.id AS employee_id,
    e.employee_code,
    e.first_name || ' ' || e.last_name AS full_name,
    e.email,
    d.name AS department_name,
    d.location AS department_location,
    m.first_name || ' ' || m.last_name AS manager_name,
    e.hire_date,
    e.salary,
    e.is_active
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN employees m ON e.manager_id = m.id;

COMMENT ON VIEW v_employee_departments IS 'Employee information with department and manager details';

-- =============================================================================
-- SAMPLE DATA
-- =============================================================================

-- Departments
INSERT INTO departments (name, budget, location) VALUES
('Engineering', 500000.00, 'Building A, Floor 3'),
('Sales', 300000.00, 'Building B, Floor 1'),
('Marketing', 200000.00, 'Building B, Floor 2'),
('Human Resources', 150000.00, 'Building A, Floor 1'),
('Finance', 250000.00, 'Building A, Floor 2'),
('Operations', 400000.00, 'Building C, Floor 1');

-- Employees
INSERT INTO employees (employee_code, first_name, last_name, email, phone, hire_date, salary, department_id, manager_id, metadata) VALUES
('EMP001', 'John', 'Smith', 'john.smith@company.com', '+1-555-0101', '2020-01-15', 95000.00, 1, NULL, '{"skills": ["Python", "JavaScript", "SQL"], "certifications": ["AWS"]}'),
('EMP002', 'Sarah', 'Johnson', 'sarah.johnson@company.com', '+1-555-0102', '2020-03-20', 85000.00, 1, 1, '{"skills": ["React", "TypeScript"], "certifications": []}'),
('EMP003', 'Michael', 'Williams', 'michael.williams@company.com', '+1-555-0103', '2019-06-10', 110000.00, 2, NULL, '{"skills": ["Sales", "Negotiation"], "certifications": ["Sales Pro"]}'),
('EMP004', 'Emily', 'Brown', 'emily.brown@company.com', '+1-555-0104', '2021-02-01', 75000.00, 2, 3, NULL),
('EMP005', '李明', 'Li', 'ming.li@company.com', '+86-138-0000-0001', '2021-05-15', 70000.00, 3, NULL, '{"skills": ["Marketing", "SEO"], "languages": ["Chinese", "English"]}'),
('EMP006', '王芳', 'Wang', 'fang.wang@company.com', '+86-138-0000-0002', '2022-01-10', 65000.00, 3, 5, '{"skills": ["Content Writing"], "languages": ["Chinese"]}'),
('EMP007', 'David', 'Miller', 'david.miller@company.com', '+1-555-0107', '2018-09-01', 80000.00, 4, NULL, NULL),
('EMP008', 'Jennifer', 'Davis', 'jennifer.davis@company.com', '+1-555-0108', '2020-11-15', 90000.00, 5, NULL, '{"skills": ["Accounting", "Excel"], "certifications": ["CPA"]}'),
('EMP009', '张伟', 'Zhang', 'wei.zhang@company.com', '+86-138-0000-0003', '2019-04-20', 72000.00, 6, NULL, NULL),
('EMP010', 'Robert', 'Wilson', 'robert.wilson@company.com', '+1-555-0110', '2023-01-05', 68000.00, 1, 1, '{"skills": ["Go", "Kubernetes"], "certifications": []}');

-- Categories
INSERT INTO categories (name, description, parent_id, sort_order) VALUES
('Electronics', 'Electronic devices and accessories', NULL, 1),
('Computers', 'Desktop and laptop computers', 1, 1),
('Smartphones', 'Mobile phones and accessories', 1, 2),
('Audio', 'Speakers, headphones, and audio equipment', 1, 3),
('Clothing', 'Apparel and fashion items', NULL, 2),
('Men''s Clothing', 'Clothing for men', 5, 1),
('Women''s Clothing', 'Clothing for women', 5, 2),
('Home & Garden', 'Home improvement and garden supplies', NULL, 3),
('Furniture', 'Indoor and outdoor furniture', 8, 1),
('Kitchen', 'Kitchen appliances and utensils', 8, 2);

-- Products
INSERT INTO products (sku, name, name_cn, description, category_id, price, cost, stock_quantity, min_stock_level, weight_kg, dimensions, tags) VALUES
('LAPTOP-001', 'ProBook 15 Laptop', '专业笔记本电脑 15寸', 'High-performance laptop with 16GB RAM and 512GB SSD', 2, 1299.99, 850.00, 45, 10, 2.1, '{"length": 35.8, "width": 24.2, "height": 1.8}', ARRAY['laptop', 'computer', 'work']),
('LAPTOP-002', 'UltraSlim 13 Laptop', '超薄笔记本 13寸', 'Lightweight laptop perfect for travel', 2, 999.99, 650.00, 30, 10, 1.3, '{"length": 30.4, "width": 21.2, "height": 1.5}', ARRAY['laptop', 'ultrabook', 'travel']),
('PHONE-001', 'SmartPhone Pro Max', '智能手机 Pro Max', 'Flagship smartphone with 256GB storage', 3, 1199.99, 750.00, 100, 20, 0.228, '{"length": 16.0, "width": 7.8, "height": 0.8}', ARRAY['phone', 'smartphone', '5g']),
('PHONE-002', 'SmartPhone Lite', '智能手机 Lite', 'Budget-friendly smartphone', 3, 399.99, 220.00, 200, 30, 0.185, '{"length": 15.2, "width": 7.2, "height": 0.8}', ARRAY['phone', 'budget', 'entry-level']),
('AUDIO-001', 'Wireless Headphones Pro', '无线耳机 Pro', 'Noise-cancelling wireless headphones', 4, 349.99, 180.00, 75, 15, 0.25, '{"length": 18.0, "width": 16.0, "height": 8.0}', ARRAY['headphones', 'wireless', 'noise-cancelling']),
('AUDIO-002', 'Bluetooth Speaker', '蓝牙音箱', 'Portable Bluetooth speaker with 20-hour battery', 4, 129.99, 65.00, 120, 25, 0.58, '{"length": 12.0, "width": 12.0, "height": 12.0}', ARRAY['speaker', 'bluetooth', 'portable']),
('SHIRT-001', 'Classic Oxford Shirt', '经典牛津衬衫', 'Men''s classic Oxford button-down shirt', 6, 59.99, 25.00, 150, 30, 0.3, NULL, ARRAY['shirt', 'formal', 'classic']),
('SHIRT-002', 'Casual Polo Shirt', '休闲Polo衫', 'Men''s casual polo shirt', 6, 39.99, 18.00, 200, 40, 0.25, NULL, ARRAY['polo', 'casual', 'summer']),
('DRESS-001', 'Summer Floral Dress', '夏季碎花连衣裙', 'Women''s floral print summer dress', 7, 79.99, 35.00, 80, 20, 0.4, NULL, ARRAY['dress', 'summer', 'floral']),
('CHAIR-001', 'Ergonomic Office Chair', '人体工学办公椅', 'Adjustable ergonomic office chair with lumbar support', 9, 399.99, 200.00, 25, 5, 18.5, '{"length": 65.0, "width": 65.0, "height": 120.0}', ARRAY['chair', 'office', 'ergonomic']),
('TABLE-001', 'Standing Desk', '升降办公桌', 'Electric height-adjustable standing desk', 9, 599.99, 320.00, 15, 3, 35.0, '{"length": 140.0, "width": 70.0, "height": 125.0}', ARRAY['desk', 'standing', 'electric']),
('KITCHEN-001', 'Smart Coffee Maker', '智能咖啡机', 'Programmable smart coffee maker with WiFi', 10, 149.99, 75.00, 50, 10, 3.2, '{"length": 25.0, "width": 20.0, "height": 35.0}', ARRAY['coffee', 'smart', 'kitchen']),
('KITCHEN-002', 'Air Fryer Pro', '空气炸锅 Pro', 'Large capacity digital air fryer', 10, 129.99, 60.00, 40, 8, 5.5, '{"length": 35.0, "width": 30.0, "height": 32.0}', ARRAY['air-fryer', 'healthy', 'cooking']);

-- Set some products as low stock or out of stock for testing
UPDATE products SET stock_quantity = 5 WHERE sku = 'CHAIR-001';
UPDATE products SET stock_quantity = 0 WHERE sku = 'TABLE-001';

-- Customers
INSERT INTO customers (customer_code, company_name, contact_name, contact_name_cn, email, phone, address, city, country, postal_code, credit_limit, customer_since, preferences) VALUES
('CUST001', 'TechCorp Solutions', 'Alice Chen', '陈爱丽', 'alice.chen@techcorp.com', '+86-21-5555-0001', '123 Technology Road, Building A', 'Shanghai', 'China', '200000', 50000.00, '2022-01-15', '{"preferred_shipping": "express", "communication": "email"}'),
('CUST002', 'Global Trade Inc', 'Bob Johnson', NULL, 'bob.johnson@globaltrade.com', '+1-555-0201', '456 Commerce Street', 'New York', 'USA', '10001', 100000.00, '2021-06-20', '{"preferred_shipping": "standard", "communication": "phone"}'),
('CUST003', '北京科技有限公司', '张三', '张三', 'zhangsan@bjtech.cn', '+86-10-5555-0001', '北京市朝阳区科技大道789号', 'Beijing', 'China', '100000', 30000.00, '2023-02-10', '{"preferred_shipping": "same-day", "language": "zh-CN"}'),
('CUST004', 'European Imports Ltd', 'Emma Schmidt', NULL, 'emma.schmidt@euimports.de', '+49-30-5555-0001', 'Hauptstraße 123', 'Berlin', 'Germany', '10115', 75000.00, '2022-08-05', '{"preferred_shipping": "express", "currency": "EUR"}'),
('CUST005', '上海贸易公司', '李四', '李四', 'lisi@shtrade.cn', '+86-21-5555-0002', '上海市浦东新区商业街456号', 'Shanghai', 'China', '200001', 25000.00, '2023-05-18', NULL),
('CUST006', 'Sunrise Electronics', 'David Kim', NULL, 'david.kim@sunrise.kr', '+82-2-5555-0001', '123 Gangnam-daero', 'Seoul', 'South Korea', '06100', 45000.00, '2022-11-30', '{"preferred_shipping": "express"}'),
('CUST007', 'Tokyo Tech Store', 'Yuki Tanaka', NULL, 'yuki.tanaka@tokyotech.jp', '+81-3-5555-0001', '1-2-3 Shibuya', 'Tokyo', 'Japan', '150-0002', 60000.00, '2021-09-12', NULL),
('CUST008', 'Australia Direct', 'James Wilson', NULL, 'james.wilson@audirect.com.au', '+61-2-5555-0001', '100 George Street', 'Sydney', 'Australia', '2000', 35000.00, '2023-03-25', '{"preferred_shipping": "economy"}');

-- Orders
INSERT INTO orders (order_number, customer_id, employee_id, order_date, required_date, shipped_date, status, shipping_address, shipping_city, shipping_country, shipping_cost, tax_amount, discount_percent, notes) VALUES
('ORD-2024-0001', 1, 3, '2024-01-15 10:30:00', '2024-01-20', '2024-01-17 14:00:00', 'delivered', '123 Technology Road, Building A', 'Shanghai', 'China', 25.00, 156.00, 5.00, 'Priority customer - handle with care'),
('ORD-2024-0002', 2, 4, '2024-01-18 14:45:00', '2024-01-25', '2024-01-22 09:30:00', 'delivered', '456 Commerce Street', 'New York', 'USA', 35.00, 245.00, 0.00, NULL),
('ORD-2024-0003', 3, 3, '2024-02-01 09:00:00', '2024-02-10', '2024-02-05 16:00:00', 'delivered', '北京市朝阳区科技大道789号', 'Beijing', 'China', 15.00, 89.00, 10.00, 'Chinese language invoice required'),
('ORD-2024-0004', 1, 4, '2024-02-15 11:20:00', '2024-02-22', NULL, 'processing', '123 Technology Road, Building A', 'Shanghai', 'China', 20.00, 120.00, 5.00, NULL),
('ORD-2024-0005', 4, 3, '2024-02-20 16:30:00', '2024-03-01', NULL, 'confirmed', 'Hauptstraße 123', 'Berlin', 'Germany', 50.00, 380.00, 0.00, 'International shipping - customs clearance needed'),
('ORD-2024-0006', 5, 4, '2024-03-01 08:45:00', '2024-03-08', NULL, 'pending', '上海市浦东新区商业街456号', 'Shanghai', 'China', 10.00, 45.00, 0.00, NULL),
('ORD-2024-0007', 6, 3, '2024-03-05 13:15:00', '2024-03-12', NULL, 'pending', '123 Gangnam-daero', 'Seoul', 'South Korea', 40.00, 210.00, 8.00, 'Gift wrapping requested'),
('ORD-2024-0008', 7, 4, '2024-03-10 10:00:00', '2024-03-17', NULL, 'pending', '1-2-3 Shibuya', 'Tokyo', 'Japan', 45.00, 178.00, 0.00, NULL),
('ORD-2024-0009', 2, 3, '2024-03-12 15:30:00', NULL, NULL, 'cancelled', '456 Commerce Street', 'New York', 'USA', 0.00, 0.00, 0.00, 'Customer cancelled - out of stock items'),
('ORD-2024-0010', 8, 4, '2024-03-15 09:20:00', '2024-03-25', NULL, 'pending', '100 George Street', 'Sydney', 'Australia', 55.00, 125.00, 3.00, NULL);

-- Order Items
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent) VALUES
-- Order 1
(1, 1, 2, 1299.99, 5.00),
(1, 5, 1, 349.99, 0.00),
-- Order 2
(2, 3, 3, 1199.99, 0.00),
(2, 6, 2, 129.99, 0.00),
-- Order 3
(3, 4, 5, 399.99, 10.00),
(3, 7, 3, 59.99, 5.00),
-- Order 4
(4, 2, 1, 999.99, 5.00),
(4, 12, 2, 149.99, 0.00),
-- Order 5
(5, 1, 5, 1299.99, 10.00),
(5, 10, 3, 399.99, 5.00),
(5, 11, 2, 599.99, 0.00),
-- Order 6
(6, 8, 10, 39.99, 0.00),
(6, 9, 5, 79.99, 0.00),
-- Order 7
(7, 3, 2, 1199.99, 8.00),
(7, 5, 2, 349.99, 8.00),
-- Order 8
(8, 4, 4, 399.99, 0.00),
(8, 13, 1, 129.99, 0.00),
-- Order 10
(10, 6, 3, 129.99, 3.00),
(10, 12, 1, 149.99, 0.00);

-- Audit logs (sample entries)
INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by, ip_address) VALUES
('products', 11, 'UPDATE', '{"stock_quantity": 20}', '{"stock_quantity": 0}', 'system', '192.168.1.100'),
('orders', 9, 'UPDATE', '{"status": "pending"}', '{"status": "cancelled"}', 'bob.johnson@globaltrade.com', '203.0.113.50'),
('products', 10, 'UPDATE', '{"stock_quantity": 30}', '{"stock_quantity": 5}', 'system', '192.168.1.100'),
('customers', 5, 'INSERT', NULL, '{"customer_code": "CUST005", "contact_name": "李四"}', 'admin', '10.0.0.1');

-- =============================================================================
-- VERIFICATION QUERIES (for testing)
-- =============================================================================

-- Uncomment to run verification queries:
-- SELECT 'Tables' AS type, COUNT(*) AS count FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- SELECT 'Views' AS type, COUNT(*) AS count FROM information_schema.views WHERE table_schema = 'public';
-- SELECT 'Products' AS type, COUNT(*) AS count FROM products;
-- SELECT 'Customers' AS type, COUNT(*) AS count FROM customers;
-- SELECT 'Orders' AS type, COUNT(*) AS count FROM orders;
-- SELECT 'Order Items' AS type, COUNT(*) AS count FROM order_items;
