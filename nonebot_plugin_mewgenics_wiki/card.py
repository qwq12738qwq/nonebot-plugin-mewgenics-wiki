from __future__ import annotations

import base64
import html
import re
from functools import lru_cache
from importlib.resources import files
from typing import Any

from jinja2 import Template
from markupsafe import Markup

from .config import CATEGORY_LABELS
from .data import CLASS_LABELS, WikiEntry, snapshot_version

TYPE_LABELS = {
    "melee": "近战",
    "magic": "魔法",
    "ranged": "远程",
    "movement": "移动",
    "spawn": "召唤",
    "heal": "治疗",
    "defense": "防御",
    "buff": "增益",
    "debuff": "减益",
    "attack": "攻击",
    "move": "移动",
    "misc": "杂项",
    "unknown": "未知",
}

KIND_LABELS = {
    "trinket": "饰品",
    "weapon": "武器",
    "neck": "颈部",
    "face": "面部",
    "head": "头部",
    "modifier": "修改器",
}

KIND_FOLDERS = {
    "trinket": "TrinketIcon",
    "weapon": "WeaponIcon",
    "neck": "NeckItemIcon",
    "face": "FaceItemIcon",
    "head": "HeadItemIcon",
}

RARITY_LABELS = {
    "common": "普通",
    "uncommon": "罕见",
    "rare": "稀有",
    "very_rare": "非常稀有",
    "quest": "任务",
    "sidequest": "支线任务",
}

DAMAGE_TYPE_LABELS = {
    "physical": "物理",
    "magic": "魔法",
    "heal": "治疗",
    "true": "真实",
}

FACTION_LABELS = {
    "enemies": "敌方",
    "allies": "友方",
    "none": "中立",
    "birds": "鸟类",
    "cavemen": "穴居人",
    "sabertooths": "剑齿虎",
    "mammoths": "猛犸",
    "third_party": "第三方",
    "solitary_enemies": "独行敌方",
    "kaiju1": "巨兽",
    "kaiju2": "巨兽",
}

STAT_LABELS = {
    "str": "力量",
    "dex": "敏捷",
    "int": "智力",
    "con": "体质",
    "cha": "魅力",
    "lck": "幸运",
    "spd": "速度",
    "shield": "护盾",
    "divine_shield": "神圣护盾",
    "strength": "力量",
    "dexterity": "敏捷",
    "constitution": "体质",
    "intelligence": "智力",
    "speed": "速度",
    "charisma": "魅力",
    "luck": "幸运",
}

STAT_ICONS = {
    "str": "str",
    "dex": "dex",
    "int": "int",
    "con": "constitution",
    "cha": "cha",
    "lck": "lck",
    "spd": "spd",
    "shield": "shield",
    "divine_shield": "divineshield",
    "strength": "str",
    "dexterity": "dex",
    "constitution": "constitution",
    "intelligence": "int",
    "speed": "spd",
    "charisma": "cha",
    "luck": "lck",
}

_STAT_ORDER = [
    "str",
    "dex",
    "int",
    "con",
    "cha",
    "lck",
    "spd",
    "shield",
    "divine_shield",
]

_CHAR_STAT_ORDER = [
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "speed",
    "charisma",
    "luck",
]

_DESCRIPTION_LABELS = {
    "ability": "基础",
    "passive": "基础",
}

_PLACEHOLDERS = {
    "{he}": "它",
    "{his}": "它的",
    "{him}": "它",
    "{they}": "它们",
    "{them}": "它们",
    "{their}": "它们的",
    "{it}": "它",
    "{its}": "它的",
    "{aux_cat_name}": "猫",
    "{buddyname}": "伙伴",
    "{v0}": "",
    "{SpawnedBy}": "",
    "{str_aux_item_desc}": "",
    "{str_aux_passive_name}": "",
    "{str_aux_passive_desc}": "",
    "{str_aux_active_name}": "",
    "{str_aux_active_desc}": "",
}


def _resource_text(*parts: str) -> str:
    return files(__package__).joinpath(*parts).read_text("utf-8")


@lru_cache(maxsize=1)
def _template() -> Template:
    return Template(_resource_text("templates", "card.html"), autoescape=True)


@lru_cache(maxsize=1)
def _css() -> str:
    font = files(__package__).joinpath("fonts", "NotoSansSC-card.woff2").read_bytes()
    font_b64 = base64.b64encode(font).decode("ascii")
    font_face = (
        "@font-face{font-family:'MewCard';"
        f"src:url(data:font/woff2;base64,{font_b64}) format('woff2');"
        "font-weight:400;font-style:normal;}"
    )
    return font_face + _resource_text("static", "card.css")


@lru_cache(maxsize=512)
def _asset_uri(relative: str) -> str | None:
    try:
        path = files(__package__).joinpath("assets", *relative.split("/"))
        if not path.is_file():
            return None
        data = path.read_bytes()
    except (FileNotFoundError, OSError):
        return None
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _img(relative: str, cls: str = "", alt: str = "") -> str:
    uri = _asset_uri(relative)
    if not uri:
        return ""
    return (
        f'<img class="{html.escape(cls)}" src="{uri}" '
        f'alt="{html.escape(alt)}">'
    )


def _badge(label: object, cls: str = "") -> str:
    if label is None or str(label).strip() == "":
        return ""
    return f'<span class="badge {html.escape(cls)}">{html.escape(str(label))}</span>'


def _tag(label: object) -> str:
    if label is None or str(label).strip() == "":
        return ""
    return f'<span class="tag">{html.escape(str(label))}</span>'


def _rich_text(text: str, aux: object = None) -> Markup:
    if not text:
        return Markup("")

    escaped = html.escape(str(text))
    if aux is not None and str(aux).strip():
        escaped = escaped.replace("{aux}", str(aux))

    for source, target in _PLACEHOLDERS.items():
        escaped = escaped.replace(source, target)
    escaped = escaped.replace("[img:{str_aux}]", "辅助")
    escaped = re.sub(r"\{[^{}]*\}", "", escaped)

    def inline_icon(match: re.Match[str]) -> str:
        name = match.group(1)
        mapped = {"con": "constitution"}.get(name, name)
        uri = _asset_uri(f"res/fonticon/{mapped}.png")
        if not uri:
            return html.escape(name)
        return (
            f'<img class="inline-icon" src="{uri}" '
            f'alt="{html.escape(name)}" title="{html.escape(name)}">'
        )

    escaped = re.sub(r"\[img:([^\]]+)\]", inline_icon, escaped)
    escaped = re.sub(r"\[s:[^\]]+\]([\s\S]*?)\[/s\]", r"<i>\1</i>", escaped)
    escaped = re.sub(r"\[b\]([\s\S]*?)\[/b\]", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\[(\d+\s+\d+)\]", r"<code>[\1]</code>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = escaped.replace("\r\n", "\n").replace("\n", "<br>")
    return Markup(escaped)


def _desc_block(label: str, text: str, aux: object = None) -> str:
    if not text:
        return ""
    label_html = f'<span class="desc-label">{html.escape(label)}</span>' if label else ""
    return (
        f'<div class="description">{label_html}'
        f"{_rich_text(text, aux=aux)}</div>"
    )


def _stat_chip(key: str, value: object, signed: bool = True) -> str:
    label = STAT_LABELS.get(key, key)
    icon = STAT_ICONS.get(key)
    icon_html = _img(f"res/fonticon/{icon}.png", alt=label) if icon else ""
    try:
        number = int(value)
        sign = "+" if signed and number > 0 else ""
        css = (
            ("positive" if number > 0 else ("negative" if number < 0 else ""))
            if signed
            else ""
        )
        shown = f"{sign}{number}"
    except (TypeError, ValueError):
        shown = str(value)
        css = ""
    return (
        f'<span class="stat {css}" title="{html.escape(label)}">'
        f"{html.escape(shown)}{icon_html}</span>"
    )


def _stats(
    stats: object, order: list[str] | None = None, signed: bool = True
) -> str:
    if not isinstance(stats, dict) or not stats:
        return ""
    keys = order or sorted(stats)
    chips = [
        _stat_chip(key, stats[key], signed=signed)
        for key in keys
        if key in stats and stats[key] is not None
    ]
    return "".join(chips)


def _level_stats(label: str, stats: object) -> str:
    chips = _stats(stats)
    if not chips:
        return ""
    return (
        f'<div class="stat-level"><div class="stat-level-label">'
        f'{html.escape(label)}</div><div class="stats">{chips}</div></div>'
    )


def _pool_text(pool: object) -> str:
    text = str(pool or "").strip()
    if text.startswith("file:"):
        text = text[5:]
    if text.endswith(".gon"):
        text = text[:-4]
    return text


def _pool_list(values: object, limit: int = 6) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if isinstance(value, dict):
            texts = value.get("tag_texts") or {}
            text = ""
            if isinstance(texts, dict):
                text = str(texts.get("zh") or texts.get("en") or "")
            text = text or _pool_text(value.get("tag"))
        else:
            text = _pool_text(value)
        if text and text not in result:
            result.append(text)
    if len(result) > limit:
        result = result[:limit] + [f"+{len(result) - limit}"]
    return result


def _tag_list(values: object, limit: int = 10) -> str:
    if not isinstance(values, list):
        return ""
    tags = []
    for value in values:
        text = str(value or "").strip()
        if not text or text.startswith("file:"):
            continue
        if text not in tags:
            tags.append(text)
    return "".join(_tag(text) for text in tags[:limit])


def _icon_box(category: str, raw: dict[str, Any]) -> str:
    if category == "ability":
        frame = raw.get("frame_number")
        image = _img(f"AbilityIcon/{frame}.png", alt="能力图标") if frame is not None else ""
    elif category == "passive":
        frame = raw.get("frame_number")
        image = _img(f"PassiveIcon/{frame}.png", alt="被动图标") if frame is not None else ""
    elif category == "item":
        frame = raw.get("frame")
        folder = KIND_FOLDERS.get(raw.get("kind") or "", "TrinketIcon")
        image = _img(f"{folder}/{frame}.png", alt="物品图标") if frame is not None else ""
        return f'<div class="icon-box item">{image}</div>'
    elif category == "character":
        image_path = str(raw.get("image_path") or "").lstrip("/")
        image = _img(image_path, "portrait", alt="角色头像") if image_path else ""
        if image:
            return f'<div class="icon-box portrait">{image}</div>'
        initial = CATEGORY_LABELS[category][:1]
        return (
            '<div class="icon-box portrait">'
            f'<span class="icon-placeholder">{initial}</span></div>'
        )
    elif category == "class":
        abilities = raw.get("abilities") or ()
        icon_entry = next(
            (
                item
                for item in abilities
                if item.raw.get("frame_number") is not None
            ),
            None,
        )
        if icon_entry is not None:
            image = _img(
                f"AbilityIcon/{icon_entry.raw['frame_number']}.png",
                alt="职业图标",
            )
            if image:
                return f'<div class="icon-box class">{image}</div>'
        initial = CATEGORY_LABELS[category][:1]
        return (
            '<div class="icon-box class">'
            f'<span class="icon-placeholder">{initial}</span></div>'
        )
    else:
        return '<div class="icon-box mutation"><span class="mutation-mark">突变</span></div>'

    if image:
        return f'<div class="icon-box {category}">{image}</div>'
    initial = CATEGORY_LABELS[category][:1]
    return (
        f'<div class="icon-box {category}">'
        f'<span class="icon-placeholder">{initial}</span></div>'
    )


def _rarity_badge(item: dict[str, Any]) -> str:
    rarity = item.get("rarity")
    if item.get("cursed"):
        return _badge("诅咒", "rarity-cursed")
    if not rarity:
        return _badge("未知稀有度")
    label = RARITY_LABELS.get(str(rarity), str(rarity))
    return _badge(label, f"rarity-{rarity}")


def _damage_value(value: object) -> str:
    text = str(value)
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return text
    match = re.match(r"^(-?\d+)", text)
    return f"{match.group(1)}+" if match else text


def _ability_card(entry: WikiEntry) -> dict[str, str]:
    raw = entry.raw
    badges = []
    if raw.get("type_icon"):
        badges.append(_badge(TYPE_LABELS.get(raw["type_icon"], raw["type_icon"]), "theme"))
    if raw.get("ability_class"):
        badges.append(
            _badge(CLASS_LABELS.get(raw["ability_class"], raw["ability_class"]))
        )

    stats = []
    cost = raw.get("cost") or {}
    if isinstance(cost, dict):
        for key, label in (("mana", "法力"), ("act_points", "行动"), ("move_points", "移动")):
            value = cost.get(key)
            if value:
                shown = STAT_LABELS.get(str(value), str(value))
                stats.append(
                    f'<span class="stat">{label} {html.escape(shown)}</span>'
                )
    damage = raw.get("damage") or {}
    if isinstance(damage, dict):
        value = damage.get("value")
        if value not in (None, "", 0, "0"):
            stats.append(
                f'<span class="stat">伤害 {html.escape(_damage_value(value))}</span>'
            )
        damage_type = damage.get("type")
        if damage_type:
            shown = DAMAGE_TYPE_LABELS.get(
                str(damage_type), str(damage_type)
            )
            stats.append(
                f'<span class="stat">{html.escape(shown)}</span>'
            )

    descs = []
    base = entry.description_zh or entry.description_en
    upgraded = _localized_texts(raw.get("description2_texts"))
    descs.append(_desc_block("基础" if upgraded and upgraded != base else "", base))
    if upgraded and upgraded != base:
        descs.append(_desc_block("升级", upgraded))

    tags = [
        str(tag) for tag in raw.get("tags") or [] if str(tag).strip()
    ]

    return {
        "title": entry.title,
        "subtitle": entry.subtitle,
        "badges_html": "".join(badges),
        "stats_html": "".join(stats),
        "desc_html": "".join(descs),
        "tags_html": "".join(_tag(tag) for tag in tags[:10]),
    }


def _passive_card(entry: WikiEntry) -> dict[str, str]:
    raw = entry.raw
    badges = []
    if raw.get("passive_class"):
        badges.append(
            _badge(CLASS_LABELS.get(raw["passive_class"], raw["passive_class"]), "theme")
        )

    levels = [
        ("基础", raw.get("stats_base")),
        ("1级", raw.get("stats_level1")),
        ("2级", raw.get("stats_level2")),
        ("1级升级", raw.get("stats_level1_upgraded")),
        ("2级升级", raw.get("stats_level2_upgraded")),
    ]
    stats_html = "".join(_level_stats(label, value) for label, value in levels)

    base = entry.description_zh or entry.description_en
    upgraded = _localized_texts(raw.get("description2_texts"))
    descs = [_desc_block("", base)]
    if upgraded and upgraded != base:
        descs.append(_desc_block("升级", upgraded))

    unlock = raw.get("unlock_requirements")
    if unlock:
        descs.append(_desc_block("解锁", _human_value(unlock)))

    return {
        "title": entry.title,
        "subtitle": entry.subtitle,
        "badges_html": "".join(badges),
        "stats_html": stats_html,
        "desc_html": "".join(descs),
        "tags_html": "",
    }


def _item_card(entry: WikiEntry) -> dict[str, str]:
    raw = entry.raw
    badges = []
    kind = raw.get("kind")
    if kind:
        badges.append(_badge(KIND_LABELS.get(kind, str(kind)), "theme"))
    badges.append(_rarity_badge(raw))
    if raw.get("is_consumable"):
        badges.append(_badge("消耗品"))
    if raw.get("durability") is not None:
        badges.append(_badge(f"耐久 {raw['durability']}"))
    if raw.get("aux") is not None:
        badges.append(_badge(f"附加 {raw['aux']}"))

    stats_html = _stats(raw.get("stats"), _STAT_ORDER)
    descs = [_desc_block("", entry.description_zh or entry.description_en)]
    if raw.get("cursed"):
        descs.append(_desc_block("", "这件物品被诅咒了。"))

    tags = list(raw.get("sets") or []) + _pool_list(raw.get("item_pools"))
    return {
        "title": entry.title,
        "subtitle": entry.subtitle,
        "badges_html": "".join(badges),
        "stats_html": stats_html,
        "desc_html": "".join(descs),
        "tags_html": "".join(_tag(tag) for tag in tags[:12]),
    }


def _mutation_card(entry: WikiEntry) -> dict[str, str]:
    raw = entry.raw
    part = _localized_texts(raw.get("part_label_texts"))
    badges = [_badge(part or "突变", "theme")]
    if raw.get("is_birth_defect"):
        badges.append(_badge(_localized_texts(raw.get("birth_defect_label_texts")) or "先天缺陷"))

    stats_html = _stats(raw.get("stats"), _STAT_ORDER)
    desc = entry.description_zh or entry.description_en
    descs = [_desc_block("", desc or "该突变没有文字描述。")]
    tags_html = _tag_list(raw.get("tags"))
    return {
        "title": entry.title,
        "subtitle": part,
        "badges_html": "".join(badges),
        "stats_html": stats_html,
        "desc_html": "".join(descs),
        "tags_html": tags_html,
    }


def _character_card(entry: WikiEntry) -> dict[str, str]:
    raw = entry.raw
    properties = raw.get("properties") or {}
    badges = []
    faction = raw.get("faction")
    if faction:
        badges.append(_badge(FACTION_LABELS.get(faction, str(faction)), "theme"))
    char_type = properties.get("type")
    if char_type:
        badges.append(_badge(str(char_type)))
    health = raw.get("health") or properties.get("health")
    if health is not None:
        badges.append(_badge(f"生命 {health}"))
    size = properties.get("size")
    if size:
        badges.append(_badge(f"体型 {size}"))
    movement = raw.get("movement") or properties.get("movement")
    if movement is not None:
        badges.append(_badge(f"移动 {movement}"))
    if raw.get("kill_required") is not None:
        badges.append(_badge(f"击杀 {raw['kill_required']}"))

    stats_html = _stats(raw.get("stats"), _CHAR_STAT_ORDER, signed=False)
    desc = entry.description_zh or entry.description_en
    descs = [_desc_block("", desc or "该角色没有文字介绍。")]
    return {
        "title": entry.title,
        "subtitle": entry.subtitle,
        "badges_html": "".join(badges),
        "stats_html": stats_html,
        "desc_html": "".join(descs),
        "tags_html": _tag_list(raw.get("tags")),
    }


def _entry_icon_uri(entry: WikiEntry) -> str | None:
    raw = entry.raw
    if entry.category == "ability":
        frame = raw.get("frame_number")
        if frame is not None:
            return _asset_uri(f"AbilityIcon/{frame}.png")
    if entry.category == "passive":
        frame = raw.get("frame_number")
        if frame is not None:
            return _asset_uri(f"PassiveIcon/{frame}.png")
    return None


def _class_preview_section(
    entries: tuple[WikiEntry, ...], limit: int = 18
) -> str:
    if not entries:
        return ""
    items = []
    for entry in entries[:limit]:
        uri = _entry_icon_uri(entry)
        if not uri:
            continue
        items.append(
            '<div class="preview-item">'
            f'<div class="preview-icon"><img src="{uri}" '
            f'alt="{html.escape(entry.title)}"></div>'
            f'<div class="preview-name">{html.escape(entry.title)}</div>'
            "</div>"
        )
    if not items:
        return ""
    note = ""
    if len(entries) > len(items):
        note = (
            f'<div class="more-note">还有 {len(entries) - len(items)} '
            "个能力未展示</div>"
        )
    return (
        '<div class="section">'
        '<div class="section-title">职业能力预览</div>'
        f'<div class="class-preview-grid">{"".join(items)}</div>'
        f"{note}</div>"
    )


def _class_meta(entry: WikiEntry) -> str:
    raw = entry.raw
    parts = []
    type_icon = raw.get("type_icon")
    if type_icon:
        parts.append(TYPE_LABELS.get(type_icon, str(type_icon)))
    cost = raw.get("cost") or {}
    if isinstance(cost, dict) and cost.get("mana"):
        mana = cost["mana"]
        parts.append(f"法力 {STAT_LABELS.get(str(mana), mana)}")
    return " · ".join(parts)


def _class_entries_section(
    title: str, entries: tuple[WikiEntry, ...], kind: str
) -> str:
    if not entries:
        return (
            '<div class="section">'
            f'<div class="section-title">{title}</div>'
            '<div class="empty-note">暂无</div></div>'
        )

    items = []
    for entry in entries:
        uri = _entry_icon_uri(entry)
        icon = (
            f'<div class="class-entry-icon"><img src="{uri}" '
            f'alt="{html.escape(entry.title)}"></div>'
            if uri
            else '<div class="class-entry-icon"></div>'
        )
        meta = _class_meta(entry) if kind == "ability" else ""
        meta_html = (
            f'<div class="class-entry-meta">{html.escape(meta)}</div>'
            if meta
            else ""
        )
        desc = entry.description_zh or entry.description_en
        desc_html = (
            f'<div class="class-entry-desc">{_rich_text(desc)}</div>'
            if desc
            else ""
        )
        items.append(
            f'<div class="class-entry">{icon}'
            '<div class="class-entry-body">'
            f'<div class="class-entry-title">{html.escape(entry.title)}</div>'
            f"{meta_html}{desc_html}</div></div>"
        )

    return (
        '<div class="section">'
        f'<div class="section-title">{title}（{len(entries)}）</div>'
        f'<div class="class-grid">{"".join(items)}</div></div>'
    )


def _class_card(entry: WikiEntry) -> dict[str, str]:
    raw = entry.raw
    passives = tuple(raw.get("passives") or ())
    abilities = tuple(raw.get("abilities") or ())
    preview = tuple(raw.get("preview") or ())

    badges = [
        _badge(f"{len(passives)} 个被动"),
        _badge(f"{len(abilities)} 个能力"),
    ]
    body = "".join(
        [
            _class_preview_section(preview),
            _class_entries_section("被动", passives, "passive"),
            _class_entries_section("能力", abilities, "ability"),
        ]
    )
    return {
        "title": entry.title,
        "subtitle": entry.subtitle,
        "badges_html": "".join(badges),
        "stats_html": "",
        "desc_html": "",
        "tags_html": "",
        "body_html": body,
    }


_CARD_BUILDERS = {
    "ability": _ability_card,
    "passive": _passive_card,
    "item": _item_card,
    "mutation": _mutation_card,
    "character": _character_card,
    "class": _class_card,
}


def _localized_texts(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    return str(value.get("zh") or value.get("en") or "")


def _human_value(value: object) -> str:
    if isinstance(value, dict):
        parts = [str(item) for item in value.values() if item not in (None, "", [])]
        return " / ".join(parts)
    if isinstance(value, list):
        return " / ".join(str(item) for item in value if item not in (None, ""))
    return str(value)


def build_card(category: str, entry: WikiEntry) -> str:
    data = _CARD_BUILDERS[category](entry)
    version = snapshot_version()
    return _template().render(
        css=Markup(_css()),
        category=category,
        eyebrow=f"Mewgenics Wiki · {CATEGORY_LABELS[category]}",
        icon_html=Markup(_icon_box(category, entry.raw)),
        title=data["title"],
        subtitle=data["subtitle"],
        badges_html=Markup(data["badges_html"]),
        stats_html=Markup(data["stats_html"]),
        desc_html=Markup(data["desc_html"]),
        tags_html=Markup(data["tags_html"]),
        body_html=Markup(data.get("body_html", "")),
        footer_left=f"Mewgenics Wiki · VersionDate {version}",
        footer_right="By: qwq12738qwq·THNEden 数据来源: mewcodex.pages.dev",
    )
