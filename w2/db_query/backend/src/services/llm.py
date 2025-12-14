"""Natural language to SQL generation service using OpenAI."""

import os
import re

from openai import APIError, OpenAI, RateLimitError

from src.models.database import TableInfo


class TextToSQLGenerator:
    """Generate SQL queries from natural language using OpenAI or compatible APIs."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialize the generator.

        Args:
            model: OpenAI model to use
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Base URL for OpenAI-compatible API (defaults to OPENAI_BASE_URL env var)
        """
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )
        self.model = model
        self.schema_context: str | None = None

    def set_schema_context(self, tables: list[TableInfo], views: list[TableInfo]) -> None:
        """Set database schema context for SQL generation.

        Args:
            tables: List of table information
            views: List of view information
        """
        lines = []
        for table in tables + views:
            cols = ", ".join(
                [f"{c.name} {c.data_type}" for c in table.columns]
            )
            table_type = "VIEW" if table.type == "VIEW" else "TABLE"
            lines.append(f"- {table.schema_name}.{table.name} ({table_type}): {cols}")

        self.schema_context = "\n".join(lines)

    def set_schema_context_from_dict(self, tables_info: list[dict]) -> None:
        """Set database schema context from dictionary format.

        Args:
            tables_info: List of table dictionaries with schemaName, name, type, columns
        """
        lines = []
        for table in tables_info:
            cols = ", ".join(
                [f"{c['name']} {c['dataType']}" for c in table.get("columns", [])]
            )
            table_type = table.get("type", "TABLE")
            schema_name = table.get("schemaName", "public")
            lines.append(f"- {schema_name}.{table['name']} ({table_type}): {cols}")

        self.schema_context = "\n".join(lines)

    def generate(self, natural_language: str) -> str:
        """Generate SQL from natural language description.

        Args:
            natural_language: Natural language query description

        Returns:
            Generated SQL query string

        Raises:
            ValueError: If generation fails or API errors occur
        """
        if self.schema_context is None:
            raise ValueError("Schema context not set. Call set_schema_context first.")

        schema_info = self.schema_context if self.schema_context else "(No tables or views in this database)"

        system_prompt = f"""You are a PostgreSQL expert. Generate SQL queries based on natural language descriptions.

Database schema:
{schema_info}

Rules:
- Only generate SELECT statements
- Do not add LIMIT (the system will add it automatically)
- Return only the SQL code, no explanations
- Use standard PostgreSQL syntax
- If the request is unclear, make reasonable assumptions based on the schema
- Always use qualified table names (schema.table) when schema is not 'public'"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": natural_language},
                ],
                temperature=0,  # Ensure consistency
                max_tokens=500,
            )

            sql = response.choices[0].message.content
            if sql is None:
                raise ValueError("LLM returned empty response")

            sql = sql.strip()

            # Clean up markdown code blocks if present
            sql = re.sub(r"^```sql\n?", "", sql)
            sql = re.sub(r"\n?```$", "", sql)
            sql = sql.strip()

            return sql

        except RateLimitError:
            raise ValueError("API rate limit exceeded. Please try again later.")
        except APIError as e:
            raise ValueError(f"LLM service error: {e}")
