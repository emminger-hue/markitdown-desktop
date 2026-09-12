import importlib.util
from pathlib import Path

from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QDesktopServices

from markitdown_desktop import RELEASES_URL, REPO_URL, __version__
from markitdown_desktop.core.settings import AppSettings
from markitdown_desktop.ui.about_dialog import LICENSES_FILE, AboutDialog, LicensesDialog

ROOT = Path(__file__).resolve().parents[1]


def make_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))


def test_about_dialog_shows_version_text_and_details(qtbot, tmp_path: Path) -> None:
    dialog = AboutDialog(make_settings(tmp_path))
    qtbot.addWidget(dialog)
    dialog.show()
    assert __version__ in dialog.version_label.text()
    assert "Marc Emminger" in dialog.version_label.text()
    html = dialog.body.text()
    assert REPO_URL in html
    assert "not affiliated" in html
    assert "Privacy" in html
    assert not dialog.details.isVisible()
    dialog.details_toggle.setChecked(True)
    assert dialog.details.isVisible()
    assert "Python" in dialog.details.text() and "OCR mode: local" in dialog.details.text()


def test_check_for_updates_opens_releases_page(qtbot, tmp_path: Path, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()))
    dialog = AboutDialog(make_settings(tmp_path))
    qtbot.addWidget(dialog)
    dialog.update_button.click()
    assert opened == [QUrl(RELEASES_URL).toString()]


def test_licenses_dialog_loads_file_and_searches(qtbot) -> None:
    dialog = LicensesDialog()
    qtbot.addWidget(dialog)
    text = dialog.text.toPlainText()
    for expected in ("markitdown", "rapidocr", "onnxruntime", "Qt (via PySide6)", "LGPL"):
        assert expected in text
    dialog.search.setText("rapidocr")
    assert dialog.find_next()
    assert dialog.text.textCursor().selectedText() == "rapidocr"


def test_licenses_file_covers_every_runtime_dependency() -> None:
    spec = importlib.util.spec_from_file_location(
        "collect_licenses", ROOT / "tools" / "collect_licenses.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = LICENSES_FILE.read_text(encoding="utf-8")
    missing = [
        f"{dist.metadata['Name']} {dist.version}"
        for dist in module.runtime_closure(module.APP).values()
        if f"{dist.metadata['Name']} {dist.version}" not in text
    ]
    assert missing == [], f"re-run tools/collect_licenses.py; missing: {missing}"
