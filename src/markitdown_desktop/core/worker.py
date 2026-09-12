from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from markitdown_desktop.core.converter import ConflictPolicy, ConversionService


@dataclass(frozen=True)
class Job:
    row: int
    source: Path
    target_dir: Path | None
    policy: ConflictPolicy


class ConversionWorker(QThread):
    """Converts a batch of jobs sequentially off the UI thread."""

    job_started = Signal(int)
    job_finished = Signal(int, object)
    batch_finished = Signal()

    def __init__(self, service: ConversionService, jobs: list[Job], parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._jobs = jobs
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        for job in self._jobs:
            if self._cancelled:
                break
            self.job_started.emit(job.row)
            result = self._service.convert(job.source, job.target_dir, job.policy)
            self.job_finished.emit(job.row, result)
        self.batch_finished.emit()
