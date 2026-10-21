#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m PyInstaller --clean --noconfirm packaging/czn_auto_macos.spec
echo "Built: $ROOT/dist/CZN_Zero_Farm.app"
