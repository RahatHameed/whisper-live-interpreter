"""English -> listener's language. Whisper only translates into English, so any
other target language goes through a second, local text translation model."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from .config import MODELS_DIR


class Translator(ABC):
    @abstractmethod
    def __call__(self, english: str) -> str: ...


class Passthrough(Translator):
    """The listener's language is English: nothing to do."""

    def __call__(self, english):
        return english


class ArgosTranslator(Translator):
    """An Argos Translate model package (CTranslate2 + SentencePiece), used
    directly so we don't pull in argostranslate's PyTorch dependency."""

    def __init__(self, model_dir: Path):
        import ctranslate2
        import sentencepiece

        self.model = ctranslate2.Translator(str(model_dir / "model"), device="cpu",
                                            compute_type="int8")
        self.sp = sentencepiece.SentencePieceProcessor(
            model_file=str(model_dir / "sentencepiece.model"))

    def __call__(self, english):
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", english) if s]
        results = self.model.translate_batch(
            [self.sp.encode(s, out_type=str) for s in sentences], beam_size=2)
        return " ".join(self.sp.decode(r.hypotheses[0]) for r in results)


def model_dir(target: str) -> Path:
    return MODELS_DIR / f"translate-en_{target}"


def translator_for(target: str) -> Translator:
    if target == "en":
        return Passthrough()
    path = model_dir(target)
    if not path.is_dir():
        raise FileNotFoundError(f"No translation model for '{target}'. Run: make language")
    return ArgosTranslator(path)
