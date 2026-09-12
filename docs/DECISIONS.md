# Entscheidungsprotokoll

Format: Nummer, Datum, Entscheidung, Begründung, Konsequenz.

## D1 – 2026-09-12 – Plattformen: macOS + Windows, kein iOS

MarkItDown ist eine Python-Bibliothek; iOS erlaubt weder klassische Installer noch das
Bundling von Python/ONNX-Laufzeiten in der Form, wie es die Anforderung „alles im Installer“
verlangt. iOS wird gestrichen; ggf. späteres Folgeprojekt.

## D2 – 2026-09-12 – Stack: Python + PySide6, Paketierung mit Briefcase

Eine Codebasis für GUI und MarkItDown-Aufruf, kein Prozess-Bridging. Briefcase erzeugt
`.dmg` (inkl. Signierung/Notarisierung) und `.msi` direkt aus `pyproject.toml`.

## D3 – 2026-09-12 – Lokales OCR mit RapidOCR statt Tesseract

`tesserocr` hat keine Windows-Wheels auf PyPI und verlangt auf macOS Version 15; Tesseract
müsste als Binary je Plattform gebündelt werden. RapidOCR 3.9 bringt PP-OCRv6-Modelle im Wheel
mit, läuft offline auf ONNX Runtime und erkennt Deutsch (inkl. Umlaute) und Englisch — im Test
mit 0,97–1,0 Konfidenz. Kosten: ~60 MB Bundle-Größe.

## D4 – 2026-09-12 – OCR-Modus-Auswahl im Erststart-Assistenten statt im Installer

Ein `.dmg` hat keine Auswahl-UI, und alle drei Modi bestehen nur aus Python-Paketen (kein
Größenvorteil durch Weglassen). Der Assistent erscheint beim ersten Start mit Modus A
vorausgewählt; die Wahl ist jederzeit in den Einstellungen änderbar.

## D5 – 2026-09-12 – macOS nur Apple Silicon, Mindestversion 14

`onnxruntime` ≥ 1.30 liefert für macOS nur noch `arm64`-Wheels (min. macOS 14). Intel-Macs
würden einen zweiten Build mit älterem Pin erfordern; bewusst nicht unterstützt.

## D6 – 2026-09-12 – Signierung: macOS ja, Windows vorerst nein

Apple-Developer-ID ist vorhanden → `.dmg` wird signiert und notarisiert. Für Windows liegt
kein Code-Signing-Zertifikat vor; der SmartScreen-Hinweis wird dokumentiert, die Pipeline
ist für spätere Signierung vorbereitet.

## D7 – 2026-09-12 – Bundle-ID `io.github.emminger-hue`

Reverse-Domain-Konvention für GitHub-gehostete Projekte. Muss vor dem ersten signierten
Release feststehen, da sie Teil der App-Identität ist; Änderung danach erzeugt eine „neue“ App.

## D9 – 2026-09-12 – Laufzeit nutzt `PySide6-Essentials`, nicht das volle `PySide6`

Die App braucht nur QtCore/QtGui/QtWidgets. Das volle Paket zieht `PySide6-Addons`
(WebEngine, Charts, 3D, …) mit und würde die Installer um weit über 100 MB vergrößern. Die
Qt-Linguist-Werkzeuge (`pyside6-lupdate`/`-lrelease`) funktionieren nur mit dem vollen Paket,
daher liegt es in den Dev-Extras; die kompilierten `.qm`-Dateien sind eingecheckt.

## D10 – 2026-09-12 – Release-Workflow testet die gebündelte App und baut auch ohne Zertifikat

Jeder Build führt `--self-test tests/fixtures/scan.pdf` mit dem gebündelten Binary aus; damit
ist belegt, dass Python, MarkItDown, ONNX Runtime und die OCR-Modelle im Paket funktionieren,
bevor ein Installer entsteht. Ohne macOS-Secrets entsteht ein ad-hoc-signiertes DMG, damit
der Workflow vor dem Hinterlegen der Zertifikate erprobt werden kann.

## D8 – 2026-09-12 – Lokaler OCR-Converter wird direkt registriert, nicht als Entry-Point-Plugin

Die App kontrolliert die `MarkItDown`-Instanz und ruft `register_converter()` selbst auf.
`enable_plugins=True` wird nur für Modus C (`markitdown-ocr`) gesetzt, damit sich die Modi
nicht gegenseitig überlagern.
