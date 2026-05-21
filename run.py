#!/usr/bin/env python3
"""Single entry point for the backend server."""

import sys
import asyncio
from pathlib import Path

# Add MediaCrawler to sys.path BEFORE uvicorn starts
# This must come before importing app.main
_mc_path = str(Path(__file__).resolve().parent / "lib" / "media_crawler_src")
if _mc_path not in sys.path:
    sys.path.insert(0, _mc_path)

import uvicorn

if __name__ == "__main__":
    # Use asyncio directly, avoid reloader which causes subprocess issues on Windows
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )
