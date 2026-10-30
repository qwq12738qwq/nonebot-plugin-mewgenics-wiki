import asyncio

import nonebot
import pytest

nonebot.init(driver="~none")
nonebot.load_plugin("nonebot_plugin_mewgenics_wiki")

_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)


@pytest.fixture(scope="session")
def event_loop():
    yield _loop
