# =============================================================================
# PostgreSQL MCP Server Test Fixtures Makefile
# =============================================================================
#
# This Makefile manages three test databases for the pg-mcp server:
#   - small_blog: Simple blog system (~5 tables, ~100 rows)
#   - medium_ecommerce: E-commerce platform (~15 tables, ~2000 rows)
#   - large_erp: Enterprise ERP system (~35 tables, ~10000 rows)
#
# Usage:
#   make all          - Create all databases
#   make small        - Create only the small blog database
#   make medium       - Create only the medium e-commerce database
#   make large        - Create only the large ERP database
#   make clean        - Drop all test databases
#   make verify       - Verify all databases are accessible
#   make stats        - Show table/row counts for all databases
#
# =============================================================================

# Database connection settings (override with environment variables)
PG_HOST ?= localhost
PG_PORT ?= 5432
PG_USER ?= postgres
PG_PASSWORD ?=

# Database names
DB_SMALL = pg_mcp_test_small
DB_MEDIUM = pg_mcp_test_medium
DB_LARGE = pg_mcp_test_large

# PostgreSQL command with connection options
PSQL = PGPASSWORD=$(PG_PASSWORD) psql -h $(PG_HOST) -p $(PG_PORT) -U $(PG_USER)

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: all small medium large clean verify stats help docker-up docker-down

# =============================================================================
# Help
# =============================================================================

help:
	@echo "PostgreSQL MCP Server Test Fixtures"
	@echo ""
	@echo "Usage:"
	@echo "  make all          - Create all test databases"
	@echo "  make small        - Create small blog database ($(DB_SMALL))"
	@echo "  make medium       - Create medium e-commerce database ($(DB_MEDIUM))"
	@echo "  make large        - Create large ERP database ($(DB_LARGE))"
	@echo "  make clean        - Drop all test databases"
	@echo "  make verify       - Verify all databases are accessible"
	@echo "  make stats        - Show table/row counts for all databases"
	@echo "  make docker-up    - Start PostgreSQL in Docker"
	@echo "  make docker-down  - Stop PostgreSQL Docker container"
	@echo ""
	@echo "Environment Variables:"
	@echo "  PG_HOST     - PostgreSQL host (default: localhost)"
	@echo "  PG_PORT     - PostgreSQL port (default: 5432)"
	@echo "  PG_USER     - PostgreSQL user (default: postgres)"
	@echo "  PG_PASSWORD - PostgreSQL password (default: postgres)"

# =============================================================================
# Main Targets
# =============================================================================

all: small medium large
	@echo "$(GREEN)✓ All test databases created successfully$(NC)"

# Create small blog database
small: drop-small
	@echo "$(YELLOW)Creating database: $(DB_SMALL)...$(NC)"
	@$(PSQL) -c "CREATE DATABASE $(DB_SMALL);" 2>/dev/null || true
	@$(PSQL) -d $(DB_SMALL) -f small_blog.sql -q
	@echo "$(GREEN)✓ $(DB_SMALL) created$(NC)"

# Create medium e-commerce database
medium: drop-medium
	@echo "$(YELLOW)Creating database: $(DB_MEDIUM)...$(NC)"
	@$(PSQL) -c "CREATE DATABASE $(DB_MEDIUM);" 2>/dev/null || true
	@$(PSQL) -d $(DB_MEDIUM) -f medium_ecommerce.sql -q
	@echo "$(GREEN)✓ $(DB_MEDIUM) created$(NC)"

# Create large ERP database
large: drop-large
	@echo "$(YELLOW)Creating database: $(DB_LARGE)...$(NC)"
	@$(PSQL) -c "CREATE DATABASE $(DB_LARGE);" 2>/dev/null || true
	@$(PSQL) -d $(DB_LARGE) -f large_erp.sql -q
	@echo "$(GREEN)✓ $(DB_LARGE) created$(NC)"

# =============================================================================
# Cleanup Targets
# =============================================================================

clean: drop-small drop-medium drop-large
	@echo "$(GREEN)✓ All test databases dropped$(NC)"

drop-small:
	@echo "Dropping $(DB_SMALL)..."
	@$(PSQL) -c "DROP DATABASE IF EXISTS $(DB_SMALL);" 2>/dev/null || true

drop-medium:
	@echo "Dropping $(DB_MEDIUM)..."
	@$(PSQL) -c "DROP DATABASE IF EXISTS $(DB_MEDIUM);" 2>/dev/null || true

drop-large:
	@echo "Dropping $(DB_LARGE)..."
	@$(PSQL) -c "DROP DATABASE IF EXISTS $(DB_LARGE);" 2>/dev/null || true

# =============================================================================
# Verification & Statistics
# =============================================================================

verify:
	@echo "Verifying database connections..."
	@echo ""
	@echo "$(YELLOW)$(DB_SMALL):$(NC)"
	@$(PSQL) -d $(DB_SMALL) -c "SELECT 'Connected' as status;" 2>/dev/null && echo "$(GREEN)  ✓ Connected$(NC)" || echo "$(RED)  ✗ Failed$(NC)"
	@echo ""
	@echo "$(YELLOW)$(DB_MEDIUM):$(NC)"
	@$(PSQL) -d $(DB_MEDIUM) -c "SELECT 'Connected' as status;" 2>/dev/null && echo "$(GREEN)  ✓ Connected$(NC)" || echo "$(RED)  ✗ Failed$(NC)"
	@echo ""
	@echo "$(YELLOW)$(DB_LARGE):$(NC)"
	@$(PSQL) -d $(DB_LARGE) -c "SELECT 'Connected' as status;" 2>/dev/null && echo "$(GREEN)  ✓ Connected$(NC)" || echo "$(RED)  ✗ Failed$(NC)"

stats:
	@echo "$(YELLOW)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(YELLOW)                    Database Statistics                         $(NC)"
	@echo "$(YELLOW)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(GREEN)$(DB_SMALL) (Blog System):$(NC)"
	@$(PSQL) -d $(DB_SMALL) -c "\
		SELECT \
			'Tables' as object_type, \
			COUNT(*)::text as count \
		FROM information_schema.tables \
		WHERE table_schema = 'blog' AND table_type = 'BASE TABLE' \
		UNION ALL \
		SELECT \
			'Views', \
			COUNT(*)::text \
		FROM information_schema.tables \
		WHERE table_schema = 'blog' AND table_type = 'VIEW' \
		UNION ALL \
		SELECT \
			'Indexes', \
			COUNT(*)::text \
		FROM pg_indexes \
		WHERE schemaname = 'blog' \
		UNION ALL \
		SELECT \
			'Custom Types', \
			COUNT(*)::text \
		FROM pg_type t \
		JOIN pg_namespace n ON t.typnamespace = n.oid \
		WHERE n.nspname = 'blog' AND t.typtype = 'e';" 2>/dev/null || echo "  Database not found"
	@echo ""
	@echo "  Row counts:"
	@$(PSQL) -d $(DB_SMALL) -t -c "\
		SELECT '  - ' || tablename || ': ' || \
			(xpath('/row/cnt/text()', xml_count))[1]::text \
		FROM ( \
			SELECT tablename, \
				query_to_xml('SELECT COUNT(*) as cnt FROM blog.' || tablename, false, true, '') as xml_count \
			FROM pg_tables WHERE schemaname = 'blog' \
		) t ORDER BY tablename;" 2>/dev/null || true
	@echo ""
	@echo "$(GREEN)$(DB_MEDIUM) (E-Commerce):$(NC)"
	@$(PSQL) -d $(DB_MEDIUM) -c "\
		SELECT \
			'Tables' as object_type, \
			COUNT(*)::text as count \
		FROM information_schema.tables \
		WHERE table_schema = 'ecommerce' AND table_type = 'BASE TABLE' \
		UNION ALL \
		SELECT \
			'Views', \
			COUNT(*)::text \
		FROM information_schema.tables \
		WHERE table_schema = 'ecommerce' AND table_type = 'VIEW' \
		UNION ALL \
		SELECT \
			'Indexes', \
			COUNT(*)::text \
		FROM pg_indexes \
		WHERE schemaname = 'ecommerce' \
		UNION ALL \
		SELECT \
			'Custom Types', \
			COUNT(*)::text \
		FROM pg_type t \
		JOIN pg_namespace n ON t.typnamespace = n.oid \
		WHERE n.nspname = 'ecommerce' AND t.typtype = 'e';" 2>/dev/null || echo "  Database not found"
	@echo ""
	@echo "  Row counts (top 10 tables):"
	@$(PSQL) -d $(DB_MEDIUM) -t -c "\
		SELECT '  - ' || tablename || ': ' || \
			(xpath('/row/cnt/text()', xml_count))[1]::text \
		FROM ( \
			SELECT tablename, \
				query_to_xml('SELECT COUNT(*) as cnt FROM ecommerce.' || tablename, false, true, '') as xml_count \
			FROM pg_tables WHERE schemaname = 'ecommerce' \
		) t ORDER BY (xpath('/row/cnt/text()', xml_count))[1]::text::int DESC LIMIT 10;" 2>/dev/null || true
	@echo ""
	@echo "$(GREEN)$(DB_LARGE) (ERP System):$(NC)"
	@$(PSQL) -d $(DB_LARGE) -c "\
		SELECT \
			'Tables' as object_type, \
			COUNT(*)::text as count \
		FROM information_schema.tables \
		WHERE table_schema = 'erp' AND table_type = 'BASE TABLE' \
		UNION ALL \
		SELECT \
			'Views', \
			COUNT(*)::text \
		FROM information_schema.tables \
		WHERE table_schema = 'erp' AND table_type = 'VIEW' \
		UNION ALL \
		SELECT \
			'Indexes', \
			COUNT(*)::text \
		FROM pg_indexes \
		WHERE schemaname = 'erp' \
		UNION ALL \
		SELECT \
			'Custom Types', \
			COUNT(*)::text \
		FROM pg_type t \
		JOIN pg_namespace n ON t.typnamespace = n.oid \
		WHERE n.nspname = 'erp' AND t.typtype = 'e';" 2>/dev/null || echo "  Database not found"
	@echo ""
	@echo "  Row counts (top 15 tables):"
	@$(PSQL) -d $(DB_LARGE) -t -c "\
		SELECT '  - ' || tablename || ': ' || \
			(xpath('/row/cnt/text()', xml_count))[1]::text \
		FROM ( \
			SELECT tablename, \
				query_to_xml('SELECT COUNT(*) as cnt FROM erp.' || tablename, false, true, '') as xml_count \
			FROM pg_tables WHERE schemaname = 'erp' \
		) t ORDER BY (xpath('/row/cnt/text()', xml_count))[1]::text::int DESC LIMIT 15;" 2>/dev/null || true

# =============================================================================
# Docker Support
# =============================================================================

docker-up:
	@echo "Starting PostgreSQL in Docker..."
	@docker run -d \
		--name pg-mcp-test \
		-e POSTGRES_USER=$(PG_USER) \
		-e POSTGRES_PASSWORD=$(PG_PASSWORD) \
		-p $(PG_PORT):5432 \
		postgres:16-alpine \
		2>/dev/null || docker start pg-mcp-test
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 3
	@echo "$(GREEN)✓ PostgreSQL is running on port $(PG_PORT)$(NC)"

docker-down:
	@echo "Stopping PostgreSQL Docker container..."
	@docker stop pg-mcp-test 2>/dev/null || true
	@docker rm pg-mcp-test 2>/dev/null || true
	@echo "$(GREEN)✓ PostgreSQL container stopped and removed$(NC)"

# =============================================================================
# Readonly User Setup (for testing)
# =============================================================================

setup-readonly-user:
	@echo "Creating readonly users for each database..."
	@$(PSQL) -d $(DB_SMALL) -c "\
		DROP USER IF EXISTS mcp_readonly; \
		CREATE USER mcp_readonly WITH PASSWORD 'readonly123'; \
		GRANT CONNECT ON DATABASE $(DB_SMALL) TO mcp_readonly; \
		GRANT USAGE ON SCHEMA blog TO mcp_readonly; \
		GRANT SELECT ON ALL TABLES IN SCHEMA blog TO mcp_readonly;" 2>/dev/null || true
	@$(PSQL) -d $(DB_MEDIUM) -c "\
		GRANT CONNECT ON DATABASE $(DB_MEDIUM) TO mcp_readonly; \
		GRANT USAGE ON SCHEMA ecommerce TO mcp_readonly; \
		GRANT SELECT ON ALL TABLES IN SCHEMA ecommerce TO mcp_readonly;" 2>/dev/null || true
	@$(PSQL) -d $(DB_LARGE) -c "\
		GRANT CONNECT ON DATABASE $(DB_LARGE) TO mcp_readonly; \
		GRANT USAGE ON SCHEMA erp TO mcp_readonly; \
		GRANT SELECT ON ALL TABLES IN SCHEMA erp TO mcp_readonly;" 2>/dev/null || true
	@echo "$(GREEN)✓ Readonly user 'mcp_readonly' created with password 'readonly123'$(NC)"

# =============================================================================
# Generate sample config
# =============================================================================

sample-config:
	@echo "# pg-mcp test configuration" > ../config.test.yaml
	@echo "databases:" >> ../config.test.yaml
	@echo "  - name: blog" >> ../config.test.yaml
	@echo "    host: $(PG_HOST)" >> ../config.test.yaml
	@echo "    port: $(PG_PORT)" >> ../config.test.yaml
	@echo "    database: $(DB_SMALL)" >> ../config.test.yaml
	@echo "    user: mcp_readonly" >> ../config.test.yaml
	@echo '    password: "$${MCP_PG_PASSWORD}"' >> ../config.test.yaml
	@echo "    schema: blog" >> ../config.test.yaml
	@echo "" >> ../config.test.yaml
	@echo "  - name: ecommerce" >> ../config.test.yaml
	@echo "    host: $(PG_HOST)" >> ../config.test.yaml
	@echo "    port: $(PG_PORT)" >> ../config.test.yaml
	@echo "    database: $(DB_MEDIUM)" >> ../config.test.yaml
	@echo "    user: mcp_readonly" >> ../config.test.yaml
	@echo '    password: "$${MCP_PG_PASSWORD}"' >> ../config.test.yaml
	@echo "    schema: ecommerce" >> ../config.test.yaml
	@echo "" >> ../config.test.yaml
	@echo "  - name: erp" >> ../config.test.yaml
	@echo "    host: $(PG_HOST)" >> ../config.test.yaml
	@echo "    port: $(PG_PORT)" >> ../config.test.yaml
	@echo "    database: $(DB_LARGE)" >> ../config.test.yaml
	@echo "    user: mcp_readonly" >> ../config.test.yaml
	@echo '    password: "$${MCP_PG_PASSWORD}"' >> ../config.test.yaml
	@echo "    schema: erp" >> ../config.test.yaml
	@echo "" >> ../config.test.yaml
	@echo "openai_api_key: \"\$${OPENAI_API_KEY}\"" >> ../config.test.yaml
	@echo "openai_model: gpt-4o-mini" >> ../config.test.yaml
	@echo "cache_refresh_interval: 3600" >> ../config.test.yaml
	@echo "max_result_rows: 1000" >> ../config.test.yaml
	@echo "query_timeout: 30" >> ../config.test.yaml
	@echo "$(GREEN)✓ Sample config written to ../config.test.yaml$(NC)"
