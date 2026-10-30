from types import SimpleNamespace

from nonebot import get_plugin_config
from nonebot.adapters.onebot.v11 import Message

from nonebot_plugin_mewgenics_wiki.config import Config
from nonebot_plugin_mewgenics_wiki.handlers import make_handler


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    async def send(self, event: object, message: Message) -> None:
        self.messages.append(message)


def test_class_reply_behavior(event_loop):
    async def run():
        config = get_plugin_config(Config).model_copy(
            update={
                "mewgenics_wiki_card_width": 900,
                "mewgenics_wiki_cache_cards": False,
            }
        )
        handler = make_handler("class", "查职业", config)

        async def send_query(query: str) -> list[Message]:
            bot = FakeBot()
            await handler(bot, SimpleNamespace(message_id=12345), Message(query))
            return bot.messages

        return (
            await send_query("法师"),
            await send_query("亡灵法师"),
            await send_query("法"),
            await send_query("绝对不存在的职业"),
        )

    exact, alias, gap, missing = event_loop.run_until_complete(run())

    assert len(exact) == 1
    assert [segment.type for segment in exact[0]] == ["reply", "image"]

    assert len(alias) == 1
    assert [segment.type for segment in alias[0]] == ["reply", "image"]

    assert len(gap) == 1
    assert [segment.type for segment in gap[0]] == ["reply", "text", "image"]
    assert "你可能在找" in gap[0][1].data["text"]

    assert len(missing) == 1
    assert [segment.type for segment in missing[0]] == ["reply", "text"]
