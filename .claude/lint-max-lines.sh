#!/bin/bash

# Pre-commit hook: Enforce 200-line maximum on specified Python files

MAX_LINES=200
FAIL=0

# Patterns to check
patterns=(
  "src/osb/tui/screens/*.py"
  "src/osb/tui/widgets/*.py"
  "src/osb/importer/*.py"
  "src/osb/db/queries.py"
)

for pattern in "${patterns[@]}"; do
  while IFS= read -r file; do
    if [ -f "$file" ]; then
      lines=$(wc -l < "$file")
      if [ "$lines" -gt "$MAX_LINES" ]; then
        echo "❌ $file: $lines lines (max: $MAX_LINES)"
        FAIL=1
      fi
    fi
  done < <(find . -path "./.git" -prune -o -name "*.py" -print 2>/dev/null | xargs basename -a 2>/dev/null | while read f; do find . -path "./.git" -prune -o -name "$f" -type f -print; done | grep -E "$(echo "$pattern" | sed 's/\*/.*/g')" | sort -u)
done

# Simpler approach: use git ls-files if in a git repo, else use find
if git rev-parse --git-dir >/dev/null 2>&1; then
  for pattern in "${patterns[@]}"; do
    eval "git ls-files '$pattern' 2>/dev/null" | while read file; do
      if [ -f "$file" ] && [[ "$file" == *.py ]]; then
        lines=$(wc -l < "$file")
        if [ "$lines" -gt "$MAX_LINES" ]; then
          echo "❌ $file: $lines lines (max: $MAX_LINES)"
          FAIL=1
        fi
      fi
    done
  done
else
  for pattern in "${patterns[@]}"; do
    find . -path "./.git" -prune -o -type f -name "*.py" -print | while read file; do
      if [[ "$file" =~ $pattern ]]; then
        lines=$(wc -l < "$file")
        if [ "$lines" -gt "$MAX_LINES" ]; then
          echo "❌ $file: $lines lines (max: $MAX_LINES)"
          FAIL=1
        fi
      fi
    done
  done
fi

if [ $FAIL -eq 1 ]; then
  echo ""
  echo "Line count limit exceeded. Refactor oversized files to stay under $MAX_LINES lines."
  exit 1
fi

exit 0
