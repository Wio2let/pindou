"""Playwright adapter — intercepts API responses from page navigation.

Instead of making API calls ourselves or parsing __INITIAL_STATE__,
we navigate the page normally and intercept the actual API responses
using Playwright's route/response interception.

This is the most reliable approach — the page's own JavaScript makes
all API calls with correct signing, and we just capture the results.
"""

import json
import logging
import asyncio
import time
from typing import Optional
from urllib.parse import quote


_PUBLISH_WINDOW_SECONDS = {
    0: None,           # any
    1: 86400,          # 24h
    2: 604800,         # 7d
    3: 2592000,        # 30d
    4: 15552000,       # 180d
}

from playwright.async_api import BrowserContext, Page

from app.adapters.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# API endpoints we want to intercept
SEARCH_API_PATH = "/api/sns/web/v1/search/notes"
FEED_API_PATH = "/api/sns/web/v1/feed"
COMMENT_API_PATH = "/api/sns/web/v2/comment/page"

# Text fragments shown by XHS' "please scan QR in app" block page
BLOCK_PAGE_HINTS = (
    "当前笔记暂时无法浏览",
    "请打开小红书",
    "扫码查看",
    "登录后查看",
)


def _parse_count(v) -> int:
    """XHS returns interact counts as strings like '1.2万' / '8888' / ''.

    Turn them into plain ints. Returns 0 on anything unparseable.
    """
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip()
    if not s:
        return 0
    try:
        if s.endswith("万"):
            return int(float(s[:-1]) * 10_000)
        if s.endswith("亿"):
            return int(float(s[:-1]) * 100_000_000)
        # Some responses use '万+' for >10k buckets.
        if s.endswith("万+"):
            return int(float(s[:-2]) * 10_000)
        return int(float(s.replace(",", "")))
    except (ValueError, TypeError):
        return 0


def _extract_image_url(img: dict) -> str:
    """Pull a usable image URL out of an XHS image_list item.

    Search responses prefer `url_default`; older shapes have plain `url`;
    some have an `info_list` array per resolution.
    """
    if not isinstance(img, dict):
        return ""
    for key in ("url_default", "url_pre", "url"):
        u = img.get(key)
        if u:
            return u
    info_list = img.get("info_list") or []
    if info_list and isinstance(info_list, list):
        return info_list[0].get("url", "") or ""
    return ""


def _build_note_url(note_id: str, xsec_token: str = "",
                    xsec_source: str = "pc_search") -> str:
    """Build a note URL that XHS will actually render for a logged-in PC user.

    Without xsec_token/xsec_source the page shows the "open app & scan QR"
    block popup — even when web_session cookies are valid.
    """
    base = f"https://www.xiaohongshu.com/explore/{note_id}"
    if not xsec_token:
        return base
    return (
        f"{base}?xsec_token={quote(xsec_token, safe='')}"
        f"&xsec_source={quote(xsec_source or 'pc_search', safe='')}"
    )


class MediaCrawlerAdapter:
    """Playwright adapter — intercepts real API responses from page navigation."""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter(min_delay=5.0)
        self._page: Optional[Page] = None
        self._initialized = False
        self._captured_data = []

    async def initialize(self, context: BrowserContext):
        self._page = await context.new_page()
        # Force desktop viewport and user-agent
        await self._page.set_viewport_size({"width": 1440, "height": 900})
        self._ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        await self._page.set_extra_http_headers({"User-Agent": self._ua})
        self._initialized = True
        logger.info("Adapter initialized (desktop mode)")

    async def _set_headers(self, referer: Optional[str] = None):
        """set_extra_http_headers replaces — always include UA when we set Referer."""
        if not self._page:
            return
        headers = {"User-Agent": getattr(self, "_ua", "")}
        if referer:
            headers["Referer"] = referer
        await self._page.set_extra_http_headers(headers)

    async def ensure_logged_in(self) -> bool:
        if not self._page:
            return False
        try:
            # Check cookies directly — far more reliable than URL sniffing.
            cookies = await self._page.context.cookies(
                urls=["https://www.xiaohongshu.com"]
            )
            names = {c["name"] for c in cookies}
            has_session = "web_session" in names
            has_a1 = "a1" in names
            if not (has_session and has_a1):
                logger.warning(
                    f"Login cookies missing — web_session={has_session}, "
                    f"a1={has_a1}. The CDP-attached Chrome must be logged in "
                    f"to xiaohongshu.com."
                )
                return False

            # Warm up the page so subsequent navigations have proper referer.
            await self._page.goto(
                "https://www.xiaohongshu.com/explore",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await self._page.wait_for_timeout(1500)
            if "login" in self._page.url.lower():
                return False
            return True
        except Exception as e:
            logger.warning(f"ensure_logged_in failed: {e}")
            return False

    async def _page_is_blocked(self) -> bool:
        """Detect XHS' 'open app & scan QR' interstitial."""
        if not self._page:
            return False
        try:
            text = await self._page.evaluate(
                "document.body?.innerText?.slice(0, 2000) || ''"
            )
            return any(h in text for h in BLOCK_PAGE_HINTS)
        except Exception:
            return False

    async def search_posts(self, keyword: str, sort: str = "general",
                            note_type: int = 0, max_count: int = 20,
                            publish_time_type: int = 0) -> list[dict]:
        """Navigate to search page and intercept the search API response."""
        if not self._page:
            raise RuntimeError("Adapter not initialized")

        await self.rate_limiter.wait()

        # URL-encode keyword so Chinese / spaces don't break the request.
        search_url = (
            f"https://www.xiaohongshu.com/search_result"
            f"?keyword={quote(keyword, safe='')}&source=web_explore_feed"
        )

        captured = []
        requests_log = []

        async def on_request(request):
            """Log all XHR/fetch requests."""
            url = request.url
            if "edith.xiaohongshu.com" in url or "api" in url.lower():
                requests_log.append(f"[{request.method}] {url}")

        async def on_response(response):
            """Capture search API responses."""
            url = response.url
            if "edith.xiaohongshu.com" in url or "api/sns" in url:
                try:
                    data = await response.json()
                    status = response.status
                    success = data.get("success", "?")
                    code = data.get("code", "?")
                    requests_log.append(f"[{response.status}] {url} → success={success} code={code}")
                except Exception:
                    requests_log.append(f"[{response.status}] {url} (not json)")

            if SEARCH_API_PATH in url:
                try:
                    data = await response.json()
                    if data.get("success"):
                        captured.append(data["data"])
                except Exception:
                    pass

        self._page.on("request", on_request)
        self._page.on("response", on_response)

        try:
            await self._page.goto(search_url, wait_until="domcontentloaded",
                                  timeout=30000)
            # Wait for at least one search API response to be intercepted,
            # then give a small grace period for additional pages of results.
            for _ in range(20):  # up to ~10s
                if captured:
                    break
                await self._page.wait_for_timeout(500)
            # Light scroll to trigger lazy-loaded feed items.
            try:
                await self._page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight * 0.6)"
                )
            except Exception:
                pass
            await self._page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning(f"Page load issue: {e}")

        self._page.remove_listener("request", on_request)
        self._page.remove_listener("response", on_response)

        logger.info(f"=== Intercepted {len(requests_log)} API calls ===")
        for line in requests_log[:30]:
            logger.info(f"  {line}")
        if len(requests_log) > 30:
            logger.info(f"  ... and {len(requests_log) - 30} more")

        page_title = await self._page.title()
        page_url = self._page.url
        page_text = await self._page.evaluate(
            "document.body?.innerText?.slice(0, 1000) || 'NO BODY'"
        )
        logger.info(f"Page title: {page_title}")
        logger.info(f"Page URL: {page_url}")
        logger.info(f"Page text: {page_text[:300]}")

        self.rate_limiter.report_success()

        # Transform captured results
        posts = []
        for data in captured:
            items = data.get("items", []) if data else []
            for item in items:
                if item.get("model_type") in ("rec_query", "hot_query"):
                    continue
                post = self._transform_search_item(item)
                if not post.get("note_id"):
                    continue
                post["_raw_time"] = self._extract_publish_time(item)
                posts.append(post)

        # Publish-time filter (client-side; XHS search API doesn't accept a
        # date filter via URL — we drop notes older than the cutoff here).
        window = _PUBLISH_WINDOW_SECONDS.get(publish_time_type)
        if window:
            cutoff = time.time() - window
            before = len(posts)
            posts = [p for p in posts if (p.get("_raw_time") or 0) >= cutoff]
            logger.info(
                f"Publish-time filter (type={publish_time_type}, window={window}s): "
                f"{before} -> {len(posts)}"
            )
        # Strip helper field before returning to caller
        for p in posts:
            p.pop("_raw_time", None)

        logger.info(f"Captured {len(posts)} posts for '{keyword}'")
        return posts[:max_count]

    @staticmethod
    def _extract_publish_time(item: dict) -> float:
        """Best-effort publish time (Unix seconds) from a search item."""
        note_card = item.get("note_card", {}) or {}
        for key in ("time", "publish_time", "publishTime", "last_update_time"):
            v = note_card.get(key) or item.get(key)
            if v:
                try:
                    n = float(v)
                except (TypeError, ValueError):
                    continue
                # XHS uses milliseconds for `time`/`last_update_time`
                if n > 1e12:
                    n = n / 1000.0
                return n
        return 0.0

    async def get_post_detail(self, note_id: str, xsec_token: str,
                                xsec_source: str = "pc_search") -> Optional[dict]:
        """Navigate to a note page and pull the full note data.

        Three-strategy extraction (most reliable first):
          1. window.__INITIAL_STATE__ — Vue's hydration data, always present
             when the page renders. Includes the full image carousel.
          2. FEED API response interception — backup if state is missing.
          3. DOM scraping of `.swiper-slide img` carousel — last-resort.
        """
        if not self._page:
            raise RuntimeError("Adapter not initialized")

        if not xsec_token:
            logger.warning(
                f"get_post_detail: missing xsec_token for {note_id}; "
                f"page will be blocked by XHS."
            )

        await self.rate_limiter.wait()

        note_url = _build_note_url(note_id, xsec_token, xsec_source)
        await self._set_headers(referer="https://www.xiaohongshu.com/search_result")

        # Set up FEED API interception (strategy 2) before navigating.
        feed_captured: dict = {}

        async def on_response(response):
            if FEED_API_PATH in response.url:
                try:
                    data = await response.json()
                    if data.get("success"):
                        feed_captured["data"] = data["data"]
                except Exception:
                    pass

        self._page.on("response", on_response)
        try:
            await self._page.goto(note_url, wait_until="domcontentloaded",
                                  timeout=30000)
            # Let the page hydrate. Vue writes __INITIAL_STATE__ during SSR but
            # the carousel images become available after a tick.
            await self._page.wait_for_timeout(2500)

            if await self._page_is_blocked():
                logger.warning(
                    f"Note {note_id} blocked by XHS — page shows QR-code wall"
                )
                self._page.remove_listener("response", on_response)
                return None
        except Exception as e:
            logger.warning(f"get_post_detail navigation failed: {e}")
            self._page.remove_listener("response", on_response)
            return None
        self._page.remove_listener("response", on_response)

        # ---- Strategy 1: __INITIAL_STATE__ ----
        state_detail = None
        try:
            state_detail = await self._page.evaluate(
                """
                (noteId) => {
                    try {
                        const state = window.__INITIAL_STATE__ || {};
                        const map = (state.note && state.note.noteDetailMap) || {};
                        const entry = map[noteId] || Object.values(map)[0];
                        const note = entry && entry.note;
                        if (!note) return null;

                        const type = (note.type || 'normal').toLowerCase();
                        const isVideo = type === 'video';

                        // Standard image extraction
                        const imgs = (note.imageList || []).map(img =>
                            img.urlDefault || img.urlPre || img.url ||
                            (img.infoList && img.infoList[0] && img.infoList[0].url) || ''
                        ).filter(Boolean);

                        // For VIDEO posts, prepend the first-frame poster so the
                        // carousel/thumbnail always has a visual.
                        if (isVideo) {
                            const v = note.video || {};
                            const candidates = [
                                // Cover variants
                                note.cover && (note.cover.urlDefault || note.cover.url || note.cover.urlPre),
                                // Video.image variants
                                v.image && (v.image.urlDefault || v.image.url || v.image.urlPre),
                                v.firstFrame, v.firstFrameUrl,
                                // Stream meta sometimes has thumbnail
                                v.media && v.media.video && v.media.video.image,
                            ];
                            for (const c of candidates) {
                                if (typeof c === 'string' && c.startsWith('http') && !imgs.includes(c)) {
                                    imgs.unshift(c);
                                    break;
                                }
                            }
                            // Fallback: build URL from firstFrameFileid via XHS CDN
                            const fid = v.firstFrameFileid || v.firstFrameFileId
                                     || (v.image && v.image.firstFrameFileid);
                            if (fid && imgs.length === 0) {
                                imgs.push('https://sns-img-bd.xhscdn.com/' + fid + '?imageView2/2/w/1080/format/jpg');
                            }
                        }

                        // Extract a usable video URL
                        const v = note.video || {};
                        let videoUrl = '';
                        const streams = v.media && v.media.stream;
                        if (streams) {
                            for (const k of ['h264', 'h265', 'av1']) {
                                const arr = streams[k];
                                if (arr && arr.length && arr[0].masterUrl) {
                                    videoUrl = arr[0].masterUrl;
                                    break;
                                }
                            }
                        }
                        if (!videoUrl && v.consumer && v.consumer.originVideoKey) {
                            videoUrl = 'http://sns-video-bd.xhscdn.com/' + v.consumer.originVideoKey;
                        }

                        return {
                            note_id: note.noteId || noteId,
                            title: note.title || '',
                            desc: note.desc || '',
                            type: type,
                            author_name: (note.user && (note.user.nickname || note.user.nickName)) || '',
                            author_id: (note.user && (note.user.userId || note.user.user_id)) || '',
                            author_avatar: (note.user && (note.user.avatar || note.user.images)) || '',
                            liked_count: (note.interactInfo && note.interactInfo.likedCount) || 0,
                            collected_count: (note.interactInfo && note.interactInfo.collectedCount) || 0,
                            comment_count: (note.interactInfo && note.interactInfo.commentCount) || 0,
                            share_count: (note.interactInfo && note.interactInfo.shareCount) || 0,
                            images: imgs,
                            video_url: videoUrl,
                        };
                    } catch (e) { return null; }
                }
                """,
                note_id,
            )
        except Exception as e:
            logger.warning(f"INITIAL_STATE extract failed: {e}")

        if state_detail and state_detail.get("images"):
            logger.info(
                f"[detail/{note_id}] Got {len(state_detail['images'])} "
                f"images from __INITIAL_STATE__"
            )
            return self._build_detail_from_state(
                state_detail, xsec_token, xsec_source
            )

        # ---- Strategy 2: FEED API ----
        feed_data = feed_captured.get("data", {})
        items = feed_data.get("items", []) if feed_data else []
        if items:
            detail = self._transform_note_detail(items[0], xsec_token, xsec_source)
            detail["xsec_token"] = xsec_token
            logger.info(f"[detail/{note_id}] Got data from FEED API")
            return detail

        # ---- Strategy 3: DOM scraping ----
        try:
            dom_data = await self._page.evaluate(
                """
                () => {
                    const seen = new Set();
                    const imgs = [];
                    const selectors = [
                        '.swiper-slide img',
                        '.note-slider img',
                        '.media-container img',
                        '.note-content .swiper-wrapper img',
                        'img.note-image',
                    ];
                    for (const sel of selectors) {
                        for (const el of document.querySelectorAll(sel)) {
                            let src = el.getAttribute('data-src') || el.currentSrc || el.src;
                            if (!src) continue;
                            if (src.includes('avatar') || src.includes('comment')) continue;
                            if (seen.has(src)) continue;
                            seen.add(src);
                            imgs.push(src);
                        }
                        if (imgs.length) break;
                    }
                    // Video posts: pull the <video poster="..."> (first frame).
                    const videoEl = document.querySelector('video');
                    if (videoEl) {
                        const poster = videoEl.getAttribute('poster');
                        if (poster && !seen.has(poster)) {
                            imgs.unshift(poster);
                            seen.add(poster);
                        }
                    }
                    return {
                        title: document.querySelector('.title, #detail-title')?.textContent?.trim() || '',
                        desc:  document.querySelector('#detail-desc, .desc')?.textContent?.trim() || '',
                        author: document.querySelector('.author-wrapper .username, .info .name')?.textContent?.trim() || '',
                        images: imgs,
                        isVideo: !!videoEl,
                    };
                }
                """
            )
        except Exception as e:
            logger.warning(f"DOM scrape failed: {e}")
            dom_data = None

        if dom_data and dom_data.get("images"):
            logger.info(
                f"[detail/{note_id}] Got {len(dom_data['images'])} images from DOM"
            )
            return {
                "note_id": note_id,
                "title": dom_data.get("title", "") or "",
                "desc": dom_data.get("desc", "") or "",
                "type": "normal",
                "author_name": dom_data.get("author", "") or "",
                "author_id": "",
                "author_avatar": "",
                "liked_count": 0,
                "collected_count": 0,
                "comment_count": 0,
                "share_count": 0,
                "image_urls": json.dumps(dom_data["images"], ensure_ascii=False),
                "video_url": "",
                "tag_list": "[]",
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
                "url": _build_note_url(note_id, xsec_token, xsec_source),
            }

        logger.warning(f"[detail/{note_id}] All three extraction strategies failed")
        return None

    def _build_detail_from_state(self, state: dict, xsec_token: str,
                                  xsec_source: str) -> dict:
        """Convert __INITIAL_STATE__ shape into our standard post dict."""
        note_id = state.get("note_id", "")
        return {
            "note_id": note_id,
            "title": state.get("title", "") or "",
            "desc": state.get("desc", "") or "",
            "type": state.get("type", "normal") or "normal",
            "author_name": state.get("author_name", "") or "",
            "author_id": state.get("author_id", "") or "",
            "author_avatar": state.get("author_avatar", "") or "",
            "liked_count": _parse_count(state.get("liked_count")),
            "collected_count": _parse_count(state.get("collected_count")),
            "comment_count": _parse_count(state.get("comment_count")),
            "share_count": _parse_count(state.get("share_count")),
            "image_urls": json.dumps(state.get("images") or [], ensure_ascii=False),
            "video_url": state.get("video_url", "") or "",
            "tag_list": "[]",
            "xsec_token": xsec_token,
            "xsec_source": xsec_source,
            "url": _build_note_url(note_id, xsec_token, xsec_source),
        }

    async def get_comments(self, note_id: str, xsec_token: str,
                            xsec_source: str = "pc_search",
                            max_count: int = 50) -> list[dict]:
        """Navigate to note page and extract comments from DOM/response."""
        if not self._page:
            raise RuntimeError("Adapter not initialized")

        if not xsec_token:
            logger.warning(
                f"get_comments: missing xsec_token for {note_id}; "
                f"XHS will show the QR-code block page."
            )

        await self.rate_limiter.wait()

        note_url = _build_note_url(note_id, xsec_token, xsec_source or "pc_search")
        await self._set_headers(referer="https://www.xiaohongshu.com/search_result")
        all_comments = []

        async def on_response(response):
            if COMMENT_API_PATH in response.url:
                try:
                    data = await response.json()
                    if data.get("success"):
                        comments = data.get("data", {}).get("comments", [])
                        for c in comments:
                            all_comments.append(self._transform_comment(c))
                except Exception:
                    pass

        self._page.on("response", on_response)
        try:
            await self._page.goto(note_url, wait_until="domcontentloaded",
                                  timeout=30000)
            await self._page.wait_for_timeout(2500)

            # Bail out clearly if XHS served the block page.
            if await self._page_is_blocked():
                logger.warning(
                    f"Note {note_id} blocked by XHS — skipping comments."
                )
                self._page.remove_listener("response", on_response)
                return []

            # Scroll to trigger lazy-loaded comments.
            for _ in range(4):
                await self._page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                await self._page.wait_for_timeout(1500)
                if len(all_comments) >= max_count:
                    break
        except Exception as e:
            logger.warning(f"Comment page load issue: {e}")

        self._page.remove_listener("response", on_response)
        logger.info(f"Captured {len(all_comments)} comments for {note_id}")
        return all_comments[:max_count]

    async def close(self):
        if self._page:
            await self._page.close()
            self._page = None
        self._initialized = False

    # ========== Data Transformers ==========

    def _transform_search_item(self, item: dict) -> dict:
        if not item or not isinstance(item, dict):
            return {}
        note_card = item.get("note_card", {}) or item
        user_info = note_card.get("user", {}) or {}
        interact = note_card.get("interact_info", {}) or {}
        image_list = note_card.get("image_list", []) or []
        tag_list = note_card.get("tag_list", []) or []
        cover = note_card.get("cover", {}) or {}
        note_id = item.get("id") or note_card.get("note_id") or ""

        # Search responses use display_title; detail responses use title.
        title = (note_card.get("display_title")
                 or note_card.get("title")
                 or "")
        desc = note_card.get("desc", "") or ""
        if not title and desc:
            title = desc[:80]

        # Build image URL list. Prefer the cover for thumbnail position —
        # for video notes the cover IS the first-frame thumbnail.
        image_urls = []
        cover_url = _extract_image_url(cover)
        if cover_url:
            image_urls.append(cover_url)
        for img in image_list:
            u = _extract_image_url(img)
            if u and u not in image_urls:
                image_urls.append(u)

        # Last-resort first-frame URL for video posts (rare path — when neither
        # `cover` nor `image_list` came back populated from the search API).
        if not image_urls and note_card.get("type") == "video":
            video = note_card.get("video", {}) or {}
            fid = (video.get("first_frame_fileid")
                   or video.get("firstFrameFileid")
                   or (video.get("image") or {}).get("first_frame_fileid"))
            if fid:
                image_urls.append(
                    f"https://sns-img-bd.xhscdn.com/{fid}"
                    f"?imageView2/2/w/1080/format/jpg"
                )

        xsec_token = item.get("xsec_token", "") or ""
        xsec_source = "pc_search"

        return {
            "note_id": note_id,
            "title": title,
            "desc": desc,
            "type": note_card.get("type", "normal"),
            "author_name": user_info.get("nickname", "") or "",
            "author_id": user_info.get("user_id", "") or "",
            "author_avatar": user_info.get("avatar", "") or "",
            "liked_count": _parse_count(interact.get("liked_count")),
            "collected_count": _parse_count(interact.get("collected_count")),
            "comment_count": _parse_count(interact.get("comment_count")),
            "share_count": _parse_count(interact.get("share_count")),
            "image_urls": json.dumps(image_urls, ensure_ascii=False),
            "video_url": "",
            "tag_list": json.dumps(
                [tag.get("name", "") for tag in tag_list], ensure_ascii=False
            ),
            "xsec_token": xsec_token,
            "xsec_source": xsec_source,
            "url": _build_note_url(note_id, xsec_token, xsec_source) if note_id else "",
        }

    def _transform_note_detail(self, detail: dict, xsec_token: str,
                                xsec_source: str = "pc_search") -> dict:
        note_card = detail.get("note_card", {}) or detail
        user_info = note_card.get("user", {}) or {}
        interact = note_card.get("interact_info", {}) or {}
        image_list = note_card.get("image_list", []) or []
        tag_list = note_card.get("tag_list", []) or []
        note_id = note_card.get("note_id") or detail.get("note_id") or ""

        title = (note_card.get("title")
                 or note_card.get("display_title")
                 or "")
        desc = note_card.get("desc", "") or ""
        if not title and desc:
            title = desc[:80]

        image_urls = [u for u in (_extract_image_url(img) for img in image_list) if u]

        return {
            "note_id": note_id,
            "title": title,
            "desc": desc,
            "type": note_card.get("type", "normal"),
            "author_name": user_info.get("nickname", "") or "",
            "author_id": user_info.get("user_id", "") or "",
            "author_avatar": user_info.get("avatar", "") or "",
            "liked_count": _parse_count(interact.get("liked_count")),
            "collected_count": _parse_count(interact.get("collected_count")),
            "comment_count": _parse_count(interact.get("comment_count")),
            "share_count": _parse_count(interact.get("share_count")),
            "image_urls": json.dumps(image_urls, ensure_ascii=False),
            "video_url": (note_card.get("video", {}).get("url", "")
                          if note_card.get("type") == "video" else ""),
            "tag_list": json.dumps(
                [tag.get("name", "") for tag in tag_list], ensure_ascii=False
            ),
            "xsec_token": xsec_token,
            "xsec_source": xsec_source,
            "url": _build_note_url(note_id, xsec_token, xsec_source) if note_id else "",
        }

    def _transform_comment(self, comment: dict) -> dict:
        if not comment:
            return {}
        user_info = comment.get("user_info", {}) or {}
        # Comment images (XHS lets users attach pics/stickers to comments)
        pictures = []
        for pic in (comment.get("pictures") or []):
            u = _extract_image_url(pic) if isinstance(pic, dict) else None
            if u:
                pictures.append(u)
        return {
            "comment_id": comment.get("id", ""),
            "content": comment.get("content", "") or "",
            "user_name": user_info.get("nickname", "") or "",
            "user_id": user_info.get("user_id", "") or "",
            "avatar": user_info.get("avatar", "") or "",
            "liked_count": _parse_count(comment.get("liked_count")),
            "sub_comment_count": _parse_count(comment.get("sub_comment_count")),
            "ip_location": comment.get("ip_location", "") or "",
            "pictures": json.dumps(pictures, ensure_ascii=False),
        }

    @property
    def is_initialized(self) -> bool:
        return self._initialized
