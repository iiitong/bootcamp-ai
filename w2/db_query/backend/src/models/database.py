"""Database-related Pydantic models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Database type literal for type safety
DbType = Literal["postgresql", "mysql"]


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class DatabaseCreateRequest(BaseModel):
    """Request body for creating/updating a database connection."""

    url: str = Field(
        ...,
        description="Database connection URL",
        examples=[
            "postgresql://user:pass@localhost:5432/mydb",
            "mysql://root@localhost:3306/testdb",
        ],
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL starts with supported database prefix."""
        valid_prefixes = ("postgresql://", "postgres://", "mysql://", "mysql+aiomysql://")
        if not v.startswith(valid_prefixes):
            raise ValueError(
                "URL must start with postgresql://, postgres://, mysql://, or mysql+aiomysql://"
            )
        return v


class DatabaseInfo(BaseModel):
    """Database connection information."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str = Field(..., description="Connection name")
    url: str = Field(..., description="Connection URL (password may be hidden)")
    db_type: DbType = Field(..., description="Database type (postgresql or mysql)")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")


class ColumnInfo(BaseModel):
    """Column information for a table or view."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type")
    nullable: bool = Field(..., description="Whether column is nullable")
    default_value: str | None = Field(None, description="Default value")
    is_primary_key: bool = Field(False, description="Whether column is primary key")
    is_foreign_key: bool = Field(False, description="Whether column is foreign key")


class TableInfo(BaseModel):
    """Table or view information."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    schema_name: str = Field(..., description="Schema name")
    name: str = Field(..., description="Table or view name")
    type: Literal["TABLE", "VIEW"] = Field(..., description="Type (TABLE or VIEW)")
    columns: list[ColumnInfo] = Field(default_factory=list, description="Column list")


class DatabaseMetadata(BaseModel):
    """Complete database metadata including tables and views."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str = Field(..., description="Connection name")
    url: str = Field(..., description="Connection URL")
    db_type: DbType = Field(..., description="Database type (postgresql or mysql)")
    tables: list[TableInfo] = Field(default_factory=list, description="Table list")
    views: list[TableInfo] = Field(default_factory=list, description="View list")
    cached_at: datetime = Field(..., description="Cache timestamp")
