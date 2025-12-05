#!/bin/bash

# Project Alpha - Setup Verification Script
# This script verifies that the project is set up correctly

set -e

echo "🔍 Project Alpha - Setup Verification"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is NOT installed"
        return 1
    fi
}

check_service() {
    if curl -s $1 > /dev/null; then
        echo -e "${GREEN}✓${NC} Service at $1 is responding"
        return 0
    else
        echo -e "${RED}✗${NC} Service at $1 is NOT responding"
        return 1
    fi
}

# Track failures
FAILURES=0

echo "1. Checking Prerequisites"
echo "-------------------------"
check_command python || ((FAILURES++))
check_command node || ((FAILURES++))
check_command psql || ((FAILURES++))
check_command uv || ((FAILURES++))
check_command yarn || ((FAILURES++))
echo ""

echo "2. Checking Python Version"
echo "--------------------------"
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"
if [[ $(echo "$PYTHON_VERSION" | cut -d. -f1,2 | awk '{print ($1 >= 3.13)}') == 1 ]]; then
    echo -e "${GREEN}✓${NC} Python version is >= 3.13"
else
    echo -e "${YELLOW}⚠${NC}  Python version should be >= 3.13"
    ((FAILURES++))
fi
echo ""

echo "3. Checking Node.js Version"
echo "---------------------------"
NODE_VERSION=$(node --version | cut -d'v' -f2)
echo "Node.js version: $NODE_VERSION"
if [[ $(echo "$NODE_VERSION" | cut -d. -f1) -ge 24 ]]; then
    echo -e "${GREEN}✓${NC} Node.js version is >= 24"
else
    echo -e "${YELLOW}⚠${NC}  Node.js version should be >= 24"
fi
echo ""

echo "4. Checking Database"
echo "--------------------"
if psql -U postgres -lqt | cut -d \| -f 1 | grep -qw project_alpha; then
    echo -e "${GREEN}✓${NC} Database 'project_alpha' exists"
else
    echo -e "${RED}✗${NC} Database 'project_alpha' does NOT exist"
    echo "   Create it with: psql -U postgres -c \"CREATE DATABASE project_alpha;\""
    ((FAILURES++))
fi
echo ""

echo "5. Checking Backend Setup"
echo "-------------------------"
if [ -d "backend/.venv" ]; then
    echo -e "${GREEN}✓${NC} Backend virtual environment exists"
else
    echo -e "${YELLOW}⚠${NC}  Backend virtual environment not found"
    echo "   Run: cd backend && uv sync"
fi

if [ -f "backend/.env" ]; then
    echo -e "${GREEN}✓${NC} Backend .env file exists"
else
    echo -e "${YELLOW}⚠${NC}  Backend .env file not found"
    echo "   Copy from: cp backend/.env.example backend/.env"
fi
echo ""

echo "6. Checking Frontend Setup"
echo "--------------------------"
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✓${NC} Frontend dependencies installed"
else
    echo -e "${YELLOW}⚠${NC}  Frontend dependencies not installed"
    echo "   Run: cd frontend && yarn install"
fi

if [ -f "frontend/.env" ]; then
    echo -e "${GREEN}✓${NC} Frontend .env file exists"
else
    echo -e "${YELLOW}⚠${NC}  Frontend .env file not found"
    echo "   Copy from: cp frontend/.env.example frontend/.env"
fi
echo ""

echo "7. Checking Services (if running)"
echo "---------------------------------"
check_service "http://localhost:8000/health" || echo "   (Backend may not be running - this is OK)"
check_service "http://localhost:5173" || echo "   (Frontend may not be running - this is OK)"
echo ""

echo "8. Checking Documentation"
echo "-------------------------"
DOCS=(
    "README.md"
    "PRE_COMMIT_SETUP.md"
    "QUICK_START.md"
    "PROJECT_SUMMARY.md"
    "../specs/w1/0001-spec.md"
    "../specs/w1/0002-implementation-plan.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "${GREEN}✓${NC} $doc exists"
    else
        echo -e "${RED}✗${NC} $doc is missing"
        ((FAILURES++))
    fi
done
echo ""

# Summary
echo "======================================"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You're ready to start development:"
    echo "1. Backend:  cd backend && uv run uvicorn app.main:app --reload"
    echo "2. Frontend: cd frontend && yarn dev"
    echo ""
    echo "Access the app at: http://localhost:5173"
    echo "API docs at: http://localhost:8000/api/v1/docs"
else
    echo -e "${YELLOW}⚠  $FAILURES issue(s) found${NC}"
    echo "Please address the issues above before starting development."
fi
echo "======================================"
