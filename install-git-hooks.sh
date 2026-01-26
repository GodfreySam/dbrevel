#!/bin/bash
# Install git hooks for the project
# This script copies hooks from git-hooks/ to .git/hooks/

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
HOOKS_SOURCE_DIR="${PROJECT_ROOT}/git-hooks"
GIT_HOOKS_DIR="${PROJECT_ROOT}/.git/hooks"

if [ ! -d "$HOOKS_SOURCE_DIR" ]; then
    echo "Error: hooks directory not found at $HOOKS_SOURCE_DIR"
    exit 1
fi

if [ ! -d "$GIT_HOOKS_DIR" ]; then
    echo "Error: .git/hooks directory not found. Are you in a git repository?"
    exit 1
fi

echo -e "${YELLOW}Installing git hooks...${NC}"

# Copy pre-push hook
if [ -f "${HOOKS_SOURCE_DIR}/pre-push" ]; then
    cp "${HOOKS_SOURCE_DIR}/pre-push" "${GIT_HOOKS_DIR}/pre-push"
    chmod +x "${GIT_HOOKS_DIR}/pre-push"
    echo -e "${GREEN}✓ Installed pre-push hook${NC}"
else
    echo "Warning: pre-push hook not found in $HOOKS_SOURCE_DIR"
fi

echo -e "\n${GREEN}✅ Git hooks installed successfully!${NC}"
echo "The pre-push hook will now run black, ruff, and mypy checks before each push."
