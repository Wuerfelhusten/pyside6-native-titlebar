# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Checks installation with python -m native_titlebar, without opening a GUI.
"""

import argparse
from collections.abc import Sequence
import json

from native_titlebar import _version
from native_titlebar import diagnostics


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the installation check and prints a human-readable or JSON report.

    Args:
        argv: Command-line arguments, or None to read the process arguments.

    Returns:
        Zero if the runtime loads, or one if the environment is unsupported.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Print a JSON report."
    )
    parser.add_argument(
        "--version", action="version", version=_version.__version__
    )
    args = parser.parse_args(argv)
    report = diagnostics.environment_report(check_runtime=True)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
    return 0 if report["runtime_available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
