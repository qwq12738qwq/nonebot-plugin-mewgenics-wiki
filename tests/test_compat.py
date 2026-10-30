from nonebot_plugin_mewgenics_wiki.compat import (
    HTMLRENDER_VERSION,
    _parse_version,
)


def test_parse_version():
    assert _parse_version("0.8.1") == (0, 8, 1)
    assert _parse_version("0.7.0rc1") == (0, 7, 0)
    assert _parse_version("0.6") == (0, 6, 0)


def test_current_version_is_tuple():
    assert len(HTMLRENDER_VERSION) == 3
