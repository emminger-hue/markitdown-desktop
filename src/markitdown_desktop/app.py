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
    import logging
    import traceback

    from markitdown_desktop.core.ocr import OcrConfig
    from markitdown_desktop.core.ocr.factory import build_markitdown

    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s", stream=sys.stdout)
    rapidocr_logger = logging.getLogger("RapidOCR")
    rapidocr_logger.addHandler(logging.StreamHandler(sys.stdout))
    rapidocr_logger.setLevel(logging.INFO)
    _print_environment()
    try:
        markdown = build_markitdown(OcrConfig()).convert(path).markdown
    except Exception:
        traceback.print_exc(file=sys.stdout)
        return 2
    print(f"self-test: {path} -> {len(markdown)} characters")
    print(markdown[:400])
    return 0 if markdown.strip() else 1


def _print_environment() -> None:
    import importlib
    import platform

    print(f"python {sys.version.split()[0]} on {platform.platform()} {platform.machine()}")
    for name in ("onnxruntime", "rapidocr", "pypdfium2", "numpy", "cv2", "PIL", "markitdown"):
        try:
            module = importlib.import_module(name)
            print(f"{name} {getattr(module, '__version__', '?')} from {module.__file__}")
        except Exception as exc:
            print(f"{name}: import failed: {exc!r}")
    try:
        import onnxruntime

        print("onnxruntime providers:", onnxruntime.get_available_providers())
    except Exception as exc:
        print("onnxruntime providers: failed:", repr(exc))
    try:
        from markitdown_desktop.core.ocr.local import get_engine

        engine = get_engine()
        print("rapidocr engine:", type(engine).__name__)
        for stage in ("text_det", "text_cls", "text_rec"):
            component = getattr(engine, stage, None)
            session = getattr(component, "session", None)
            print(f"  {stage}: {type(component).__name__}, session={type(session).__name__}")
    except Exception:
        import traceback

        traceback.print_exc(file=sys.stdout)


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
