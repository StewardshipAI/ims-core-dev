#!/bin/bash
# Ultra-Simple Deploy Script
# Run this in WSL: bash quick-deploy.sh

echo "🚀 Quick Deploy to GitHub..."
echo ""

# Go to repo
cd /mnt/c/Users/natha/OneDrive/Documents/Claude-BuildsDocs/ims-core-dev || exit 1

# Create branch
git checkout -b feature/epic-2-complete-honesty-audit || git checkout feature/epic-2-complete-honesty-audit

# Create directory
mkdir -p docs/honesty-audit

# Copy files
AUDIT="/mnt/c/Users/natha/OneDrive/Documents/Claude-BuildsDocs/Honesty Audit/H.A.IMS-Core-Dev"
cp "$AUDIT"/*.md docs/honesty-audit/ 2>/dev/null

# Add and commit
git add docs/honesty-audit/
git commit -m "feat(epic-2): Complete Agent Control Flow + Honesty Audit (Score: +5)"

# Push
echo ""
echo "Ready to push. Run this command:"
echo "  git push -u origin feature/epic-2-complete-honesty-audit"
echo ""
