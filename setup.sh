#!/bin/bash

# DbRevel Complete Setup Script
# Sets up the entire development environment (databases + backend + frontend)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

clear
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║                    dbrevel SETUP                           ║"
echo "║         AI-Powered Universal Database SDK                  ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}\n"

# Check Docker
if command_exists docker; then
    print_status 0 "Docker installed"
    docker --version
else
    print_status 1 "Docker not found"
    echo -e "${RED}Please install Docker Desktop: https://www.docker.com/products/docker-desktop${NC}"
    exit 1
fi

# Check Docker Compose
if command_exists docker-compose || docker compose version &> /dev/null; then
    print_status 0 "Docker Compose installed"
else
    print_status 1 "Docker Compose not found"
    echo -e "${RED}Please install Docker Compose${NC}"
    exit 1
fi

# Check Python (optional, for local development)
if command_exists python3; then
    print_status 0 "Python 3 installed ($(python3 --version))"
    HAS_PYTHON=true
else
    print_status 1 "Python 3 not found (optional for local dev)"
    HAS_PYTHON=false
fi

echo ""

# Step 2: Environment setup
echo -e "${YELLOW}Step 2: Setting up environment...${NC}\n"

if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}\n"

    echo -e "${YELLOW}⚠️  IMPORTANT: You need to add your Gemini API key${NC}"
    echo -e "${BLUE}Get your API key from: https://makersuite.google.com/app/apikey${NC}\n"

    read -p "Do you have your Gemini API key ready? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Gemini API key: " api_key
        if [[ -n "$api_key" ]]; then
            # Update .env file with API key
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                sed -i '' "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=$api_key/" .env
            else
                # Linux
                sed -i "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=$api_key/" .env
            fi
            echo -e "${GREEN}✓ API key saved to .env${NC}"
        fi
    else
        echo -e "${YELLOW}Please edit .env and add your GEMINI_API_KEY before starting${NC}"
    fi
else
    echo -e "${GREEN}✓ .env file already exists${NC}"

    # Check if API key is set
    if grep -q "GEMINI_API_KEY=your_gemini_api_key_here" .env; then
        echo -e "${RED}⚠️  WARNING: Gemini API key not configured in .env${NC}"
        echo -e "${YELLOW}Please edit .env and add your GEMINI_API_KEY${NC}"
    else
        echo -e "${GREEN}✓ Gemini API key appears to be configured${NC}"
    fi
fi

echo ""

# Step 3: Start Docker services
echo -e "${YELLOW}Step 3: Starting Docker services...${NC}\n"

# Pull images first
echo -e "${YELLOW}Pulling Docker images (this may take a few minutes)...${NC}"
docker-compose pull

# Start services
echo -e "${YELLOW}Starting all services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Check service health
echo -e "\n${YELLOW}Checking service health...${NC}\n"

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_status 0 "API is running"
else
    print_status 1 "API not responding yet (may need more time)"
fi

echo ""

# Final instructions
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    SETUP COMPLETE!                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}Your DbRevel environment is ready!${NC}\n"

echo -e "${YELLOW}Access your services:${NC}"
echo "  • API:      http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Frontend: http://localhost:3000"
echo ""

echo -e "${YELLOW}Useful commands:${NC}"
echo "  • View logs:     docker-compose logs -f"
echo "  • Stop services: docker-compose down"
echo "  • Restart:       docker-compose restart"
echo "  • Test API:      ./test_api.sh"
echo ""

echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Make sure your Gemini API key is set in .env"
echo "  2. Open http://localhost:8000/docs in your browser"
echo "  3. Try a query from the frontend: http://localhost:3000"
echo ""

echo -e "${GREEN}Happy building! 🚀${NC}\n"
