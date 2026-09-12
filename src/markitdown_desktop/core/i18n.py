from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

SOURCE_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("de", "en")
SYSTEM = "system"
TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "i18n"


def resolve_language(setting: str) -> str:
    if setting in SUPPORTED_LANGUAGES:
        return setting
    for ui_language in system_ui_languages():
        code = ui_language.replace("_", "-").split("-")[0].lower()
        if code in SUPPORTED_LANGUAGES:
            return code
    return SOURCE_LANGUAGE


def system_ui_languages() -> list[str]:
    """The user's preferred UI languages, most preferred first.

    Inside a macOS app bundle that declares no localizations, Qt only ever reports
    English, so the user's preference list is read from the system defaults there.
    """
    languages: list[str] = []
    if sys.platform == "darwin":
        languages.extend(macos_apple_languages())
    languages.extend(QLocale.system().uiLanguages())
    return languages


def macos_apple_languages(read_defaults=None) -> list[str]:
    """Parse `defaults read -g AppleLanguages`, e.g. '(\\n "de-DE",\\n "en-DE"\\n)'."""
    try:
        output = (
            read_defaults()
            if read_defaults is not None
            else subprocess.run(
                ["defaults", "read", "-g", "AppleLanguages"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout
        )
    except Exception:
        return []
    return re.findall(r'"([A-Za-z0-9-]+)"', output)


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
