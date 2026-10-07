"""Local (offline) language detection, used to pick a sensible target
language before calling DeepL so we don't spend a request translating text
into the language it's already in.

Kana/Hangul are checked directly since they identify Japanese/Korean with
certainty; everything else goes through langdetect if it's installed. If it
isn't, or the text is too short/ambiguous to call, detect() returns None and
the caller falls back to its default target.
"""

import threading

from deepl_popup import languages

try:
    from langdetect import DetectorFactory, detect_langs
    from langdetect.lang_detect_exception import LangDetectException

    DetectorFactory.seed = 0  # langdetect is nondeterministic without this
except ImportError:
    detect_langs = None

MIN_PROBABILITY = 0.7
# langdetect confidently misfires on very short text ("OK" -> Portuguese).
MIN_LETTERS = 12

# langdetect codes that don't map to DeepL's by simple upper-casing.
_LANGDETECT_TO_DEEPL = {
    "no": "NB",
}

# langdetect lazily loads its language profiles on first use, which isn't
# thread-safe; serialize calls.
_lock = threading.Lock()


def _script_language(text: str) -> str | None:
    for ch in text:
        cp = ord(ch)
        if 0x3040 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF or 0xFF66 <= cp <= 0xFF9F:
            return "JA"  # hiragana / katakana / halfwidth katakana
        if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F:
            return "KO"  # hangul
    return None


def _has_han(text: str) -> bool:
    return any(0x4E00 <= ord(ch) <= 0x9FFF or 0x3400 <= ord(ch) <= 0x4DBF for ch in text)


def detect(text: str) -> str | None:
    """Return the bare DeepL source code (e.g. "EN", "JA") for `text`, or None if unsure."""
    if not text or not text.strip():
        return None
    script_lang = _script_language(text)
    if script_lang:
        return script_lang
    if detect_langs is None:
        return None
    has_han = _has_han(text)
    if not has_han and sum(ch.isalpha() for ch in text) < MIN_LETTERS:
        return None
    try:
        with _lock:
            candidates = detect_langs(text)
    except LangDetectException:
        return None
    if not candidates or candidates[0].prob < MIN_PROBABILITY:
        return None
    code = candidates[0].lang
    code = _LANGDETECT_TO_DEEPL.get(code) or languages.to_source_code(code.upper())
    # Kanji without kana could be Chinese or Japanese; langdetect sometimes
    # calls it something else entirely (e.g. Korean), so only trust "ZH".
    if has_han and code != "ZH":
        return None
    return code


def choose_target(detected: str | None, ranked_targets: list[str]) -> str | None:
    """Pick the highest-ranked target that differs from the detected source language."""
    if not ranked_targets:
        return None
    if detected:
        for target in ranked_targets:
            if languages.to_source_code(target) != detected:
                return target
    return ranked_targets[0]
