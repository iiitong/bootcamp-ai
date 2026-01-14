# pg_mcp_test_medium Database Reference

A medium-sized e-commerce database with products, orders, and customer management.

## Connection Info

- **Host**: localhost
- **Port**: 5432
- **User**: postgres
- **Password**: (empty)
- **Database**: pg_mcp_test_medium

## Schema: ecommerce

### Tables

#### ecommerce.categories
Product categories with hierarchical structure.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| parent_id | integer | YES | | FK to categories.id (self-referential) |
| name | varchar | NO | | Category name |
| slug | varchar | NO | | URL-friendly identifier |
| description | text | YES | | Category description |
| image_url | varchar | YES | | Category image URL |
| is_active | boolean | YES | true | Active status |
| sort_order | integer | YES | 0 | Display order |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### ecommerce.suppliers
Product suppliers/vendors.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| name | varchar | NO | | Supplier name |
| code | varchar | NO | | Unique supplier code |
| contact_name | varchar | YES | | Contact person |
| email | varchar | YES | | Contact email |
| phone | varchar | YES | | Contact phone |
| address | text | YES | | Physical address |
| country | varchar | YES | | Country |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### ecommerce.products
Products available for sale.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| category_id | integer | YES | | FK to categories.id |
| supplier_id | integer | YES | | FK to suppliers.id |
| sku | varchar | NO | | Unique SKU |
| name | varchar | NO | | Product name |
| description | text | YES | | Product description |
| price | numeric | NO | | Sale price |
| cost_price | numeric | YES | | Cost price |
| compare_at_price | numeric | YES | | Original price for discounts |
| weight_kg | numeric | YES | | Product weight |
| status | product_status | NO | 'draft' | Product status |
| is_featured | boolean | YES | false | Featured flag |
| meta_title | varchar | YES | | SEO title |
| meta_description | text | YES | | SEO description |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |
| updated_at | timestamptz | YES | CURRENT_TIMESTAMP | Last update |

#### ecommerce.product_variants
Product variants (size, color, etc.).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| product_id | integer | NO | | FK to products.id |
| sku | varchar | NO | | Unique variant SKU |
| name | varchar | NO | | Variant name |
| price_modifier | numeric | YES | 0 | Price adjustment |
| weight_modifier | numeric | YES | 0 | Weight adjustment |
| is_default | boolean | YES | false | Default variant flag |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### ecommerce.inventory
Stock levels for products/variants.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| product_id | integer | NO | | FK to products.id |
| variant_id | integer | YES | | FK to product_variants.id |
| quantity | integer | NO | 0 | Current stock |
| reserved_quantity | integer | NO | 0 | Reserved for orders |
| reorder_level | integer | YES | 10 | Reorder threshold |
| reorder_quantity | integer | YES | 50 | Quantity to reorder |
| warehouse_location | varchar | YES | | Location in warehouse |
| last_restock_at | timestamptz | YES | | Last restock time |
| updated_at | timestamptz | YES | CURRENT_TIMESTAMP | Last update |

#### ecommerce.customers
Customer accounts.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| email | varchar | NO | | Unique email |
| password_hash | varchar | NO | | Hashed password |
| first_name | varchar | YES | | First name |
| last_name | varchar | YES | | Last name |
| phone | varchar | YES | | Phone number |
| date_of_birth | date | YES | | Birth date |
| is_verified | boolean | YES | false | Email verified |
| is_active | boolean | YES | true | Account active |
| accepts_marketing | boolean | YES | false | Marketing consent |
| total_orders | integer | YES | 0 | Order count |
| total_spent | numeric | YES | 0 | Lifetime value |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Registration time |
| last_login_at | timestamptz | YES | | Last login |

#### ecommerce.addresses
Customer shipping/billing addresses.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| customer_id | integer | NO | | FK to customers.id |
| address_type | address_type | NO | 'both' | billing/shipping/both |
| is_default | boolean | YES | false | Default address flag |
| first_name | varchar | YES | | First name |
| last_name | varchar | YES | | Last name |
| company | varchar | YES | | Company name |
| address_line1 | varchar | NO | | Street address |
| address_line2 | varchar | YES | | Apt/Suite |
| city | varchar | NO | | City |
| state | varchar | YES | | State/Province |
| postal_code | varchar | YES | | Postal code |
| country | varchar | NO | | Country |
| phone | varchar | YES | | Phone |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### ecommerce.orders
Customer orders.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| customer_id | integer | YES | | FK to customers.id |
| order_number | varchar | NO | | Unique order number |
| status | order_status | NO | 'pending' | Order status |
| subtotal | numeric | NO | | Before tax/shipping |
| tax_amount | numeric | YES | 0 | Tax amount |
| shipping_amount | numeric | YES | 0 | Shipping cost |
| discount_amount | numeric | YES | 0 | Discount applied |
| total_amount | numeric | NO | | Final total |
| currency | varchar | YES | 'USD' | Currency code |
| shipping_address_id | integer | YES | | FK to addresses.id |
| billing_address_id | integer | YES | | FK to addresses.id |
| shipping_method | shipping_method | YES | | Shipping method |
| notes | text | YES | | Order notes |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Order time |
| updated_at | timestamptz | YES | CURRENT_TIMESTAMP | Last update |
| shipped_at | timestamptz | YES | | Ship time |
| delivered_at | timestamptz | YES | | Delivery time |

#### ecommerce.order_items
Line items in orders.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| order_id | integer | NO | | FK to orders.id |
| product_id | integer | YES | | FK to products.id |
| variant_id | integer | YES | | FK to product_variants.id |
| product_name | varchar | NO | | Snapshot of product name |
| variant_name | varchar | YES | | Snapshot of variant name |
| sku | varchar | YES | | Snapshot of SKU |
| quantity | integer | NO | | Quantity ordered |
| unit_price | numeric | NO | | Price per unit |
| total_price | numeric | NO | | Line total |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### ecommerce.payments
Payment records for orders.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| order_id | integer | NO | | FK to orders.id |
| payment_method | payment_method | NO | | Payment type |
| status | payment_status | NO | 'pending' | Payment status |
| amount | numeric | NO | | Payment amount |
| currency | varchar | YES | 'USD' | Currency code |
| transaction_id | varchar | YES | | Gateway transaction ID |
| gateway_response | jsonb | YES | | Gateway response data |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |
| processed_at | timestamptz | YES | | Processing time |

#### ecommerce.shipments
Shipping records.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| order_id | integer | NO | | FK to orders.id |
| carrier | varchar | YES | | Shipping carrier |
| tracking_number | varchar | YES | | Tracking number |
| shipping_method | shipping_method | NO | | Shipping method |
| estimated_delivery | date | YES | | Estimated delivery |
| actual_delivery | date | YES | | Actual delivery |
| weight_kg | numeric | YES | | Package weight |
| shipping_cost | numeric | YES | | Shipping cost |
| status | varchar | YES | 'pending' | Shipment status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |
| shipped_at | timestamptz | YES | | Ship time |

#### ecommerce.coupons
Discount coupons.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| code | varchar | NO | | Unique coupon code |
| description | text | YES | | Coupon description |
| discount_type | varchar | NO | | percentage/fixed |
| discount_value | numeric | NO | | Discount amount |
| min_order_amount | numeric | YES | | Minimum order |
| max_uses | integer | YES | | Max total uses |
| used_count | integer | YES | 0 | Times used |
| starts_at | timestamptz | YES | | Start date |
| expires_at | timestamptz | YES | | Expiration date |
| is_active | boolean | YES | true | Active status |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### ecommerce.order_coupons
Junction table for coupons applied to orders.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| order_id | integer | NO | | FK to orders.id |
| coupon_id | integer | NO | | FK to coupons.id |
| discount_applied | numeric | NO | | Discount amount applied |

Primary Key: (order_id, coupon_id)

#### ecommerce.reviews
Product reviews.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| product_id | integer | NO | | FK to products.id |
| customer_id | integer | YES | | FK to customers.id |
| order_id | integer | YES | | FK to orders.id |
| rating | integer | NO | | 1-5 rating |
| title | varchar | YES | | Review title |
| content | text | YES | | Review content |
| is_verified_purchase | boolean | YES | false | Verified purchase |
| is_approved | boolean | YES | false | Moderation status |
| helpful_count | integer | YES | 0 | Helpful votes |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |

#### ecommerce.carts
Shopping carts.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| customer_id | integer | YES | | FK to customers.id |
| session_id | varchar | YES | | Guest session ID |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Creation time |
| updated_at | timestamptz | YES | CURRENT_TIMESTAMP | Last update |
| expires_at | timestamptz | YES | +30 days | Expiration time |

#### ecommerce.cart_items
Items in shopping carts.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | auto | Primary key |
| cart_id | integer | NO | | FK to carts.id |
| product_id | integer | NO | | FK to products.id |
| variant_id | integer | YES | | FK to product_variants.id |
| quantity | integer | NO | | Quantity |
| created_at | timestamptz | YES | CURRENT_TIMESTAMP | Added time |

### Views

#### ecommerce.product_catalog
Active products with category, supplier, stock, and review info.

Columns: id, sku, name, description, price, compare_at_price, status, is_featured, category_name, category_slug, supplier_name, available_stock, avg_rating, review_count

#### ecommerce.customer_orders_summary
Customer lifetime value and order statistics.

Columns: customer_id, email, first_name, last_name, order_count, lifetime_value, avg_order_value, last_order_date, first_order_date

#### ecommerce.daily_sales
Daily sales aggregation.

Columns: order_date, order_count, gross_sales, total_discounts, total_tax, total_shipping, net_sales, unique_customers, items_sold

#### ecommerce.top_products
Best-selling products by quantity sold.

Columns: id, sku, name, category, total_sold, total_revenue, order_count

#### ecommerce.low_stock_products
Products below reorder level.

Columns: id, sku, name, status, supplier_name, supplier_email, current_stock, reserved_quantity, reorder_level, reorder_quantity, warehouse_location

### Enum Types

#### ecommerce.address_type
Values: `billing`, `shipping`, `both`

#### ecommerce.order_status
Values: `pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled`, `refunded`

#### ecommerce.payment_method
Values: `credit_card`, `debit_card`, `paypal`, `bank_transfer`, `crypto`

#### ecommerce.payment_status
Values: `pending`, `authorized`, `captured`, `failed`, `refunded`

#### ecommerce.product_status
Values: `draft`, `active`, `out_of_stock`, `discontinued`

#### ecommerce.shipping_method
Values: `standard`, `express`, `overnight`, `pickup`

### Key Indexes

- Full-text search on products: `idx_products_name_search` (GIN)
- Partial index for featured: `idx_products_is_featured` WHERE is_featured = true
- Partial index for low stock: `idx_inventory_low_stock` WHERE quantity <= reorder_level

### Sample Row Counts

- categories: ~19 rows
- products: ~150 rows
- customers: ~200 rows
- orders: ~500 rows
- order_items: ~1500 rows
- reviews: ~81 rows

### Common Query Patterns

1. **Product catalog with filters**: Use product_catalog view with WHERE clauses
2. **Order history by customer**: Join orders -> order_items with customer_id filter
3. **Sales analytics**: Use daily_sales view or aggregate orders by date
4. **Inventory alerts**: Use low_stock_products view
5. **Customer segmentation**: Use customer_orders_summary view
6. **Product search**: Use full-text search on products.name
