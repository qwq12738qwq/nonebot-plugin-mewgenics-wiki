from nonebot_plugin_mewgenics_wiki.data import load_category, search


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


def test_missing_query():
    assert search("ability", "绝对不存在的词条xyz", 3) == []
