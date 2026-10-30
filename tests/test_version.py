import re
from pathlib import Path

from nonebot_plugin_mewgenics_wiki.card import build_card
from nonebot_plugin_mewgenics_wiki.data import search
from nonebot_plugin_mewgenics_wiki.version import plugin_version


def _pyproject_version() -> str:
    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        "utf-8"
    )
    block = text.split("[project]", 1)[1].split("\n[", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"', block, re.M)
    assert match
    return match.group(1)


def test_plugin_version_matches_pyproject():
    assert plugin_version() == _pyproject_version()


def test_footer_contains_plugin_version():
    entry = search("ability", "小行星", 1)[0]
    html = build_card("ability", entry)
    assert f"插件 v{plugin_version()}" in html
