from nonebot import get_plugin_config

from nonebot_plugin_mewgenics_wiki.config import Config
from nonebot_plugin_mewgenics_wiki.data import get_manifest, search
from nonebot_plugin_mewgenics_wiki.renderer import get_card

CASES = {
    "ability": "跳跃",
    "passive": "吸血",
    "item": "剑",
    "mutation": "击退",
    "character": "猫",
    "class": "坦克",
}


def test_manifest():
    manifest = get_manifest()
    assert manifest["counts"]["abilities"] > 0
    assert manifest["asset_count"] > 0
    assert manifest["snapshot_version"] != "unknown"


async def _render_all(config: Config) -> None:
    for category, query in CASES.items():
        results = search(category, query, 1)
        assert results, f"no search result for {category}:{query}"
        png = await get_card(category, results[0], config)
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(png) > 5000


def test_render_all_cards(event_loop):
    config = get_plugin_config(Config).model_copy(
        update={
            "mewgenics_wiki_card_width": 900,
            "mewgenics_wiki_cache_cards": False,
        }
    )
    event_loop.run_until_complete(_render_all(config))
