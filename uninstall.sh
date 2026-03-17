#!/bin/sh
# uninstall.sh — Remove Orthodox Study Bible
# Usage: curl -sSL https://raw.githubusercontent.com/IFAKA/orthodox-study-bible/main/uninstall.sh | sh

set -e

echo "Removing app data…"
if command -v osb >/dev/null 2>&1; then
    osb --uninstall || true
fi

echo "Uninstalling osb tool…"
if command -v uv >/dev/null 2>&1; then
    uv tool uninstall orthodox-study-bible || true
fi

echo "Done."
