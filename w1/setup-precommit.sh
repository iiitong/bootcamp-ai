#!/bin/bash

# Pre-commit Setup Script
# This script installs and configures pre-commit hooks for the project

set -e  # Exit on error

echo "🚀 Setting up pre-commit hooks..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 pre-commit not found. Installing..."

    # Try uv first, then pip
    if command -v uv &> /dev/null; then
        echo "Using uv to install pre-commit..."
        uv tool install pre-commit
    elif command -v pip &> /dev/null; then
        echo "Using pip to install pre-commit..."
        pip install pre-commit
    else
        echo "❌ Error: Neither uv nor pip found. Please install pre-commit manually:"
        echo "   pip install pre-commit"
        exit 1
    fi
else
    echo "✅ pre-commit is already installed"
fi

# Install the git hooks
echo "🔧 Installing git hooks..."
pre-commit install

# Optional: Run on all files to check setup
echo ""
echo "Would you like to run pre-commit on all files now? (y/n)"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "🔍 Running pre-commit on all files..."
    pre-commit run --all-files || {
        echo ""
        echo "⚠️  Some checks failed, but that's OK!"
        echo "Files have been automatically fixed where possible."
        echo "Please review the changes and commit them."
    }
else
    echo "⏭️  Skipping pre-commit run. It will run automatically on your next commit."
fi

echo ""
echo "✨ Pre-commit setup complete!"
echo ""
echo "Next steps:"
echo "  1. Make changes to your code"
echo "  2. git add ."
echo "  3. git commit -m 'your message'"
echo "  4. Pre-commit will automatically check your code!"
echo ""
echo "To manually run pre-commit:"
echo "  pre-commit run --all-files"
echo ""
echo "To update hooks:"
echo "  pre-commit autoupdate"
