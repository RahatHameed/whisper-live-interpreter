"""Cut a live audio stream into speech chunks at natural pauses.

Pure logic with no I/O: feed it 30 ms int16 frames, it returns a float32
chunk whenever one is complete. That keeps it easy to test with synthetic audio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

import numpy as np

SAMPLE_RATE = 16000                     # Whisper's input rate
FRAME_MS = 30


@dataclass
class ChunkerConfig:
    min_chunk: float = 1.0              # min seconds per chunk
    max_chunk: float = 6.0              # target max seconds (hard cap: +4 s)
    silence: float = 0.5                # pause (s) that ends a chunk
    threshold_db: float = -45.0         # min speech level in dBFS


def _frames(seconds: float) -> int:
    return int(seconds * 1000 / FRAME_MS)


class SpeechChunker:
    """Energy VAD with an adaptive noise floor."""

    def __init__(self, config: ChunkerConfig | None = None, sample_rate: int = SAMPLE_RATE):
        cfg = config or ChunkerConfig()
        self.frame_size = sample_rate * FRAME_MS // 1000
        self.threshold_db = cfg.threshold_db
        self.silence_needed = _frames(cfg.silence)
        self.short_pause = max(1, _frames(0.15))
        self.min_frames = _frames(cfg.min_chunk)
        self.soft_max = _frames(cfg.max_chunk)
        self.hard_max = _frames(cfg.max_chunk + 4)
        self.preroll = _frames(0.3)
        self.min_voiced = _frames(0.3)
        self.noise_db = -60.0
        self.history: list[np.ndarray] = []
        self._reset()

    def _reset(self) -> None:
        self.buf: list[np.ndarray] = []
        self.in_speech, self.silent, self.voiced = False, 0, 0

    def feed(self, frame: np.ndarray) -> np.ndarray | None:
        """Add one int16 frame; return a finished chunk or None."""
        rms = np.sqrt(np.mean((frame.astype(np.float32) / 32768.0) ** 2)) + 1e-9
        db = 20 * np.log10(rms)
        speech = db > max(self.threshold_db, self.noise_db + 10)
        if not speech:                  # slowly track background level
            self.noise_db = 0.95 * self.noise_db + 0.05 * db

        if not self.in_speech:
            self.history = (self.history + [frame])[-self.preroll:]
            if speech:
                self.in_speech, self.buf, self.silent, self.voiced = True, list(self.history), 0, 1
            return None

        self.buf.append(frame)
        if speech:
            self.silent, self.voiced = 0, self.voiced + 1
        else:
            self.silent += 1
        n = len(self.buf)
        if (self.silent >= self.silence_needed and n >= self.min_frames) \
                or (n >= self.soft_max and self.silent >= self.short_pause) \
                or n >= self.hard_max:
            return self._emit()
        return None

    def flush(self) -> np.ndarray | None:
        """Return whatever speech is still buffered (end of stream)."""
        return self._emit() if self.buf else None

    def _emit(self) -> np.ndarray | None:
        chunk = None
        if self.voiced >= self.min_voiced:      # ignore clicks and short noises
            chunk = np.concatenate(self.buf).astype(np.float32) / 32768.0
        self._reset()
        return chunk


def iter_frames(read: Callable[[int], bytes], frame_size: int) -> Iterator[np.ndarray]:
    """Yield int16 frames from a raw s16le byte stream until it ends."""
    frame_bytes = frame_size * 2
    pending = b""
    while True:
        data = read(frame_bytes)
        if not data:
            return
        pending += data
        while len(pending) >= frame_bytes:
            yield np.frombuffer(pending[:frame_bytes], dtype=np.int16)
            pending = pending[frame_bytes:]
