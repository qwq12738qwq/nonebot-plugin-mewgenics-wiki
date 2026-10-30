from nonebot import get_driver, get_plugin_config, on_command, require
from nonebot.plugin import PluginMetadata


def _ensure_htmlrender_provider() -> None:
    config = get_driver().config
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


_ensure_htmlrender_provider()
require("nonebot_plugin_htmlrender")

from .config import COMMAND_TRIGGERS, Config
from .handlers import make_handler

__plugin_meta__ = PluginMetadata(
    name="Mewgenics Wiki 图鉴查询",
    description="查询 Mewgenics Wiki 的能力、被动、物品、突变与角色，并生成站点风格卡片",
    usage="\n".join(
        f"/{trigger} <名称>" for trigger, _ in COMMAND_TRIGGERS
    ),
    type="application",
    homepage="https://mewcodex.pages.dev/?lang=zh",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

_config = get_plugin_config(Config)

for _trigger, _category in COMMAND_TRIGGERS:
    on_command(_trigger, priority=5, block=True).append_handler(
        make_handler(_category, _trigger, _config)
    )
