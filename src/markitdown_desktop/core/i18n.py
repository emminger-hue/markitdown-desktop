from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

SOURCE_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("de", "en")
SYSTEM = "system"
TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "i18n"


def resolve_language(setting: str) -> str:
    if setting in SUPPORTED_LANGUAGES:
        return setting
    for ui_language in QLocale.system().uiLanguages():
        code = ui_language.replace("_", "-").split("-")[0].lower()
        if code in SUPPORTED_LANGUAGES:
            return code
    return SOURCE_LANGUAGE


def install_translators(app: QCoreApplication, language: str) -> list[QTranslator]:
    """Load Qt's own strings (buttons, dialogs) and ours; returns what was installed."""
    installed: list[QTranslator] = []
    if language == SOURCE_LANGUAGE:
        return installed
    qt_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name, directory in (
        (f"qtbase_{language}", qt_dir),
        (f"markitdown_desktop_{language}", str(TRANSLATIONS_DIR)),
    ):
        translator = QTranslator(app)
        if translator.load(name, directory):
            app.installTranslator(translator)
            installed.append(translator)
    return installed
