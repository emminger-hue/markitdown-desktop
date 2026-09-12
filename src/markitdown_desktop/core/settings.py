from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from PySide6.QtCore import QSettings

from markitdown_desktop import APP_NAME, ORG_NAME
from markitdown_desktop.core.converter import ConflictPolicy


class TargetMode(StrEnum):
    SAME_DIR = "same_dir"
    FIXED_DIR = "fixed_dir"


ASK = "ask"


class AppSettings:
    """Typed facade over QSettings. Pass a custom QSettings (e.g. INI in a temp dir) for tests."""

    def __init__(self, store: QSettings | None = None) -> None:
        self._s = store if store is not None else QSettings(ORG_NAME, APP_NAME)

    @property
    def target_mode(self) -> TargetMode:
        return TargetMode(str(self._s.value("output/target_mode", TargetMode.SAME_DIR)))

    @target_mode.setter
    def target_mode(self, mode: TargetMode) -> None:
        self._s.setValue("output/target_mode", str(mode))

    @property
    def target_dir(self) -> Path | None:
        raw = self._s.value("output/target_dir", "")
        return Path(str(raw)) if raw else None

    @target_dir.setter
    def target_dir(self, path: Path | None) -> None:
        self._s.setValue("output/target_dir", str(path) if path else "")

    def effective_target_dir(self) -> Path | None:
        if self.target_mode is TargetMode.FIXED_DIR and self.target_dir is not None:
            return self.target_dir
        return None

    @property
    def conflict_policy(self) -> ConflictPolicy | None:
        """None means "ask the user"."""
        raw = str(self._s.value("output/conflict_policy", ASK))
        return None if raw == ASK else ConflictPolicy(raw)

    @conflict_policy.setter
    def conflict_policy(self, policy: ConflictPolicy | None) -> None:
        self._s.setValue("output/conflict_policy", ASK if policy is None else str(policy))

    @property
    def first_run_done(self) -> bool:
        return bool(self._s.value("app/first_run_done", False, type=bool))

    @first_run_done.setter
    def first_run_done(self, done: bool) -> None:
        self._s.setValue("app/first_run_done", done)

    def sync(self) -> None:
        self._s.sync()
