-- =============================================================================
-- Small Database: Simple Blog System
-- Tables: 5 | Views: 2 | Custom Types: 2 | Indexes: ~8
-- Data: 10-50 rows per table
-- =============================================================================

-- Drop existing objects
DROP SCHEMA IF EXISTS blog CASCADE;
CREATE SCHEMA blog;
SET search_path TO blog;

-- =============================================================================
-- Custom Types
-- =============================================================================

CREATE TYPE post_status AS ENUM ('draft', 'published', 'archived');
CREATE TYPE user_role AS ENUM ('reader', 'author', 'admin');

-- =============================================================================
-- Tables
-- =============================================================================

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    role user_role NOT NULL DEFAULT 'reader',
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE users IS 'Blog platform registered users';
COMMENT ON COLUMN users.role IS 'User permission level: reader, author, or admin';

-- Posts table
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    content TEXT NOT NULL,
    excerpt TEXT,
    status post_status NOT NULL DEFAULT 'draft',
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE posts IS 'Blog posts written by authors';
COMMENT ON COLUMN posts.slug IS 'URL-friendly identifier for the post';

-- Tags table
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE tags IS 'Tags for categorizing posts';

-- Post-Tag relationship (many-to-many)
CREATE TABLE post_tags (
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

-- Comments table
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE comments IS 'User comments on blog posts';
COMMENT ON COLUMN comments.parent_id IS 'For nested/threaded comments';

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX idx_posts_author_id ON posts(author_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_published_at ON posts(published_at DESC);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_author_id ON comments(author_id);
CREATE INDEX idx_comments_created_at ON comments(created_at DESC);

-- =============================================================================
-- Views
-- =============================================================================

-- Recent published posts with author info
CREATE VIEW recent_posts AS
SELECT
    p.id,
    p.title,
    p.slug,
    p.excerpt,
    p.view_count,
    p.published_at,
    u.username AS author_username,
    u.display_name AS author_name,
    (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id AND c.is_approved) AS comment_count,
    (SELECT ARRAY_AGG(t.name) FROM tags t
     JOIN post_tags pt ON t.id = pt.tag_id
     WHERE pt.post_id = p.id) AS tags
FROM posts p
JOIN users u ON p.author_id = u.id
WHERE p.status = 'published'
ORDER BY p.published_at DESC;

-- User statistics
CREATE VIEW user_stats AS
SELECT
    u.id,
    u.username,
    u.display_name,
    u.role,
    COUNT(DISTINCT p.id) AS post_count,
    COALESCE(SUM(p.view_count), 0) AS total_views,
    COUNT(DISTINCT c.id) AS comment_count,
    MAX(p.published_at) AS last_post_date
FROM users u
LEFT JOIN posts p ON u.id = p.author_id AND p.status = 'published'
LEFT JOIN comments c ON u.id = c.author_id
GROUP BY u.id, u.username, u.display_name, u.role;

-- =============================================================================
-- Sample Data
-- =============================================================================

-- Users (10 users)
INSERT INTO users (username, email, password_hash, display_name, role, bio) VALUES
('admin', 'admin@blog.com', '$2b$12$hash1', 'Site Admin', 'admin', 'Platform administrator'),
('alice', 'alice@example.com', '$2b$12$hash2', 'Alice Chen', 'author', 'Tech writer and software engineer'),
('bob', 'bob@example.com', '$2b$12$hash3', 'Bob Smith', 'author', 'Data science enthusiast'),
('charlie', 'charlie@example.com', '$2b$12$hash4', 'Charlie Wang', 'author', 'Full-stack developer'),
('diana', 'diana@example.com', '$2b$12$hash5', 'Diana Lopez', 'reader', 'Avid reader'),
('eve', 'eve@example.com', '$2b$12$hash6', 'Eve Johnson', 'reader', NULL),
('frank', 'frank@example.com', '$2b$12$hash7', 'Frank Brown', 'reader', 'Just browsing'),
('grace', 'grace@example.com', '$2b$12$hash8', 'Grace Kim', 'author', 'DevOps engineer'),
('henry', 'henry@example.com', '$2b$12$hash9', 'Henry Davis', 'reader', NULL),
('iris', 'iris@example.com', '$2b$12$hash10', 'Iris Wilson', 'author', 'Cloud architect');

-- Tags (8 tags)
INSERT INTO tags (name, slug, description) VALUES
('Python', 'python', 'Python programming language'),
('JavaScript', 'javascript', 'JavaScript and TypeScript'),
('Database', 'database', 'SQL and NoSQL databases'),
('DevOps', 'devops', 'CI/CD, containers, and infrastructure'),
('Machine Learning', 'machine-learning', 'AI and ML topics'),
('Tutorial', 'tutorial', 'Step-by-step guides'),
('Opinion', 'opinion', 'Opinion pieces and editorials'),
('News', 'news', 'Industry news and updates');

-- Posts (15 posts)
INSERT INTO posts (author_id, title, slug, content, excerpt, status, view_count, published_at) VALUES
(2, 'Getting Started with Python', 'getting-started-python', 'Python is a versatile programming language...', 'A beginner guide to Python', 'published', 1250, NOW() - INTERVAL '30 days'),
(2, 'Advanced Python Decorators', 'advanced-python-decorators', 'Decorators are a powerful Python feature...', 'Deep dive into decorators', 'published', 890, NOW() - INTERVAL '25 days'),
(3, 'Introduction to Pandas', 'intro-pandas', 'Pandas is essential for data analysis...', 'Learn Pandas basics', 'published', 2100, NOW() - INTERVAL '20 days'),
(3, 'SQL vs NoSQL Databases', 'sql-vs-nosql', 'When to choose SQL or NoSQL...', 'Database comparison guide', 'published', 1560, NOW() - INTERVAL '18 days'),
(4, 'Building REST APIs with FastAPI', 'rest-apis-fastapi', 'FastAPI makes building APIs easy...', 'FastAPI tutorial', 'published', 3200, NOW() - INTERVAL '15 days'),
(4, 'Docker for Beginners', 'docker-beginners', 'Containers have revolutionized deployment...', 'Docker basics explained', 'published', 2800, NOW() - INTERVAL '12 days'),
(8, 'Kubernetes in Production', 'kubernetes-production', 'Running K8s at scale requires...', 'K8s best practices', 'published', 1890, NOW() - INTERVAL '10 days'),
(8, 'CI/CD Pipeline Design', 'cicd-pipeline-design', 'A good CI/CD pipeline should...', 'CI/CD architecture guide', 'published', 1450, NOW() - INTERVAL '8 days'),
(10, 'AWS vs Azure vs GCP', 'cloud-comparison', 'Comparing major cloud providers...', 'Cloud platform comparison', 'published', 4500, NOW() - INTERVAL '5 days'),
(10, 'Serverless Architecture Patterns', 'serverless-patterns', 'Serverless computing offers...', 'Serverless design patterns', 'published', 2100, NOW() - INTERVAL '3 days'),
(2, 'Python Type Hints Guide', 'python-type-hints', 'Type hints improve code quality...', 'Master Python typing', 'draft', 0, NULL),
(3, 'Data Visualization Best Practices', 'data-viz-best-practices', 'Effective visualizations tell stories...', 'Visualization tips', 'draft', 0, NULL),
(4, 'Microservices Communication', 'microservices-communication', 'Service-to-service communication...', 'Microservices patterns', 'archived', 560, NOW() - INTERVAL '60 days'),
(8, 'GitOps Workflow', 'gitops-workflow', 'GitOps brings Git to operations...', 'GitOps introduction', 'published', 980, NOW() - INTERVAL '1 day'),
(10, 'Multi-Cloud Strategy', 'multi-cloud-strategy', 'Using multiple cloud providers...', 'Multi-cloud architecture', 'published', 720, NOW() - INTERVAL '6 hours');

-- Post-Tags relationships
INSERT INTO post_tags (post_id, tag_id) VALUES
(1, 1), (1, 6),      -- Python post: Python, Tutorial
(2, 1),              -- Advanced Python: Python
(3, 1), (3, 6),      -- Pandas: Python, Tutorial
(4, 3),              -- SQL vs NoSQL: Database
(5, 1), (5, 6),      -- FastAPI: Python, Tutorial
(6, 4), (6, 6),      -- Docker: DevOps, Tutorial
(7, 4),              -- K8s: DevOps
(8, 4),              -- CI/CD: DevOps
(9, 4), (9, 7),      -- Cloud comparison: DevOps, Opinion
(10, 4),             -- Serverless: DevOps
(11, 1),             -- Type hints: Python
(12, 1), (12, 5),    -- Data viz: Python, ML
(13, 4),             -- Microservices: DevOps
(14, 4), (14, 8),    -- GitOps: DevOps, News
(15, 4), (15, 7);    -- Multi-cloud: DevOps, Opinion

-- Comments (30 comments)
INSERT INTO comments (post_id, author_id, parent_id, content, is_approved, created_at) VALUES
(1, 5, NULL, 'Great introduction! Very helpful for beginners.', TRUE, NOW() - INTERVAL '29 days'),
(1, 6, NULL, 'Could you add more examples?', TRUE, NOW() - INTERVAL '28 days'),
(1, 2, 2, 'Sure, I will update the post soon!', TRUE, NOW() - INTERVAL '28 days'),
(3, 7, NULL, 'Pandas changed how I work with data.', TRUE, NOW() - INTERVAL '19 days'),
(3, 5, NULL, 'The examples are very clear.', TRUE, NOW() - INTERVAL '18 days'),
(4, 8, NULL, 'We use PostgreSQL and it works great for our scale.', TRUE, NOW() - INTERVAL '17 days'),
(4, 9, NULL, 'What about NewSQL databases?', TRUE, NOW() - INTERVAL '16 days'),
(5, 6, NULL, 'FastAPI is indeed faster than Flask!', TRUE, NOW() - INTERVAL '14 days'),
(5, 7, NULL, 'Love the async support.', TRUE, NOW() - INTERVAL '13 days'),
(5, 9, NULL, 'Best API framework for Python.', TRUE, NOW() - INTERVAL '12 days'),
(6, 5, NULL, 'Finally understood Docker networking!', TRUE, NOW() - INTERVAL '11 days'),
(6, 9, 11, 'That part confused me too initially.', TRUE, NOW() - INTERVAL '11 days'),
(7, 6, NULL, 'Running K8s is not easy...', TRUE, NOW() - INTERVAL '9 days'),
(7, 4, 13, 'That is why managed K8s exists!', TRUE, NOW() - INTERVAL '9 days'),
(8, 5, NULL, 'We use GitHub Actions, works well.', TRUE, NOW() - INTERVAL '7 days'),
(8, 7, NULL, 'Jenkins is still king for complex pipelines.', TRUE, NOW() - INTERVAL '7 days'),
(8, 6, 16, 'Have you tried Tekton?', TRUE, NOW() - INTERVAL '6 days'),
(9, 7, NULL, 'Great comparison, very balanced.', TRUE, NOW() - INTERVAL '4 days'),
(9, 5, NULL, 'We went with AWS, no regrets.', TRUE, NOW() - INTERVAL '4 days'),
(9, 9, NULL, 'Azure has better enterprise integration.', TRUE, NOW() - INTERVAL '3 days'),
(9, 6, NULL, 'GCP for ML workloads is unbeatable.', TRUE, NOW() - INTERVAL '3 days'),
(10, 7, NULL, 'Lambda cold starts are still an issue.', TRUE, NOW() - INTERVAL '2 days'),
(10, 5, 22, 'Provisioned concurrency helps.', TRUE, NOW() - INTERVAL '2 days'),
(14, 9, NULL, 'GitOps is the future!', TRUE, NOW() - INTERVAL '12 hours'),
(14, 7, NULL, 'We use ArgoCD, highly recommend.', TRUE, NOW() - INTERVAL '10 hours'),
(15, 5, NULL, 'Multi-cloud is complex but worth it.', TRUE, NOW() - INTERVAL '5 hours'),
(15, 6, NULL, 'Vendor lock-in is real.', TRUE, NOW() - INTERVAL '4 hours'),
(15, 9, 27, 'Use Terraform to stay portable.', TRUE, NOW() - INTERVAL '3 hours'),
(1, 9, NULL, 'Coming back to say this helped me land my first job!', TRUE, NOW() - INTERVAL '1 hour'),
(5, NULL, NULL, 'This comment awaiting moderation.', FALSE, NOW() - INTERVAL '30 minutes');
