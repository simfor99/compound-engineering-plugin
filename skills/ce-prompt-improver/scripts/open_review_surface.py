#!/usr/bin/env python3
"""Open a rendered review surface with WSL2-safe Windows file URI handling."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote


def is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def path_to_file_uri(path: Path) -> str:
    resolved = path.expanduser().resolve()
    if is_wsl():
        distro = os.environ.get("WSL_DISTRO_NAME") or "Ubuntu"
        quoted = quote(str(resolved), safe="/._-~")
        return f"file://///wsl.localhost/{quote(distro, safe='')}{quoted}"
    return resolved.as_uri()


def powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def open_uri(uri: str, browser: str) -> None:
    if is_wsl() and shutil.which("powershell.exe"):
        command = (
            "Start-Process "
            f"-FilePath {powershell_quote(browser)} "
            f"-ArgumentList {powershell_quote(uri)}"
        )
        subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], check=True)
        return

    opener = shutil.which(browser) or shutil.which("xdg-open")
    if not opener:
        raise RuntimeError(f"No opener found for browser '{browser}'. URI: {uri}")
    subprocess.run([opener, uri], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path, help="Path to rendered html/index.html")
    parser.add_argument("--browser", default="firefox")
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    if not args.html.exists():
        raise SystemExit(f"HTML file not found: {args.html}")
    if args.html.suffix.lower() not in {".html", ".htm"}:
        raise SystemExit(f"Expected an HTML file, got: {args.html}")

    uri = path_to_file_uri(args.html)
    print(uri)

    if args.print_only:
        return 0

    try:
        open_uri(uri, args.browser)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to open browser: {exc}", file=sys.stderr)
        print(f"Open manually: {uri}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
