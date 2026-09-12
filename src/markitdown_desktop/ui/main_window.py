from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from markitdown_desktop import APP_NAME
from markitdown_desktop.core.converter import (
    SUPPORTED_EXTENSIONS,
    ConflictPolicy,
    ConversionResult,
    ConversionService,
    Status,
    expand_paths,
    is_supported,
    output_path_for,
)
from markitdown_desktop.core.ocr import OcrConfig
from markitdown_desktop.core.ocr.factory import build_markitdown
from markitdown_desktop.core.secrets import MemorySecretStore, SecretStore
from markitdown_desktop.core.settings import AppSettings, TargetMode
from markitdown_desktop.core.worker import ConversionWorker, Job
from markitdown_desktop.ui.drop_zone import DropZone, local_paths
from markitdown_desktop.ui.settings_dialog import SettingsDialog
from markitdown_desktop.ui.system import open_path, reveal_in_file_manager

COL_FILE, COL_STATUS, COL_RESULT = 0, 1, 2


class MainWindow(QMainWindow):
    batch_finished = Signal()

    def __init__(
        self,
        settings: AppSettings | None = None,
        secrets: SecretStore | None = None,
        service: ConversionService | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings if settings is not None else AppSettings()
        self._secrets: SecretStore = secrets if secrets is not None else MemorySecretStore()
        self._service = (
            service if service is not None else ConversionService(factory=self._make_markitdown)
        )
        self._worker: ConversionWorker | None = None
        self._queue: list[Job] = []
        self._sources: dict[int, Path] = {}
        self._results: dict[int, ConversionResult] = {}
        self._build_ui()
        self._load_settings()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.resize(680, 520)
        self.setAcceptDrops(True)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setSpacing(10)
        self.setCentralWidget(central)

        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.add_files)
        self.drop_zone.clicked.connect(self._choose_files)
        root.addWidget(self.drop_zone)

        target_row = QHBoxLayout()
        self.same_dir_radio = QRadioButton(self.tr("Save next to the source file"))
        self.fixed_dir_radio = QRadioButton(self.tr("Save to folder:"))
        self.target_dir_edit = QLineEdit()
        self.target_dir_edit.setReadOnly(True)
        self.target_dir_edit.setPlaceholderText(self.tr("No folder chosen"))
        self.browse_dir_button = QPushButton(self.tr("Choose…"))
        target_row.addWidget(self.same_dir_radio)
        target_row.addWidget(self.fixed_dir_radio)
        target_row.addWidget(self.target_dir_edit, 1)
        target_row.addWidget(self.browse_dir_button)
        root.addLayout(target_row)
        self.same_dir_radio.toggled.connect(self._on_target_mode_toggled)
        self.browse_dir_button.clicked.connect(self._choose_target_dir)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            [self.tr("File"), self.tr("Status"), self.tr("Result")]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_FILE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_RESULT, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(lambda index: self._open_output(index.row()))
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.settings_button = QPushButton(self.tr("Settings…"))
        self.settings_button.clicked.connect(self.open_settings)
        bottom.addWidget(self.settings_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        self.clear_button = QPushButton(self.tr("Clear list"))
        self.clear_button.clicked.connect(self.clear_list)
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.cancel_button)
        bottom.addWidget(self.clear_button)
        root.addLayout(bottom)

    def _make_markitdown(self):
        return build_markitdown(OcrConfig.from_settings(self._settings, self._secrets))

    def open_settings(self) -> None:
        dialog = SettingsDialog(self._settings, self._secrets, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_settings()

    def apply_settings(self) -> None:
        """Rebuild the MarkItDown instance lazily so the new OCR mode is used next time."""
        self._service.reset()

    def _load_settings(self) -> None:
        fixed = self._settings.target_mode is TargetMode.FIXED_DIR
        self.fixed_dir_radio.setChecked(fixed)
        self.same_dir_radio.setChecked(not fixed)
        target = self._settings.target_dir
        self.target_dir_edit.setText(str(target) if target else "")

    # -------------------------------------------------------------- targets
    def _on_target_mode_toggled(self, same_dir: bool) -> None:
        if same_dir:
            self._settings.target_mode = TargetMode.SAME_DIR
        elif self._settings.target_dir is None:
            self._choose_target_dir()
        else:
            self._settings.target_mode = TargetMode.FIXED_DIR

    def _choose_target_dir(self) -> None:
        start = self._settings.target_dir
        chosen = QFileDialog.getExistingDirectory(
            self, self.tr("Choose target folder"), str(start) if start else ""
        )
        if chosen:
            self._settings.target_dir = Path(chosen)
            self._settings.target_mode = TargetMode.FIXED_DIR
            self.target_dir_edit.setText(chosen)
            self.fixed_dir_radio.setChecked(True)
        elif self._settings.target_dir is None:
            self.same_dir_radio.setChecked(True)

    def _choose_files(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Choose files to convert"),
            "",
            self.tr("Supported files ({patterns});;All files (*)").format(patterns=patterns),
        )
        if files:
            self.add_files([Path(f) for f in files])

    # ---------------------------------------------------------------- queue
    def add_files(self, paths: list[Path]) -> None:
        files = expand_paths(paths)
        if not files:
            return
        target_dir = self._settings.effective_target_dir()
        policy = self._settings.conflict_policy
        conflicts = [
            f for f in files if is_supported(f) and output_path_for(f, target_dir).exists()
        ]
        if conflicts and policy is None:
            policy = self._ask_conflict_policy(len(conflicts))
            if policy is None:
                return
        for source in files:
            row = self._append_row(source)
            if is_supported(source):
                self._set_pending(row)
                self._queue.append(Job(row, source, target_dir, policy or ConflictPolicy.RENAME))
            else:
                self._set_status(row, Status.UNSUPPORTED, source.suffix)
        self._start_if_idle()

    def _ask_conflict_policy(self, count: int) -> ConflictPolicy | None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(self.tr("Markdown file already exists"))
        box.setText(self.tr("%n Markdown file(s) already exist at the target location.", "", count))
        box.setInformativeText(self.tr("What should happen to existing files?"))
        overwrite = box.addButton(self.tr("Overwrite"), QMessageBox.ButtonRole.ActionRole)
        keep_both = box.addButton(self.tr("Keep both"), QMessageBox.ButtonRole.ActionRole)
        skip = box.addButton(self.tr("Skip"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        remember = QCheckBox(self.tr("Remember my choice"))
        box.setCheckBox(remember)
        box.setDefaultButton(keep_both)
        box.exec()
        clicked = box.clickedButton()
        policy: ConflictPolicy | None = None
        if clicked is overwrite:
            policy = ConflictPolicy.OVERWRITE
        elif clicked is keep_both:
            policy = ConflictPolicy.RENAME
        elif clicked is skip:
            policy = ConflictPolicy.SKIP
        if policy is not None and remember.isChecked():
            self._settings.conflict_policy = policy
        return policy

    def _start_if_idle(self) -> None:
        if self._worker is not None or not self._queue:
            return
        jobs, self._queue = self._queue, []
        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.cancel_button.setEnabled(True)
        self.clear_button.setEnabled(False)
        worker = ConversionWorker(self._service, jobs, self)
        worker.job_started.connect(self._on_job_started)
        worker.job_finished.connect(self._on_job_finished)
        worker.batch_finished.connect(self._on_batch_finished)
        self._worker = worker
        worker.start()

    def cancel(self) -> None:
        for job in self._queue:
            self._set_cancelled(job.row)
        self._queue.clear()
        if self._worker is not None:
            self._worker.cancel()

    def clear_list(self) -> None:
        if self._worker is not None:
            return
        self.table.setRowCount(0)
        self._sources.clear()
        self._results.clear()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

    @property
    def is_busy(self) -> bool:
        return self._worker is not None

    @property
    def results(self) -> dict[int, ConversionResult]:
        return dict(self._results)

    # -------------------------------------------------------- worker slots
    def _on_job_started(self, row: int) -> None:
        self._set_cell(row, COL_STATUS, self.tr("Converting…"))

    def _on_job_finished(self, row: int, result: ConversionResult) -> None:
        self._results[row] = result
        self._set_status(row, result.status, result.message)
        if result.output is not None and result.succeeded:
            self._set_cell(row, COL_RESULT, result.output.name, str(result.output))
        elif result.message:
            self._set_cell(row, COL_RESULT, result.message, result.message)
        self.progress.setValue(self.progress.value() + 1)

    def _on_batch_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            if worker.cancelled:
                self._queue.clear()
            worker.wait()
            worker.deleteLater()
        for row in range(self.table.rowCount()):
            if row not in self._results and self._is_pending(row):
                self._set_cancelled(row)
        self.progress.setValue(self.progress.maximum())
        self.cancel_button.setEnabled(False)
        self.clear_button.setEnabled(True)
        self.batch_finished.emit()
        self._start_if_idle()

    # --------------------------------------------------------------- table
    def _append_row(self, source: Path) -> int:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._sources[row] = source
        self._set_cell(row, COL_FILE, source.name, str(source))
        self._set_cell(row, COL_STATUS, "")
        self._set_cell(row, COL_RESULT, "")
        return row

    def _set_cell(
        self, row: int, column: int, text: str, tooltip: str | None = None
    ) -> QTableWidgetItem:
        item = self.table.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            self.table.setItem(row, column, item)
        item.setText(text)
        item.setToolTip(tooltip if tooltip is not None else text)
        return item

    def _set_pending(self, row: int) -> None:
        item = self._set_cell(row, COL_STATUS, self.tr("Pending"))
        item.setData(Qt.ItemDataRole.UserRole, "pending")

    def _is_pending(self, row: int) -> bool:
        item = self.table.item(row, COL_STATUS)
        return item is not None and item.data(Qt.ItemDataRole.UserRole) == "pending"

    def _set_cancelled(self, row: int) -> None:
        item = self._set_cell(row, COL_STATUS, self.tr("Cancelled"))
        item.setData(Qt.ItemDataRole.UserRole, "cancelled")

    def _set_status(self, row: int, status: Status, message: str) -> None:
        text = {
            Status.OK: self.tr("Done"),
            Status.EMPTY: self.tr("Done (no text found)"),
            Status.SKIPPED: self.tr("Skipped (file exists)"),
            Status.UNSUPPORTED: self.tr("Unsupported"),
            Status.ERROR: self.tr("Error"),
        }[status]
        item = self._set_cell(row, COL_STATUS, text, message or text)
        item.setData(Qt.ItemDataRole.UserRole, str(status))

    def status_text(self, row: int) -> str:
        item = self.table.item(row, COL_STATUS)
        return item.text() if item is not None else ""

    def _open_output(self, row: int) -> None:
        result = self._results.get(row)
        if result is not None and result.output is not None and result.output.exists():
            open_path(result.output)

    def _show_context_menu(self, pos: QPoint) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu(self)
        result = self._results.get(row)
        has_output = result is not None and result.output is not None and result.output.exists()
        open_md = menu.addAction(self.tr("Open Markdown"))
        reveal_md = menu.addAction(self.tr("Show Markdown in file manager"))
        open_md.setEnabled(has_output)
        reveal_md.setEnabled(has_output)
        menu.addSeparator()
        open_src = menu.addAction(self.tr("Open source file"))
        reveal_src = menu.addAction(self.tr("Show source in file manager"))
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        source = self._sources[row]
        if chosen is open_md and result is not None and result.output is not None:
            open_path(result.output)
        elif chosen is reveal_md and result is not None and result.output is not None:
            reveal_in_file_manager(result.output)
        elif chosen is open_src:
            open_path(source)
        elif chosen is reveal_src:
            reveal_in_file_manager(source)

    # ------------------------------------------------------- window events
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if local_paths(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = local_paths(event.mimeData())
        if paths:
            event.acceptProposedAction()
            self.add_files(paths)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait(10_000)
        self._settings.sync()
        super().closeEvent(event)
