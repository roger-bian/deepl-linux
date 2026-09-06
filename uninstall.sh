#!/usr/bin/env bash
set -euo pipefail

AUTOSTART_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/deepl-popup.desktop"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/deepl-popup"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/deepl-popup"

echo "==> Removing autostart entry"
rm -f "$AUTOSTART_FILE"

echo "==> Stopping any running daemon"
pkill -f "deepl_popup.daemon" 2>/dev/null || true

if [[ "${1:-}" == "--purge" ]]; then
  echo "==> Purging config and cache (API key will be deleted)"
  rm -rf "$CONFIG_DIR" "$CACHE_DIR"
else
  echo "==> Leaving $CONFIG_DIR and $CACHE_DIR in place (pass --purge to remove them too)"
fi

echo "==> Uninstall complete. Remember to also remove the Ctrl+Alt+C custom shortcut"
echo "    from Settings -> Keyboard -> Shortcuts if you no longer want it."
