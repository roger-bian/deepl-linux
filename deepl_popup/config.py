import configparser
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from deepl_popup import languages

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "deepl-popup"
CONFIG_PATH = CONFIG_DIR / "config.ini"

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "deepl-popup"
LANGUAGES_CACHE_PATH = CACHE_DIR / "languages.json"
LANGUAGES_CACHE_MAX_AGE = 7 * 24 * 3600  # 7 days


@dataclass
class Config:
    api_key: str | None = None
    default_target_lang: str = "EN-US"
    preferred_variants: dict = field(default_factory=lambda: dict(languages.DEFAULT_TARGET_VARIANT))


def load() -> Config:
    """Load config from disk. Never raises; missing file/key just yields defaults."""
    cfg = Config()
    if not CONFIG_PATH.exists():
        return cfg
    parser = configparser.ConfigParser()
    try:
        parser.read(CONFIG_PATH)
    except configparser.Error:
        return cfg
    if parser.has_section("deepl"):
        cfg.api_key = parser.get("deepl", "api_key", fallback=None) or None
        cfg.default_target_lang = parser.get("deepl", "default_target_lang", fallback=cfg.default_target_lang)
    return cfg


def save(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    parser = configparser.ConfigParser()
    parser["deepl"] = {
        "api_key": cfg.api_key or "",
        "default_target_lang": cfg.default_target_lang,
    }
    tmp_path = CONFIG_PATH.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        parser.write(f)
    os.chmod(tmp_path, 0o600)
    os.rename(tmp_path, CONFIG_PATH)


def set_api_key(api_key: str) -> None:
    cfg = load()
    cfg.api_key = api_key
    save(cfg)


def load_language_cache():
    """Returns (source_list, target_list) or (None, None) if no fresh cache exists."""
    if not LANGUAGES_CACHE_PATH.exists():
        return None, None
    try:
        data = json.loads(LANGUAGES_CACHE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None, None
    if time.time() - data.get("fetched_at", 0) > LANGUAGES_CACHE_MAX_AGE:
        return None, None
    return data.get("source"), data.get("target")


def save_language_cache(source_list, target_list) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {"fetched_at": time.time(), "source": source_list, "target": target_list}
    tmp_path = LANGUAGES_CACHE_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data))
    os.rename(tmp_path, LANGUAGES_CACHE_PATH)
