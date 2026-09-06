import errno
import os
import socket

SOCKET_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"),
    "deepl-popup.sock",
)

SHOW_MESSAGE = b"SHOW\n"


class DaemonAlreadyRunning(Exception):
    pass


def bind_server_socket() -> socket.socket:
    """Bind the single-instance server socket, clearing a stale socket file if needed.

    Raises DaemonAlreadyRunning if a live daemon already owns the socket.
    """
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.bind(SOCKET_PATH)
    except OSError as e:
        if e.errno != errno.EADDRINUSE:
            raise
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.connect(SOCKET_PATH)
            probe.close()
            s.close()
            raise DaemonAlreadyRunning(SOCKET_PATH)
        except (ConnectionRefusedError, FileNotFoundError):
            probe.close()
            os.unlink(SOCKET_PATH)
            s.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o600)
    s.listen(5)
    return s


def send_show() -> bool:
    """Connect to a running daemon and ask it to show its window.

    Returns True on success, False if no daemon is listening.
    """
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(SOCKET_PATH)
        s.sendall(SHOW_MESSAGE)
        return True
    except OSError:
        return False
    finally:
        s.close()
