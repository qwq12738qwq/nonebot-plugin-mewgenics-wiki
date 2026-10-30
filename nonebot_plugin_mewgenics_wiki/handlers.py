from __future__ import annotations

import base64

from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from .config import CATEGORY_EXAMPLES, CATEGORY_LABELS, Config
from .data import search
from .renderer import get_card, has_cached_card


def _image_message(data: bytes) -> Message:
    encoded = base64.b64encode(data).decode("ascii")
    return Message(MessageSegment.image(f"base64://{encoded}"))


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
                f"请告诉我你想查询的名称~ 例如：/{trigger} {example}",
            )
            return

        results = search(
            category, query, limit=config.mewgenics_wiki_max_results
        )
        if not results:
            await bot.send(
                event,
                f"图鉴的【{label}】里没有找到包含【{query}】的记录喵~\n"
                "(可能是分类不对，或者游戏里叫别的名字噢)",
            )
            return

        entry = results[0]
        notes: list[str] = []
        if not has_cached_card(category, entry, config):
            notes.append("正在生成图鉴卡片，请稍候...")
        if len(results) > 1:
            notes.append(
                f"匹配到 {len(results)} 条，展示最匹配的「{entry.title}」。"
            )
        if notes:
            await bot.send(event, "\n".join(notes))

        try:
            data = await get_card(category, entry, config)
        except Exception:
            logger.exception("Mewgenics Wiki: 卡片渲染失败")
            await bot.send(
                event,
                "卡片生成失败啦，可能是渲染组件还没准备好喵~ 请稍后再试！",
            )
            return

        try:
            await bot.send(event, _image_message(data))
        except Exception:
            logger.exception("Mewgenics Wiki: 发送卡片失败")
            await bot.send(event, "卡片已生成，但发送失败了喵~ 请稍后再试！")

    return handler
