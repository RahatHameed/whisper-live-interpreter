"""Speech recognition: language detection, speech -> English, speech -> text."""
from __future__ import annotations

import os
from typing import Protocol

import numpy as np


class Recognizer(Protocol):
    """What the Interpreter needs from a speech model. Swap in another engine by
    implementing these three methods."""

    def detect_language(self, audio: np.ndarray) -> tuple[str, float]: ...

    def translate(self, audio: np.ndarray, language: str | None, prompt: str = "") -> str:
        """Speech in `language` (None = let the model guess) -> English text."""

    def transcribe(self, audio: np.ndarray, language: str, prompt: str = "") -> str:
        """Speech -> text in the same language."""


def pick_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import ctranslate2
        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


class WhisperRecognizer:
    """faster-whisper. Language ID runs on the small 'base' model (~0.3 s on CPU)
    instead of a second encoder pass of the big model (~2 s)."""

    LID_MODEL = "base"

    def __init__(self, model: str = "auto", device: str = "auto",
                 compute: str | None = None, beam: int = 1):
        from faster_whisper import WhisperModel

        device = pick_device(device)
        if model == "auto":
            model = "large-v3" if device == "cuda" else "medium"
        compute = compute or ("float16" if device == "cuda" else "int8")
        self.description = f"{model} on {device} ({compute})"
        self.warning = ("turbo models are not trained for translation; use large-v3/medium/small"
                        if "turbo" in model else None)
        self.beam = beam
        self.model = WhisperModel(model, device=device, compute_type=compute,
                                  cpu_threads=os.cpu_count() or 4)
        self.lid = WhisperModel(self.LID_MODEL, device=device, compute_type=compute)

    def detect_language(self, audio):
        language, probability, _ = self.lid.detect_language(audio)
        return language, probability

    def translate(self, audio, language, prompt=""):
        return self._run(audio, language, prompt, task="translate")

    def transcribe(self, audio, language, prompt=""):
        return self._run(audio, language, prompt, task="transcribe")

    def _run(self, audio, language, prompt, task):
        segments, _ = self.model.transcribe(
            audio, language=language, task=task,
            beam_size=self.beam, vad_filter=True,
            condition_on_previous_text=False, without_timestamps=True,
            initial_prompt=prompt or None,
        )
        # Background music pushes no_speech_prob up on real speech, so judge by avg_logprob
        parts = [s.text.strip() for s in segments if s.avg_logprob > -1.0]
        return " ".join(p for p in parts if p).strip()
