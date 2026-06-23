#!/bin/bash
# macOS Quickstart Setup — check installed status
# Usage: check_installed.sh  →  JSON of installed/missing

set -euo pipefail

check_xcode()     { xcode-select -p &>/dev/null; }
check_brew()      { command -v brew &>/dev/null; }
check_opencode()  { brew list --formula 2>/dev/null | grep -qxF opencode; }
check_playwright(){ brew list --formula 2>/dev/null | grep -qxF playwright-cli; }
check_omlx()      { brew list --formula 2>/dev/null | grep -qxF omlx; }
check_hf()        { brew list --formula 2>/dev/null | grep -qxF hf; }
check_model()     { [[ -d "$HOME/models/mlx-community/Qwen3.5-9B-MLX-4bit" ]]; }
check_hermes()    { brew list --formula 2>/dev/null | grep -qxF hermes-agent; }
check_ssh()       { [[ -f "$HOME/.ssh/id_ed25519" ]]; }

ALL_ITEMS=( xcode brew opencode playwright omlx hf model hermes ssh )

echo '{'
_first=true
for item in "${ALL_ITEMS[@]}"; do
    $_first || echo ','
    _first=false
    if "check_$item"; then
        printf '  "%s": true' "$item"
    else
        printf '  "%s": false' "$item"
    fi
done
echo ''
echo '}'
