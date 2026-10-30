"""Configuration loader using Pydantic v2 and PyYAML, with .env support."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env if present
load_dotenv()


class GeneralConfig(BaseModel):
    node_prefix: str = "[xBench]"
    log_level: str = "INFO"
    theme: str = "dark"


class PathsConfig(BaseModel):
    bin_dir: Path = Path("bin")
    subscriptions_file: Path = Path("data/subscriptions.txt")
    custom_nodes_file: Path = Path("data/custom_nodes.txt")
    blacklist_file: Path = Path("data/blacklist.txt")
    database_path: Path = Path("data/nodes_cache.db")
    output_http_file: Path = Path("../results/nodes_http.txt")
    output_speed_file: Path = Path("../results/nodes_speed.txt")


class XrayConfig(BaseModel):
    batch_size: int = 50
    startup_timeout_sec: float = 5.0
    listen_host: str = "127.0.0.1"


class GeoConfig(BaseModel):
    cache_ttl_days: int = 14
    blocked_google_countries: List[str] = Field(default_factory=lambda: ["IR", "RU"])
    check_google_country: bool = True
    primary_api_url: str = "http://ip-api.com/json/{ip}?fields=status,countryCode,isp"
    backup_api_urls: List[str] = Field(
        default_factory=lambda: [
            "https://ipwho.is/{ip}",
            "https://ipinfo.io/{ip}/json",
        ]
    )
    google_check_url: str = "https://www.youtube.com/sw.js_data"
    google_fallback_url: str = "https://www.google.com/preferences?hl=en"


class HttpTestConfig(BaseModel):
    test_url: str = "http://cp.cloudflare.com/generate_204"
    timeout_sec: float = 6.0
    concurrency: int = 12
    warmup_requests: int = 1
    timed_requests: int = 1


class SpeedTestConfig(BaseModel):
    payload_url: str = "https://speed.cloudflare.com/__down?bytes=5000000"
    timeout_sec: float = 10.0
    concurrency: int = 4
    min_speed_mbps: float = 0.1
    bottom_third_divisor: int = 3
    max_consecutive_zero_runs: int = 3


class GithubConfig(BaseModel):
    token: Optional[str] = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))
    repo: Optional[str] = Field(default_factory=lambda: os.getenv("GITHUB_REPO"))
    branch: str = Field(default_factory=lambda: os.getenv("GITHUB_BRANCH", "main"))
    commit_message_prefix: str = "Update proxy nodes [automated]"


class AppConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    xray: XrayConfig = Field(default_factory=XrayConfig)
    geo: GeoConfig = Field(default_factory=GeoConfig)
    http_test: HttpTestConfig = Field(default_factory=HttpTestConfig)
    speed_test: SpeedTestConfig = Field(default_factory=SpeedTestConfig)
    github: GithubConfig = Field(default_factory=GithubConfig)


def load_config(config_path: Path | str = "config.yaml") -> AppConfig:
    """Load configuration from a YAML file, merging environment variables."""
    cfg_file = Path(config_path)
    data = {}
    if cfg_file.is_file():
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    config = AppConfig(**data)
    return config
