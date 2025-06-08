#!/bin/bash
cd "$(dirname "$0")/.."
source venv-guest-key/bin/activate 2>/dev/null || echo "⚠️ Aucun venv activé"
python3 src/main.py
