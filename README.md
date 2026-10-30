# pyside6-native-titlebar

Native Windows title bar integration for PySide6 applications.

- Native minimize, maximize, and close buttons managed by Windows
- Interactive Qt widgets in the title bar
- Caption colors that follow the Qt palette
- Window classes based on both `QWidget` and `QMainWindow`

Qt draws the window icon and title. Windows manages the caption buttons on the same window.

## Installation

Requires Windows, Python **3.11–3.14**, and **Windows App Runtime 1.7**. Install the runtime for your Python architecture using [Microsoft's installer](https://learn.microsoft.com/windows/apps/windows-app-sdk/downloads). Other runtime versions can coexist, but do not replace 1.7.

```powershell
python -m pip install pyside6-native-titlebar
```

## Quick start

```python
from PySide6 import QtWidgets

import native_titlebar


def main() -> int:
    """Runs a window with an interactive title bar button."""
    app = QtWidgets.QApplication([])
    window = native_titlebar.NativeWindow()
    window.setWindowTitle("My application")

    action = QtWidgets.QPushButton("Action")
    window.titleBar().addWidget(action)
    window.setCentralWidget(QtWidgets.QLabel("Window content"))
    window.resize(1000, 600)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

Use `NativeWindow` for a simple widget window. Use `NativeMainWindow` when your application needs Qt menus, toolbars, dock widgets, or a status bar. Both classes provide the same `titleBar()` API.

Both window classes use `setCentralWidget()`, `centralWidget()`, and `takeCentralWidget()` for content. Public methods and signals follow Qt's `camelCase` convention. Read state through getter methods such as `window.titleBar()`, `window.titleBar().widgets()`, and `window.lastError()`.

## QMainWindow

`NativeMainWindow` inherits directly from `QMainWindow`. Use it in place of `NativeWindow` in the example above, or subclass it in your application:

```python
class MainWindow(native_titlebar.NativeMainWindow):
    """An application window with standard Qt menus and central content."""

    def __init__(self) -> None:
        """Creates the editor and its menu."""
        super().__init__()
        self.setWindowTitle("My editor")
        self.setCentralWidget(QtWidgets.QTextEdit())
        file_menu = self.menuBar().addMenu("&File")
        close_action = file_menu.addAction("Close")
        close_action.triggered.connect(self.close)
        self.statusBar().showMessage("Ready")
```

The title bar sits above the menu and toolbar areas. Standard methods such as `addDockWidget()`, `addToolBar()`, `saveState()`, and `restoreState()` remain available.

## Title bar controls

Add controls with `window.titleBar().addWidget(widget)`. They receive normal Qt mouse, keyboard, and focus events. Free space remains available for dragging the window. `removeWidget(widget)` hides a control without deleting it; it stays owned by the title bar until reparented.

Use `setWindowTitle()` and `setWindowIcon()` to update the caption, `window.titleBar().setTitleVisible(False)` or `setIconVisible(False)` to hide either element, and `window.setTallTitleBar(True)` for a taller caption area. Button colors follow `QPalette.Window` and `QPalette.WindowText`; Windows controls the close-button hover color.

Create and modify widgets on the QApplication GUI thread. Keep the standard window frame enabled; do not combine the library with frameless flags or another title bar integration. API details and ownership rules are documented in the docstrings.

## Button colors

Caption buttons automatically fade when the window loses focus. A distinct `QPalette.Inactive.WindowText` color is preserved; otherwise, the inactive symbol color blends 40% of the active foreground with the inactive background. Windows manages the actual focus transition.

Override individual states through the title bar of either window class:

```python
from PySide6 import QtGui

role = native_titlebar.ButtonColorRole
bar = window.titleBar()
bar.setButtonColor(role.FOREGROUND, QtGui.QColor("#ffffff"))
bar.setButtonColor(role.INACTIVE_FOREGROUND, QtGui.QColor("#808080"))
bar.setButtonColor(role.HOVER_BACKGROUND, QtGui.QColor("#404040"))

current_color = bar.buttonColor(role.INACTIVE_FOREGROUND)
bar.setButtonColor(role.HOVER_BACKGROUND, None)  # Restore one default.
bar.resetButtonColors()  # Restore all palette-based defaults.
```

`ButtonColorRole` provides `BACKGROUND` and `FOREGROUND` roles for the normal, `INACTIVE_`, `HOVER_`, and `PRESSED_` states. Overrides survive palette changes and reopening the window. `buttonColor()` and `buttonColors()` return independent copies of the resolved colors; `buttonColorsChanged` signals changes to explicit overrides. Native updates are applied on the next event-loop turn.

These settings affect the three native caption buttons. Use the Qt palette for the surrounding title bar and title text. Background colors support transparency; foreground alpha is ignored by Windows. Windows retains the close button's hover and pressed backgrounds, and Windows 10 may ignore custom caption colors.

## Examples

Run the examples from a local checkout after `uv sync --locked`:

```powershell
uv run python examples/demo.py
uv run python examples/demo.py --extended
uv run python examples/main_window.py
uv run python examples/gallery.py
```

The [basic demo](https://github.com/Wuerfelhusten/pyside6-native-titlebar/blob/master/examples/demo.py) shows interactive title bar controls. The [main-window demo](https://github.com/Wuerfelhusten/pyside6-native-titlebar/blob/master/examples/main_window.py) includes an editor, menus, a toolbar, a dock, and a status bar. The [gallery](https://github.com/Wuerfelhusten/pyside6-native-titlebar/blob/master/examples/gallery.py) lets you explore themes and caption settings.

## Troubleshooting

Check the installed dependencies and Windows App Runtime without opening a window:

```powershell
python -m native_titlebar
python -m native_titlebar --json
```

Window creation raises a `NativeTitleBarError` subclass if initialization fails. Later integration errors are logged and emitted through `window.integrationError`. Use `window.diagnostics()` for a structured snapshot of native geometry and the last error. Report problems through [GitHub Issues](https://github.com/Wuerfelhusten/pyside6-native-titlebar/issues).

## License

[MIT](https://github.com/Wuerfelhusten/pyside6-native-titlebar/blob/master/LICENSE) — Copyright (c) 2026 Modding Forge.
