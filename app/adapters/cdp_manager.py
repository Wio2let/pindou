"""CDP (Chrome DevTools Protocol) browser connection management."""

from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext

from app.config import settings


class CDPManager:
    """Manages connection to a Chrome browser via CDP.

    Connects to an existing Chrome instance with --remote-debugging-port=9222,
    and uses the default browser context so cookies from the user's
    manual login are immediately available.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or settings.chrome_host
        self.port = port or settings.chrome_port
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._browser is not None

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context

    async def connect(self) -> BrowserContext:
        """Connect to Chrome via CDP and use the default browser context.

        Using the default context means cookies from the user's manual
        login to xiaohongshu.com are immediately available to our crawler.
        """
        if self.is_connected:
            return self._context

        self._playwright = await async_playwright().start()

        cdp_url = f"http://{self.host}:{self.port}"

        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Chrome at {cdp_url}. "
                f"Make sure Chrome is running with --remote-debugging-port={self.port}. "
                f"Error: {e}"
            )

        # Use the browser's DEFAULT context so we get the user's existing cookies
        contexts = self._browser.contexts
        if contexts:
            self._context = contexts[0]
        else:
            # Fallback: create a new context
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )

        self._connected = True
        return self._context

    async def disconnect(self):
        """Clean up resources. Note: does NOT close the default context."""
        self._context = None
        self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._connected = False

    async def ensure_connected(self) -> BrowserContext:
        """Reconnect if needed."""
        if not self.is_connected:
            return await self.connect()
        return self._context
