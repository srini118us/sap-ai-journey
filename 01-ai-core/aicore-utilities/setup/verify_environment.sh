#!/bin/bash
# Environment verification for SAP AI Core work
# Run this whenever returning to the environment to confirm everything still works.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

echo "==============================================="
echo "SAP AI Core Environment Verification"
echo "==============================================="

# Check 1: Python venv active
echo ""
echo "[1/5] Python environment"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "  OK: venv active at $VIRTUAL_ENV"
else
    echo "  WARN: no venv active. Consider: source venv/bin/activate"
fi

# Check 2: Required Python packages
echo ""
echo "[2/5] Python packages"
python3 -c "import requests; print(f'  OK: requests {requests.__version__}')" || {
    echo "  FAIL: requests not installed. Run: pip install requests"
    exit 1
}

# Check 3: AI Core service key
echo ""
echo "[3/5] AI Core service key"
if [ -f ~/.aicore/aicore-key.json ]; then
    PERMS=$(stat -c "%a" ~/.aicore/aicore-key.json)
    echo "  OK: ~/.aicore/aicore-key.json (permissions: $PERMS)"
    if [ "$PERMS" != "600" ]; then
        echo "  WARN: permissions should be 600. Fix: chmod 600 ~/.aicore/aicore-key.json"
    fi
else
    echo "  FAIL: ~/.aicore/aicore-key.json not found"
    echo "  Get from BTP Cockpit: ai-core service > Service Keys > View > Save"
    exit 1
fi

# Check 4: AWS CLI and credentials
echo ""
echo "[4/5] AWS CLI"
if command -v aws &> /dev/null; then
    echo "  OK: $(aws --version 2>&1 | head -1)"
    if [ -f ~/.aws/credentials ]; then
        PROFILES=$(grep -E '^\[' ~/.aws/credentials | tr -d '[]' | tr '\n' ' ')
        echo "  Profiles: $PROFILES"
    fi
else
    echo "  WARN: AWS CLI not installed (only needed for S3 operations)"
fi

# Check 5: AI Core smoke test
echo ""
echo "[5/5] AI Core API smoke test"
python3 "$ROOT/scripts/smoke_test.py" 2>&1 | tail -20

echo ""
echo "==============================================="
echo "Environment verification complete"
echo "==============================================="
