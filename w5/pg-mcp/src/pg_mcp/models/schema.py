from enum import Enum

from pydantic import BaseModel, Field


class IndexType(str, Enum):
    """索引类型"""
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    BRIN = "brin"


class ColumnInfo(BaseModel):
    """列信息"""
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    is_unique: bool = False
    default_value: str | None = None
    comment: str | None = None

    # 外键信息
    foreign_key_table: str | None = None
    foreign_key_column: str | None = None

    # ENUM 类型的可选值
    enum_values: list[str] | None = None


class IndexInfo(BaseModel):
    """索引信息"""
    name: str
    columns: list[str]
    index_type: IndexType = IndexType.BTREE
    is_unique: bool = False
    is_primary: bool = False


class TableInfo(BaseModel):
    """表信息"""
    name: str
    schema_name: str = "public"
    columns: list[ColumnInfo] = Field(default_factory=list)
    indexes: list[IndexInfo] = Field(default_factory=list)
    comment: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.schema_name}.{self.name}"


class ViewInfo(BaseModel):
    """视图信息"""
    name: str
    schema_name: str = "public"
    columns: list[ColumnInfo] = Field(default_factory=list)
    definition: str | None = None  # CREATE VIEW 语句


class EnumTypeInfo(BaseModel):
    """枚举类型信息"""
    name: str
    schema_name: str = "public"
    values: list[str]


class DatabaseSchema(BaseModel):
    """数据库完整 Schema"""
    name: str  # 数据库别名
    tables: list[TableInfo] = Field(default_factory=list)
    views: list[ViewInfo] = Field(default_factory=list)
    enum_types: list[EnumTypeInfo] = Field(default_factory=list)

    # 缓存元数据
    cached_at: float | None = None  # Unix timestamp

    @property
    def tables_count(self) -> int:
        return len(self.tables)

    @property
    def views_count(self) -> int:
        return len(self.views)

    def to_prompt_text(self) -> str:
        """生成用于 LLM Prompt 的 Schema 描述"""
        lines = [f"Database: {self.name}\n"]

        # 表信息
        if self.tables:
            lines.append("## Tables\n")
            for table in self.tables:
                lines.append(f"### {table.full_name}")
                if table.comment:
                    lines.append(f"Description: {table.comment}")
                lines.append("Columns:")
                for col in table.columns:
                    col_desc = f"  - {col.name}: {col.data_type}"
                    attrs = []
                    if col.is_primary_key:
                        attrs.append("PRIMARY KEY")
                    if not col.is_nullable:
                        attrs.append("NOT NULL")
                    if col.is_unique:
                        attrs.append("UNIQUE")
                    if col.foreign_key_table:
                        attrs.append(f"FK -> {col.foreign_key_table}.{col.foreign_key_column}")
                    if col.enum_values:
                        attrs.append(f"ENUM: {col.enum_values}")
                    if col.comment:
                        attrs.append(f'"{col.comment}"')
                    if attrs:
                        col_desc += f" ({', '.join(attrs)})"
                    lines.append(col_desc)

                if table.indexes:
                    lines.append("Indexes:")
                    for idx in table.indexes:
                        idx_attrs = []
                        if idx.is_primary:
                            idx_attrs.append("PRIMARY")
                        if idx.is_unique:
                            idx_attrs.append("UNIQUE")
                        idx_attrs.append(idx.index_type.value)
                        lines.append(
                            f"  - {idx.name} ({', '.join(idx_attrs)} on {', '.join(idx.columns)})"
                        )
                lines.append("")

        # 视图信息
        if self.views:
            lines.append("## Views\n")
            for view in self.views:
                lines.append(f"### {view.schema_name}.{view.name}")
                lines.append("Columns:")
                for col in view.columns:
                    lines.append(f"  - {col.name}: {col.data_type}")
                lines.append("")

        # 枚举类型
        if self.enum_types:
            lines.append("## Custom Types\n")
            for enum in self.enum_types:
                values_str = ", ".join(repr(v) for v in enum.values)
                lines.append(f"- {enum.schema_name}.{enum.name}: ENUM ({values_str})")

        return "\n".join(lines)

    def get_table(self, name: str, schema: str = "public") -> TableInfo | None:
        """根据名称获取表信息

        Args:
            name: 表名
            schema: schema 名称

        Returns:
            表信息或 None
        """
        for table in self.tables:
            if table.name == name and table.schema_name == schema:
                return table
        return None

    def get_view(self, name: str, schema: str = "public") -> ViewInfo | None:
        """根据名称获取视图信息

        Args:
            name: 视图名
            schema: schema 名称

        Returns:
            视图信息或 None
        """
        for view in self.views:
            if view.name == name and view.schema_name == schema:
                return view
        return None
