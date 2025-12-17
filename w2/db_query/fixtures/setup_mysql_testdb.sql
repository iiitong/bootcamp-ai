-- MySQL Test Database Setup Script
-- Database: ecommerce_test
-- Description: E-commerce domain test database with 5 tables and 1000+ records
-- Usage: mysql -u root < scripts/setup_mysql_testdb.sql

-- ============================================
-- T035: Idempotent setup - drop and recreate
-- ============================================
DROP DATABASE IF EXISTS ecommerce_test;
CREATE DATABASE ecommerce_test
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ecommerce_test;

-- ============================================
-- T029: DDL - Table Definitions
-- ============================================

-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Products table
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    category VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Orders table (1000+ records target)
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status ENUM('pending', 'paid', 'shipped', 'completed', 'cancelled') NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Payments table
CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    amount DECIMAL(10,2) NOT NULL,
    method ENUM('credit_card', 'debit_card', 'alipay', 'wechat') NOT NULL,
    status ENUM('pending', 'success', 'failed', 'refunded') NOT NULL DEFAULT 'pending',
    paid_at DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Reviews table
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    rating TINYINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_product (user_id, product_id)
) ENGINE=InnoDB;

-- ============================================
-- T030: User Data (100 records)
-- ============================================

-- Generate 100 users using stored procedure
DELIMITER //
CREATE PROCEDURE generate_users()
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= 100 DO
        INSERT INTO users (username, email, created_at)
        VALUES (
            CONCAT('user_', LPAD(i, 3, '0')),
            CONCAT('user', i, '@example.com'),
            DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 365) DAY)
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL generate_users();
DROP PROCEDURE generate_users;

-- ============================================
-- T031: Product Data (50 records)
-- ============================================

-- Generate 50 products
DELIMITER //
CREATE PROCEDURE generate_products()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE categories VARCHAR(255) DEFAULT 'Electronics,Clothing,Books,Home,Sports,Toys,Food,Beauty,Garden,Office';
    DECLARE cat_count INT DEFAULT 10;
    DECLARE random_cat VARCHAR(50);
    DECLARE cat_index INT;

    WHILE i <= 50 DO
        SET cat_index = FLOOR(RAND() * cat_count) + 1;
        SET random_cat = SUBSTRING_INDEX(SUBSTRING_INDEX(categories, ',', cat_index), ',', -1);

        INSERT INTO products (name, description, price, stock, category, created_at)
        VALUES (
            CONCAT('Product ', i, ' - ', random_cat),
            CONCAT('This is a detailed description for product ', i, '. High quality ', random_cat, ' item.'),
            ROUND(10 + RAND() * 990, 2),
            FLOOR(RAND() * 100),
            random_cat,
            DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 180) DAY)
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL generate_products();
DROP PROCEDURE generate_products;

-- ============================================
-- T032: Order Data (1500 records - exceeds 1000+ requirement)
-- ============================================

DELIMITER //
CREATE PROCEDURE generate_orders()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE random_user INT;
    DECLARE random_amount DECIMAL(10,2);
    DECLARE random_status INT;
    DECLARE status_val VARCHAR(20);
    DECLARE order_date DATETIME;

    WHILE i <= 1500 DO
        SET random_user = FLOOR(1 + RAND() * 100);
        SET random_amount = ROUND(20 + RAND() * 980, 2);
        SET random_status = FLOOR(RAND() * 5);
        SET order_date = DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 365) DAY);

        CASE random_status
            WHEN 0 THEN SET status_val = 'pending';
            WHEN 1 THEN SET status_val = 'paid';
            WHEN 2 THEN SET status_val = 'shipped';
            WHEN 3 THEN SET status_val = 'completed';
            ELSE SET status_val = 'cancelled';
        END CASE;

        INSERT INTO orders (user_id, total_amount, status, created_at, updated_at)
        VALUES (
            random_user,
            random_amount,
            status_val,
            order_date,
            DATE_ADD(order_date, INTERVAL FLOOR(RAND() * 7) DAY)
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL generate_orders();
DROP PROCEDURE generate_orders;

-- ============================================
-- T033: Payment Data (1200 records - ~80% of orders)
-- ============================================

DELIMITER //
CREATE PROCEDURE generate_payments()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE order_count INT;
    DECLARE random_order INT;
    DECLARE order_amount DECIMAL(10,2);
    DECLARE random_method INT;
    DECLARE method_val VARCHAR(20);
    DECLARE random_status INT;
    DECLARE status_val VARCHAR(20);
    DECLARE order_created DATETIME;

    SELECT COUNT(*) INTO order_count FROM orders;

    WHILE i <= 1200 DO
        -- Get a random order that doesn't have a payment yet
        SELECT id, total_amount, created_at INTO random_order, order_amount, order_created
        FROM orders
        WHERE id NOT IN (SELECT order_id FROM payments)
        ORDER BY RAND()
        LIMIT 1;

        IF random_order IS NOT NULL THEN
            SET random_method = FLOOR(RAND() * 4);
            SET random_status = FLOOR(RAND() * 4);

            CASE random_method
                WHEN 0 THEN SET method_val = 'credit_card';
                WHEN 1 THEN SET method_val = 'debit_card';
                WHEN 2 THEN SET method_val = 'alipay';
                ELSE SET method_val = 'wechat';
            END CASE;

            CASE random_status
                WHEN 0 THEN SET status_val = 'pending';
                WHEN 1 THEN SET status_val = 'success';
                WHEN 2 THEN SET status_val = 'success';  -- More successful payments
                ELSE SET status_val = 'failed';
            END CASE;

            INSERT INTO payments (order_id, amount, method, status, paid_at)
            VALUES (
                random_order,
                order_amount,
                method_val,
                status_val,
                CASE WHEN status_val = 'success' THEN DATE_ADD(order_created, INTERVAL FLOOR(RAND() * 24) HOUR) ELSE NULL END
            );
        END IF;

        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL generate_payments();
DROP PROCEDURE generate_payments;

-- ============================================
-- T034: Review Data (300 records)
-- ============================================

DELIMITER //
CREATE PROCEDURE generate_reviews()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE random_user INT;
    DECLARE random_product INT;
    DECLARE random_rating INT;
    DECLARE review_comments TEXT DEFAULT 'Great product!,Good quality for the price.,Exactly as described.,Fast shipping!,Highly recommended.,Could be better.,Average product.,Not worth the money.,Excellent!,Satisfactory.';
    DECLARE comment_index INT;
    DECLARE random_comment VARCHAR(255);
    DECLARE dup_error INT DEFAULT 0;

    DECLARE CONTINUE HANDLER FOR 1062 SET dup_error = 1;

    WHILE i <= 300 DO
        SET dup_error = 0;
        SET random_user = FLOOR(1 + RAND() * 100);
        SET random_product = FLOOR(1 + RAND() * 50);
        SET random_rating = FLOOR(1 + RAND() * 5);
        SET comment_index = FLOOR(RAND() * 10) + 1;
        SET random_comment = SUBSTRING_INDEX(SUBSTRING_INDEX(review_comments, ',', comment_index), ',', -1);

        INSERT INTO reviews (user_id, product_id, rating, comment, created_at)
        VALUES (
            random_user,
            random_product,
            random_rating,
            random_comment,
            DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 180) DAY)
        );

        IF dup_error = 0 THEN
            SET i = i + 1;
        END IF;
    END WHILE;
END //
DELIMITER ;

CALL generate_reviews();
DROP PROCEDURE generate_reviews;

-- ============================================
-- Verification Queries
-- ============================================

SELECT 'Database setup complete!' AS message;
SELECT 'Table record counts:' AS info;
SELECT 'users' AS table_name, COUNT(*) AS record_count FROM users
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'payments', COUNT(*) FROM payments
UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews;

-- Show sample data
SELECT 'Sample users:' AS info;
SELECT * FROM users LIMIT 3;

SELECT 'Sample orders with user info:' AS info;
SELECT o.id, u.username, o.total_amount, o.status, o.created_at
FROM orders o
JOIN users u ON o.user_id = u.id
ORDER BY o.total_amount DESC
LIMIT 5;

SELECT 'Order status distribution:' AS info;
SELECT status, COUNT(*) as count
FROM orders
GROUP BY status
ORDER BY count DESC;
