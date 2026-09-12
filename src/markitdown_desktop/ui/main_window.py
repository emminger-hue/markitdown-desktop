from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMainWindow

from markitdown_desktop import APP_NAME


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(480, 360)
        self.setCentralWidget(QLabel("MarkItDown Desktop – scaffold"))
