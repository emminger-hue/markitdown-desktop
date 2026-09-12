from __future__ import annotations

import platform
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from markitdown_desktop import (
    APP_NAME,
    AUTHOR,
    COPYRIGHT_YEAR,
    RELEASES_URL,
    REPO_URL,
    __version__,
)
from markitdown_desktop.core.i18n import resolve_language, system_ui_languages
from markitdown_desktop.core.settings import AppSettings
from markitdown_desktop.ui.system import fit_height_to_wrapped_text

RESOURCES = Path(__file__).resolve().parent.parent / "resources"
LICENSES_FILE = RESOURCES / "THIRD_PARTY_LICENSES.txt"


class AboutDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle(self.tr("About {app}").format(app=APP_NAME))
        self.setMinimumWidth(560)
        root = QVBoxLayout(self)
        root.setSpacing(12)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QPixmap(str(RESOURCES / "icon-128.png")).scaled(72, 72))
        header.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        title = QLabel(APP_NAME)
        font = title.font()
        font.setPointSize(font.pointSize() + 6)
        font.setBold(True)
        title.setFont(font)
        self.version_label = QLabel(
            self.tr("Version {version} · © {year} {author} · MIT license").format(
                version=__version__, year=COPYRIGHT_YEAR, author=AUTHOR
            )
        )
        titles.addWidget(title)
        titles.addWidget(self.version_label)
        titles.addStretch(1)
        header.addLayout(titles, 1)
        root.addLayout(header)

        self.body = QLabel(self.body_html())
        self.body.setWordWrap(True)
        self.body.setOpenExternalLinks(True)
        self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        root.addWidget(self.body)

        self.details_toggle = QToolButton()
        self.details_toggle.setText(self.tr("Details"))
        self.details_toggle.setCheckable(True)
        self.details_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.details_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.details_toggle.setAutoRaise(True)
        self.details_toggle.toggled.connect(self._toggle_details)
        root.addWidget(self.details_toggle)
        self.details = QLabel(self.details_text())
        self.details.setFont(QFont("Menlo, Consolas, monospace"))
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.setWordWrap(True)
        self.details.setVisible(False)
        root.addWidget(self.details)

        buttons = QDialogButtonBox()
        self.update_button = QPushButton(self.tr("Check for updates"))
        self.licenses_button = QPushButton(self.tr("Third-party licenses"))
        buttons.addButton(self.update_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(self.licenses_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self.update_button.clicked.connect(self.check_for_updates)
        self.licenses_button.clicked.connect(self.show_licenses)
        root.addWidget(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        fit_height_to_wrapped_text(self)

    def body_html(self) -> str:
        paragraphs = [
            self.tr(
                "Converts documents to Markdown: drop a file onto the window or choose it, "
                "and a Markdown file with the same name is written next to it. The target "
                "folder can be changed in Settings."
            ),
            "<b>"
            + self.tr("Supported formats:")
            + "</b> "
            + self.tr(
                "PDF, Word (DOCX), PowerPoint (PPTX), Excel (XLSX/XLS), images (PNG, JPG, "
                "TIFF, BMP, WebP, GIF), HTML, CSV, JSON, XML, EPUB, ZIP, Outlook messages "
                "(MSG), Jupyter notebooks."
            ),
            "<b>"
            + self.tr("Text recognition (OCR)")
            + "</b> "
            + self.tr(
                "for scanned PDFs and images: <i>Local</i> (default) runs entirely on this "
                "computer without an internet connection – no file leaves the machine. It "
                "reads Latin script (e.g. German, English, French), Greek and Chinese; not "
                "Cyrillic, Arabic or Hebrew. <i>Azure Document Intelligence</i> and "
                "<i>LLM Vision</i> send the documents to the respective service; credentials "
                "are kept in the system keychain."
            ),
            "<b>"
            + self.tr("Note:")
            + "</b> "
            + self.tr("Check the result for complex layouts, scanned tables and handwriting."),
            "<b>"
            + self.tr("Privacy:")
            + "</b> "
            + self.tr(
                "The app collects no data and does not connect to the internet in local "
                "mode. In the cloud modes, document contents are transmitted to Microsoft "
                "Azure or the chosen LLM provider under their privacy terms. “Check for "
                "updates” only opens the releases page in your browser."
            ),
            "<b>"
            + self.tr("Built on:")
            + "</b> "
            + self.tr(
                "MarkItDown (Microsoft, MIT), RapidOCR (Apache 2.0), ONNX Runtime (MIT), "
                "Qt / PySide6 (LGPL v3, dynamically linked), PDFium (Apache 2.0 / BSD), "
                "PyMuPDF (AGPL v3). This is an independent project and is not affiliated "
                "with or endorsed by Microsoft."
            ),
            self.tr(
                "Provided without warranty of any kind under the MIT license. Source code, "
                "new versions and bug reports: {link}"
            ).format(link=f'<a href="{REPO_URL}">{REPO_URL.removeprefix("https://")}</a>'),
        ]
        return "".join(f"<p>{text}</p>" for text in paragraphs)

    def details_text(self) -> str:
        try:
            import PySide6

            pyside = PySide6.__version__
        except Exception:
            pyside = "?"
        lines = [
            f"{APP_NAME} {__version__}",
            f"Python {platform.python_version()} · Qt {QLibraryInfo.version().toString()}"
            f" · PySide6 {pyside}",
            f"{platform.system()} {platform.release()} ({platform.machine()})",
            self.tr("Settings file: {path}").format(path=QSettings().fileName()),
            self.tr("OCR mode: {mode}").format(mode=self._settings.ocr_mode),
            self.tr("UI language: {language} (system: {system})").format(
                language=resolve_language(self._settings.language),
                system=", ".join(system_ui_languages()[:3]) or "-",
            ),
        ]
        return "\n".join(lines)

    def _toggle_details(self, checked: bool) -> None:
        self.details_toggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        self.details.setVisible(checked)
        layout = self.layout()
        if layout is not None:
            layout.activate()
            self.resize(self.width(), layout.totalHeightForWidth(self.width()))

    def check_for_updates(self) -> None:
        QDesktopServices.openUrl(QUrl(RELEASES_URL))

    def show_licenses(self) -> None:
        LicensesDialog(self).exec()


class LicensesDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Third-party licenses"))
        self.resize(720, 560)
        root = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Search (Enter for next match)"))
        self.search.returnPressed.connect(self.find_next)
        root.addWidget(self.search)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Menlo, Consolas, monospace"))
        self.text.setPlainText(load_licenses_text())
        root.addWidget(self.text, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def find_next(self) -> bool:
        needle = self.search.text()
        if not needle:
            return False
        if self.text.find(needle):
            return True
        self.text.moveCursor(self.text.textCursor().MoveOperation.Start)
        return self.text.find(needle)


def load_licenses_text() -> str:
    try:
        return LICENSES_FILE.read_text(encoding="utf-8")
    except OSError:
        return f"{LICENSES_FILE.name} is missing from this build."


def open_about(settings: AppSettings, parent: QWidget | None) -> None:
    AboutDialog(settings, parent).exec()
