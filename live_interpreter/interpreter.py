"""Per-chunk decision logic: what the listener sees and hears.

Depends only on the Recognizer and Translator interfaces, so it can be tested
with fakes and reused with other speech or translation engines.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from .filters import echoes_prompt, is_hallucination, looks_german
from .recognizer import Recognizer
from .translation import Translator

NATIVE_MIN_CONFIDENCE = 0.7             # sure enough it's already the listener's language
HINT_MIN_CONFIDENCE = 0.5               # sure enough to tell Whisper the source language


@dataclass
class Line:
    text: str                           # in the listener's language
    language: str                       # detected spoken language
    native: bool                        # already in the listener's language: show, don't voice


class Interpreter:
    def __init__(self, recognizer: Recognizer, translator: Translator, target: str,
                 expected: str | None = None, prompt: str = "", voice_native: bool = False,
                 glossary: Callable[[str], str] = lambda text: text,
                 log: Callable[[str], None] = print):
        self.recognizer = recognizer
        self.translator = translator
        self.glossary = glossary        # final corrections in the listener's language
        self.target = target
        self.expected = expected        # spoken-language hint, e.g. "de"; None = auto
        self.prompt = prompt
        self.voice_native = voice_native
        self.log = log

    def process(self, audio: np.ndarray) -> Line | None:
        language, confidence = self.recognizer.detect_language(audio)
        native = (not self.voice_native and language == self.target
                  and confidence >= NATIVE_MIN_CONFIDENCE)
        if native:
            text = self.recognizer.transcribe(audio, language, self.prompt)
        else:
            text = self._to_english(audio, language, confidence)

        if not text or is_hallucination(text):
            return None
        if echoes_prompt(text, self.prompt):
            self.log(f"(dropped prompt echo: {text})")
            return None
        if not native and looks_german(text):
            self.log(f"(dropped untranslated German: {text[:60]})")
            return None
        if not native:
            text = self.translator(text)
        return Line(text=self.glossary(text), language=language, native=native)

    def _to_english(self, audio, language, confidence):
        source = self.expected or (language if confidence >= HINT_MIN_CONFIDENCE else None)
        text = self.recognizer.translate(audio, source, self.prompt)
        if text and looks_german(text) and self.prompt:
            # German words in the prompt can make Whisper transcribe instead of translate
            text = self.recognizer.translate(audio, "de", "")
            if not text:
                self.log("(dropped chunk: still untranslated without --prompt)")
        return text
