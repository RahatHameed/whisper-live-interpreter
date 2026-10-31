"""Text -> speech with Piper (local neural TTS)."""
from __future__ import annotations

from pathlib import Path


class PiperSynthesizer:
    def __init__(self, voice: Path, speed: float = 1.1):
        from piper import PiperVoice

        self.voice = PiperVoice.load(str(voice))
        self.sample_rate = self.voice.config.sample_rate
        self.length_scale = 1.0 / max(0.5, speed)

    def synth(self, text: str, hurry: bool = False) -> bytes:
        """Return raw s16le mono PCM. `hurry` speaks faster to catch up on a backlog."""
        scale = self.length_scale * (0.8 if hurry else 1.0)
        try:                                    # piper-tts >= 1.3
            from piper import SynthesisConfig
            cfg = SynthesisConfig(length_scale=scale)
            return b"".join(c.audio_int16_bytes for c in self.voice.synthesize(text, syn_config=cfg))
        except ImportError:                     # piper-tts 1.2
            return b"".join(self.voice.synthesize_stream_raw(text, length_scale=scale))
