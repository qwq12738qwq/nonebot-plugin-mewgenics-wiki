from nonebot import get_plugin_config, on_command
from nonebot.plugin import PluginMetadata

from .config import COMMAND_TRIGGERS, Config
from .handlers import make_handler

__plugin_meta__ = PluginMetadata(
    name="Mewgenics Wiki 图鉴查询",
    description="Mewgenics Wiki 插件",
    usage="\n".join(
        f"/{trigger} <名称>" for trigger, _ in COMMAND_TRIGGERS
    ),
    type="application",
    homepage="https://github.com/qwq12738qwq/nonebot-plugin-mewgenics-wiki",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

_config = get_plugin_config(Config)

for _trigger, _category in COMMAND_TRIGGERS:
    on_command(_trigger, priority=5, block=True).append_handler(
        make_handler(_category, _trigger, _config)
    )
