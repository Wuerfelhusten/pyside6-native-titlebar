# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Checks installation failures without creating native windows.
"""

import json
import subprocess
import sys
import textwrap

import pytest

import native_titlebar
from native_titlebar import __main__
from native_titlebar import diagnostics
from native_titlebar.platform import windows


def _unexpected_bootstrap() -> None:
    """Fails if a read-only operation loads the native runtime."""
    pytest.fail("A read-only report must not initialize native libraries")


def _missing_runtime() -> None:
    """Simulates an unavailable native runtime."""
    msg = "Install Runtime 1.7 x64"
    raise native_titlebar.RuntimeUnavailableError(msg)


def test_environment_report_does_not_initialize_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checks that reporting versions has no native-runtime side effects."""
    monkeypatch.setattr(windows, "ensure_runtime", _unexpected_bootstrap)
    report = diagnostics.environment_report()
    assert report["runtime_available"] is None
    assert report["library"] == native_titlebar.__version__
    assert json.loads(json.dumps(report)) == report


def test_unsupported_platform_raises_specific_public_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checks the public error type when Windows APIs are unavailable."""
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(native_titlebar.UnsupportedPlatformError):
        windows.ensure_runtime()


def test_cli_returns_failure_and_actionable_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Checks the failure exit code and machine-readable recovery message."""
    monkeypatch.setattr(windows, "ensure_runtime", _missing_runtime)
    assert __main__.main(["--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["runtime_available"] is False
    assert "Runtime 1.7" in report["error"]


def test_import_and_version_do_not_bootstrap_runtime() -> None:
    """Checks import side effects in a fresh interpreter."""
    # Run a fixed snippet with this interpreter, without a shell.
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            textwrap.dedent("""\
                import sys

                import native_titlebar

                assert not any(
                    name.startswith("winui3.microsoft.ui")
                    for name in sys.modules
                )
                print(native_titlebar.__version__)
            """),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.stdout.strip() == native_titlebar.__version__


def test_native_window_requires_qapplication_before_touching_hwnd() -> None:
    """Checks that missing QApplication raises before any native GUI work."""
    # Run a fixed snippet with this interpreter, without a shell.
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            textwrap.dedent("""\
                import native_titlebar

                try:
                    native_titlebar.NativeWindow()
                except native_titlebar.GUIThreadError:
                    print("rejected")
            """),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.stdout.strip() == "rejected"
