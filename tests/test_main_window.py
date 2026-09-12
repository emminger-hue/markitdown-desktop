import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from markitdown_desktop.core.converter import ConflictPolicy, ConversionService, Status
from markitdown_desktop.core.settings import AppSettings, TargetMode
from markitdown_desktop.core.worker import ConversionWorker, Job
from markitdown_desktop.ui.drop_zone import DropZone
from markitdown_desktop.ui.main_window import COL_RESULT, MainWindow

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TIMEOUT = 60_000


def copy_fixture(name: str, into: Path) -> Path:
    target = into / name
    shutil.copy(FIXTURES / name, target)
    return target


@pytest.fixture
def window(qtbot, settings: AppSettings) -> MainWindow:
    win = MainWindow(settings=settings, service=ConversionService())
    qtbot.addWidget(win)
    win.show()
    return win


def mime_for(paths: list[Path]) -> QMimeData:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


def test_worker_converts_jobs_sequentially(qtbot, tmp_path: Path) -> None:
    sources = [copy_fixture("sample.csv", tmp_path), copy_fixture("sample.html", tmp_path)]
    jobs = [Job(i, src, None, ConflictPolicy.RENAME) for i, src in enumerate(sources)]
    worker = ConversionWorker(ConversionService(), jobs)
    finished: list[tuple[int, Status]] = []
    worker.job_finished.connect(lambda row, result: finished.append((row, result.status)))
    with qtbot.waitSignal(worker.batch_finished, timeout=TIMEOUT):
        worker.start()
    worker.wait()
    assert finished == [(0, Status.OK), (1, Status.OK)]
    assert (tmp_path / "sample.md").exists() and (tmp_path / "sample (2).md").exists()


def test_drop_zone_accepts_local_files_and_emits(qtbot, tmp_path: Path) -> None:
    zone = DropZone()
    qtbot.addWidget(zone)
    src = copy_fixture("sample.csv", tmp_path)
    mime = mime_for([src])
    enter = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    zone.dragEnterEvent(enter)
    assert enter.isAccepted()
    assert zone.property("active") is True

    drop = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(zone.files_dropped, timeout=1000) as blocker:
        zone.dropEvent(drop)
    assert blocker.args == [[src]]
    assert zone.property("active") is False


def test_drop_zone_ignores_non_file_data(qtbot) -> None:
    zone = DropZone()
    qtbot.addWidget(zone)
    mime = QMimeData()
    mime.setText("just text")
    enter = QDragEnterEvent(
        QPoint(1, 1),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    zone.dragEnterEvent(enter)
    assert not enter.isAccepted()


def test_add_files_converts_next_to_source(qtbot, window: MainWindow, tmp_path: Path) -> None:
    docx = copy_fixture("sample.docx", tmp_path)
    junk = copy_fixture("unsupported.xyz", tmp_path)
    with qtbot.waitSignal(window.batch_finished, timeout=TIMEOUT):
        window.add_files([docx, junk])
    assert window.table.rowCount() == 2
    assert window.results[0].status is Status.OK
    assert window.results[0].output == tmp_path / "sample.md"
    assert window.table.item(0, COL_RESULT).text() == "sample.md"
    assert window.status_text(1) == "Unsupported"
    assert 1 not in window.results
    assert not window.is_busy


def test_folder_drop_converts_supported_files_only(
    qtbot, window: MainWindow, tmp_path: Path
) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    copy_fixture("sample.csv", folder)
    copy_fixture("unsupported.xyz", folder)
    mime = mime_for([folder])  # must outlive the event: Qt only borrows the pointer
    drop = QDropEvent(
        QPointF(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(window.batch_finished, timeout=TIMEOUT):
        window.dropEvent(drop)
    assert window.table.rowCount() == 1
    assert (folder / "sample.md").exists()


def test_fixed_target_directory_is_used(
    qtbot, window: MainWindow, settings: AppSettings, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    out.mkdir()
    settings.target_mode = TargetMode.FIXED_DIR
    settings.target_dir = out
    csv = copy_fixture("sample.csv", tmp_path)
    with qtbot.waitSignal(window.batch_finished, timeout=TIMEOUT):
        window.add_files([csv])
    assert window.results[0].output == out / "sample.md"


def test_conflict_dialog_choice_is_applied(
    qtbot, window: MainWindow, tmp_path: Path, monkeypatch
) -> None:
    csv = copy_fixture("sample.csv", tmp_path)
    (tmp_path / "sample.md").write_text("keep", encoding="utf-8")
    asked: list[int] = []

    def fake_ask(count: int) -> ConflictPolicy:
        asked.append(count)
        return ConflictPolicy.SKIP

    monkeypatch.setattr(window, "_ask_conflict_policy", fake_ask)
    with qtbot.waitSignal(window.batch_finished, timeout=TIMEOUT):
        window.add_files([csv])
    assert asked == [1]
    assert window.results[0].status is Status.SKIPPED
    assert (tmp_path / "sample.md").read_text(encoding="utf-8") == "keep"


def test_remembered_policy_skips_dialog(
    qtbot, window: MainWindow, settings: AppSettings, tmp_path: Path, monkeypatch
) -> None:
    settings.conflict_policy = ConflictPolicy.OVERWRITE
    csv = copy_fixture("sample.csv", tmp_path)
    (tmp_path / "sample.md").write_text("old", encoding="utf-8")
    monkeypatch.setattr(
        window, "_ask_conflict_policy", lambda _count: pytest.fail("dialog must not open")
    )
    with qtbot.waitSignal(window.batch_finished, timeout=TIMEOUT):
        window.add_files([csv])
    assert "| Position | Betrag |" in (tmp_path / "sample.md").read_text(encoding="utf-8")


def test_cancelled_dialog_adds_nothing(window: MainWindow, tmp_path: Path, monkeypatch) -> None:
    csv = copy_fixture("sample.csv", tmp_path)
    (tmp_path / "sample.md").write_text("keep", encoding="utf-8")
    monkeypatch.setattr(window, "_ask_conflict_policy", lambda _count: None)
    window.add_files([csv])
    assert window.table.rowCount() == 0
    assert not window.is_busy


def test_clear_list_resets_table(qtbot, window: MainWindow, tmp_path: Path) -> None:
    csv = copy_fixture("sample.csv", tmp_path)
    with qtbot.waitSignal(window.batch_finished, timeout=TIMEOUT):
        window.add_files([csv])
    window.clear_list()
    assert window.table.rowCount() == 0
    assert window.results == {}
