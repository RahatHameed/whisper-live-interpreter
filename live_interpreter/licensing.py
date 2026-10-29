"""Which listener languages are verified for commercial use, and why.

Safe by default: a language counts as *verified* only if every downloaded part it
needs has an explicit license that allows commercial use. Anything else is refused
unless the user confirms personal use (`make language TO=xx PERSONAL=1`).

What was checked (2026-10-29; re-check before changing anything here):
- Whisper models: MIT, stated on the weights. Used for every language.
- Piper voices: each carries the license of its training recordings (MODEL_CARD).
  Many are research-only or non-commercial (e.g. en_US-lessac, tr_TR-dfki), and many
  others were fine-tuned from lessac, which leaves them unclear.
- Argos translation models (needed for every language except English): the Argos
  software is MIT/CC0, but the model packages carry no explicit license and were
  trained on mixed web corpora, so no non-English language is verified yet.
"""
from __future__ import annotations

# Per language, the voice with the cleanest license: permissive dataset license
# (CC0, public domain, CC BY, CC BY-SA, Apache) and trained from scratch.
PREFERRED_VOICES = {
    "ca": "ca_ES-upc_ona-x_low",        # CC BY-SA 3.0 ES
    "de": "de_DE-mls-medium",           # CC BY 4.0 (Multilingual LibriSpeech)
    "el": "el_GR-rapunzelina-medium",   # CC0
    "en": "en_US-ljspeech-medium",      # public domain (LJ Speech)
    "es": "es_ES-carlfm-x_low",         # public domain
    "fr": "fr_FR-mls-medium",           # CC BY 4.0 (Multilingual LibriSpeech)
    "it": "it_IT-serena-medium",        # CC BY 4.0
    "nb": "no_NO-nvcc-medium",          # CC0
    "nl": "nl_BE-rdh-medium",           # CC0
    "sv": "sv_SE-nst-medium",           # CC0
    "uk": "uk_UA-ukrainian_tts-medium",  # CC0
}

# Voices verified for commercial use: public domain / CC0 / CC BY, trained from scratch.
VERIFIED_VOICES = {"en_US-ljspeech-medium"}

# Languages whose translation step is verified. English needs none (Whisper only).
VERIFIED_TRANSLATION = {"en"}


def license_problems(target: str, voice_key: str | None) -> list[str]:
    """Reasons this setup is not verified for commercial use (empty list = verified)."""
    problems = []
    if target not in VERIFIED_TRANSLATION:
        problems.append(f"the en->{target} translation model has no explicit license")
    if voice_key and voice_key not in VERIFIED_VOICES:
        problems.append(f"the voice {voice_key} is not verified for commercial use")
    return problems
