#!/bin/bash
# macOS Quickstart Setup — install individual items
# Usage: installer.sh install <item> [<item>...]

set -euo pipefail

install_xcode() {
    xcode-select --install 2>/dev/null || true
    for _ in $(seq 1 300); do
        xcode-select -p &>/dev/null && return 0
        # If the installer dialog is gone, user cancelled
        if ! pgrep -q "Install Command Line" 2>/dev/null; then
            sleep 2
            xcode-select -p &>/dev/null && return 0
            return 1
        fi
        sleep 1
    done
    return 1
}

install_brew() {
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
    eval "$(/opt/homebrew/bin/brew shellenv)"
}

install_opencode() {
    brew tap anomalyco/tap
    brew install opencode

    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    mkdir -p "$HOME/.config/opencode/"
    cp -r "$script_dir/opencode/." "$HOME/.config/opencode/"
}

install_playwright() { brew install playwright-cli; }

install_omlx() {
    brew tap jundot/omlx https://github.com/jundot/omlx
    brew install omlx
}

install_hf() { brew install hf; }

install_model() {
    mkdir -p "$HOME/models"
    hf download mlx-community/Qwen3.5-9B-MLX-4bit --local-dir "$HOME/models"
}

install_hermes() { brew install hermes-agent; }

install_ssh() {
    mkdir -p "$HOME/.ssh"
    if [[ ! -f "$HOME/.ssh/id_ed25519" ]]; then
        ssh-keygen -t ed25519 -C "github" -f "$HOME/.ssh/id_ed25519" -N ""
    fi
    local cfg="$HOME/.ssh/config"
    if [[ ! -f "$cfg" ]]; then
        cat > "$cfg" <<'CONF'
Host github.com
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
CONF
    elif ! grep -q "Host github.com" "$cfg" 2>/dev/null; then
        cat >> "$cfg" <<'CONF'

Host github.com
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
CONF
    fi
    ssh-add --apple-use-keychain ~/.ssh/id_ed25519 2>/dev/null || \
        ssh-add -K ~/.ssh/id_ed25519 2>/dev/null || true
}

case "${1:-}" in
    install)
        shift
        for item in "$@"; do
            "install_$item"
        done
        ;;
    *)
        echo "Usage: $0 install <item...>" >&2
        exit 1
        ;;
esac
