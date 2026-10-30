#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

from fontTools import subset

DEFAULT_FONT_URL = (
    "https://cdn.jsdelivr.net/gh/googlefonts/noto-cjk@main/"
    "Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
)
LICENSE_URL = "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/LICENSE"

EXTRA_TEXT = """
能力 被动 物品 突变 角色 图鉴 查询 数据快照 来源 属性 类型 稀有度 套装 标签
部位 费用 伤害 描述 升级 匹配 展示 最匹配 条 未找到 请稍候 生命 移动 击杀
尸体 阵营 体型 护盾 神圣护盾 力量 敏捷 智力 体质 魅力 幸运 速度 章节 池
解锁 需求 出生缺陷 敌方 友方 中立 技能 天赋 道具 变体 普通 罕见 稀有 非常稀有
任务 支线任务 未知 消耗品 头部 面部 颈部 武器 饰品 修改器 猫 数据 版本
正在生成 图鉴卡片 没有找到 可能是 分类不对 游戏里 叫别的名字 未知稀有度
诅咒 耐久 附加 独行敌方 巨兽 德鲁伊 死灵法师 灵能 战士 法师 坦克 工匠
盗贼 武僧 屠夫 猎人 医者 小丑 无色 近战 远程 召唤 防御 增益 减益 攻击
杂项 物理 魔法 治疗 真实 法力 行动 该突变没有文字描述 该角色没有文字介绍
耳朵突变 身体突变 眼睛突变 后腿突变 尾部突变 嘴巴突变 前腿突变
职业 职业能力预览 个被动 个能力 还有 未展示 暂无 牧师 灵能者 无项圈
紊乱 战士 盗贼 坦克 法师 猎人 死灵法师 屠夫 武僧 德鲁伊 工匠 小丑
，。！？、：；（）【】「」·—…《》“”‘’+-:/%()[]{}<>#&×÷±
"""


def download(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return target
    with urllib.request.urlopen(url, timeout=120) as resp:
        target.write_bytes(resp.read())
    return target


def walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=Path("nonebot_plugin_mewgenics_wiki"))
    parser.add_argument("--font-source", default="")
    parser.add_argument("--font-cache", type=Path, default=Path(".cache/NotoSansCJKsc-Regular.otf"))
    parser.add_argument("--license-cache", type=Path, default=Path(".cache/OFL.txt"))
    args = parser.parse_args()

    if args.font_source:
        source = Path(args.font_source).expanduser()
        if not source.exists():
            source = download(args.font_source, args.font_cache)
    else:
        source = download(DEFAULT_FONT_URL, args.font_cache)

    chars: set[str] = set(EXTRA_TEXT)
    for path in (args.package / "data").glob("*.json"):
        data = json.loads(path.read_text("utf-8"))
        for text in walk_strings(data):
            chars.update(text)

    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.desubroutinize = True

    font = subset.load_font(str(source), options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text="".join(sorted(chars)))
    subsetter.subset(font)

    out_dir = args.package / "fonts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "NotoSansSC-card.woff2"
    subset.save_font(font, str(out_path), options)

    try:
        license_path = download(LICENSE_URL, args.license_cache)
        (out_dir / "OFL.txt").write_bytes(license_path.read_bytes())
    except OSError as exc:
        print(f"warning: license download failed: {exc}")

    print(f"font subset: {out_path} ({out_path.stat().st_size} bytes), chars={len(chars)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
