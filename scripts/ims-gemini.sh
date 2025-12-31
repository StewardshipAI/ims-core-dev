#!/bin/bash
# IMS + Gemini-CLI Integration Script
# Purpose: Query IMS for optimal model, then execute with gemini-cli
# Usage: ./ims-gemini.sh "your prompt here"

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
IMS_API_URL="${IMS_API_URL:-http://localhost:8000}"
ADMIN_API_KEY="${ADMIN_API_KEY}"
DEFAULT_STRATEGY="${IMS_STRATEGY:-cost}"
MIN_CONTEXT="${IMS_MIN_CONTEXT:-10000}"

# Function: Check if IMS is running
check_ims_health() {
    echo -e "${YELLOW}🔍 Checking IMS health...${NC}"
    
    if ! HEALTH=$(curl -s -f "${IMS_API_URL}/health" 2>/dev/null); then
        echo -e "${RED}❌ IMS API not responding at ${IMS_API_URL}${NC}"
        echo "   Start IMS with: docker-compose up -d"
        exit 1
    fi
    
    STATUS=$(echo "$HEALTH" | jq -r '.status')
    
    if [ "$STATUS" != "healthy" ]; then
        echo -e "${RED}❌ IMS is unhealthy: $STATUS${NC}"
        echo "   Check logs with: docker-compose logs api"
        exit 1
    fi
    
    echo -e "${GREEN}✅ IMS is healthy${NC}"
}

# Function: Query IMS for model recommendation
get_model_recommendation() {
    local prompt="$1"
    local prompt_length=${#prompt}
    
    # Estimate required context (rough heuristic: 1 char ≈ 0.3 tokens)
    local estimated_tokens=$((prompt_length * 3 / 10))
    local required_context=$((estimated_tokens + MIN_CONTEXT))
    
    echo -e "${YELLOW}🤖 Querying IMS for optimal model...${NC}"
    echo "   Prompt length: $prompt_length chars (~$estimated_tokens tokens)"
    echo "   Required context: $required_context tokens"
    
    local request_body=$(cat <<EOF
{
  "strategy": "$DEFAULT_STRATEGY",
  "min_context_window": $required_context,
  "min_capability_tier": "Tier_1"
}
EOF
)
    
    RECOMMENDATION=$(curl -s -X POST "${IMS_API_URL}/api/v1/recommend" \
        -H "Content-Type: application/json" \
        -H "X-Admin-Key: $ADMIN_API_KEY" \
        -d "$request_body")
    
    # Check if request failed
    if [ $? -ne 0 ] || [ -z "$RECOMMENDATION" ]; then
        echo -e "${RED}❌ Failed to get recommendation from IMS${NC}"
        exit 1
    fi
    
    # Extract model ID
    MODEL=$(echo "$RECOMMENDATION" | jq -r '.[0].model_id')
    
    if [ -z "$MODEL" ] || [ "$MODEL" == "null" ]; then
        echo -e "${RED}❌ No suitable model found for requirements${NC}"
        echo "   Try reducing context requirements or changing strategy"
        exit 1
    fi
    
    # Extract model details
    VENDOR=$(echo "$RECOMMENDATION" | jq -r '.[0].vendor_id')
    TIER=$(echo "$RECOMMENDATION" | jq -r '.[0].capability_tier')
    CONTEXT=$(echo "$RECOMMENDATION" | jq -r '.[0].context_window')
    COST_IN=$(echo "$RECOMMENDATION" | jq -r '.[0].cost_in_per_mil')
    COST_OUT=$(echo "$RECOMMENDATION" | jq -r '.[0].cost_out_per_mil')
    
    echo -e "${GREEN}✅ Selected: $MODEL${NC}"
    echo "   Vendor: $VENDOR"
    echo "   Tier: $TIER"
    echo "   Context: $CONTEXT tokens"
    echo "   Cost: \$${COST_IN}/\$${COST_OUT} per 1M tokens (in/out)"
}

# Function: Execute with gemini-cli
execute_with_gemini() {
    local prompt="$1"
    
    echo -e "${YELLOW}🚀 Executing with gemini-cli...${NC}"
    echo ""
    
    # Check if gemini-cli is installed
    if ! command -v gemini-cli &> /dev/null; then
        echo -e "${RED}❌ gemini-cli not found${NC}"
        echo "   Please install it or use the mock for testing."
        echo "   Mock: echo -e '#!/bin/bash\necho \"[MOCK] Calling Gemini with \$@\"' > gemini-cli && chmod +x gemini-cli"
        exit 1
    fi
    
    # Start timer
    START_TIME=$(date +%s%N)
    
    # Execute with selected model
    # Pass through all additional arguments
    gemini-cli --model="$MODEL" "$@"
    
    EXIT_CODE=$?
    
    # End timer
    END_TIME=$(date +%s%N)
    LATENCY=$(( (END_TIME - START_TIME) / 1000000 ))
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}✅ Execution completed successfully (${LATENCY}ms)${NC}"
    else
        echo -e "\n${RED}❌ Execution failed with exit code $EXIT_CODE${NC}"
    fi
    
    return $EXIT_CODE
}

# Function: Log usage to IMS
log_usage() {
    echo -e "${YELLOW}📊 Logging telemetry...${NC}"
    
    # Heuristic for token counts (if not provided by tool)
    local tokens_in=$(( ${#1} / 4 ))
    local tokens_out=0 # Unknown without parsing tool output
    
    local payload=$(cat <<EOF
{
  "model_id": "$MODEL",
  "vendor_id": "$VENDOR",
  "tokens_in": $tokens_in,
  "tokens_out": $tokens_out,
  "latency_ms": $LATENCY,
  "success": $([ $EXIT_CODE -eq 0 ] && echo "true" || echo "false")
}
EOF
)

    # In a real implementation, this would POST to /api/v1/telemetry/log
    # For now, we emit a "simulated" event to the console
    echo "   Model: $MODEL | Latency: ${LATENCY}ms | Tokens: ~$tokens_in"
    
    # TODO: await curl -s -X POST "${IMS_API_URL}/api/v1/telemetry/log" ...
}

# Main execution
main() {
    # Check for required environment variables
    if [ -z "$ADMIN_API_KEY" ]; then
        echo -e "${RED}❌ ADMIN_API_KEY not set${NC}"
        echo "   Export it or add to .env file"
        exit 1
    fi
    
    # Validate arguments
    if [ $# -eq 0 ]; then
        echo "Usage: $0 \"your prompt here\" [additional gemini-cli options]"
        echo ""
        echo "Environment variables:"
        echo "  IMS_API_URL       - IMS API endpoint (default: http://localhost:8000)"
        echo "  IMS_STRATEGY      - Selection strategy: cost|performance (default: cost)"
        echo "  IMS_MIN_CONTEXT   - Minimum context window (default: 10000)"
        echo "  ADMIN_API_KEY     - IMS admin API key (required)"
        echo ""
        echo "Examples:"
        echo "  $0 \"What is 2+2?\""
        echo "  IMS_STRATEGY=performance $0 \"Analyze this complex code...\""
        exit 1
    fi
    
    # Execute workflow
    check_ims_health
    get_model_recommendation "$1"
    execute_with_gemini "$@"
    log_usage
}

# Run main
main "$@"
