from nonebot_plugin_mewgenics_wiki.data import (
    is_exact_match,
    load_category,
    search,
)


def test_categories_are_loaded():
    for category in ("ability", "passive", "item", "mutation", "character"):
        assert load_category(category)


def test_exact_item_name_wins():
    results = search("item", "边角金属帽子", 3)
    assert results
    assert results[0].title == "边角金属帽子"


def test_exact_passive_name_wins():
    results = search("passive", "腐化", 3)
    assert results
    assert results[0].title == "腐化"


def test_description_search():
    assert search("mutation", "击退", 3)
    assert search("character", "猫", 3)


def test_class_search():
    results = search("class", "坦克", 3)
    assert results
    assert results[0].code == "Tank"
    assert search("class", "Necromancer", 3)[0].code == "Necromancer"


def test_class_exact_and_fuzzy():
    mage = search("class", "法师", 1)[0]
    assert mage.code == "Mage"
    assert is_exact_match(mage, "法师")
    assert not is_exact_match(mage, "法")

    necromancer = search("class", "亡灵法师", 1)[0]
    assert necromancer.code == "Necromancer"
    assert not is_exact_match(necromancer, "亡灵法师")

    exact_necro = search("class", "死灵法师", 1)[0]
    assert exact_necro.code == "Necromancer"
    assert is_exact_match(exact_necro, "死灵法师")


def test_missing_query():
    assert search("ability", "绝对不存在的词条xyz", 3) == []
