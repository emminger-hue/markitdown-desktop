import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def settings(tmp_path: Path):
    from PySide6.QtCore import QSettings

    from markitdown_desktop.core.settings import AppSettings

    return AppSettings(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
