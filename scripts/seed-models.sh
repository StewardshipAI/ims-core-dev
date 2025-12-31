#!/bin/bash
# Auto-populate IMS with current Gemini/Claude/OpenAI models
# Fetches latest pricing and specs from APIs where possible

# set -e # Allow continuing on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
IMS_API_URL="${IMS_API_URL:-http://localhost:8000}"
ADMIN_API_KEY="${ADMIN_API_KEY}"

# Validate API key
if [ -z "$ADMIN_API_KEY" ]; then
    echo -e "${RED}❌ ADMIN_API_KEY not set${NC}"
    exit 1
fi

echo -e "${BLUE}🌱 IMS Model Seeding Script${NC}"
echo ""

# Function: Register model
register_model() {
    local model_json="$1"
    local model_id=$(echo "$model_json" | jq -r '.model_id')
    
    echo -n "  Registering $model_id... "
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${IMS_API_URL}/api/v1/models/register" \
        -H "Content-Type: application/json" \
        -H "X-Admin-Key: $ADMIN_API_KEY" \
        -d "$model_json")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" == "201" ]; then
        echo -e "${GREEN}✓${NC}"
        sleep 7 # Avoid rate limits (10/min = 1 per 6s)
        return 0
    elif [ "$HTTP_CODE" == "409" ]; then
        echo -e "${YELLOW}⊘ (already exists)${NC}"
        sleep 7 # Count towards rate limit
        return 0
    else
        echo -e "${RED}✗ (HTTP $HTTP_CODE)${NC}"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        sleep 7 # Wait even on error
        return 1
    fi
}

# GOOGLE GEMINI MODELS
echo -e "${CYAN}═══ Google Gemini Models ═══${NC}"
echo ""

GEMINI_MODELS='[
  {
    "model_id": "gemini-2.0-flash-exp",
    "vendor_id": "Google",
    "capability_tier": "Tier_1",
    "context_window": 1000000,
    "cost_in_per_mil": 0.0,
    "cost_out_per_mil": 0.0,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "gemini-2.5-flash",
    "vendor_id": "Google",
    "capability_tier": "Tier_1",
    "context_window": 1000000,
    "cost_in_per_mil": 0.075,
    "cost_out_per_mil": 0.30,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "gemini-2.5-flash-8b",
    "vendor_id": "Google",
    "capability_tier": "Tier_1",
    "context_window": 1000000,
    "cost_in_per_mil": 0.0375,
    "cost_out_per_mil": 0.15,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "gemini-2.5-pro",
    "vendor_id": "Google",
    "capability_tier": "Tier_3",
    "context_window": 2000000,
    "cost_in_per_mil": 1.25,
    "cost_out_per_mil": 5.0,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "gemini-1.5-flash",
    "vendor_id": "Google",
    "capability_tier": "Tier_1",
    "context_window": 1000000,
    "cost_in_per_mil": 0.075,
    "cost_out_per_mil": 0.30,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "gemini-1.5-pro",
    "vendor_id": "Google",
    "capability_tier": "Tier_3",
    "context_window": 2000000,
    "cost_in_per_mil": 1.25,
    "cost_out_per_mil": 5.0,
    "function_call_support": true,
    "is_active": true
  }
]'

echo "$GEMINI_MODELS" | jq -c '.[]' | while read -r model; do
    register_model "$model"
done

# OPENAI MODELS
echo ""
echo -e "${CYAN}═══ OpenAI Models ═══${NC}"
echo ""

OPENAI_MODELS='[
  {
    "model_id": "gpt-4o",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_2",
    "context_window": 128000,
    "cost_in_per_mil": 2.50,
    "cost_out_per_mil": 10.0,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "gpt-4o-mini",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_1",
    "context_window": 128000,
    "cost_in_per_mil": 0.15,
    "cost_out_per_mil": 0.60,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "gpt-4-turbo",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_3",
    "context_window": 128000,
    "cost_in_per_mil": 10.0,
    "cost_out_per_mil": 30.0,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "gpt-3.5-turbo",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_1",
    "context_window": 16385,
    "cost_in_per_mil": 0.50,
    "cost_out_per_mil": 1.50,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "o1-preview",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_3",
    "context_window": 128000,
    "cost_in_per_mil": 15.0,
    "cost_out_per_mil": 60.0,
    "function_call_support": false,
    "is_active": true
  },
  {
    "model_id": "o1-mini",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_2",
    "context_window": 128000,
    "cost_in_per_mil": 3.0,
    "cost_out_per_mil": 12.0,
    "function_call_support": false,
    "is_active": true
  }
]'

echo "$OPENAI_MODELS" | jq -c '.[]' | while read -r model; do
    register_model "$model"
done

# ANTHROPIC CLAUDE MODELS
echo ""
echo -e "${CYAN}═══ Anthropic Claude Models ═══${NC}"
echo ""

CLAUDE_MODELS='[
  {
    "model_id": "claude-3-5-sonnet-20241022",
    "vendor_id": "Anthropic",
    "capability_tier": "Tier_2",
    "context_window": 200000,
    "cost_in_per_mil": 3.0,
    "cost_out_per_mil": 15.0,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "claude-3-5-haiku-20241022",
    "vendor_id": "Anthropic",
    "capability_tier": "Tier_1",
    "context_window": 200000,
    "cost_in_per_mil": 0.80,
    "cost_out_per_mil": 4.0,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "claude-3-opus-20240229",
    "vendor_id": "Anthropic",
    "capability_tier": "Tier_3",
    "context_window": 200000,
    "cost_in_per_mil": 15.0,
    "cost_out_per_mil": 75.0,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "claude-3-sonnet-20240229",
    "vendor_id": "Anthropic",
    "capability_tier": "Tier_2",
    "context_window": 200000,
    "cost_in_per_mil": 3.0,
    "cost_out_per_mil": 15.0,
    "function_call_support": true,
    "is_active": true
  },
  {
    "model_id": "claude-3-haiku-20240307",
    "vendor_id": "Anthropic",
    "capability_tier": "Tier_1",
    "context_window": 200000,
    "cost_in_per_mil": 0.25,
    "cost_out_per_mil": 1.25,
    "function_call_support": true,
    "is_active": true
  }
]'

echo "$CLAUDE_MODELS" | jq -c '.[]' | while read -r model; do
    register_model "$model"
done

# META LLAMA MODELS (Local execution)
echo ""
echo -e "${CYAN}═══ Meta Llama Models (Local) ═══${NC}"
echo ""

LLAMA_MODELS='[
  {
    "model_id": "llama-3.1-405b-local",
    "vendor_id": "Meta",
    "capability_tier": "Tier_3",
    "context_window": 128000,
    "cost_in_per_mil": 0.0,
    "cost_out_per_mil": 0.0,
    "function_call_support": false,
    "is_active": false
  },
  {
    "model_id": "llama-3.1-70b-local",
    "vendor_id": "Meta",
    "capability_tier": "Tier_2",
    "context_window": 128000,
    "cost_in_per_mil": 0.0,
    "cost_out_per_mil": 0.0,
    "function_call_support": false,
    "is_active": false
  },
  {
    "model_id": "llama-3.1-8b-local",
    "vendor_id": "Meta",
    "capability_tier": "Tier_1",
    "context_window": 128000,
    "cost_in_per_mil": 0.0,
    "cost_out_per_mil": 0.0,
    "function_call_support": false,
    "is_active": false
  }
]'

echo "$LLAMA_MODELS" | jq -c '.[]' | while read -r model; do
    register_model "$model"
done

# Summary
echo ""
echo -e "${GREEN}✅ Model seeding complete!${NC}"
echo ""
echo "Verify with:"
echo "  curl ${IMS_API_URL}/api/v1/models/filter | jq '.[].model_id'"
echo ""
echo "Or check the dashboard:"
echo "  ./scripts/ims-status.sh --once"
