# DB Query Tool Makefile
# Usage: make [target]

.PHONY: all install dev backend frontend test lint clean help

# Default target
all: help

#---------------------------------------------------------------------------
# Installation
#---------------------------------------------------------------------------

## Install all dependencies (backend and frontend)
install: install-backend install-frontend

## Install backend dependencies
install-backend:
	cd backend && uv sync --dev

## Install frontend dependencies
install-frontend:
	cd frontend && yarn install

#---------------------------------------------------------------------------
# Development
#---------------------------------------------------------------------------

## Start development servers (backend and frontend)
dev:
	@echo "Starting development servers..."
	@make -j2 backend frontend

## Start backend server (port 8000)
backend:
	cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

## Start frontend server (port 5173)
frontend:
	cd frontend && yarn dev

## Start backend in background
backend-bg:
	cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &

#---------------------------------------------------------------------------
# Testing
#---------------------------------------------------------------------------

## Run all tests
test: test-backend test-frontend

## Run backend tests
test-backend:
	cd backend && uv run pytest -v

## Run backend tests with coverage
test-backend-cov:
	cd backend && uv run pytest --cov=src --cov-report=html

## Run frontend tests
test-frontend:
	cd frontend && yarn test:run

## Run frontend tests with coverage
test-frontend-cov:
	cd frontend && yarn test --coverage

#---------------------------------------------------------------------------
# Code Quality
#---------------------------------------------------------------------------

## Run all linting
lint: lint-backend lint-frontend

## Run backend linting
lint-backend:
	cd backend && uv run ruff check .

## Run backend linting with auto-fix
lint-backend-fix:
	cd backend && uv run ruff check --fix .

## Format backend code
format-backend:
	cd backend && uv run ruff format .

## Run frontend linting
lint-frontend:
	cd frontend && yarn lint

## Run frontend type checking
typecheck-frontend:
	cd frontend && yarn typecheck

#---------------------------------------------------------------------------
# Build
#---------------------------------------------------------------------------

## Build frontend for production
build-frontend:
	cd frontend && yarn build

## Build backend package
build-backend:
	cd backend && uv build

## Build all
build: build-backend build-frontend

#---------------------------------------------------------------------------
# Database
#---------------------------------------------------------------------------

## Create PostgreSQL test database
db-create:
	createdb db_query_test || true

## Load PostgreSQL test schema
db-load:
	psql db_query_test < fixtures/test_schema.sql

## Setup PostgreSQL test database (create + load)
db-setup-pg: db-create db-load

## Setup MySQL test database
db-setup-mysql:
	mysql -u root < fixtures/setup_mysql_testdb.sql

## Setup all test databases (PostgreSQL + MySQL)
db-setup: db-setup-pg db-setup-mysql

## Drop PostgreSQL test database
db-drop:
	dropdb db_query_test || true

## Drop MySQL test database
db-drop-mysql:
	mysql -u root -e "DROP DATABASE IF EXISTS ecommerce_test"

## Reset PostgreSQL test database
db-reset: db-drop db-setup-pg

## Reset MySQL test database
db-reset-mysql: db-drop-mysql db-setup-mysql

## Reset all test databases
db-reset-all: db-reset db-reset-mysql

#---------------------------------------------------------------------------
# Cleanup
#---------------------------------------------------------------------------

## Clean build artifacts
clean:
	rm -rf backend/.pytest_cache
	rm -rf backend/htmlcov
	rm -rf backend/dist
	rm -rf backend/.ruff_cache
	rm -rf frontend/dist
	rm -rf frontend/coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

## Clean all (including dependencies)
clean-all: clean
	rm -rf backend/.venv
	rm -rf frontend/node_modules

#---------------------------------------------------------------------------
# Documentation
#---------------------------------------------------------------------------

## Open API documentation in browser
docs:
	open http://localhost:8000/docs

## Generate API client (requires openapi-generator)
gen-client:
	@echo "Fetching OpenAPI spec..."
	curl -s http://localhost:8000/openapi.json -o openapi.json
	@echo "Generating TypeScript client..."
	npx @openapitools/openapi-generator-cli generate \
		-i openapi.json \
		-g typescript-fetch \
		-o frontend/src/api-client
	rm openapi.json

#---------------------------------------------------------------------------
# Docker (optional)
#---------------------------------------------------------------------------

## Build Docker images
docker-build:
	docker build -t db-query-backend ./backend
	docker build -t db-query-frontend ./frontend

## Run with Docker Compose
docker-up:
	docker-compose up -d

## Stop Docker containers
docker-down:
	docker-compose down

#---------------------------------------------------------------------------
# Help
#---------------------------------------------------------------------------

## Show this help message
help:
	@echo "DB Query Tool - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make install      # Install all dependencies"
	@echo "  make dev          # Start development servers"
	@echo "  make test         # Run all tests"
	@echo "  make lint         # Run linting"
	@echo "  make db-setup     # Setup test database"
