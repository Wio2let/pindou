"""Cookie/session state persistence manager."""

import json
import os
import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import BrowserContext

from app.config import settings


class CookieManager:
    """Manages Xiaohongshu login cookie persistence.

    Stores cookies to disk so login survives restarts.
    Works with Playwright CDP-connected browser contexts.
    """

    def __init__(self, cookie_dir: Optional[str] = None):
        self.cookie_dir = Path(cookie_dir or settings.cookie_dir)
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        self._cookie_file = self.cookie_dir / "xhs_cookies.json"

    @property
    def has_cookies(self) -> bool:
        return self._cookie_file.exists()

    async def save(self, context: BrowserContext):
        """Save current browser context cookies to disk."""
        cookies = await context.cookies()
        self._cookie_file.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))

    async def load(self, context: BrowserContext) -> bool:
        """Load cookies from disk into browser context."""
        if not self.has_cookies:
            return False
        try:
            cookies = json.loads(self._cookie_file.read_text())
            if cookies:
                await context.add_cookies(cookies)
                return True
        except (json.JSONDecodeError, OSError):
            return False
        return False

    async def verify_login(self, context: BrowserContext) -> bool:
        """Verify that the current context has valid Xiaohongshu cookies.

        Checks for the presence of key cookies without navigating.
        """
        try:
            cookies = await context.cookies(urls=["https://www.xiaohongshu.com"])
            cookie_names = {c["name"] for c in cookies}
            # web_session + a1 are the key login/signing cookies
            return "web_session" in cookie_names and "a1" in cookie_names
        except Exception:
            return False

    def clear(self):
        """Remove stored cookies."""
        if self._cookie_file.exists():
            self._cookie_file.unlink()

    async def wait_for_login(
        self, context: BrowserContext, timeout: int = 120
    ) -> bool:
        """Show QR code and wait for user to scan it.

        Opens a headed page to xiaohongshu.com/login, shows QR code,
        and polls until login completes or timeout.
        """
        page = await context.new_page()
        await page.goto(
            "https://www.xiaohongshu.com/login",
            wait_until="domcontentloaded",
        )

        # Wait for the cookies to include `web_session` (login indicator)
        elapsed = 0
        poll_interval = 2
        while elapsed < timeout:
            cookies = await context.cookies()
            for cookie in cookies:
                if cookie.get("name") == "web_session":
                    # User scanned QR code and logged in
                    await self.save(context)
                    await page.close()
                    return True
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        await page.close()
        return False
