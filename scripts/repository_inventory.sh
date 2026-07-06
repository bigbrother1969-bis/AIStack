#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

REPORT="$ROOT/reports/generated/repository-inventory.md"

echo "# Repository Inventory" > "$REPORT"
echo "" >> "$REPORT"

echo "Generated: $(date)" >> "$REPORT"

echo "" >> "$REPORT"

echo "---" >> "$REPORT"

echo "" >> "$REPORT"

echo "## Directory Tree" >> "$REPORT"

echo '```text' >> "$REPORT"

tree -a \
-I '.git|__pycache__|*.pyc|node_modules|.venv|venv' \
"$ROOT" >> "$REPORT"

echo '```' >> "$REPORT"

echo "" >> "$REPORT"

echo "---" >> "$REPORT"

echo "" >> "$REPORT"

echo "## Markdown files" >> "$REPORT"

find "$ROOT" \
-name "*.md" \
| sort >> "$REPORT"

echo "" >> "$REPORT"

echo "---" >> "$REPORT"

echo "" >> "$REPORT"

echo "## Python files" >> "$REPORT"

find "$ROOT" \
-name "*.py" \
| sort >> "$REPORT"

echo "" >> "$REPORT"

echo "---" >> "$REPORT"

echo "" >> "$REPORT"

echo "## Shell scripts" >> "$REPORT"

find "$ROOT" \
-name "*.sh" \
| sort >> "$REPORT"

echo ""

echo "Repository inventory generated."

echo "$REPORT"
