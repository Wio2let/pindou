"""System status and configuration API endpoints."""

import os
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, engine
from app.adapters.cdp_manager import CDPManager
from app.adapters.cookie_manager import CookieManager

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
async def health_check():
    """Backend health check."""
    return {
        "status": "ok",
        "app": "xhs-monitor",
        "version": "0.1.0",
    }


@router.get("/login-status")
async def login_status():
    """Check Xiaohongshu login cookie status."""
    cookie_file = os.path.join(
        os.environ.get("COOKIE_DIR", "./data/cookies"), "xhs_cookies.json"
    )
    has_cookie = os.path.exists(cookie_file)
    return {
        "logged_in": has_cookie,
        "cookie_file": cookie_file if has_cookie else None,
    }


@router.get("/debug-cookies")
async def debug_cookies():
    """Connect to Chrome via CDP and show available Xiaohongshu cookies."""
    cdp = CDPManager()
    cm = CookieManager()
    try:
        context = await cdp.connect()
        cookies = await context.cookies(urls=["https://www.xiaohongshu.com"])
        cookie_names = [c["name"] for c in cookies]
        has_a1 = "a1" in cookie_names
        has_web_session = "web_session" in cookie_names
        return {
            "connected": True,
            "cookies_found": len(cookies),
            "cookie_names": cookie_names[:20],
            "has_a1": has_a1,
            "has_web_session": has_web_session,
            "has_saved_file": cm.has_cookies,
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }
    finally:
        await cdp.disconnect()
