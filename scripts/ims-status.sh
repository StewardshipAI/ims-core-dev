#!/bin/bash
# IMS Status Dashboard
# Real-time health monitoring and statistics

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
IMS_API_URL="${IMS_API_URL:-http://localhost:8000}"
ADMIN_API_KEY="${ADMIN_API_KEY}"
REFRESH_INTERVAL="${REFRESH_INTERVAL:-5}"

# Function: Print header
print_header() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║            IMS CORE - STATUS DASHBOARD                        ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}API Endpoint:${NC} $IMS_API_URL"
    echo -e "${BLUE}Refresh:${NC} Every ${REFRESH_INTERVAL}s (Ctrl+C to exit)"
    echo ""
}

# Function: Get health status
get_health() {
    if ! HEALTH=$(curl -s -f "${IMS_API_URL}/health" 2>/dev/null); then
        echo -e "${RED}❌ API UNREACHABLE${NC}"
        return 1
    fi
    
    echo "$HEALTH"
}

# Function: Get metrics
get_metrics() {
    if [ -z "$ADMIN_API_KEY" ]; then
        echo "{}"
        return
    fi
    
    METRICS=$(curl -s -f -H "X-Admin-Key: $ADMIN_API_KEY" \
        "${IMS_API_URL}/metrics" 2>/dev/null || echo "{}")
    
    echo "$METRICS"
}

# Function: Display health status
display_health() {
    local health="$1"
    
    echo -e "${CYAN}═══════════════════ SYSTEM HEALTH ═══════════════════${NC}"
    echo ""
    
    # Overall status
    STATUS=$(echo "$health" | jq -r '.status')
    
    if [ "$STATUS" == "healthy" ]; then
        echo -e "  Overall Status: ${GREEN}●${NC} HEALTHY"
    else
        echo -e "  Overall Status: ${RED}●${NC} UNHEALTHY"
    fi
    
    # Database
    DB=$(echo "$health" | jq -r '.database')
    if [ "$DB" == "healthy" ]; then
        echo -e "  Database:       ${GREEN}●${NC} Connected"
    else
        echo -e "  Database:       ${RED}●${NC} $DB"
    fi
    
    # Cache (Redis)
    CACHE=$(echo "$health" | jq -r '.cache')
    if [ "$CACHE" == "healthy" ]; then
        echo -e "  Cache (Redis):  ${GREEN}●${NC} Connected"
    elif [ "$CACHE" == "not_configured" ]; then
        echo -e "  Cache (Redis):  ${YELLOW}○${NC} Not Configured"
    else
        echo -e "  Cache (Redis):  ${RED}●${NC} $CACHE"
    fi
    
    # RabbitMQ
    RMQ=$(echo "$health" | jq -r '.rabbitmq // "unknown"')
    if [ "$RMQ" == "connected" ]; then
        echo -e "  RabbitMQ:       ${GREEN}●${NC} Connected"
    elif [ "$RMQ" == "unknown" ]; then
        echo -e "  RabbitMQ:       ${YELLOW}○${NC} Unknown"
    else
        echo -e "  RabbitMQ:       ${RED}●${NC} $RMQ"
    fi
    
    # Connection pool stats
    MIN_CONN=$(echo "$health" | jq -r '.pool_stats.min_connections // 0')
    MAX_CONN=$(echo "$health" | jq -r '.pool_stats.max_connections // 0')
    
    if [ "$MIN_CONN" != "0" ]; then
        echo ""
        echo -e "  Pool Config:    ${MIN_CONN}-${MAX_CONN} connections"
    fi
}

# Function: Display metrics
display_metrics() {
    local metrics="$1"
    
    echo ""
    echo -e "${CYAN}═══════════════════ USAGE METRICS ═══════════════════${NC}"
    echo ""
    
    if [ "$metrics" == "{}" ]; then
        echo -e "  ${YELLOW}No metrics available (requires ADMIN_API_KEY)${NC}"
        return
    fi
    
    # Models
    TOTAL_MODELS=$(echo "$metrics" | jq -r '.total_models_registered // 0')
    echo -e "  Models Registered:     ${GREEN}$TOTAL_MODELS${NC}"
    
    # Queries
    TOTAL_QUERIES=$(echo "$metrics" | jq -r '.total_model_queries // 0')
    FILTER_QUERIES=$(echo "$metrics" | jq -r '.total_filter_queries // 0')
    echo -e "  Model Queries:         ${BLUE}$TOTAL_QUERIES${NC}"
    echo -e "  Filter Queries:        ${BLUE}$FILTER_QUERIES${NC}"
    
    # Vendor breakdown
    echo ""
    echo -e "  ${CYAN}By Vendor:${NC}"
    
    for vendor in "Google" "OpenAI" "Anthropic" "Meta"; do
        COUNT=$(echo "$metrics" | jq -r ".\"vendor_models:${vendor}\" // 0")
        if [ "$COUNT" != "0" ]; then
            printf "    %-12s %3s models\n" "$vendor:" "$COUNT"
        fi
    done
}

# Function: Display Docker container status
display_docker() {
    echo ""
    echo -e "${CYAN}═══════════════════ DOCKER STATUS ═══════════════════${NC}"
    echo ""
    
    if ! command -v docker &> /dev/null; then
        echo -e "  ${YELLOW}Docker not found${NC}"
        return
    fi
    
    # Get container status
    CONTAINERS=$(docker ps --filter "name=ims-" --format "{{.Names}}\t{{.Status}}" 2>/dev/null || echo "")
    
    if [ -z "$CONTAINERS" ]; then
        echo -e "  ${RED}No IMS containers running${NC}"
        echo -e "  ${YELLOW}Start with: docker-compose up -d${NC}"
        return
    fi
    
    echo "$CONTAINERS" | while IFS=$'\t' read -r name status; do
        # Extract just the container name
        SHORT_NAME=$(echo "$name" | sed 's/ims-//')
        
        # Color code based on status
        if [[ $status == *"Up"* ]]; then
            # Extract uptime
            UPTIME=$(echo "$status" | sed 's/Up //')
            printf "  ${GREEN}●${NC} %-12s ${GREEN}Running${NC} (%s)\n" "$SHORT_NAME" "$UPTIME"
        else
            printf "  ${RED}●${NC} %-12s ${RED}%s${NC}\n" "$SHORT_NAME" "$status"
        fi
    done
}

# Function: Display quick actions
display_actions() {
    echo ""
    echo -e "${CYAN}═══════════════════ QUICK ACTIONS ═══════════════════${NC}"
    echo ""
    echo -e "  ${BLUE}[L]${NC} View Logs        ${BLUE}[R]${NC} Restart Services"
    echo -e "  ${BLUE}[M]${NC} List Models      ${BLUE}[H]${NC} View Help"
    echo -e "  ${BLUE}[Q]${NC} Quit Dashboard"
    echo ""
}

# Function: Main loop
main_loop() {
    while true; do
        print_header
        
        # Get data
        HEALTH=$(get_health)
        METRICS=$(get_metrics)
        
        # Display sections
        display_health "$HEALTH"
        display_metrics "$METRICS"
        display_docker
        display_actions
        
        # Wait for next refresh
        sleep "$REFRESH_INTERVAL"
    done
}

# Function: Interactive mode
interactive_mode() {
    print_header
    
    HEALTH=$(get_health)
    METRICS=$(get_metrics)
    
    display_health "$HEALTH"
    display_metrics "$METRICS"
    display_docker
    display_actions
    
    # Read user input
    read -p "Choose action: " -n 1 -r
    echo ""
    
    case $REPLY in
        l|L)
            echo "Which service? (api/postgres/redis/rabbitmq): "
            read -r service
            docker-compose logs -f "ims-$service" 2>/dev/null || echo "Service not found"
            ;;
        r|R)
            echo "Restarting services..."
            docker-compose restart
            echo "Done! Press any key to continue..."
            read -n 1
            ;;
        m|M)
            curl -s "${IMS_API_URL}/api/v1/models/filter" | jq '.[].model_id'
            echo ""
            echo "Press any key to continue..."
            read -n 1
            ;;
        h|H)
            echo ""
            echo "IMS Status Dashboard Help"
            echo "========================="
            echo ""
            echo "Environment Variables:"
            echo "  IMS_API_URL       - API endpoint (default: http://localhost:8000)"
            echo "  ADMIN_API_KEY     - Admin key for metrics access"
            echo "  REFRESH_INTERVAL  - Refresh rate in seconds (default: 5)"
            echo ""
            echo "Usage:"
            echo "  $0              - Watch mode (auto-refresh)"
            echo "  $0 --once       - Single snapshot"
            echo "  $0 --interactive - Interactive menu"
            echo ""
            echo "Press any key to continue..."
            read -n 1
            ;;
        q|Q)
            echo "Exiting..."
            exit 0
            ;;
        *)
            ;;
    esac
    
    interactive_mode
}

# Parse arguments
case "${1:-}" in
    --once)
        print_header
        HEALTH=$(get_health)
        METRICS=$(get_metrics)
        display_health "$HEALTH"
        display_metrics "$METRICS"
        display_docker
        ;;
    --interactive)
        interactive_mode
        ;;
    --help)
        echo "IMS Status Dashboard"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --once          Show single snapshot and exit"
        echo "  --interactive   Interactive mode with menu"
        echo "  --help          Show this help"
        echo ""
        echo "Default: Watch mode (auto-refresh every ${REFRESH_INTERVAL}s)"
        ;;
    *)
        main_loop
        ;;
esac
