"""Text checks that catch typical Whisper failures before anything is spoken."""
from __future__ import annotations

# Phrases Whisper invents on silence or noise
HALLUCINATIONS = {
    "you", "thank you.", "thanks for watching!", "thank you for watching.",
    "thanks for watching.", "bye.", "subtitles by the amara.org community",
}

# Common German function words (none of them common English words) to spot
# chunks Whisper transcribed instead of translating.
GERMAN_WORDS = {
    "der", "die", "das", "und", "ist", "nicht", "ein", "eine", "einen", "einer",
    "eines", "dem", "den", "des", "mit", "sich", "auch", "auf", "für", "von",
    "zu", "zum", "zur", "bei", "nach", "sie", "wir", "ich", "es", "wird",
    "werden", "wurde", "haben", "sind", "dass", "wie", "oder", "aber", "noch",
    "nur", "im", "vom", "über", "sowie", "wieder", "etwa", "weil", "wenn",
    "kann", "aus", "nachdem", "wiederum",
}


def words(text: str) -> list[str]:
    stripped = (w.strip(".,;:!?\"'()…-").lower() for w in text.split())
    return [w for w in stripped if w]


def is_hallucination(text: str) -> bool:
    return text.lower() in HALLUCINATIONS


def looks_german(text: str) -> bool:
    w = words(text)
    hits = sum(x in GERMAN_WORDS for x in w)
    return hits >= 1 and hits / max(1, len(w)) >= 0.25


def echoes_prompt(text: str, prompt: str) -> bool:
    """True if every word of the line also appears in the prompt."""
    vocab = set(words(prompt.replace(",", " ")))
    w = words(text)
    return bool(prompt) and bool(w) and all(x in vocab for x in w)
