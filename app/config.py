import sys
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

# Add MediaCrawler source to Python path
_mc_path = str(Path(__file__).resolve().parent.parent / "lib" / "media_crawler_src")
if _mc_path not in sys.path:
    sys.path.insert(0, _mc_path)


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/xhs_monitor.db"
    chrome_port: int = 9222
    chrome_host: str = "127.0.0.1"
    cookie_dir: str = "./data/cookies"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
