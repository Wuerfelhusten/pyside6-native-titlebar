# pyside6-native-titlebar

Native Windows title bar integration for PySide6 applications:

- Native minimize, maximize, and close buttons managed by Windows App Runtime
- Real Qt widgets in the title bar, with ordinary focus and input handling
- Palette-aware caption colors and responsive layouts during resizing

Qt draws the optional window icon and title. Windows manages the caption controls on the existing Qt window; no top-level overlay is created.

## Installation

The project targets Python 3.11–3.14 and requires **Windows App Runtime 1.7**. Dependencies select PySide6 6.8.3 for Python 3.11–3.13 and PySide6 6.12.0 for Python 3.14. Install the runtime separately for your Python architecture using [Microsoft's installer](https://learn.microsoft.com/windows/apps/windows-app-sdk/downloads). Runtime 1.8 alone does not satisfy these bindings.

Install from PyPI:

```powershell
python -m pip install pyside6-native-titlebar
```

To install a local checkout, use `python -m pip install .`. For development and examples:

```powershell
uv sync --locked
uv run python -m native_titlebar
```

The diagnostic command checks installation without opening a window. Use `--json` for structured output.

## Quick start

```python
from PySide6 import QtWidgets

import native_titlebar


def main() -> int:
    """Runs a native window with an interactive Qt title bar button."""
    app = QtWidgets.QApplication([])
    window = native_titlebar.NativeWindow()
    window.setWindowTitle("My application")

    action = QtWidgets.QPushButton("Action")
    window.titlebar.add_widget(action)
    window.set_central_widget(QtWidgets.QLabel("Window content"))
    window.resize(1000, 600)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

Create and modify widgets on the QApplication GUI thread. Inherited Qt methods keep their Qt names; the library API uses `snake_case`.

## Examples

The main demo is [`examples/demo.py`](examples/demo.py). The gallery adds theme, height, title, and icon controls:

```powershell
uv run python examples/demo.py
uv run python examples/demo.py --extended
uv run python examples/gallery.py
```

## API documentation

Typed Google-style docstrings are the API reference. Read them in your editor or through Python's built-in documentation viewer:

```powershell
uv run python -m pydoc native_titlebar
uv run python -m pydoc native_titlebar.reports
```

`NativeWindow` owns the content widget and a `TitleBar`. Use `add_widget()` and `remove_widget()` for title bar controls, `set_central_widget()` to replace content, and `take_central_widget()` to retain content without deleting it. `setWindowTitle()` and `setWindowIcon()` update the Qt-painted caption.

Native button colors follow `QPalette.Window` and `WindowText`. Windows retains its close-button hover color. Constructor failures raise `NativeTitleBarError` subclasses; later failures are logged and emitted through `integration_error`. `diagnostics()` returns a typed, JSON-compatible window snapshot. The result schemas are defined in `native_titlebar.reports`.

Version 1.0.0 is the first stable release and has been exercised on Windows 11. Windows 10 is an API target but has not been tested locally. Snap, physical DPI transitions, multiple monitors, and high-contrast behavior still need manual validation. Do not combine this library with frameless flags or another HWND/title bar layer.

## Development

The project follows Google Python style, enables mypy strict mode, and selects all stable Ruff rules with documented compatibility exceptions. CI and local hooks enforce the same checks:

```powershell
uv run black --check src examples tests tools
uv run ruff check .
uv run pylint src/native_titlebar examples tests tools
uv run mypy
uv run pytest -q
uv build
```

Native tests need a signed-in Windows desktop and Runtime 1.7. Use `uv run pytest -q -m "not windows"` for the portable subset.

## Releases

Development uses the `master` branch. Pushing a version tag such as `v1.0.0` starts the release workflow. It checks that the tag matches `src/native_titlebar/_version.py`, runs the required quality checks, builds and validates the distributions, and tests wheel installation on Windows with Python 3.11–3.14. Only then does it publish to PyPI through Trusted Publishing and create a GitHub release with the wheel and source archive attached. These hosted checks do not replace interactive native-window testing.

Before the first release, configure a [pending Trusted Publisher on PyPI](https://pypi.org/manage/account/publishing/) and the GitHub environment `pypi` with these exact values:

| Setting | Value |
| --- | --- |
| PyPI project name | `pyside6-native-titlebar` |
| GitHub owner | `Wuerfelhusten` |
| GitHub repository | `pyside6-native-titlebar` |
| Workflow filename | `release.yml` |
| Environment name | `pypi` |

Trusted Publishing uses short-lived GitHub identity credentials; no PyPI API token is required. Configure any environment review policy to match your release process. An approval requirement pauses publication until a reviewer approves it.

Update `__version__` in `src/native_titlebar/_version.py`, refresh `uv.lock` with `uv lock`, and commit both changes on `master`. Commit messages may be ordinary descriptive text; Conventional Commits are not required. After the checks pass, publish the version tag using Git:

```powershell
git push origin master
git tag v1.0.0
git push origin v1.0.0
```

Use the version you actually set in `_version.py`; PyPI versions cannot be reused. The Release workflow can also be started manually on `master` with a matching version input, optionally prefixed with `v`. Manual runs publish to PyPI but do not create a GitHub release. Branch pushes run CI and packaging checks without publishing.

## License

MIT — see [LICENSE](LICENSE). Google's included Pylint configuration retains its [Apache-2.0 license](LICENSES/Apache-2.0.txt) and its copyright notice in `.pylintrc`.
