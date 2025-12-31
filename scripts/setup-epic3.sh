#!/bin/bash
set -e

echo "🚀 Setting up IMS Epic 3: Action Gateway..."

# 1. Install dependencies
echo "📦 Installing vendor SDKs..."
if [ -n "$VIRTUAL_ENV" ]; then
    pip install -r requirements.txt
else
    echo "⚠️  Not in virtual environment. Using pip directly (might fail on system Python)."
    # Attempt install or warn
    pip install google-generativeai openai anthropic || echo "❌ Failed to install packages. Check permissions or venv."
fi

# 2. Check API Keys
echo "🔑 Checking API Keys..."
if grep -q "GOOGLE_API_KEY" .env; then echo "✅ Google Key found"; else echo "❌ Google Key missing"; fi
if grep -q "OPENAI_API_KEY" .env; then echo "✅ OpenAI Key found"; else echo "❌ OpenAI Key missing"; fi
if grep -q "ANTHROPIC_API_KEY" .env; then echo "✅ Anthropic Key found"; else echo "❌ Anthropic Key missing"; fi

echo "✅ Setup complete. Restart API to load new dependencies."
echo "   docker-compose restart api"
