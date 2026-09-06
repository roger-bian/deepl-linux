#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(command -v python3)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/deepl-popup.desktop"

echo "==> Installing system dependencies (apt)"
sudo apt-get update -qq
sudo apt-get install -y python3-gi gir1.2-gtk-3.0 python3-requests wl-clipboard

echo "==> Writing autostart entry: $AUTOSTART_FILE"
mkdir -p "$AUTOSTART_DIR"
sed \
  -e "s#{{REPO_DIR}}#${REPO_DIR}#g" \
  -e "s#{{PYTHON_BIN}}#${PYTHON_BIN}#g" \
  "$REPO_DIR/packaging/deepl-popup.desktop.tmpl" > "$AUTOSTART_FILE"

echo "==> Starting the daemon now (also autostarts on future logins)"
if ! (cd "$REPO_DIR" && "$PYTHON_BIN" -m deepl_popup.daemon --debug >/tmp/deepl-popup-daemon.log 2>&1 &); then
  echo "Warning: failed to start the daemon now; it will start on next login." >&2
fi

cat <<EOF

==> Install complete.

One manual step remains (Wayland does not allow apps to register global
hotkeys themselves, so this has to be done via the desktop's own settings):

  1. Open Settings -> Keyboard -> Shortcuts -> Custom Shortcuts -> Add
  2. Name:    DeepL Popup
  3. Command: ${PYTHON_BIN} ${REPO_DIR}/deepl_popup/trigger.py
  4. Key:     Ctrl+Alt+C  (or whatever you prefer)

After that, pressing the shortcut with something on your clipboard will pop
up the translator. If you haven't set a DeepL API key yet, the popup's first
screen will ask for one (get a free key at https://www.deepl.com/pro-api).

To set the key from the terminal instead:
  ${PYTHON_BIN} -m deepl_popup.daemon --set-key "YOUR_API_KEY"
EOF
