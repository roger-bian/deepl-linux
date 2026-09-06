#!/usr/bin/env python3
"""Standalone trigger invoked by the COSMIC custom keyboard shortcut.

Deliberately dependency-free (stdlib only, no `gi`/GTK import) so it starts
and exits almost instantly when the hotkey fires. Duplicates the small
socket-path/protocol logic from deepl_popup/ipc.py instead of importing it,
since this script is run directly (not as part of the package) and must not
pay any GTK import cost.
"""
import os
import socket
import sys

SOCKET_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"),
    "deepl-popup.sock",
)


def main() -> int:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(SOCKET_PATH)
        s.sendall(b"SHOW\n")
    except OSError:
        return 1
    finally:
        s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
