from importlib.resources import files

from nonebot_plugin_mewgenics_wiki.card import _css

PACKAGE = "nonebot_plugin_mewgenics_wiki"


def test_bundled_chinese_font():
    font = files(PACKAGE).joinpath("fonts", "NotoSansSC-card.woff2").read_bytes()
    assert len(font) > 100_000

    css = files(PACKAGE).joinpath("static", "card.css").read_text("utf-8")
    assert "MewCard" in css


def test_rendered_card_embeds_font():
    css = _css()
    assert "@font-face" in css
    assert "data:font/woff2;base64" in css
    assert "MewCard" in css
