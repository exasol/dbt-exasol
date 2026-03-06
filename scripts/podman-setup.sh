#!/usr/bin/env bash
set -e

echo "Setting up Podman helper binaries..."

# Locate installed binaries
VF_BIN=$(find ~/.local/share/mise/installs -name "vfkit-unsigned" | head -n 1)
GV_BIN=$(find ~/.local/share/mise/installs -name "gvproxy-darwin" -o -name "gvproxy" -type f | grep -v "shims" | head -n 1)

SHIMS_DIR="$HOME/.local/share/mise/shims"
mkdir -p "$SHIMS_DIR"

if [ -n "$VF_BIN" ]; then
    ln -sf "$VF_BIN" "$SHIMS_DIR/vfkit"
    chmod +x "$VF_BIN"
    echo "Linked vfkit -> $VF_BIN"
else
    echo "Warning: vfkit-unsigned not found in mise installs"
fi

if [ -n "$GV_BIN" ]; then
    ln -sf "$GV_BIN" "$SHIMS_DIR/gvproxy"
    chmod +x "$GV_BIN"
    echo "Linked gvproxy -> $GV_BIN"
else
    echo "Warning: gvproxy not found in mise installs"
fi

# Configure containers.conf
mkdir -p ~/.config/containers
CONF_FILE=~/.config/containers/containers.conf

if [ ! -f "$CONF_FILE" ]; then
    echo "[engine]" > "$CONF_FILE"
    echo "helper_binaries_dir = [\"$SHIMS_DIR\"]" >> "$CONF_FILE"
    echo "Created $CONF_FILE"
elif ! grep -q "helper_binaries_dir" "$CONF_FILE"; then
    if grep -q "\[engine\]" "$CONF_FILE"; then
        sed -i.bak '/\[engine\]/a\
helper_binaries_dir = ["'"$SHIMS_DIR"'"]
' "$CONF_FILE"
        rm -f "$CONF_FILE.bak"
    else
        echo -e "\n[engine]\nhelper_binaries_dir = [\"$SHIMS_DIR\"]" >> "$CONF_FILE"
    fi
    echo "Updated $CONF_FILE"
else
    echo "$CONF_FILE already configured."
fi

echo "✅ Podman setup complete. Try running 'podman machine start' now."
