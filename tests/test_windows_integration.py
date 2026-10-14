# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Runs real HWND tests on a Windows desktop with Windows App Runtime 1.7.
"""

from collections.abc import Iterator
from collections.abc import Sequence
import ctypes
from ctypes import wintypes
import sys
import threading

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtTest
from PySide6 import QtWidgets
import pytest
import shiboken6

import native_titlebar
from native_titlebar import geometry

# These integration tests inspect the Qt/WinRT boundary and inject native
# failures. Keeping that boundary private avoids exposing a test-only API.
# pylint: disable=protected-access

pytestmark = [
    pytest.mark.windows,
    pytest.mark.skipif(
        sys.platform != "win32", reason="Requires real Windows HWNDs"
    ),
]


@pytest.fixture(name="app", scope="module")
def _app() -> QtWidgets.QApplication:
    """Keeps one QApplication alive for the complete integration test module."""
    application = QtWidgets.QApplication.instance()
    if application is None:
        application = QtWidgets.QApplication([])
    assert isinstance(application, QtWidgets.QApplication)
    application.setQuitOnLastWindowClosed(False)
    return application


@pytest.fixture(name="window")
def _window(
    app: QtWidgets.QApplication,
) -> Iterator[native_titlebar.NativeWindow]:
    """Yields a visible native window and deletes it after each test."""
    del app  # The fixture dependency keeps QApplication alive during the test.
    window = native_titlebar.NativeWindow()
    window.setWindowTitle("Native Titlebar — Automated Test")
    window.resize(900, 400)
    window.show()
    QtTest.QTest.qWait(80)
    yield window
    window.close()
    window.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(
        None, QtCore.QEvent.Type.DeferredDelete
    )


def _settle() -> None:
    """Lets queued layout, paint, and native synchronization events run."""
    QtTest.QTest.qWait(60)


def _hit_test(window: native_titlebar.NativeWindow, x: int, y: int) -> int:
    """Sends WM_NCHITTEST at physical client coordinates to the real HWND."""
    api = ctypes.WinDLL("user32", use_last_error=True)
    api.ClientToScreen.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.POINT),
    ]
    api.ClientToScreen.restype = wintypes.BOOL
    api.SendMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    api.SendMessageW.restype = ctypes.c_ssize_t
    point = wintypes.POINT(x, y)
    hwnd = int(window.winId())
    assert api.ClientToScreen(hwnd, ctypes.byref(point))
    return int(
        api.SendMessageW(
            hwnd, 0x0084, 0, (point.x & 0xFFFF) | ((point.y & 0xFFFF) << 16)
        )
    )


def _fail_palette(palette: QtGui.QPalette) -> None:
    """Simulates failure while applying native caption colors."""
    del palette  # The injected failure is independent of palette contents.
    msg = "simulated native failure"
    raise OSError(msg)


def test_caption_controls_are_children_of_the_only_visible_root(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks HWND ownership and the native frame's required window styles."""
    info = window.diagnostics()
    assert info["visible_top_level_count"] == 1
    assert info["has_native_caption"]
    assert info["has_system_menu"]
    assert info["has_resize_border"]
    caption = [
        c
        for c in info["children"]
        if c["class"] == "ReunionWindowingCaptionControls"
    ]
    assert len(caption) == 1
    assert caption[0]["root_hwnd"] == info["hwnd"]
    assert info["last_error"] is None


def test_resize_recenters_widget_and_updates_native_input_regions(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks layout and native hit testing while resizing programmatically."""
    button = QtWidgets.QPushButton("Test")
    button.setFixedWidth(150)
    window.titlebar.addWidget(button)
    clicks = []
    button.clicked.connect(lambda: clicks.append(True))
    for width in (900, 1200, 700):
        window.resize(width, 400)
        _settle()
        assert abs(button.geometry().center().x() - window.width() / 2) <= 1
        info = window.diagnostics()
        rect = info["interactive_rectangles_px"][0]
        assert (
            _hit_test(
                window,
                rect["x"] + rect["width"] // 2,
                rect["y"] + rect["height"] // 2,
            )
            == 1
        )
        assert _hit_test(window, 30, 16) == 2  # HTCAPTION outside controls
        QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
    assert len(clicks) == 3


def test_line_edit_focus_and_input(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks that a title bar input receives normal Qt focus and key events."""
    edit = QtWidgets.QLineEdit()
    window.titlebar.addWidget(edit)
    _settle()
    edit.setFocus()
    QtTest.QTest.keyClicks(edit, "native title bar")
    assert edit.text() == "native title bar"
    rect = window.diagnostics()["interactive_rectangles_px"][0]
    assert (
        _hit_test(window, rect["x"] + rect["width"] // 2, rect["y"] + 10) == 1
    )


def test_hidden_removed_and_deleted_widgets_no_longer_exclude_drag_area(
    window: native_titlebar.NativeWindow,
) -> None:
    """Exercises hide, remove, and deferred Qt destruction on one title bar."""
    button = QtWidgets.QPushButton("Hide me")
    window.titlebar.addWidget(button)
    _settle()
    button.hide()
    _settle()
    assert not window.diagnostics()["interactive_rectangles_px"]
    button.show()
    _settle()
    assert len(window.diagnostics()["interactive_rectangles_px"]) == 1
    window.titlebar.removeWidget(button)
    _settle()
    assert not window.diagnostics()["interactive_rectangles_px"]
    second = QtWidgets.QPushButton("Delete me")
    window.titlebar.addWidget(second)
    second.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(
        None, QtCore.QEvent.Type.DeferredDelete
    )
    _settle()
    assert not window.diagnostics()["interactive_rectangles_px"]


def test_palette_matches_native_buttons_and_hover_contrast_after_theme_changes(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks native button colors and contrast in dark and light palettes."""
    for background, text in (
        ("#202020", "#ffffff"),
        ("#f4f4f4", "#161616"),
        ("#000000", "#ffffff"),
    ):
        palette = QtGui.QPalette(window.palette())
        palette.setColor(
            QtGui.QPalette.ColorRole.Window, QtGui.QColor(background)
        )
        palette.setColor(
            QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(text)
        )
        window.setPalette(palette)
        _settle()
        assert window._backend is not None
        assert window._backend.native is not None
        bar = window._backend.native.title_bar
        actual = bar.button_background_color
        assert actual is not None
        expected = QtGui.QColor(background)
        assert (actual.r, actual.g, actual.b) == (
            expected.red(),
            expected.green(),
            expected.blue(),
        )
        normal_lightness = QtGui.QColor(background).lightnessF()
        hover = bar.button_hover_background_color
        pressed = bar.button_pressed_background_color
        assert hover is not None
        assert pressed is not None
        hover_lightness = QtGui.QColor(hover.r, hover.g, hover.b).lightnessF()
        pressed_lightness = QtGui.QColor(
            pressed.r, pressed.g, pressed.b
        ).lightnessF()
        if normal_lightness < 0.5:
            assert normal_lightness < hover_lightness < pressed_lightness
        else:
            assert normal_lightness > hover_lightness > pressed_lightness
        for actual in (
            bar.button_hover_foreground_color,
            bar.button_pressed_foreground_color,
        ):
            assert actual is not None
            expected = QtGui.QColor(text)
            assert (actual.r, actual.g, actual.b) == (
                expected.red(),
                expected.green(),
                expected.blue(),
            )
        assert window.diagnostics()["last_error"] is None


def test_maximize_restore_and_central_widget_ownership(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks maximized layout and ownership transfer through the Qt aliases."""
    replacement = QtWidgets.QWidget()
    window.setCentralWidget(replacement)
    window.showMaximized()
    _settle()
    assert window.isMaximized()
    assert replacement.geometry().top() == window.titlebar.height()
    assert replacement.geometry().bottom() == window.height() - 1
    window.showNormal()
    _settle()
    assert not window.isMaximized()
    assert window.takeCentralWidget() is replacement
    assert replacement.parent() is None
    replacement.deleteLater()


def test_two_independent_windows_and_close_reopen(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks independent native handles and reattachment after reopening."""
    other = native_titlebar.NativeWindow()
    other.show()
    _settle()
    assert int(other.winId()) != int(window.winId())
    other.close()
    other.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(
        None, QtCore.QEvent.Type.DeferredDelete
    )
    window.close()
    window.show()
    _settle()
    assert window.diagnostics()["last_error"] is None
    assert window._backend is not None
    assert window._backend.native is not None
    assert window._backend.native.title_bar.extends_content_into_title_bar


def test_native_resize_defers_region_writes_but_keeps_widgets_centered(
    window: native_titlebar.NativeWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Checks that modal resizing defers native updates without freezing Qt."""
    button = QtWidgets.QPushButton("Resize")
    button.setFixedWidth(150)
    window.titlebar.addWidget(button)
    _settle()
    assert window._backend is not None
    previous_regions = window._backend.regions
    writes = []
    original = window._backend.set_regions

    def record(regions: Sequence[geometry.Rect]) -> None:
        """Records native updates while preserving their original behavior."""
        writes.append(regions)
        original(regions)

    monkeypatch.setattr(window._backend, "set_regions", record)
    message = wintypes.MSG()
    message.hWnd = int(window.winId())
    message.message = 0x0231
    # Exercise Qt's actual pointer wrapper and its stub-declared integer form.
    window.nativeEvent(
        QtCore.QByteArray(b"windows_generic_MSG"),
        shiboken6.VoidPtr(ctypes.addressof(message)),
    )
    assert window.diagnostics()["in_native_move_size"]
    for width in (1100, 700, 1200):
        window.resize(width, 400)
        _settle()
        assert abs(button.geometry().center().x() - window.width() / 2) <= 1
    assert not writes
    assert window._backend.regions == previous_regions
    message.message = 0x0232
    window.nativeEvent(
        QtCore.QByteArray(b"windows_generic_MSG"),
        ctypes.addressof(message),
    )
    _settle()
    assert not window.diagnostics()["in_native_move_size"]
    assert writes
    assert window._backend.regions != previous_regions
    rect = window.diagnostics()["interactive_rectangles_px"][0]
    assert (
        _hit_test(window, rect["x"] + rect["width"] // 2, rect["y"] + 10) == 1
    )


def test_snake_case_api_and_qt_compatibility_share_ownership(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks that both public naming conventions operate on the same state."""
    button = QtWidgets.QPushButton("Reusable")
    window.titlebar.add_widget(button)
    _settle()
    assert window.titlebar.widgets == (button,)
    window.titlebar.removeWidget(button)
    assert button.isHidden()
    assert button.parentWidget() is window.titlebar
    window.titlebar.addWidget(button)
    button.show()
    _settle()
    assert len(window.diagnostics()["interactive_rectangles_px"]) == 1
    assert window.integrationError is window.integration_error


def test_reparented_controls_stop_excluding_native_drag_regions(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks that moving a control out of the title bar restores dragging."""
    button = QtWidgets.QPushButton("Move")
    window.titlebar.add_widget(button)
    _settle()
    button.setParent(window.central_widget())
    button.show()
    _settle()
    assert not window.titlebar.widgets
    assert not window.diagnostics()["interactive_rectangles_px"]


def test_invalid_ownership_does_not_disrupt_existing_widgets(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks rejection of cycles and duplicate ownership without data loss."""
    button = QtWidgets.QPushButton("Keep")
    window.titlebar.add_widget(button)
    for invalid, message in (
        (window, "cannot contain itself or an ancestor"),
        (window.titlebar, "cannot contain itself or an ancestor"),
        (button, "already in this title bar"),
    ):
        with pytest.raises(ValueError, match=message):
            window.titlebar.add_widget(invalid)
    with pytest.raises(ValueError, match="cannot be central widgets"):
        window.set_central_widget(window.titlebar)
    _settle()
    assert window.titlebar.widgets == (button,)
    assert window.last_error is None


def test_tall_caption_survives_close_and_reopen(
    window: native_titlebar.NativeWindow,
) -> None:
    """Uses actual SDK metrics before and after reopening the native window."""
    standard_height = window.titlebar.height()
    window.set_tall_title_bar()
    _settle()
    tall_height = window.titlebar.height()
    assert tall_height > standard_height
    window.close()
    window.show()
    _settle()
    assert window.titlebar.height() == tall_height
    window.setTallTitleBar(False)
    _settle()
    assert window.titlebar.height() == standard_height


def test_widget_mutation_from_worker_thread_is_rejected(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks GUI-thread enforcement before Qt ownership can be changed."""
    button = QtWidgets.QPushButton("GUI-owned")
    failures = []

    def mutate() -> None:
        """Attempts a forbidden mutation and records the public exception."""
        try:
            window.titlebar.add_widget(button)
        except native_titlebar.GUIThreadError as exc:
            failures.append(str(exc))

    worker = threading.Thread(target=mutate)
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert len(failures) == 1
    assert not window.titlebar.widgets
    button.deleteLater()


def test_deleted_central_content_can_be_replaced(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks replacement after Qt has destroyed the previous content widget."""
    old = window.central_widget()
    assert old is not None
    old.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(
        None, QtCore.QEvent.Type.DeferredDelete
    )
    assert window.central_widget() is None
    replacement = QtWidgets.QWidget()
    window.set_central_widget(replacement)
    _settle()
    assert window.centralWidget() is replacement


def test_fullscreen_restores_titlebar_and_input_regions(
    window: native_titlebar.NativeWindow,
) -> None:
    """Checks title bar visibility and hit testing after leaving full screen."""
    button = QtWidgets.QPushButton("Restore")
    window.titlebar.add_widget(button)
    window.showFullScreen()
    _settle()
    assert window.titlebar.isHidden()
    assert not window.diagnostics()["drag_rectangles_px"]
    window.showNormal()
    _settle()
    assert not window.titlebar.isHidden()
    rect = window.diagnostics()["interactive_rectangles_px"][0]
    assert (
        _hit_test(window, rect["x"] + rect["width"] // 2, rect["y"] + 10) == 1
    )


def test_async_failure_is_signaled_and_cleared_after_recovery(
    window: native_titlebar.NativeWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Injects an OSError at the Qt/WinRT boundary and then restores it."""
    failures: list[str] = []
    window.integration_error.connect(failures.append)
    assert window._backend is not None
    original = window._backend.set_palette

    monkeypatch.setattr(window._backend, "set_palette", _fail_palette)
    window._sync_safely()
    assert window.last_error == "simulated native failure"
    assert failures == [window.last_error]
    monkeypatch.setattr(window._backend, "set_palette", original)
    window._sync_safely()
    assert window.last_error is None
