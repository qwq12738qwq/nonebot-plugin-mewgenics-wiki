from pydantic import BaseModel, Field


class Config(BaseModel):
    mewgenics_wiki_card_width: int = Field(default=1200, ge=600)
    mewgenics_wiki_device_pixel_ratio: float = Field(default=1.0, ge=1.0, le=4.0)
    mewgenics_wiki_max_results: int = Field(default=3, ge=1, le=10)
    mewgenics_wiki_fuzzy_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    mewgenics_wiki_cache_cards: bool = True
    mewgenics_wiki_render_timeout: int = Field(default=30, ge=5)


# 命令触发词 → 图鉴分类
COMMAND_TRIGGERS: list[tuple[str, str]] = [
    ("查能力", "ability"),    # 查能力：生成能力卡片
    ("查被动", "passive"),    # 查被动：生成被动卡片
    ("查物品", "item"),       # 查物品：生成物品卡片
    ("查突变", "mutation"),   # 查突变：生成突变卡片
    ("查角色", "character"),  # 查角色：生成角色卡片
    ("查职业", "class"),      # 查职业：生成职业长图
]

# 分类 → 中文名
CATEGORY_LABELS: dict[str, str] = {
    "ability": "能力",
    "passive": "被动",
    "item": "物品",
    "mutation": "突变",
    "character": "角色",
    "class": "职业",
}

# 分类 → 用法示例
CATEGORY_EXAMPLES: dict[str, str] = {
    "ability": "跳跃",
    "passive": "吸血",
    "item": "剑齿虎",
    "mutation": "击退",
    "character": "猫",
    "class": "坦克",
}
