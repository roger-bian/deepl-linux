# DeepL Popup Translator

A lightweight Linux equivalent of the DeepL Windows/Mac desktop app's
quick-translate popup: copy some text, press a keyboard shortcut, and get a
small window with the original text (editable) and its translation side by
side, backed by the DeepL API.

Built for Pop!_OS / COSMIC on Wayland, using GTK3 (PyGObject) — no
Electron/Node, no X11-only tricks.

## How it works

Wayland doesn't let arbitrary apps grab a global hotkey themselves, so this
app runs as two pieces:

- **`deepl_popup.daemon`** — a background process (autostarted at login)
  that owns the popup window and listens on a local Unix socket
  (`$XDG_RUNTIME_DIR/deepl-popup.sock`).
- **`deepl_popup/trigger.py`** — a tiny, near-instant script bound to a
  custom keyboard shortcut in your desktop's own settings. It just pings the
  daemon's socket to say "show yourself."

This mirrors how the official app achieves an instant popup.

## Install

```bash
git clone <this repo> deepl-linux
cd deepl-linux
./install.sh
```

`install.sh` will:
1. Install apt dependencies: `python3-gi`, `gir1.2-gtk-3.0`, `python3-requests`, `wl-clipboard`.
2. Write an autostart entry to `~/.config/autostart/deepl-popup.desktop` so the daemon starts every login.
3. Start the daemon immediately.

**One manual step** (this can't be scripted — it's a Wayland/COSMIC
limitation, not a shortcut): open **Settings → Keyboard → Shortcuts → Custom
Shortcuts → Add**, and set:

- Name: `DeepL Popup`
- Command: `<path to python3> <repo path>/deepl_popup/trigger.py` (the exact
  command is printed at the end of `install.sh`)
- Key combination: `Ctrl+Alt+C` (or whatever you prefer)

## First run / API key

Get a free API key at <https://www.deepl.com/pro-api>. The first time you
open the popup without a configured key, it shows a one-field setup screen
to paste it in. You can also set it from the terminal:

```bash
python3 -m deepl_popup.daemon --set-key "YOUR_API_KEY"
```

The key is stored in `~/.config/deepl-popup/config.ini` (mode 600).

## Using it

1. Copy some text anywhere.
2. Press your shortcut (e.g. Ctrl+Alt+C).
3. The popup appears with the copied text on the left (auto-translated on
   the right). Edit the left side and click **Translate** (or Ctrl+Enter) to
   re-translate.
4. Use the swap button (⇄) to swap the two languages and text.
5. Click **Copy** to copy the translated text to your clipboard.
6. Press Escape or close the window to dismiss it — the daemon stays running
   so the next press of the shortcut is instant.

## Uninstall

```bash
./uninstall.sh          # stops the daemon, removes the autostart entry
./uninstall.sh --purge  # also deletes your saved API key and language cache
```

Also remove the custom keyboard shortcut from Settings → Keyboard →
Shortcuts if you no longer want it.

## Troubleshooting

- **Daemon not running**: `pgrep -af deepl_popup` — if nothing shows up, run
  `python3 -m deepl_popup.daemon --debug` manually to see errors, or check
  `/tmp/deepl-popup-daemon.log`.
- **Shortcut does nothing**: confirm the daemon is running (above), then
  test the socket directly:
  `python3 -c "from deepl_popup import ipc; print(ipc.send_show())"` — this
  should return `True` and make the window appear.
- **Popup appears but you can't type into it immediately**: this is a known
  Wayland focus-stealing quirk. If it happens consistently, see the
  fallback notes in `deepl_popup/window.py`'s `on_show_requested` (running
  the daemon with `GDK_BACKEND=x11` in the autostart entry is the documented
  workaround).
- **"Invalid API key" banner**: check `~/.config/deepl-popup/config.ini`.

## Manual testing (no GUI automation needed)

```bash
# 1. Confirm your API key works, independent of the app:
curl -H "Authorization: DeepL-Auth-Key YOUR_KEY" \
     --data-urlencode "text=hello" --data "target_lang=JA" \
     https://api-free.deepl.com/v2/translate

# 2. Run the daemon in the foreground with logging:
python3 -m deepl_popup.daemon --debug

# 3. In another terminal, trigger it manually:
python3 deepl_popup/trigger.py
```
