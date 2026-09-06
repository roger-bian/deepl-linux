import argparse
import logging
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from deepl_popup import config, ipc
from deepl_popup.window import PopupWindow

log = logging.getLogger("deepl_popup.daemon")


class Daemon:
    def __init__(self):
        self.window = PopupWindow()
        self._py_sock = None

    def start(self):
        try:
            self._py_sock = ipc.bind_server_socket()
        except ipc.DaemonAlreadyRunning:
            log.info("daemon already running, forwarding SHOW and exiting")
            ipc.send_show()
            sys.exit(0)

        GLib.io_add_watch(self._py_sock.fileno(), GLib.IO_IN, self._on_socket_readable)
        log.info("listening on %s", ipc.SOCKET_PATH)

        Gtk.main()

    def _on_socket_readable(self, fd, condition):
        conn, _ = self._py_sock.accept()
        try:
            data = conn.recv(64)
        finally:
            conn.close()
        if data.strip() == b"SHOW":
            log.debug("received SHOW")
            self.window.on_show_requested()
        return True


def main():
    parser = argparse.ArgumentParser(description="DeepL popup translator daemon")
    parser.add_argument("--debug", action="store_true", help="log to stdout")
    parser.add_argument("--set-key", metavar="API_KEY", help="save the DeepL API key and exit")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.set_key:
        config.set_api_key(args.set_key)
        print(f"API key saved to {config.CONFIG_PATH}")
        return

    daemon = Daemon()
    daemon.start()


if __name__ == "__main__":
    main()
