#!/bin/sh
# install.sh — One-command installer for Orthodox Study Bible
# Usage: curl -sSL https://raw.githubusercontent.com/IFAKA/orthodox-study-bible/main/install.sh | sh

set -e

REPO="https://github.com/IFAKA/orthodox-study-bible"

# Check for uv; install if missing
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv (Python package manager)…"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this session
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

echo "Installing Orthodox Study Bible…"
uv tool install --force "git+${REPO}"

echo ""
echo "Done! Run:  osb"
echo "(On first launch the scripture database will be downloaded automatically.)"
