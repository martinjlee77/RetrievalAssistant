#!/bin/bash
# Try different pip installation methods
if command -v pip3 >/dev/null 2>&1; then
    pip3 install --break-system-packages -r website-requirements.txt
elif command -v pip >/dev/null 2>&1; then
    pip install --break-system-packages -r website-requirements.txt
else
    # Fallback: try to bootstrap pip first
    python -c "import subprocess; subprocess.run(['python', '-m', 'ensurepip', '--user'])" || true
    python -m pip install --user --break-system-packages -r website-requirements.txt
fi