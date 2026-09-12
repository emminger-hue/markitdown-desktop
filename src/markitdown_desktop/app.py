from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from markitdown_desktop import APP_NAME, ORG_NAME, __version__


def create_app(argv: list[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationVersion(__version__)
    return app


def self_test(path: str) -> int:
    """Convert one file with the offline engine and report; used to verify packaged builds."""
    from markitdown_desktop.core.ocr import OcrConfig
    from markitdown_desktop.core.ocr.factory import build_markitdown

    markdown = build_markitdown(OcrConfig()).convert(path).markdown
    print(f"self-test: {path} -> {len(markdown)} characters")
    print(markdown[:400])
    return 0 if markdown.strip() else 1


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        sys.exit(self_test(sys.argv[2]))
    app = create_app()
    from markitdown_desktop.core.i18n import install_translators, resolve_language
    from markitdown_desktop.core.secrets import KeyringSecretStore
    from markitdown_desktop.core.settings import AppSettings
    from markitdown_desktop.ui.first_run_dialog import run_first_run
    from markitdown_desktop.ui.main_window import MainWindow

    settings = AppSettings()
    secrets = KeyringSecretStore()
    install_translators(app, resolve_language(settings.language))
    window = MainWindow(settings=settings, secrets=secrets)
    window.show()
    run_first_run(settings, secrets, window)
    window.apply_settings()
    sys.exit(app.exec())
