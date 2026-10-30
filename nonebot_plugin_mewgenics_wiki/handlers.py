from __future__ import annotations

import base64

from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from .config import CATEGORY_EXAMPLES, CATEGORY_LABELS, Config
from .data import is_exact_match, search
from .renderer import get_card


def _reply_message(
    event: Event, text: str | None = None, image: bytes | None = None
) -> Message:
    message = Message()
    message_id = getattr(event, "message_id", None)
    if message_id is not None:
        message.append(MessageSegment.reply(message_id))
    if text:
        message.append(MessageSegment.text(text))
    if image is not None:
        encoded = base64.b64encode(image).decode("ascii")
        message.append(MessageSegment.image(f"base64://{encoded}"))
    return message


def make_handler(category: str, trigger: str, config: Config):
    label = CATEGORY_LABELS[category]
    example = CATEGORY_EXAMPLES[category]

    async def handler(
        bot: Bot, event: Event, arg: Message = CommandArg()
    ) -> None:
        query = arg.extract_plain_text().strip()
        if not query:
            await bot.send(
                event,
                _reply_message(
                    event,
                    f"请告诉我你想查询的名称~ 例如：/{trigger} {example}",
                ),
            )
            return

        results = search(
            category,
            query,
            limit=config.mewgenics_wiki_max_results,
            fuzzy_threshold=config.mewgenics_wiki_fuzzy_threshold,
        )
        if not results:
            await bot.send(
                event,
                _reply_message(
                    event,
                    f"图鉴的【{label}】里没有找到包含【{query}】的记录喵~\n"
                    "(可能是分类不对，或者游戏里叫别的名字噢)",
                ),
            )
            return

        entry = results[0]
        hint = None
        if not is_exact_match(entry, query):
            hint = f"你可能在找「{entry.title}」\n"

        try:
            data = await get_card(category, entry, config)
        except Exception:
            logger.exception("Mewgenics Wiki: 卡片渲染失败")
            await bot.send(
                event,
                _reply_message(
                    event,
                    "卡片生成失败啦，可能是渲染组件还没准备好喵~ "
                    "请稍后再试！",
                ),
            )
            return

        try:
            await bot.send(event, _reply_message(event, hint, data))
        except Exception:
            logger.exception("Mewgenics Wiki: 发送卡片失败")
            await bot.send(
                event,
                _reply_message(event, "卡片已生成，但发送失败了喵~ 请稍后再试！"),
            )

    return handler
