from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from markitdown_desktop.core.converter import ConflictPolicy
from markitdown_desktop.core.i18n import SYSTEM
from markitdown_desktop.core.ocr import DEFAULT_LLM_MODEL, OcrConfig, OcrMode
from markitdown_desktop.core.ocr.factory import check_azure_connection, check_llm_connection
from markitdown_desktop.core.secrets import AZURE_KEY, LLM_API_KEY, SecretStore, SecretStoreError
from markitdown_desktop.core.settings import AppSettings
from markitdown_desktop.ui.system import fit_height_to_wrapped_text


class OcrModeChooser(QWidget):
    """Three radio buttons with explanations; shared by the settings dialog and first run."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._buttons: dict[OcrMode, QRadioButton] = {}
        descriptions = [
            (
                OcrMode.LOCAL,
                self.tr("Local OCR (recommended)"),
                self.tr(
                    "Runs on this computer, works offline, no account needed. Reads Latin "
                    "script (e.g. German, English, French), Greek and Chinese; no Cyrillic, "
                    "Arabic or Hebrew."
                ),
            ),
            (
                OcrMode.AZURE,
                self.tr("Azure Document Intelligence"),
                self.tr(
                    "Microsoft's cloud OCR with the best layout recognition. "
                    "Requires an Azure resource, its endpoint and key; files are uploaded."
                ),
            ),
            (
                OcrMode.LLM,
                self.tr("LLM Vision (OpenAI-compatible)"),
                self.tr(
                    "Uses a vision model such as gpt-4o via the official markitdown-ocr plugin. "
                    "Requires an API key; files are uploaded."
                ),
            ),
        ]
        for mode, title, text in descriptions:
            button = QRadioButton(title)
            hint = QLabel(text)
            hint.setWordWrap(True)
            hint.setIndent(22)
            hint.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            layout.addWidget(button)
            layout.addWidget(hint)
            self._buttons[mode] = button
        self._buttons[OcrMode.LOCAL].setChecked(True)

    @property
    def mode(self) -> OcrMode:
        for mode, button in self._buttons.items():
            if button.isChecked():
                return mode
        return OcrMode.LOCAL

    @mode.setter
    def mode(self, mode: OcrMode) -> None:
        self._buttons[mode].setChecked(True)

    def button(self, mode: OcrMode) -> QRadioButton:
        return self._buttons[mode]


class SettingsDialog(QDialog):
    def __init__(
        self, settings: AppSettings, secrets: SecretStore, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._secrets = secrets
        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumWidth(520)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        ocr_group = QGroupBox(self.tr("Text recognition (OCR)"))
        ocr_layout = QVBoxLayout(ocr_group)
        self.mode_chooser = OcrModeChooser()
        ocr_layout.addWidget(self.mode_chooser)
        root.addWidget(ocr_group)

        self.azure_group = QGroupBox(self.tr("Azure Document Intelligence"))
        azure_form = QFormLayout(self.azure_group)
        self.azure_endpoint = QLineEdit()
        self.azure_endpoint.setPlaceholderText("https://<resource>.cognitiveservices.azure.com/")
        self.azure_key = QLineEdit()
        self.azure_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.azure_test = QPushButton(self.tr("Test connection"))
        azure_form.addRow(self.tr("Endpoint"), self.azure_endpoint)
        azure_form.addRow(self.tr("Key"), self.azure_key)
        azure_form.addRow("", self._right(self.azure_test))
        root.addWidget(self.azure_group)

        self.llm_group = QGroupBox(self.tr("LLM Vision"))
        llm_form = QFormLayout(self.llm_group)
        self.llm_api_key = QLineEdit()
        self.llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.llm_model = QLineEdit()
        self.llm_model.setPlaceholderText(DEFAULT_LLM_MODEL)
        self.llm_base_url = QLineEdit()
        self.llm_base_url.setPlaceholderText(self.tr("https://api.openai.com/v1 (default)"))
        self.llm_test = QPushButton(self.tr("Test connection"))
        llm_form.addRow(self.tr("API key"), self.llm_api_key)
        llm_form.addRow(self.tr("Model"), self.llm_model)
        llm_form.addRow(self.tr("Base URL"), self.llm_base_url)
        llm_form.addRow("", self._right(self.llm_test))
        root.addWidget(self.llm_group)

        output_group = QGroupBox(self.tr("Output"))
        output_form = QFormLayout(output_group)
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem(self.tr("Ask every time"), "ask")
        self.conflict_combo.addItem(self.tr("Overwrite"), str(ConflictPolicy.OVERWRITE))
        self.conflict_combo.addItem(self.tr("Keep both (add a number)"), str(ConflictPolicy.RENAME))
        self.conflict_combo.addItem(self.tr("Skip"), str(ConflictPolicy.SKIP))
        output_form.addRow(self.tr("If the Markdown file exists"), self.conflict_combo)
        self.language_combo = QComboBox()
        self.language_combo.addItem(self.tr("System language"), SYSTEM)
        self.language_combo.addItem("Deutsch", "de")
        self.language_combo.addItem("English", "en")
        output_form.addRow(self.tr("Language"), self.language_combo)
        restart_hint = QLabel(self.tr("Takes effect after restarting the app."))
        restart_hint.setEnabled(False)
        output_form.addRow("", restart_hint)
        root.addWidget(output_group)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        for mode in OcrMode:
            self.mode_chooser.button(mode).toggled.connect(self._update_enabled)
        self.azure_test.clicked.connect(self._test_azure)
        self.llm_test.clicked.connect(self._test_llm)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        fit_height_to_wrapped_text(self)

    @staticmethod
    def _right(widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(widget)
        return box

    def _load(self) -> None:
        self.mode_chooser.mode = OcrMode(self._settings.ocr_mode)
        self.azure_endpoint.setText(self._settings.azure_endpoint)
        self.llm_model.setText(self._settings.llm_model)
        self.llm_base_url.setText(self._settings.llm_base_url)
        try:
            self.azure_key.setText(self._secrets.get(AZURE_KEY) or "")
            self.llm_api_key.setText(self._secrets.get(LLM_API_KEY) or "")
        except SecretStoreError as exc:
            self._warn(self.tr("Stored keys could not be read"), str(exc))
        policy = self._settings.conflict_policy
        self.conflict_combo.setCurrentIndex(
            self.conflict_combo.findData("ask" if policy is None else str(policy))
        )
        self.language_combo.setCurrentIndex(
            max(0, self.language_combo.findData(self._settings.language))
        )
        self._update_enabled()

    def _update_enabled(self) -> None:
        mode = self.mode_chooser.mode
        self.azure_group.setEnabled(mode is OcrMode.AZURE)
        self.llm_group.setEnabled(mode is OcrMode.LLM)

    def current_config(self) -> OcrConfig:
        return OcrConfig(
            mode=self.mode_chooser.mode,
            azure_endpoint=self.azure_endpoint.text().strip(),
            azure_key=self.azure_key.text().strip(),
            llm_base_url=self.llm_base_url.text().strip(),
            llm_api_key=self.llm_api_key.text().strip(),
            llm_model=self.llm_model.text().strip() or DEFAULT_LLM_MODEL,
        )

    def _run_check(self, action: Callable[[], None]) -> None:
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            action()
        except Exception as exc:
            QGuiApplication.restoreOverrideCursor()
            self._warn(self.tr("Connection failed"), str(exc))
            return
        QGuiApplication.restoreOverrideCursor()
        QMessageBox.information(self, self.tr("Connection OK"), self.tr("The service answered."))

    def _test_azure(self) -> None:
        config = self.current_config()
        self._run_check(lambda: check_azure_connection(config.azure_endpoint, config.azure_key))

    def _test_llm(self) -> None:
        config = self.current_config()
        self._run_check(lambda: check_llm_connection(config))

    def _warn(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def accept(self) -> None:
        config = self.current_config()
        if not config.is_ready:
            self._warn(
                self.tr("Missing credentials"),
                self.tr("Please enter the credentials for the selected OCR mode."),
            )
            return
        try:
            self._store_secret(AZURE_KEY, config.azure_key)
            self._store_secret(LLM_API_KEY, config.llm_api_key)
        except SecretStoreError as exc:
            self._warn(self.tr("Keys could not be stored"), str(exc))
            return
        self._settings.ocr_mode = str(config.mode)
        self._settings.azure_endpoint = config.azure_endpoint
        self._settings.llm_base_url = config.llm_base_url
        self._settings.llm_model = config.llm_model
        data = self.conflict_combo.currentData()
        self._settings.conflict_policy = None if data == "ask" else ConflictPolicy(data)
        language = str(self.language_combo.currentData())
        language_changed = language != self._settings.language
        self._settings.language = language
        self._settings.sync()
        if language_changed:
            QMessageBox.information(
                self,
                self.tr("Restart required"),
                self.tr("The new language will be used the next time you start the app."),
            )
        super().accept()

    def _store_secret(self, name: str, value: str) -> None:
        if value:
            self._secrets.set(name, value)
        else:
            self._secrets.delete(name)
