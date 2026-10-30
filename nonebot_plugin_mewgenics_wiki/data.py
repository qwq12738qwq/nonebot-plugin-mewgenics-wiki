from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

DATA_FILES = {
    "ability": "abilities_combined.json",
    "passive": "passives_combined.json",
    "item": "items_db.json",
    "mutation": "mutations_combined.json",
    "character": "characters_db.json",
}

CLASS_LABELS = {
    "Fighter": "战士",
    "Thief": "盗贼",
    "Tank": "坦克",
    "Mage": "法师",
    "Medic": "牧师",
    "Hunter": "猎人",
    "Necromancer": "死灵法师",
    "Butcher": "屠夫",
    "Monk": "武僧",
    "Druid": "德鲁伊",
    "Psychic": "灵能者",
    "Tinkerer": "工匠",
    "Jester": "小丑",
    "Colorless": "无项圈",
}


@dataclass(frozen=True)
class WikiEntry:
    category: str
    code: str
    name_zh: str
    name_en: str
    description_zh: str
    description_en: str
    raw: dict[str, Any]
    search_text: str

    @property
    def title(self) -> str:
        return self.name_zh or self.name_en or self.code

    @property
    def subtitle(self) -> str:
        return self.name_en if self.name_en and self.name_en != self.title else ""


def _texts(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(text) for key, text in value.items() if text}


def _localized(texts: object, fallback: object = "") -> str:
    values = _texts(texts)
    return values.get("zh") or values.get("en") or (str(fallback) if fallback else "")


def _resource_json(*parts: str) -> Any:
    with files(__package__).joinpath(*parts).open("rb") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def get_manifest() -> dict[str, Any]:
    try:
        return _resource_json("manifest.json")
    except (FileNotFoundError, ValueError):
        return {"snapshot_version": "unknown", "generated_at": ""}


def snapshot_version() -> str:
    return str(get_manifest().get("snapshot_version") or "unknown")


@lru_cache(maxsize=1)
def snapshot_cache_key() -> str:
    manifest = get_manifest()
    raw = f"{manifest.get('snapshot_version')}|{manifest.get('generated_at')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _ability_entry(raw: dict[str, Any]) -> WikiEntry | None:
    if raw.get("frame_number") is None:
        return None
    name_zh = _localized(raw.get("ability_name_texts"), raw.get("ability_name"))
    name_en = _texts(raw.get("ability_name_texts")).get("en") or str(
        raw.get("ability_name") or ""
    )
    if not (name_zh or name_en):
        return None
    desc_zh = _localized(raw.get("description_texts"), raw.get("description"))
    desc_en = _texts(raw.get("description_texts")).get("en") or str(
        raw.get("description") or ""
    )
    parts = [
        name_zh,
        name_en,
        str(raw.get("ability_code") or ""),
        desc_zh,
        desc_en,
        str(raw.get("ability_class") or ""),
        str(raw.get("type_icon") or ""),
        " ".join(str(tag) for tag in raw.get("tags") or []),
        " ".join(str(pool) for pool in raw.get("ability_pools") or []),
    ]
    return WikiEntry(
        "ability",
        str(raw.get("ability_code") or ""),
        name_zh,
        name_en,
        desc_zh,
        desc_en,
        raw,
        "\n".join(part for part in parts if part).casefold(),
    )


def _passive_entry(raw: dict[str, Any]) -> WikiEntry | None:
    name_zh = _localized(raw.get("passive_name_texts"), raw.get("passive_name"))
    name_en = _texts(raw.get("passive_name_texts")).get("en") or str(
        raw.get("passive_name") or ""
    )
    if not (name_zh or name_en):
        return None
    desc_zh = _localized(raw.get("description_texts"), raw.get("description"))
    desc_en = _texts(raw.get("description_texts")).get("en") or str(
        raw.get("description") or ""
    )
    parts = [
        name_zh,
        name_en,
        str(raw.get("passive_code") or ""),
        desc_zh,
        desc_en,
        _localized(raw.get("description2_texts"), raw.get("description_2")),
        str(raw.get("passive_class") or ""),
        " ".join(str(pool) for pool in raw.get("passive_pools") or []),
    ]
    return WikiEntry(
        "passive",
        str(raw.get("passive_code") or ""),
        name_zh,
        name_en,
        desc_zh,
        desc_en,
        raw,
        "\n".join(part for part in parts if part).casefold(),
    )


def _item_entry(raw: dict[str, Any]) -> WikiEntry | None:
    name_zh = _localized(raw.get("item_name_texts"), raw.get("item_name"))
    name_en = _texts(raw.get("item_name_texts")).get("en") or str(
        raw.get("item_name") or ""
    )
    if not (name_zh or name_en):
        return None
    desc_zh = _localized(raw.get("description_texts"), raw.get("description"))
    desc_en = _texts(raw.get("description_texts")).get("en") or str(
        raw.get("description") or ""
    )
    pool_texts = []
    for pool in raw.get("item_pools") or []:
        if isinstance(pool, dict):
            pool_texts.append(_localized(pool.get("tag_texts"), pool.get("tag")))
        else:
            pool_texts.append(str(pool))
    parts = [
        name_zh,
        name_en,
        str(raw.get("item_code") or ""),
        desc_zh,
        desc_en,
        str(raw.get("kind") or ""),
        str(raw.get("rarity") or ""),
        " ".join(str(value) for value in raw.get("sets") or []),
        " ".join(pool_texts),
    ]
    return WikiEntry(
        "item",
        str(raw.get("item_code") or ""),
        name_zh,
        name_en,
        desc_zh,
        desc_en,
        raw,
        "\n".join(part for part in parts if part).casefold(),
    )


def _mutation_entry(raw: dict[str, Any]) -> WikiEntry | None:
    name_en = str(raw.get("display_name") or "")
    if not name_en:
        return None
    part_zh = _localized(raw.get("part_label_texts"))
    desc_zh = _localized(raw.get("description_texts"))
    desc_en = _texts(raw.get("description_texts")).get("en") or ""
    parts = [
        name_en,
        str(raw.get("raw_comment") or ""),
        part_zh,
        _localized(raw.get("birth_defect_label_texts")),
        desc_zh,
        desc_en,
        " ".join(str(tag) for tag in raw.get("tags") or []),
    ]
    return WikiEntry(
        "mutation",
        str(raw.get("mutation_id") or ""),
        "",
        name_en,
        desc_zh,
        desc_en,
        raw,
        "\n".join(part for part in parts if part).casefold(),
    )


def _character_entry(raw: dict[str, Any]) -> WikiEntry | None:
    name_zh = _localized(raw.get("name_texts"), raw.get("character_key"))
    name_en = _texts(raw.get("name_texts")).get("en") or str(
        raw.get("character_key") or ""
    )
    if not (name_zh or name_en):
        return None
    desc_zh = _localized(raw.get("tooltip_texts"))
    desc_en = _texts(raw.get("tooltip_texts")).get("en") or ""
    parts = [
        name_zh,
        name_en,
        str(raw.get("character_key") or ""),
        desc_zh,
        desc_en,
        str(raw.get("faction") or ""),
        " ".join(str(tag) for tag in raw.get("tags") or []),
        str((raw.get("properties") or {}).get("type") or ""),
    ]
    return WikiEntry(
        "character",
        str(raw.get("character_key") or ""),
        name_zh,
        name_en,
        desc_zh,
        desc_en,
        raw,
        "\n".join(part for part in parts if part).casefold(),
    )


_ENTRY_BUILDERS = {
    "ability": _ability_entry,
    "passive": _passive_entry,
    "item": _item_entry,
    "mutation": _mutation_entry,
    "character": _character_entry,
}


def _dedupe_key(entry: WikiEntry) -> tuple:
    raw = entry.raw
    return (
        entry.name_zh or entry.name_en,
        entry.description_zh or entry.description_en,
        raw.get("kind"),
        raw.get("rarity"),
        raw.get("faction"),
        repr(raw.get("stats")),
    )


def _is_special_class_ability(entry: WikiEntry) -> bool:
    pools = [str(pool) for pool in entry.raw.get("ability_pools") or []]
    return any(
        pool.startswith(("file:special_enemy_abilities", "file:item_abilities"))
        for pool in pools
    )


@lru_cache(maxsize=1)
def load_classes() -> tuple[WikiEntry, ...]:
    passives = load_category("passive")
    abilities = load_category("ability")

    class_names = sorted(
        {
            str(entry.raw.get("passive_class"))
            for entry in passives
            if entry.raw.get("passive_class")
        }
        | {
            str(entry.raw.get("ability_class"))
            for entry in abilities
            if entry.raw.get("ability_class")
        }
    )

    classes: list[WikiEntry] = []
    for class_name in class_names:
        class_passives = tuple(
            entry
            for entry in passives
            if entry.raw.get("passive_class") == class_name
        )
        class_abilities = tuple(
            entry
            for entry in abilities
            if entry.raw.get("ability_class") == class_name
            and not _is_special_class_ability(entry)
        )

        label = CLASS_LABELS.get(class_name, class_name)
        classes.append(
            WikiEntry(
                "class",
                class_name,
                label,
                class_name,
                "",
                "",
                {
                    "class": class_name,
                    "passives": class_passives,
                    "abilities": class_abilities,
                },
                f"{label}\n{class_name}\n职业".casefold(),
            )
        )
    return tuple(classes)


@lru_cache(maxsize=None)
def load_category(category: str) -> tuple[WikiEntry, ...]:
    if category == "class":
        return load_classes()

    filename = DATA_FILES[category]
    payload = _resource_json("data", filename)
    if isinstance(payload, list):
        items = payload
    else:
        key = {
            "ability": "abilities",
            "passive": "passives",
            "item": "items",
            "mutation": "mutations",
            "character": "characters",
        }[category]
        items = payload.get(key) or []

    builder = _ENTRY_BUILDERS[category]
    entries: list[WikiEntry] = []
    seen: set[tuple] = set()
    for raw in items:
        entry = builder(raw)
        if entry is None:
            continue
        key = _dedupe_key(entry)
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return tuple(entries)


def _score(entry: WikiEntry, query: str) -> int | None:
    names = [
        name.casefold()
        for name in (entry.name_zh, entry.name_en)
        if name
    ]
    code = entry.code.casefold()

    if query in names:
        return 0
    if any(name.startswith(query) for name in names):
        return 1
    if query == code:
        return 1
    if any(query in name for name in names):
        return 2
    if query and query in code:
        return 3
    if query and query in entry.search_text:
        return 4
    return None


def search(category: str, query: str, limit: int = 3) -> list[WikiEntry]:
    needle = query.strip().casefold()
    if not needle:
        return []

    scored = []
    for index, entry in enumerate(load_category(category)):
        score = _score(entry, needle)
        if score is not None:
            scored.append((score, len(entry.title), index, entry))

    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in scored[:limit]]
