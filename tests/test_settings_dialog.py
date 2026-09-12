from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog

from markitdown_desktop.core.converter import ConflictPolicy
from markitdown_desktop.core.ocr import OcrMode
from markitdown_desktop.core.secrets import AZURE_KEY, LLM_API_KEY, MemorySecretStore
from markitdown_desktop.core.settings import AppSettings
from markitdown_desktop.ui.first_run_dialog import FirstRunDialog, run_first_run
from markitdown_desktop.ui.main_window import MainWindow
from markitdown_desktop.ui.settings_dialog import SettingsDialog


def make_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))


def test_dialog_loads_and_saves_llm_mode(qtbot, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    secrets = MemorySecretStore()
    dialog = SettingsDialog(settings, secrets)
    qtbot.addWidget(dialog)
    assert dialog.mode_chooser.mode is OcrMode.LOCAL
    assert not dialog.llm_group.isEnabled()

    dialog.mode_chooser.mode = OcrMode.LLM
    assert dialog.llm_group.isEnabled()
    dialog.llm_api_key.setText("sk-abc")
    dialog.llm_model.setText("")
    dialog.llm_base_url.setText(" https://llm.example/v1 ")
    dialog.conflict_combo.setCurrentIndex(dialog.conflict_combo.findData("overwrite"))
    dialog.accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert settings.ocr_mode == "llm"
    assert settings.llm_model == "gpt-4o"
    assert settings.llm_base_url == "https://llm.example/v1"
    assert settings.conflict_policy is ConflictPolicy.OVERWRITE
    assert secrets.get(LLM_API_KEY) == "sk-abc"
    assert secrets.get(AZURE_KEY) is None

    again = SettingsDialog(settings, secrets)
    qtbot.addWidget(again)
    assert again.mode_chooser.mode is OcrMode.LLM
    assert again.llm_api_key.text() == "sk-abc"


def test_dialog_refuses_cloud_mode_without_credentials(qtbot, tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    dialog = SettingsDialog(settings, MemorySecretStore())
    qtbot.addWidget(dialog)
    warnings: list[str] = []
    monkeypatch.setattr(dialog, "_warn", lambda title, text: warnings.append(title))
    dialog.mode_chooser.mode = OcrMode.AZURE
    dialog.accept()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert warnings == ["Missing credentials"]
    assert settings.ocr_mode == "local"


def test_first_run_dialog_defaults_to_local(qtbot, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    dialog = FirstRunDialog(settings)
    qtbot.addWidget(dialog)
    assert dialog.mode_chooser.mode is OcrMode.LOCAL
    dialog.accept()
    assert settings.first_run_done is True
    assert settings.ocr_mode == "local"


def test_first_run_is_skipped_once_done(qtbot, tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    settings.first_run_done = True
    window = MainWindow(settings=settings, secrets=MemorySecretStore())
    qtbot.addWidget(window)
    monkeypatch.setattr(FirstRunDialog, "exec", lambda self: (_ for _ in ()).throw(AssertionError))
    run_first_run(settings, MemorySecretStore(), window)


def test_first_run_opens_settings_for_cloud_mode(qtbot, tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    window = MainWindow(settings=settings, secrets=MemorySecretStore())
    qtbot.addWidget(window)
    opened: list[str] = []

    def fake_first_run_exec(self) -> int:
        self.mode_chooser.mode = OcrMode.AZURE
        self.accept()
        return QDialog.DialogCode.Accepted

    def fake_settings_exec(self) -> int:
        opened.append("settings")
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(FirstRunDialog, "exec", fake_first_run_exec)
    monkeypatch.setattr(SettingsDialog, "exec", fake_settings_exec)
    run_first_run(settings, MemorySecretStore(), window)
    assert settings.ocr_mode == "azure"
    assert opened == ["settings"]
