"""Shared application text normalization helpers."""

import re


def normalize_control_text(text: str) -> str:
    """Normalize short memory and confirmation control text."""

    normalized = str(text or "").strip().lower().replace("ё", "е")
    normalized = re.sub(r"[,:;]+", " ", normalized)
    return " ".join(normalized.split())
