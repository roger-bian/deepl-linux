"""Language code helpers and fallback lists for the source/target combo boxes.

DeepL's source and target language code sets differ: target codes include
regional variants (EN-GB, EN-US, PT-BR, PT-PT, ZH-HANS) while source codes
are bare (EN, PT, ZH). Swapping the two combo values naively would produce
invalid codes, so this module provides the mapping helpers used by the
swap feature in window.py.
"""

# Bare source code -> preferred target variant, for codes that have regional
# target variants. Codes not listed here are used unchanged as targets.
DEFAULT_TARGET_VARIANT = {
    "EN": "EN-US",
    "PT": "PT-PT",
    "ZH": "ZH-HANS",
}

# Fallback lists used if both the network and the local cache are unavailable.
FALLBACK_SOURCE_LANGUAGES = [
    {"language": "AUTO", "name": "Detect language"},
    {"language": "EN", "name": "English"},
    {"language": "JA", "name": "Japanese"},
    {"language": "DE", "name": "German"},
    {"language": "FR", "name": "French"},
    {"language": "ES", "name": "Spanish"},
    {"language": "IT", "name": "Italian"},
    {"language": "PT", "name": "Portuguese"},
    {"language": "ZH", "name": "Chinese"},
    {"language": "RU", "name": "Russian"},
    {"language": "KO", "name": "Korean"},
    {"language": "NL", "name": "Dutch"},
    {"language": "PL", "name": "Polish"},
]

FALLBACK_TARGET_LANGUAGES = [
    {"language": "EN-US", "name": "English (American)"},
    {"language": "EN-GB", "name": "English (British)"},
    {"language": "JA", "name": "Japanese"},
    {"language": "DE", "name": "German"},
    {"language": "FR", "name": "French"},
    {"language": "ES", "name": "Spanish"},
    {"language": "IT", "name": "Italian"},
    {"language": "PT-PT", "name": "Portuguese (European)"},
    {"language": "PT-BR", "name": "Portuguese (Brazilian)"},
    {"language": "ZH-HANS", "name": "Chinese (simplified)"},
    {"language": "RU", "name": "Russian"},
    {"language": "KO", "name": "Korean"},
    {"language": "NL", "name": "Dutch"},
    {"language": "PL", "name": "Polish"},
]

# All known valid target codes (from the fallback list), used to recognize a
# code that's already a valid target id and shouldn't be re-mapped.
KNOWN_TARGET_CODES = {row["language"] for row in FALLBACK_TARGET_LANGUAGES}


def to_source_code(code: str) -> str:
    """Convert a (possibly regional) target code into a bare source code."""
    if not code:
        return code
    return code.split("-")[0]


def to_target_code(code: str, preferred_variants: dict | None = None) -> str:
    """Convert a bare source code into a usable target code.

    If `code` is already a known valid target id, it's returned unchanged.
    Otherwise consult `preferred_variants` (falling back to
    DEFAULT_TARGET_VARIANT) for a regional-variant mapping.
    """
    if not code:
        return code
    if code in KNOWN_TARGET_CODES:
        return code
    variants = preferred_variants or DEFAULT_TARGET_VARIANT
    return variants.get(code, code)
