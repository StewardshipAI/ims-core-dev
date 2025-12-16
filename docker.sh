#!/bin/bash
# IMS Docker Helper Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load .env file
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Create .env from .env.example:"
    echo "  cp .env.example .env"
    exit 1
fi

# Export .env variables
export $(cat .env | grep -v '^#' | xargs)

# Function: Start containers
start() {
    echo -e "${YELLOW}🚀 Starting IMS containers...${NC}"
    docker-compose up -d
    echo -e "${GREEN}✅ Containers started!${NC}"
    echo ""
    echo "Services:"
    echo "  📊 PostgreSQL: localhost:5432"
    echo "  💾 Redis: localhost:6379"
    echo "  🔗 API: http://localhost:8000"
    echo "  📚 Swagger UI: http://localhost:8000/docs"
    echo ""
    docker-compose ps
}

# Function: Stop containers
stop() {
    echo -e "${YELLOW}🛑 Stopping IMS containers...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Containers stopped!${NC}"
}

# Function: Stop & remove volumes (clean slate)
clean() {
    echo -e "${RED}⚠️  Removing containers AND all data...${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        echo -e "${GREEN}✅ All data removed!${NC}"
    fi
}

# Function: View logs
logs() {
    docker-compose logs -f ${1:-api}
}

# Function: Run tests
test() {
    echo -e "${YELLOW}🧪 Running tests...${NC}"
    docker-compose run --rm api pytest tests/ -v
}

# Function: Create test data
populate() {
    echo -e "${YELLOW}📝 Registering test models...${NC}"
    
    ADMIN_KEY=$(grep ADMIN_API_KEY .env | cut -d= -f2)
    
    # Wait for API to be ready
    echo "⏳ Waiting for API to be healthy..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null; then
            echo "✅ API is ready!"
            break
        fi
        echo "  Attempt $i/30..."
        sleep 1
    done
    
    # Register models
    echo ""
    echo "Registering test models..."
    
    curl -s -X POST http://localhost:8000/api/v1/models/register \
      -H "Content-Type: application/json" \
      -H "X-Admin-Key: $ADMIN_KEY" \
      -d '{
        "model_id": "gpt-4-turbo",
        "vendor_id": "OpenAI",
        "capability_tier": "Tier_1",
        "context_window": 128000,
        "cost_in_per_mil": 10.0,
        "cost_out_per_mil": 30.0,
        "function_call_support": true,
        "is_active": true
      }' > /dev/null && echo "✅ Registered: gpt-4-turbo"
    
    curl -s -X POST http://localhost:8000/api/v1/models/register \
      -H "Content-Type: application/json" \
      -H "X-Admin-Key: $ADMIN_KEY" \
      -d '{
        "model_id": "claude-3-opus",
        "vendor_id": "Anthropic",
        "capability_tier": "Tier_1",
        "context_window": 200000,
        "cost_in_per_mil": 15.0,
        "cost_out_per_mil": 75.0,
        "function_call_support": true,
        "is_active": true
      }' > /dev/null && echo "✅ Registered: claude-3-opus"
    
    curl -s -X POST http://localhost:8000/api/v1/models/register \
      -H "Content-Type: application/json" \
      -H "X-Admin-Key: $ADMIN_KEY" \
      -d '{
        "model_id": "gemini-pro",
        "vendor_id": "Google",
        "capability_tier": "Tier_2",
        "context_window": 32000,
        "cost_in_per_mil": 0.5,
        "cost_out_per_mil": 1.5,
        "function_call_support": true,
        "is_active": true
      }' > /dev/null && echo "✅ Registered: gemini-pro"
    
    echo ""
    echo -e "${GREEN}✅ Test data loaded!${NC}"
    echo "Try: curl -s http://localhost:8000/api/v1/models/filter?vendor_id=OpenAI | jq"
}

# Function: Print help
help() {
    cat << EOF
${GREEN}IMS Docker Helper${NC}

Usage: ./docker.sh [COMMAND]

Commands:
  start       🚀 Start all containers (PostgreSQL, Redis, API)
  stop        🛑 Stop all containers
  clean       🧹 Remove containers and ALL data (WARNING!)
  logs        📋 View container logs (default: api)
  test        🧪 Run pytest suite
  populate    📝 Register test models
  ps          📊 Show container status
  help        ❓ Show this help message

Examples:
  ./docker.sh start                 # Start containers
  ./docker.sh logs api              # View API logs
  ./docker.sh logs postgres         # View PostgreSQL logs
  ./docker.sh populate              # Load test data
  ./docker.sh clean                 # Remove everything

Environment:
  Edit .env before running commands

Documentation:
  Swagger UI: http://localhost:8000/docs
  ReDoc: http://localhost:8000/redoc
EOF
}

# Main
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    clean)
        clean
        ;;
    logs)
        logs $2
        ;;
    test)
        test
        ;;
    populate)
        populate
        ;;
    ps)
        docker-compose ps
        ;;
    help)
        help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        help
        exit 1
        ;;
esac
