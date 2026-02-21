#!/bin/bash
set -euo pipefail

MAIN_USER="tim"
SANDBOX_USER="claude-sandbox"
MAIN_HOME="/home/$MAIN_USER"
SANDBOX_HOME="/home/$SANDBOX_USER"

echo "=== 1. Create sandboxed user ==="
if ! id "$SANDBOX_USER" &>/dev/null; then
  sudo useradd -m "$SANDBOX_USER" -s /bin/bash
  echo "Created $SANDBOX_USER user"
else
  echo "$SANDBOX_USER user already exists, skipping"
fi

echo ""
echo "=== 2. Grant $MAIN_USER access to sandbox home ==="
sudo setfacl -R -m u:$MAIN_USER:rwx "$SANDBOX_HOME"
sudo setfacl -R -d -m u:$MAIN_USER:rwx "$SANDBOX_HOME"
echo "$MAIN_USER has rwx on $SANDBOX_HOME"

echo ""
echo "=== 3. Grant access to github directory ==="
sudo setfacl -R -m u:$SANDBOX_USER:rwx "$MAIN_HOME/github"
sudo setfacl -R -d -m u:$SANDBOX_USER:rwx "$MAIN_HOME/github"
sudo setfacl -R -d -m u:$MAIN_USER:rwx "$MAIN_HOME/github"
echo "ACLs set on $MAIN_HOME/github (rwx, default rwx for both users)"

echo ""
echo "=== 4. Grant traverse access to $MAIN_HOME ==="
sudo setfacl -m u:$SANDBOX_USER:--x "$MAIN_HOME"
echo "Execute-only on $MAIN_HOME (traverse, no read)"

echo ""
echo "=== 5. Grant access to claude binary and Node.js ==="
# Traverse intermediate directories
sudo setfacl -m u:$SANDBOX_USER:--x "$MAIN_HOME/.local"
sudo setfacl -m u:$SANDBOX_USER:--x "$MAIN_HOME/.local/bin"
sudo setfacl -m u:$SANDBOX_USER:--x "$MAIN_HOME/.local/share"
echo "Traverse access to .local/, .local/bin/, .local/share/"
# Actual binary access
sudo setfacl -R -m u:$SANDBOX_USER:r-x "$MAIN_HOME/.local/share/claude"
sudo setfacl -m u:$SANDBOX_USER:r-x "$MAIN_HOME/.local/bin/claude"
echo "Read+execute on claude binary"
# Node.js
sudo setfacl -m u:$SANDBOX_USER:--x "$MAIN_HOME/.nvm"
sudo setfacl -R -m u:$SANDBOX_USER:r-x "$MAIN_HOME/.nvm/versions"
echo "Read+execute on Node.js via nvm"
# Symlink claude into sandbox user's own .local/bin so ~/.local/bin check passes
mkdir -p "$SANDBOX_HOME/.local/bin"
CLAUDE_VERSION=$(readlink -f "$MAIN_HOME/.local/bin/claude")
ln -sf "$CLAUDE_VERSION" "$SANDBOX_HOME/.local/bin/claude"
echo "Symlinked $SANDBOX_HOME/.local/bin/claude -> $CLAUDE_VERSION"
# Ensure sandbox user's PATH includes ~/.local/bin
if ! grep -q 'HOME/.local/bin' "$SANDBOX_HOME/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:/home/'"$MAIN_USER"'/.local/bin:/home/'"$MAIN_USER"'/.nvm/versions/node/v20.19.5/bin:$PATH"' >> "$SANDBOX_HOME/.bashrc"
  echo "Added PATH to $SANDBOX_HOME/.bashrc"
else
  echo "PATH already configured in $SANDBOX_HOME/.bashrc"
fi

echo ""
echo "=== 6. Share .claude config directory ==="
if [ -L "$SANDBOX_HOME/.claude" ]; then
  echo ".claude symlink already exists, skipping"
elif [ -d "$SANDBOX_HOME/.claude" ]; then
  rm -rf "$SANDBOX_HOME/.claude"
  ln -s "$MAIN_HOME/.claude" "$SANDBOX_HOME/.claude"
  echo "Replaced .claude dir with symlink -> $MAIN_HOME/.claude"
else
  ln -s "$MAIN_HOME/.claude" "$SANDBOX_HOME/.claude"
  echo "Created symlink $SANDBOX_HOME/.claude -> $MAIN_HOME/.claude"
fi
sudo setfacl -R -m u:$SANDBOX_USER:rwx "$MAIN_HOME/.claude"
sudo setfacl -R -d -m u:$SANDBOX_USER:rwx "$MAIN_HOME/.claude"
echo "ACLs set on $MAIN_HOME/.claude (rwx, default rwx)"

echo ""
echo "=== 7. Configure git safe directory ==="
sudo -u "$SANDBOX_USER" git config --global --add safe.directory "$MAIN_HOME/github/*"
echo "Added $MAIN_HOME/github/* as safe directory for $SANDBOX_USER"

echo ""
echo "=== 8. Network restrictions ==="
SANDBOX_UID=$(id -u "$SANDBOX_USER")
echo "Sandbox UID: $SANDBOX_UID"

# Flush any existing rules for this user first (idempotent re-runs)
EXISTING=$(sudo iptables -S OUTPUT 2>/dev/null | grep "owner --uid-owner $SANDBOX_UID" | wc -l)
if [ "$EXISTING" -gt 0 ]; then
  echo "Flushing $EXISTING existing iptables rules for UID $SANDBOX_UID"
  sudo iptables -S OUTPUT 2>/dev/null | grep "owner --uid-owner $SANDBOX_UID" | while read -r rule; do
    sudo iptables $(echo "$rule" | sed 's/^-A/-D/')
  done
else
  echo "No existing iptables rules to flush"
fi

sudo iptables -A OUTPUT -m owner --uid-owner "$SANDBOX_UID" -d api.anthropic.com -j ACCEPT
echo "ACCEPT: api.anthropic.com"
sudo iptables -A OUTPUT -m owner --uid-owner "$SANDBOX_UID" -d statsig.anthropic.com -j ACCEPT
echo "ACCEPT: statsig.anthropic.com"
sudo iptables -A OUTPUT -m owner --uid-owner "$SANDBOX_UID" -p udp --dport 53 -j ACCEPT
echo "ACCEPT: DNS (udp/53)"
sudo iptables -A OUTPUT -m owner --uid-owner "$SANDBOX_UID" -o lo -j ACCEPT
echo "ACCEPT: loopback"
sudo iptables -A OUTPUT -m owner --uid-owner "$SANDBOX_UID" -j DROP
echo "DROP: everything else"

echo ""
echo "=== 9. Protect .env files ==="
ENV_COUNT=$(find "$MAIN_HOME/github" -name ".env*" | wc -l)
find "$MAIN_HOME/github" -name ".env*" -exec sudo setfacl -m u:$SANDBOX_USER:--- {} \;
echo "Blocked access to $ENV_COUNT .env files"

echo ""
echo "==============================="
echo "Setup complete!"
echo "Run Claude in the sandbox with:"
echo "  claude-sandbox"
echo "==============================="
