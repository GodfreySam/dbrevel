#!/bin/bash

# DbRevel Backend Startup Script
# This script sets up a Python virtual environment and starts the FastAPI backend

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 DbRevel Backend Startup${NC}\n"

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found${NC}"
    echo "Please run this script from the backend/ directory"
    exit 1
fi

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Found Python $PYTHON_VERSION${NC}\n"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}\n"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}\n"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}\n"

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip -q
echo -e "${GREEN}✓ pip upgraded${NC}\n"

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}\n"

# Check for .env file
echo -e "${YELLOW}Checking configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}Warning: .env file not found in current directory${NC}"
    echo "Please copy .env.example to .env and add your GEMINI_API_KEY"
    echo ""
    # Check if .env.example exists in current dir or parent dir
    if [ -f ".env.example" ]; then
        ENV_EXAMPLE=".env.example"
    elif [ -f "../.env.example" ]; then
        ENV_EXAMPLE="../.env.example"
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi

    read -p "Would you like to create .env now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "$ENV_EXAMPLE" .env
        echo -e "${YELLOW}Please edit .env and add your GEMINI_API_KEY${NC}"
        exit 0
    fi
fi

# Check required environment variables
if [ -f ".env" ]; then
    # Load environment variables from .env file safely
    # This handles special characters in values (like URLs with colons, slashes, etc.)
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        # Remove leading/trailing whitespace
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            # Split on first = only (to handle values with = signs)
            if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
                key="${BASH_REMATCH[1]}"
                value="${BASH_REMATCH[2]}"
                # Remove quotes from value if present
                value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                # Remove leading/trailing whitespace from key
                key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                # Export the variable using declare (safer than eval)
                declare -x "${key}"="${value}"
            fi
    done < .env

    if [ -z "$GEMINI_API_KEY" ]; then
        echo -e "${RED}Error: GEMINI_API_KEY not set in .env${NC}"
        exit 1
    fi

    if [ -z "$POSTGRES_URL" ]; then
        echo -e "${YELLOW}Warning: POSTGRES_URL not set, using default${NC}"
        export POSTGRES_URL="postgresql://dev:dev@localhost:5432/dbreveldemo"
    fi

    if [ -z "$MONGODB_URL" ]; then
        echo -e "${YELLOW}Warning: MONGODB_URL not set, using default${NC}"
        export MONGODB_URL="mongodb://localhost:27017/dbreveldemo"
    fi

    echo -e "${GREEN}✓ Configuration loaded${NC}\n"
fi

# Start databases using Docker Compose
echo -e "${YELLOW}Starting databases with Docker Compose...${NC}"

# Determine docker-compose command (support both standalone and plugin versions)
DOCKER_COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
fi

if [ -n "$DOCKER_COMPOSE_CMD" ]; then
    # Navigate to project root (parent directory from backend/)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        echo -e "${YELLOW}Found docker-compose.yml, starting services...${NC}"
        # Temporarily disable exit on error for this section
        set +e
        cd "$PROJECT_ROOT"
        $DOCKER_COMPOSE_CMD up -d postgres mongodb redis > /dev/null 2>&1
        DOCKER_EXIT_CODE=$?
        cd "$SCRIPT_DIR"
        set -e

        if [ $DOCKER_EXIT_CODE -eq 0 ]; then
            echo -e "${GREEN}✓ Docker Compose services started${NC}\n"
            # Wait a moment for services to be ready
            sleep 2
        else
            echo -e "${YELLOW}⚠ Docker Compose command failed (services may already be running)${NC}\n"
        fi
    else
        echo -e "${YELLOW}⚠ docker-compose.yml not found in project root${NC}"
        echo "  Skipping Docker Compose startup"
        echo ""
    fi
else
    echo -e "${YELLOW}⚠ Docker Compose not found${NC}"
    echo "  Make sure Docker is installed and docker-compose/docker compose is available"
    echo "  Or start databases manually: docker-compose up -d postgres mongodb redis"
    echo ""
fi

# Check if databases are running (if using local Docker)
echo -e "${YELLOW}Checking database connections...${NC}"

# Try to connect to PostgreSQL
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
    else
        echo -e "${YELLOW}⚠ PostgreSQL not detected on localhost:5432${NC}"
        echo "  Make sure your database is running or update POSTGRES_URL in .env"
    fi
else
    echo -e "${YELLOW}⚠ pg_isready not found, skipping PostgreSQL check${NC}"
fi

# Try to connect to MongoDB
if command -v mongosh &> /dev/null; then
    if mongosh --eval "db.adminCommand('ping')" mongodb://localhost:27017 &> /dev/null; then
        echo -e "${GREEN}✓ MongoDB is running${NC}"
    else
        echo -e "${YELLOW}⚠ MongoDB not detected on localhost:27017${NC}"
        echo "  Make sure your database is running or update MONGODB_URL in .env"
    fi
else
    echo -e "${YELLOW}⚠ mongosh not found, skipping MongoDB check${NC}"
fi

echo ""

# Start the server
echo -e "${GREEN}Starting DbRevel API server...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"
echo "----------------------------------------"
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
echo "ReDoc: http://localhost:8000/redoc"
echo "----------------------------------------"
echo ""

# Start uvicorn with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Deactivate virtual environment on exit (won't actually run if Ctrl+C is used)
deactivate
