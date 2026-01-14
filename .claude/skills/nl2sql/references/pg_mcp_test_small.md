# pg_mcp_test_small Database Reference

A small blog system database with user-generated content management.

## Connection Info

- **Host**: localhost
- **Port**: 5432
- **User**: postgres
- **Password**: (empty)
- **Database**: pg_mcp_test_small

## Schema: blog

### Tables

#### blog.users
User accounts for the blog system.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| username | varchar | NO | | Unique username |
| email | varchar | NO | | Unique email address |
| password_hash | varchar | NO | | Hashed password |
| display_name | varchar | YES | | Display name |
| role | user_role | NO | 'reader' | User permission level |
| bio | text | YES | | User biography |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Account creation time |
| last_login_at | timestamptz | YES | | Last login time |

#### blog.posts
Blog posts created by authors.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| author_id | integer | NO | | FK to users.id |
| title | varchar | NO | | Post title |
| slug | varchar | NO | | URL-friendly identifier |
| content | text | NO | | Post content |
| excerpt | text | YES | | Post excerpt/summary |
| status | post_status | NO | 'draft' | Publication status |
| view_count | integer | YES | 0 | Number of views |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |
| updated_at | timestamptz | YES | CURRENT_TIMESTAMP | Last update time |
| published_at | timestamptz | YES | | Publication time |

#### blog.tags
Tags for categorizing posts.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| name | varchar | NO | | Unique tag name |
| slug | varchar | NO | | URL-friendly identifier |
| description | text | YES | | Tag description |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### blog.post_tags
Junction table linking posts to tags (many-to-many).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| post_id | integer | NO | | FK to posts.id |
| tag_id | integer | NO | | FK to tags.id |

Primary Key: (post_id, tag_id)

#### blog.comments
Comments on blog posts.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| post_id | integer | NO | | FK to posts.id |
| author_id | integer | YES | | FK to users.id (nullable for guest comments) |
| parent_id | integer | YES | | FK to comments.id (for threaded comments) |
| content | text | NO | | Comment content |
| is_approved | boolean | YES | false | Moderation status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

### Views

#### blog.recent_posts
Shows recently published posts with author info and engagement metrics.

Columns: id, title, slug, excerpt, view_count, published_at, author_username, author_name, comment_count, tags (array)

#### blog.user_stats
Shows user statistics including post counts and engagement.

Columns: id, username, display_name, role, post_count, total_views, comment_count, last_post_date

### Enum Types

#### blog.user_role
Values: `reader`, `author`, `admin`

#### blog.post_status
Values: `draft`, `published`, `archived`

### Key Indexes

- `users_pkey` - PRIMARY KEY on users(id)
- `users_username_key` - UNIQUE on users(username)
- `users_email_key` - UNIQUE on users(email)
- `posts_pkey` - PRIMARY KEY on posts(id)
- `posts_slug_key` - UNIQUE on posts(slug)
- `idx_posts_author_id` - INDEX on posts(author_id)
- `idx_posts_status` - INDEX on posts(status)
- `idx_posts_published_at` - INDEX on posts(published_at DESC)
- `idx_comments_post_id` - INDEX on comments(post_id)

### Foreign Key Relationships

```text
users.id <-- posts.author_id
users.id <-- comments.author_id
posts.id <-- post_tags.post_id
tags.id <-- post_tags.tag_id
posts.id <-- comments.post_id
comments.id <-- comments.parent_id (self-referential)
```

### Sample Row Counts

- users: ~10 rows
- posts: ~15 rows
- comments: ~30 rows
- tags: ~8 rows

### Common Query Patterns

1. **Get published posts with author info**: Join posts with users where status = 'published'
2. **Get posts by tag**: Join posts -> post_tags -> tags
3. **Get comment threads**: Use recursive CTE on comments.parent_id
4. **Get user statistics**: Use the user_stats view
5. **Get recent posts**: Use the recent_posts view or filter by published_at DESC
