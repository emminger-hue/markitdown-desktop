from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget


def fit_height_to_wrapped_text(widget: QWidget) -> None:
    """Qt sizes dialogs from minimumSizeHint, which ignores word-wrapped labels; grow to fit."""
    layout = widget.layout()
    if layout is None or not layout.hasHeightForWidth():
        return
    width = max(widget.width(), widget.minimumWidth())
    widget.resize(width, max(widget.height(), layout.totalHeightForWidth(width)))


def open_path(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def reveal_in_file_manager(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    elif sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", str(path)])
    else:
        open_path(path.parent)
