"""Sample schemas for testing."""

from pg_mcp.models.schema import (
    ColumnInfo,
    DatabaseSchema,
    EnumTypeInfo,
    IndexInfo,
    TableInfo,
    ViewInfo,
)


def create_ecommerce_schema() -> DatabaseSchema:
    """Create a sample e-commerce database schema.

    Returns:
        Sample DatabaseSchema for testing
    """
    return DatabaseSchema(
        name="ecommerce",
        tables=[
            TableInfo(
                name="users",
                schema_name="public",
                comment="User accounts",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        comment="Primary key",
                    ),
                    ColumnInfo(
                        name="email",
                        data_type="varchar(255)",
                        is_nullable=False,
                        is_unique=True,
                        comment="User email address",
                    ),
                    ColumnInfo(
                        name="name",
                        data_type="varchar(100)",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="status",
                        data_type="user_status",
                        is_nullable=False,
                        default_value="'active'",
                        enum_values=["active", "inactive", "suspended"],
                    ),
                    ColumnInfo(
                        name="created_at",
                        data_type="timestamp with time zone",
                        is_nullable=False,
                        default_value="now()",
                    ),
                ],
                indexes=[
                    IndexInfo(
                        name="users_pkey",
                        columns=["id"],
                        is_primary=True,
                    ),
                    IndexInfo(
                        name="users_email_key",
                        columns=["email"],
                        is_unique=True,
                    ),
                ],
            ),
            TableInfo(
                name="products",
                schema_name="public",
                comment="Product catalog",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="name",
                        data_type="varchar(200)",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="description",
                        data_type="text",
                        is_nullable=True,
                    ),
                    ColumnInfo(
                        name="price",
                        data_type="numeric(10,2)",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="category_id",
                        data_type="integer",
                        is_nullable=True,
                        foreign_key_table="categories",
                        foreign_key_column="id",
                    ),
                    ColumnInfo(
                        name="stock_quantity",
                        data_type="integer",
                        is_nullable=False,
                        default_value="0",
                    ),
                ],
                indexes=[
                    IndexInfo(
                        name="products_pkey",
                        columns=["id"],
                        is_primary=True,
                    ),
                    IndexInfo(
                        name="products_category_idx",
                        columns=["category_id"],
                    ),
                ],
            ),
            TableInfo(
                name="categories",
                schema_name="public",
                comment="Product categories",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="name",
                        data_type="varchar(100)",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="parent_id",
                        data_type="integer",
                        is_nullable=True,
                        foreign_key_table="categories",
                        foreign_key_column="id",
                    ),
                ],
            ),
            TableInfo(
                name="orders",
                schema_name="public",
                comment="Customer orders",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="user_id",
                        data_type="integer",
                        is_nullable=False,
                        foreign_key_table="users",
                        foreign_key_column="id",
                    ),
                    ColumnInfo(
                        name="status",
                        data_type="order_status",
                        is_nullable=False,
                        default_value="'pending'",
                        enum_values=["pending", "confirmed", "shipped", "delivered", "cancelled"],
                    ),
                    ColumnInfo(
                        name="total_amount",
                        data_type="numeric(12,2)",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="created_at",
                        data_type="timestamp with time zone",
                        is_nullable=False,
                        default_value="now()",
                    ),
                ],
                indexes=[
                    IndexInfo(
                        name="orders_pkey",
                        columns=["id"],
                        is_primary=True,
                    ),
                    IndexInfo(
                        name="orders_user_idx",
                        columns=["user_id"],
                    ),
                    IndexInfo(
                        name="orders_status_idx",
                        columns=["status"],
                    ),
                ],
            ),
            TableInfo(
                name="order_items",
                schema_name="public",
                comment="Items in orders",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="order_id",
                        data_type="integer",
                        is_nullable=False,
                        foreign_key_table="orders",
                        foreign_key_column="id",
                    ),
                    ColumnInfo(
                        name="product_id",
                        data_type="integer",
                        is_nullable=False,
                        foreign_key_table="products",
                        foreign_key_column="id",
                    ),
                    ColumnInfo(
                        name="quantity",
                        data_type="integer",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="unit_price",
                        data_type="numeric(10,2)",
                        is_nullable=False,
                    ),
                ],
            ),
        ],
        views=[
            ViewInfo(
                name="active_users",
                schema_name="public",
                columns=[
                    ColumnInfo(name="id", data_type="integer"),
                    ColumnInfo(name="email", data_type="varchar(255)"),
                    ColumnInfo(name="name", data_type="varchar(100)"),
                ],
                definition="SELECT id, email, name FROM users WHERE status = 'active'",
            ),
            ViewInfo(
                name="order_summary",
                schema_name="public",
                columns=[
                    ColumnInfo(name="user_id", data_type="integer"),
                    ColumnInfo(name="user_name", data_type="varchar(100)"),
                    ColumnInfo(name="total_orders", data_type="bigint"),
                    ColumnInfo(name="total_spent", data_type="numeric"),
                ],
                definition="""
                SELECT u.id as user_id, u.name as user_name,
                       COUNT(o.id) as total_orders,
                       SUM(o.total_amount) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                GROUP BY u.id, u.name
                """,
            ),
        ],
        enum_types=[
            EnumTypeInfo(
                name="user_status",
                schema_name="public",
                values=["active", "inactive", "suspended"],
            ),
            EnumTypeInfo(
                name="order_status",
                schema_name="public",
                values=["pending", "confirmed", "shipped", "delivered", "cancelled"],
            ),
        ],
        cached_at=1704067200.0,
    )


def create_simple_schema() -> DatabaseSchema:
    """Create a minimal schema for simple tests.

    Returns:
        Simple DatabaseSchema with one table
    """
    return DatabaseSchema(
        name="simple_db",
        tables=[
            TableInfo(
                name="items",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="name",
                        data_type="text",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="value",
                        data_type="integer",
                        is_nullable=True,
                    ),
                ],
            ),
        ],
        cached_at=1704067200.0,
    )
