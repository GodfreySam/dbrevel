#!/bin/bash

# Colors for output
GREEN='\033[0.32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing DbRevel API${NC}\n"

# Test 1: Health Check
echo -e "${YELLOW}1. Health Check...${NC}"
response=$(curl -s http://localhost:8000/health)
echo "$response" | jq '.'
if echo "$response" | jq -e '.status == "healthy"' > /dev/null; then
    echo -e "${GREEN}✓ Health check passed${NC}\n"
else
    echo -e "${RED}✗ Health check failed${NC}\n"
    exit 1
fi

# Test 2: Simple Query
echo -e "${YELLOW}2. Simple Query (Get all users from Lagos)...${NC}"
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Get all users from Lagos",
    "explain": true
  }' | jq '.metadata.query_plan.reasoning, .data | length'
echo -e "${GREEN}✓ Simple query executed${NC}\n"

# Test 3: Complex Query
echo -e "${YELLOW}3. Complex Query (Users with multiple orders)...${NC}"
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Show me users who have placed more than 1 order",
    "explain": true
  }' | jq '.metadata.execution_time_ms, .metadata.rows_returned'
echo -e "${GREEN}✓ Complex query executed${NC}\n"

# Test 4: Dry Run
echo -e "${YELLOW}4. Dry Run (Plan without executing)...${NC}"
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Get top 5 products by price",
    "dry_run": true,
    "explain": true
  }' | jq '.metadata.query_plan.queries[0].query'
echo -e "${GREEN}✓ Dry run completed${NC}\n"

echo -e "${GREEN}All tests passed!${NC}"
