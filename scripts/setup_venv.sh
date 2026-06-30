#!/usr/bin/env bash
# Set up the Python virtual environment for analysis scripts.
#
# Usage:
#   ./scripts/setup_venv.sh
#   ./scripts/setup_venv.sh /path/to/agent-control-theory
#
# After running, activate with: source scripts/.venv/bin/activate

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "Creating venv at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Installing requirements..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q

# Install agent-control-theory if path provided
ACT_LIB="${1:-}"
if [ -n "$ACT_LIB" ]; then
    echo "Installing agent-control-theory from $ACT_LIB..."
    "$VENV_DIR/bin/pip" install -e "$ACT_LIB[all]" -q
else
    echo "NOTE: agent-control-theory not installed."
    echo "  Run: $VENV_DIR/bin/pip install -e /path/to/agent-control-theory[all]"
    echo "  Or:  uv pip install -e /path/to/agent-control-theory[all]"
fi

echo ""
echo "Done. Activate with:"
echo "  source $VENV_DIR/bin/activate"
