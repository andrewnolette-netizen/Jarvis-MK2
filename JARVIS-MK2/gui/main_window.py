# --------------------------------------------------------------
# gui/main_window.py
# Simple PyQt6 HUD that subscribes to the PUB socket of the core service
# and displays status events in a cyan‑on‑black “Iron Man” style.
# --------------------------------------------------------------
import sys
import asyncio
import json
import threading
from typing import Any

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor

import zmq
import zmq.asyncio

# -----------------------------------------------------------------
# Bridge object – runs an asyncio loop in a background thread and
# forwards incoming ZMQ messages as Qt signals.
# -----------------------------------------------------------------
class Bridge(QObject):
    message_received = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.ctx = zmq.asyncio.Context()
        self.socket = self.ctx.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5556")  # PUB port from JarvisService
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

    async def listen(self):
        while True:
            try:
                raw = await self.socket.recv_string()
                msg = json.loads(raw)
                self.message_received.emit(msg)
            except Exception as e:
                print(f"[⚠] Bridge error: {e}")

# -----------------------------------------------------------------
# Main Window – semi‑transparent HUD
# -----------------------------------------------------------------
class JarvisWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS HUD")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(900, 600)

        # ---- Central widget ----
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title bar (just for demo)
        title = QLabel("JARVIS – Interactive Assistant")
        title.setFont(QFont("Consolas", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: rgb(0, 255, 255);")  # cyan
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Conversation / event log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 12))
        self.log.setStyleSheet(
            """
            background: rgba(0, 0, 0, 180);
            color: #0ff;
            border: 1px solid #0ff;
            border-radius: 6px;
            padding: 8px;
            """
        )
        layout.addWidget(self.log, stretch=1)

        # Bottom bar with a test button
        btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Command")
        self.test_btn.clicked.connect(self._send_test)
        btn_layout.addWidget(self.test_btn)
        layout.addLayout(btn_layout)

        # ---- ZMQ bridge (pub/sub) ----
        self.bridge = Bridge()
        self.bridge.message_received.connect(self._handle_message)

        # Run the asyncio listener in its own thread
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True).start()

        # Timer to keep the Qt event loop alive (required when mixing with asyncio)
        self._qt_timer = QTimer(self)
        self._qt_timer.setInterval(50)  # ms
        self._qt_timer.timeout.connect(lambda: None)  # no‑op, just keeps Qt ticking
        self._qt_timer.start()

        # Initial greeting
        self._log("System online. Awaiting command…", is_system=True)

    # -----------------------------------------------------------------
    # Asyncio loop runner (runs in its own thread)
    # -----------------------------------------------------------------
    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.create_task(self.bridge.listen())
        self._loop.run_forever()

    # -----------------------------------------------------------------
    # Helper to append text to the log
    # -----------------------------------------------------------------
    def _log(self, text: str, *, is_system: bool = False):
        prefix = "[SYS] " if is_system else "[USR] "
        formatted = f"{prefix}{text}"
        self.log.append(formatted)
        # Auto‑scroll to bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    # -----------------------------------------------------------------
    # Slot: inbound message from the core service (we PUB status updates)
    # -----------------------------------------------------------------
    def _handle_message(self, msg: dict):
        # Expected format from service: {"event": "...", "data": {...}, "timestamp": ...}
        if msg.get("event") == "task_started":
            data = msg.get("data", {})
            self._log(
                f"▶️  Started: {data.get('title')} (id: {data.get('task_id', '?')})",
                is_system=True,
            )
        elif msg.get("event") == "task_completed":
            data = msg.get("data", {})
            self._log(
                f"✅  Completed: {data.get('title')} (id: {data.get('task_id', '?')})",
                is_system=True,
            )
        elif msg.get("event") == "task_failed":
            data = msg.get("data", {})
            self._log(
                f"❌  Failed: {data.get('title')} (id: {data.get('task_id', '?')}) – {data.get('error')}",
                is_system=True,
            )
        else:
            # Fallback – pretty‑print the whole message
            self._log(json.dumps(msg, indent=2), is_system=True)

    # -----------------------------------------------------------------
    # Send a test request via REQ socket (mirrors what the voice agent does)
    # -----------------------------------------------------------------
    def _send_test(self):
        async def send():
            ctx = zmq.asyncio.Context()
            sock = ctx.socket(zmq.REQ)
            sock.connect("tcp://localhost:5555")
            request = {
                "jsonrpc": "2.0",
                "method": "plan_goal",
                "params": {"goal": "Show me the current system status"},
                "id": "gui-test",
            }
            await sock.send_string(json.dumps(request))
            reply = await sock.recv_string()
            self._log(f"Response: {reply}")
            await sock.close()
            ctx.term()

        asyncio.run_coroutine_threadsafe(send(), self._loop)

# -----------------------------------------------------------------
# Application entry point
# -----------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    win = JarvisWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()