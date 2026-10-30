from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from nonebot import get_driver


def _parse_version(raw: str) -> tuple[int, int, int]:
    parts: list[int] = []
    for chunk in raw.split(".")[:3]:
        digits = ""
        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits or 0))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def htmlrender_version() -> tuple[int, int, int]:
    try:
        return _parse_version(version("nonebot-plugin-htmlrender"))
    except PackageNotFoundError:
        return (0, 0, 0)


HTMLRENDER_VERSION = htmlrender_version()


def ensure_htmlrender_backend() -> None:
    config = get_driver().config

    if HTMLRENDER_VERSION >= (0, 8, 0):
        render = getattr(config, "render", None)
        if render is None:
            setattr(config, "render", {"provider": "playwright", "startup": "off"})
        elif isinstance(render, dict):
            if not render.get("provider"):
                render["provider"] = "playwright"
            if not render.get("startup"):
                render["startup"] = "off"
        elif not getattr(render, "provider", None):
            try:
                render.provider = "playwright"
            except (AttributeError, ValueError):
                pass
        return

    if HTMLRENDER_VERSION >= (0, 7, 0):
        if getattr(config, "render_backend", None) in (None, ""):
            setattr(config, "render_backend", "playwright")
