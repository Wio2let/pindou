"""Bilibili video search via the public web search API.

Faster and more reliable than headless Playwright. We just need a `buvid3`
cookie which Bilibili hands out on the first visit to www.bilibili.com.
"""

import re
import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/bilibili", tags=["bilibili"])

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Cache the buvid cookie so we don't re-fetch on every search.
_cookie_cache: dict = {"jar": None, "ts": 0.0}
_COOKIE_TTL_SEC = 1800

_HTML_TAG = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return _HTML_TAG.sub("", s or "").strip()


def _abs_url(u: str) -> str:
    """Bilibili returns protocol-less URLs like //i0.hdslb.com/..."""
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    return u


async def _ensure_cookies(client: httpx.AsyncClient) -> None:
    """Warm the client cookie jar with buvid3/buvid4 from www.bilibili.com."""
    now = time.time()
    cached = _cookie_cache.get("jar")
    if cached and (now - _cookie_cache["ts"] < _COOKIE_TTL_SEC):
        for c in cached:
            client.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
        return

    try:
        await client.get("https://www.bilibili.com/", timeout=8.0)
        _cookie_cache["jar"] = list(client.cookies.jar)
        _cookie_cache["ts"] = now
    except Exception:
        # Search often still works even without warm cookies — keep going.
        pass


@router.get("/search")
async def search_videos(
    keyword: str = Query(..., min_length=1),
    page: int = Query(1, ge=1, le=50),
    order: str = Query(
        "totalrank",
        pattern=r"^(totalrank|click|pubdate|dm|stow|scores)$",
        description="totalrank=综合 click=播放 pubdate=最新 dm=弹幕 stow=收藏 scores=评论",
    ),
    duration: int = Query(
        0, ge=0, le=4,
        description="0=全部 1=<10min 2=10-30min 3=30-60min 4=>60min",
    ),
):
    """Search Bilibili videos. Returns a normalized list of video metadata."""
    api_url = "https://api.bilibili.com/x/web-interface/search/type"
    params = {
        "search_type": "video",
        "keyword": keyword,
        "page": page,
        "order": order,
    }
    if duration:
        params["duration"] = duration

    headers = {
        "User-Agent": _UA,
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        await _ensure_cookies(client)
        try:
            resp = await client.get(api_url, params=params, timeout=15.0)
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502, detail=f"Bilibili request failed: {e}"
            )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Bilibili returned HTTP {resp.status_code}",
        )

    try:
        body = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Bilibili returned non-JSON")

    if body.get("code") != 0:
        msg = body.get("message") or "unknown error"
        raise HTTPException(
            status_code=502, detail=f"Bilibili API error: {msg}"
        )

    data = body.get("data") or {}
    raw_items = data.get("result") or []

    items = []
    for it in raw_items:
        if it.get("type") and it.get("type") != "video":
            continue
        bvid = it.get("bvid") or ""
        items.append({
            "bvid": bvid,
            "aid": it.get("id") or it.get("aid") or 0,
            "title": _strip_html(it.get("title", "")),
            "description": _strip_html(it.get("description", "")),
            "pic": _abs_url(it.get("pic", "")),
            "author": it.get("author", "") or "",
            "mid": it.get("mid") or 0,
            "play": int(it.get("play") or 0),
            "danmaku": int(it.get("danmaku") or 0),
            "like": int(it.get("like") or 0),
            "favorites": int(it.get("favorites") or 0),
            "video_review": int(it.get("video_review") or 0),
            "duration": it.get("duration") or "",
            "pubdate": int(it.get("pubdate") or 0),
            "tag": it.get("tag", "") or "",
            "url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
        })

    return {
        "items": items,
        "total": int(data.get("numResults") or 0),
        "page": int(data.get("page") or page),
        "page_size": int(data.get("pagesize") or len(items)),
        "num_pages": int(data.get("numPages") or 1),
        "keyword": keyword,
    }
