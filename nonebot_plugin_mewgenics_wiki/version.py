from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def plugin_version() -> str:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text("utf-8")
        if "[project]" in text:
            block = text.split("[project]", 1)[1].split("\n[", 1)[0]
            match = re.search(r'^version\s*=\s*"([^"]+)"', block, re.M)
            if match:
                return match.group(1)

    try:
        return version("nonebot-plugin-mewgenics-wiki")
    except PackageNotFoundError:
        return "unknown"
