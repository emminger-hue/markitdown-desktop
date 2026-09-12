from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


def local_paths(mime: QMimeData) -> list[Path]:
    if not mime.hasUrls():
        return []
    return [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]


class DropZone(QFrame):
    files_dropped = Signal(list)
    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(140)
        self.setProperty("active", False)
        self.setStyleSheet(
            """
            QFrame#dropZone { border: 2px dashed palette(mid); border-radius: 12px; }
            QFrame#dropZone[active="true"] { border-color: palette(highlight);
                                              background: palette(alternate-base); }
            """
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title = QLabel(self.tr("Drop files here"))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self._title.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        self._title.setFont(font)
        self._hint = QLabel(self.tr("or click to choose files"))
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)
        layout.addWidget(self._hint)

    def _set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if local_paths(event.mimeData()):
            event.acceptProposedAction()
            self._set_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._set_active(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_active(False)
        paths = local_paths(event.mimeData())
        if paths:
            event.acceptProposedAction()
            self.files_dropped.emit(paths)
        else:
            event.ignore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
