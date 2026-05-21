"""Adaptive rate limiter for Xiaohongshu API requests."""

import asyncio
import random
import time
from typing import Optional


class RateLimiter:
    """Adaptive rate limiter with exponential backoff on errors.

    Starts with a default delay between requests and automatically
    increases delay when errors (CAPTCHAs, 429s) are detected.
    """

    def __init__(self, min_delay: float = 3.0, max_delay: float = 60.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._current_delay = min_delay
        self._last_request_time: float = 0
        self._consecutive_errors = 0

    async def wait(self):
        """Wait appropriate time before next request."""
        if self._last_request_time == 0:
            self._last_request_time = time.time()
            return

        elapsed = time.time() - self._last_request_time
        # Add random jitter (±30%)
        jitter = random.uniform(0.7, 1.3)
        delay = self._current_delay * jitter

        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)

        self._last_request_time = time.time()

    def report_success(self):
        """Report a successful request — gradually decrease delay."""
        self._consecutive_errors = 0
        # Slowly recover towards min_delay
        self._current_delay = max(
            self.min_delay, self._current_delay * 0.9
        )

    def report_error(self, is_captcha: bool = False):
        """Report a failed request — increase delay."""
        self._consecutive_errors += 1

        if is_captcha:
            # CAPTCHA: aggressively back off
            self._current_delay = min(
                self.max_delay, self._current_delay * 3
            )
        else:
            # Other errors: moderate backoff
            self._current_delay = min(
                self.max_delay, self._current_delay * 1.5
            )

    @property
    def current_delay(self) -> float:
        return self._current_delay

    async def reset(self):
        """Reset to minimum delay."""
        self._current_delay = self.min_delay
        self._consecutive_errors = 0
