from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from markitdown_desktop import APP_NAME
from markitdown_desktop.core.ocr import OcrMode
from markitdown_desktop.core.secrets import SecretStore
from markitdown_desktop.core.settings import AppSettings
from markitdown_desktop.ui.settings_dialog import OcrModeChooser, SettingsDialog


class FirstRunDialog(QDialog):
    """Shown once after installation: pick how scans and images are read."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle(self.tr("Welcome to {app}").format(app=APP_NAME))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        intro = QLabel(
            self.tr(
                "Drop a file onto the window and a Markdown file with the same name is written "
                "next to it. For scanned PDFs and images the text has to be recognised first — "
                "choose how. You can change this any time in Settings."
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.mode_chooser = OcrModeChooser()
        layout.addWidget(self.mode_chooser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(self.tr("Continue"))
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self._settings.ocr_mode = str(self.mode_chooser.mode)
        self._settings.first_run_done = True
        self._settings.sync()
        super().accept()


def run_first_run(settings: AppSettings, secrets: SecretStore, parent: QWidget) -> None:
    if settings.first_run_done:
        return
    dialog = FirstRunDialog(settings, parent)
    dialog.exec()
    if OcrMode(settings.ocr_mode) is not OcrMode.LOCAL:
        SettingsDialog(settings, secrets, parent).exec()
