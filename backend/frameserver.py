"""The cluster's own framebuffer over HTTP, for testing what watches it.

``GET /frame.png`` answers with the cluster window as it is drawn right now.
A camera-based checker can be run end to end against it with no camera, and
with no doubt about what was on the glass: the picture is the framebuffer.

The grab has to happen on the Qt thread; the HTTP thread asks for one and
waits for it.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, Signal, Slot


class FrameServer(QObject):
    """Serves ``grab()`` of a QQuickWindow as PNG on ``port`` (0 picks one)."""

    _wanted = Signal()

    def __init__(self, window_lookup, port: int = 0, host: str = "127.0.0.1",
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lookup = window_lookup
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._png = b""
        self._wanted.connect(self._grab)
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                pass

            def do_GET(self):
                if self.path.split("?")[0] != "/frame.png":
                    self.send_error(404)
                    return
                png = server.frame()
                if not png:
                    self.send_error(503, "the cluster window is not up yet")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(png)

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.port = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()
        print(f"frames: http://127.0.0.1:{self.port}/frame.png", flush=True)

    def stop(self) -> None:
        self.httpd.shutdown()

    def frame(self, timeout: float = 5.0) -> bytes:
        """PNG of the window as drawn now. Called from any thread but the Qt one."""
        with self._lock:
            self._done.clear()
            self._wanted.emit()
            if not self._done.wait(timeout):
                return b""
            return self._png

    @Slot()
    def _grab(self) -> None:
        png = b""
        try:
            window = self._lookup()
            if window is not None:
                image = window.grabWindow()
                data = QByteArray()
                buf = QBuffer(data)
                buf.open(QIODevice.WriteOnly)
                image.save(buf, "PNG")
                png = bytes(data)
        finally:
            self._png = png
            self._done.set()
