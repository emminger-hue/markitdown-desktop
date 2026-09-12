"""Collect the licenses of every runtime dependency into one text file for the About dialog.

Run inside a virtualenv that has the app installed:  python tools/collect_licenses.py
Writes src/markitdown_desktop/resources/THIRD_PARTY_LICENSES.txt. Commit the result and
re-run whenever dependencies change (tests/test_licenses.py fails when it is stale).
"""

from __future__ import annotations

import re
import sys
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src" / "markitdown_desktop" / "resources" / "THIRD_PARTY_LICENSES.txt"
TEXTS = Path(__file__).resolve().parent / "license_texts"
APP = "markitdown-desktop"
RULE = "=" * 78

# Components that pip does not know about but that ship inside the installers.
EXTRA_COMPONENTS = [
    (
        "Python",
        "3.12",
        "PSF-2.0",
        "https://www.python.org/",
        "Copyright (c) 2001 Python Software Foundation. All rights reserved.\n"
        "Licensed under the Python Software Foundation License Version 2; the full text is "
        "available at https://docs.python.org/3/license.html and inside the Python "
        "framework bundled with this application.",
    ),
    (
        "Qt (via PySide6)",
        "6",
        "LGPL-3.0-only",
        "https://www.qt.io/",
        "Copyright (C) The Qt Company Ltd. Qt is used under the GNU Lesser General Public "
        "License v3 and is linked dynamically: the Qt libraries inside the application "
        "bundle can be replaced with a compatible build. Qt source code is available at "
        "https://code.qt.io/ and https://download.qt.io/official_releases/qt/.",
    ),
    (
        "PDFium (via pypdfium2)",
        "",
        "Apache-2.0 AND BSD-3-Clause",
        "https://pdfium.googlesource.com/pdfium/",
        "Copyright 2014 The PDFium Authors. See the pypdfium2 entry for the license texts.",
    ),
]

FALLBACK_TEXTS = {
    "MIT": "MIT.txt",
    "APACHE-2.0": "Apache-2.0.txt",
    "BSD-3-CLAUSE": "BSD-3-Clause.txt",
    "LGPL-3.0-ONLY": "LGPL-3.0.txt",
    "LGPL-3.0": "LGPL-3.0.txt",
}


# The installers target these platforms; this script usually runs on Linux.
TARGET_ENVIRONMENTS = (
    {"sys_platform": "darwin", "platform_system": "Darwin", "os_name": "posix"},
    {"sys_platform": "win32", "platform_system": "Windows", "os_name": "nt"},
)


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# Requirements that only the Windows wheels of some packages declare (per-wheel metadata),
# so a closure computed on Linux or macOS would not see them.
PLATFORM_WHEEL_REQUIREMENTS = [
    "coloredlogs",  # onnxruntime (Windows)
    "humanfriendly",  # coloredlogs
    "pyreadline3",  # humanfriendly (Windows)
    "sympy",  # onnxruntime (Windows)
    "mpmath",  # sympy
]


def runtime_closure(root: str) -> dict[str, Distribution]:
    """Every distribution reachable from the app's (non-dev) requirements."""
    seen: dict[str, Distribution] = {}
    pending = [Requirement(r) for r in distribution(root).requires or [] if _is_runtime(r)]
    pending += [Requirement(r) for r in PLATFORM_WHEEL_REQUIREMENTS]
    while pending:
        requirement = pending.pop()
        name = canonical(requirement.name)
        if name in seen:
            continue
        try:
            dist = distribution(requirement.name)
        except PackageNotFoundError:
            continue
        seen[name] = dist
        for child in dist.requires or []:
            child_req = Requirement(child)
            if _marker_applies(child_req, requirement.extras):
                pending.append(child_req)
    return dict(sorted(seen.items()))


def _is_runtime(requirement: str) -> bool:
    return _marker_applies(Requirement(requirement), set())


def _marker_applies(req: Requirement, parent_extras: set[str]) -> bool:
    if req.marker is None:
        return True
    return any(
        req.marker.evaluate({**environment, "extra": extra})
        for environment in TARGET_ENVIRONMENTS
        for extra in (parent_extras or {""})
    )


def license_id(dist: Distribution) -> str:
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression
    raw = (meta.get("License") or "").strip()
    if raw:
        return raw.splitlines()[0][:80]
    for classifier in meta.get_all("Classifier") or []:
        if classifier.startswith("License ::"):
            return classifier.split("::")[-1].strip()
    return "unknown"


def license_files(dist: Distribution) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for file in dist.files or []:
        name = file.name.upper()
        if not any(key in name for key in ("LICENSE", "COPYING", "NOTICE")):
            continue
        if "3RD" in name or "THIRD" in name:
            continue
        try:
            text = Path(str(dist.locate_file(file))).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if text.strip():
            found.append((str(file), text.strip()))
    return found


def fallback_text(identifier: str) -> str | None:
    key = re.split(r"\s+(?:AND|OR)\s+", identifier.upper())[0].strip()
    filename = FALLBACK_TEXTS.get(key)
    return (TEXTS / filename).read_text(encoding="utf-8") if filename else None


def render(dists: dict[str, Distribution]) -> str:
    out = [
        "THIRD-PARTY LICENSES",
        "",
        "MarkItDown Desktop bundles the following components. Each entry lists the",
        "component, its license and the license text or notice that applies. Version",
        "numbers are those of the environment this file was generated in; the installer",
        "may carry a newer patch release of a component under the same license.",
        "",
    ]
    for name, version, identifier, home, text in EXTRA_COMPONENTS:
        out += [
            RULE,
            f"{name} {version}".strip(),
            f"License: {identifier}",
            f"Homepage: {home}",
            "",
            text,
            "",
        ]
    for dist in dists.values():
        meta = dist.metadata
        identifier = license_id(dist)
        home = meta.get("Home-page") or _project_url(meta) or ""
        author = meta.get("Author") or meta.get("Author-email") or ""
        out += [RULE, f"{meta['Name']} {dist.version}", f"License: {identifier}"]
        if home:
            out.append(f"Homepage: {home}")
        if author:
            out.append(f"Author: {author}")
        out.append("")
        files = license_files(dist)
        if files:
            for path, text in files:
                out += [f"--- {path} ---", text, ""]
        else:
            fallback = fallback_text(identifier)
            if fallback:
                out += [
                    f"(No license file is shipped in the package; "
                    f"standard {identifier} text follows.)",
                    "",
                    fallback.strip(),
                    "",
                ]
            else:
                out += ["(No license text is shipped in the package; see the homepage.)", ""]
    return "\n".join(out) + "\n"


def _project_url(meta) -> str:
    for url in meta.get_all("Project-URL") or []:
        label, _, target = url.partition(",")
        if label.strip().lower() in ("homepage", "repository", "source", "home"):
            return target.strip()
    return ""


def main() -> None:
    dists = runtime_closure(APP)
    OUTPUT.write_text(render(dists), encoding="utf-8")
    size_kb = OUTPUT.stat().st_size // 1024
    print(f"{len(dists)} distributions -> {OUTPUT.relative_to(ROOT)} ({size_kb} KB)")
    if "--list" in sys.argv:
        print(", ".join(dists))


if __name__ == "__main__":
    main()
