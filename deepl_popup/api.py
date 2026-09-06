import requests

API_BASE = "https://api-free.deepl.com/v2"


class DeepLError(Exception):
    pass


class AuthError(DeepLError):
    pass


class QuotaExceededError(DeepLError):
    pass


class RateLimitError(DeepLError):
    pass


class NetworkError(DeepLError):
    pass


class TranslationResult:
    def __init__(self, text: str, detected_source_language: str):
        self.text = text
        self.detected_source_language = detected_source_language


def translate(text, target_lang, source_lang=None, api_key=None, timeout=10) -> TranslationResult:
    if not api_key:
        raise AuthError("no API key configured")
    payload = {"text": [text], "target_lang": target_lang}
    if source_lang and source_lang.lower() != "auto":
        payload["source_lang"] = source_lang
    try:
        resp = requests.post(
            f"{API_BASE}/translate",
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            data=payload,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise NetworkError(str(e)) from e
    _raise_for_status(resp)
    t = resp.json()["translations"][0]
    return TranslationResult(t["text"], t["detected_source_language"])


def get_languages(kind, api_key, timeout=10):
    """kind: 'source' or 'target'. Returns [{"language": "EN", "name": "English", ...}, ...]."""
    if not api_key:
        raise AuthError("no API key configured")
    try:
        resp = requests.get(
            f"{API_BASE}/languages",
            params={"type": kind},
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise NetworkError(str(e)) from e
    _raise_for_status(resp)
    return resp.json()


def _raise_for_status(resp):
    if resp.status_code == 200:
        return
    if resp.status_code in (401, 403):
        raise AuthError(f"invalid API key ({resp.status_code})")
    if resp.status_code == 456:
        raise QuotaExceededError("translation quota exceeded")
    if resp.status_code == 429:
        raise RateLimitError("rate limited")
    raise DeepLError(f"DeepL API error {resp.status_code}: {resp.text[:200]}")
