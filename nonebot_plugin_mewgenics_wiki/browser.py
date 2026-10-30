from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from nonebot.log import logger
from nonebot_plugin_localstore import get_plugin_cache_file
from playwright.async_api import (
    Browser,
    Error as PlaywrightError,
    Page,
    Playwright,
    async_playwright,
)

from .config import CATEGORY_PAGES, Config

_HIDE_OVERLAYS_CSS = """
#announcementModal,
.announcement-button,
#imageModal {
    display: none !important;
}
"""

_NAME_CELL_SELECTORS = {
    "ability": ".ability-name",
    "passive": ".passive-name",
    "item": ".item-name",
    "mutation": ".mutation-name",
    "character": ".character-name",
}

_COLLECT_ROWS = """
(selector) => [...document.querySelectorAll('#tableBody tr')]
    .map((tr, index) => ({ tr, index }))
    .filter(({ tr }) =>
        tr.getClientRects().length > 0 && !tr.querySelector('td.no-results')
    )
    .map(({ tr, index }) => {
        const cell = tr.querySelector(selector);
        return {
            index,
            name: cell ? (cell.textContent || '').trim() : '',
        };
    });
"""


class EntryNotFound(LookupError):
    def __init__(self, query: str, debug_path: Optional[Path] = None) -> None:
        super().__init__(query)
        self.query = query
        self.debug_path = debug_path


class BrowserManager:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._launch_lock: Optional[asyncio.Lock] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _ensure_primitives(self) -> None:
        if self._launch_lock is None:
            self._launch_lock = asyncio.Lock()
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(
                max(1, self._config.mewcodex_max_concurrency)
            )

    async def _get_browser(self) -> Browser:
        self._ensure_primitives()
        assert self._launch_lock is not None

        async with self._launch_lock:
            if self._browser is not None and self._browser.is_connected():
                return self._browser

            if self._playwright is None:
                self._playwright = await async_playwright().start()

            self._browser = await self._playwright.chromium.launch(
                headless=self._config.mewcodex_headless,
                args=self._config.mewcodex_browser_args or None,
            )
            logger.debug("Mewcodex: Chromium 已启动")
            return self._browser

    async def screenshot_row(self, category: str, query: str) -> Path:
        self._ensure_primitives()
        assert self._semaphore is not None

        page_path = CATEGORY_PAGES[category]
        url = (
            f"{self._config.mewcodex_base_url.rstrip('/')}/{page_path}?lang=zh"
        )
        timeout_ms = self._config.mewcodex_timeout * 1000

        async with self._semaphore:
            browser = await self._get_browser()
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                locale="zh-CN",
            )
            try:
                page = await context.new_page()
                await page.goto(
                    url, wait_until="networkidle", timeout=timeout_ms
                )
                await page.add_style_tag(content=_HIDE_OVERLAYS_CSS)
                await page.wait_for_function(
                    "() => [...document.querySelectorAll('#tableBody tr')]"
                    ".some(tr => !tr.querySelector('td.no-results'))",
                    timeout=timeout_ms,
                )

                search_input = page.locator("#searchInput")
                await search_input.fill(query)
                await page.wait_for_timeout(self._config.mewcodex_settle_ms)

                infos = await page.evaluate(
                    _COLLECT_ROWS, _NAME_CELL_SELECTORS[category]
                )
                if not infos:
                    debug_path = await self._capture_debug(page)
                    raise EntryNotFound(query, debug_path)

                index = self._pick_row_index(infos, query)
                target = get_plugin_cache_file(f"{uuid.uuid4().hex}.png")
                await page.locator("#tableBody tr").nth(index).screenshot(
                    path=str(target)
                )
                return target
            finally:
                await context.close()

    def _pick_row_index(self, infos: list[dict], query: str) -> int:
        needle = query.casefold()

        for info in infos:
            if str(info["name"]).casefold() == needle:
                return int(info["index"])
        for info in infos:
            if needle in str(info["name"]).casefold():
                return int(info["index"])
        return int(infos[0]["index"])

    async def _capture_debug(self, page: Page) -> Optional[Path]:
        if not self._config.mewcodex_debug_screenshot:
            return None

        debug_path = get_plugin_cache_file(
            f"debug_{uuid.uuid4().hex}.png"
        )
        try:
            await page.screenshot(path=str(debug_path))
            return debug_path
        except PlaywrightError as exc:
            logger.warning(f"Mewcodex: 调试截图失败: {exc}")
            return None

    async def close(self) -> None:
        self._ensure_primitives()
        assert self._launch_lock is not None

        async with self._launch_lock:
            if self._browser is not None:
                try:
                    await self._browser.close()
                except PlaywrightError as exc:
                    logger.warning(f"Mewcodex: 关闭浏览器失败: {exc}")
                self._browser = None

            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except PlaywrightError as exc:
                    logger.warning(f"Mewcodex: 停止 Playwright 失败: {exc}")
                self._playwright = None
