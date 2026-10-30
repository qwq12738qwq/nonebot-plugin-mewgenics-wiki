from __future__ import annotations

import hashlib
from pathlib import Path

from nonebot import require

require("nonebot_plugin_htmlrender")

from nonebot_plugin_htmlrender import render_html
from nonebot_plugin_localstore import get_plugin_cache_dir

from .card import build_card
from .config import Config
from .data import WikiEntry, snapshot_cache_key

_LAYOUT_VERSION = "10"


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
    artifact = await render_html(
        html,
        width=config.mewgenics_wiki_card_width,
        height=None,
        device_pixel_ratio=config.mewgenics_wiki_device_pixel_ratio,
        image_format="png",
        timeout_seconds=config.mewgenics_wiki_render_timeout,
    )
    data = bytes(artifact)

    if config.mewgenics_wiki_cache_cards:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_bytes(data)
        temp.replace(path)

    return data
