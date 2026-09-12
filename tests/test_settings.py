from pathlib import Path

from PySide6.QtCore import QSettings

from markitdown_desktop.core.converter import ConflictPolicy
from markitdown_desktop.core.settings import AppSettings, TargetMode


def make_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))


def test_defaults(tmp_path: Path) -> None:
    s = make_settings(tmp_path)
    assert s.target_mode is TargetMode.SAME_DIR
    assert s.target_dir is None
    assert s.effective_target_dir() is None
    assert s.conflict_policy is None
    assert s.first_run_done is False


def test_roundtrip_persists_to_disk(tmp_path: Path) -> None:
    s = make_settings(tmp_path)
    s.target_mode = TargetMode.FIXED_DIR
    s.target_dir = tmp_path / "out"
    s.conflict_policy = ConflictPolicy.OVERWRITE
    s.first_run_done = True
    s.sync()

    again = make_settings(tmp_path)
    assert again.target_mode is TargetMode.FIXED_DIR
    assert again.effective_target_dir() == tmp_path / "out"
    assert again.conflict_policy is ConflictPolicy.OVERWRITE
    assert again.first_run_done is True


def test_fixed_mode_without_folder_falls_back_to_source_dir(tmp_path: Path) -> None:
    s = make_settings(tmp_path)
    s.target_mode = TargetMode.FIXED_DIR
    assert s.effective_target_dir() is None
    s.conflict_policy = None
    assert s.conflict_policy is None
