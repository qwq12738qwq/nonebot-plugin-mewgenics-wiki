from __future__ import annotations

import hashlib
from pathlib import Path

from nonebot import require

from .card import build_card
from .compat import HTMLRENDER_VERSION, ensure_htmlrender_backend
from .config import Config
from .data import WikiEntry, snapshot_cache_key

ensure_htmlrender_backend()
require("nonebot_plugin_htmlrender")

from nonebot_plugin_localstore import get_plugin_cache_dir

_LAYOUT_VERSION = "10"


async def _render_png(
    html: str, width: int, device_pixel_ratio: float, timeout_seconds: int
) -> bytes:
    if HTMLRENDER_VERSION >= (0, 8, 0):
        from nonebot_plugin_htmlrender import render_html

        artifact = await render_html(
            html,
            width=width,
            height=None,
            device_pixel_ratio=device_pixel_ratio,
            image_format="png",
            timeout_seconds=timeout_seconds,
        )
        return bytes(artifact)

    from nonebot_plugin_htmlrender import html_to_pic

    kwargs: dict[str, object] = {
        "html": html,
        "wait": 0,
        "template_path": "file:///",
        "type": "png",
        "quality": None,
        "device_scale_factor": device_pixel_ratio,
        "screenshot_timeout": timeout_seconds * 1000,
        "viewport": {"width": width, "height": 800},
    }
    if HTMLRENDER_VERSION >= (0, 7, 0):
        kwargs["full_page"] = True
    return await html_to_pic(**kwargs)


def _card_path(category: str, entry: WikiEntry, config: Config) -> Path:
    key = (
        f"{entry.code}|{_LAYOUT_VERSION}|"
        f"{config.mewgenics_wiki_card_width}|"
        f"{config.mewgenics_wiki_device_pixel_ratio}"
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:24]
    return (
        get_plugin_cache_dir()
        / "cards"
        / snapshot_cache_key()
        / category
        / f"{digest}.png"
    )


def has_cached_card(category: str, entry: WikiEntry, config: Config) -> bool:
    return (
        config.mewgenics_wiki_cache_cards
        and _card_path(category, entry, config).exists()
    )


async def get_card(
    category: str, entry: WikiEntry, config: Config
) -> bytes:
    path = _card_path(category, entry, config)
    if config.mewgenics_wiki_cache_cards and path.exists():
        return path.read_bytes()

    html = build_card(category, entry)
    data = await _render_png(
        html,
        config.mewgenics_wiki_card_width,
        config.mewgenics_wiki_device_pixel_ratio,
        config.mewgenics_wiki_render_timeout,
    )

    if config.mewgenics_wiki_cache_cards:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_bytes(data)
        temp.replace(path)

    return data
