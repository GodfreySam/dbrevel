#!/bin/bash

# Docker Image Pull Script with Retry Logic
# Handles network timeouts and retries failed pulls

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Docker Image Puller with Retry Logic${NC}\n"

# Function to pull image with retries
pull_with_retry() {
    local image=$1
    local max_attempts=3
    local attempt=1

    echo -e "${YELLOW}Pulling: $image${NC}"

    while [ $attempt -le $max_attempts ]; do
        echo -e "  Attempt $attempt/$max_attempts..."

        if docker pull "$image" 2>&1; then
            echo -e "${GREEN}✓ Successfully pulled: $image${NC}\n"
            return 0
        else
            if [ $attempt -lt $max_attempts ]; then
                echo -e "${YELLOW}  Failed, retrying in 5 seconds...${NC}"
                sleep 5
            else
                echo -e "${RED}✗ Failed to pull: $image after $max_attempts attempts${NC}\n"
                return 1
            fi
        fi
        attempt=$((attempt + 1))
    done
}

# List of images to pull
images=(
    "postgres:16-alpine"
    "mongo:7"
    "redis:7-alpine"
    "nginx:alpine"
)

failed_images=()

# Pull each image
for image in "${images[@]}"; do
    if ! pull_with_retry "$image"; then
        failed_images+=("$image")
    fi
done

# Summary
echo -e "${BLUE}════════════════════════════════════════${NC}"
if [ ${#failed_images[@]} -eq 0 ]; then
    echo -e "${GREEN}All images pulled successfully!${NC}"
    echo -e "\nYou can now run: ${YELLOW}docker-compose up -d${NC}"
else
    echo -e "${RED}Failed to pull ${#failed_images[@]} image(s):${NC}"
    for img in "${failed_images[@]}"; do
        echo -e "  - $img"
    done
    echo -e "\n${YELLOW}Troubleshooting:${NC}"
    echo "  1. Check your internet connection"
    echo "  2. Try again later (Docker registry may be busy)"
    echo "  3. Check if you're behind a firewall/proxy"
    echo "  4. Try: docker pull <image> manually"
    exit 1
fi
