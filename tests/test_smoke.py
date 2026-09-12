import tomllib
from pathlib import Path

import markitdown_desktop
from markitdown_desktop.ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_consistent_with_pyproject() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == markitdown_desktop.__version__
    assert data["tool"]["briefcase"]["version"] == markitdown_desktop.__version__


def test_self_test_converts_a_scan(capsys, tmp_path: Path) -> None:
    from PIL import Image

    from markitdown_desktop.app import self_test

    assert self_test(str(ROOT / "tests" / "fixtures" / "scan.pdf")) == 0
    assert "4711" in capsys.readouterr().out
    blank = tmp_path / "blank.png"
    Image.new("RGB", (200, 100), "white").save(blank)
    assert self_test(str(blank)) == 1


def test_main_window_shows(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert window.windowTitle() == markitdown_desktop.APP_NAME
