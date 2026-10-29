"""Paths, constants, the listener's saved choice and the run settings."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .chunker import ChunkerConfig

ROOT = Path(__file__).resolve().parent.parent
VOICES_DIR = ROOT / "voices"
MODELS_DIR = ROOT / "models"
CONF_PATH = ROOT / ".interpreter.conf"
GLOSSARY_PATH = ROOT / "glossary.cfg"
TRANSCRIPTS_DIR = ROOT / "transcripts"   # git-ignored; only with --save-transcript
DEFAULT_TARGET = "en"


@dataclass
class UserConfig:
    """What the listener chose with `make language`: the language they hear and its voice."""
    target: str = DEFAULT_TARGET
    voice: str | None = None            # path relative to ROOT
    personal_use: bool = False          # confirmed: unverified licenses, personal use only

    @classmethod
    def load(cls, path: Path = CONF_PATH) -> UserConfig:
        values = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip()
        return cls(target=values.get("TARGET", DEFAULT_TARGET), voice=values.get("VOICE") or None,
                   personal_use=values.get("PERSONAL_USE") == "1")

    def save(self, path: Path = CONF_PATH) -> None:
        # KEY=value lines so the Makefile could include it too
        path.write_text(f"TARGET={self.target}\nVOICE={self.voice or ''}\n"
                        f"PERSONAL_USE={int(self.personal_use)}\n")

    @property
    def voice_path(self) -> Path | None:
        if self.voice:
            return ROOT / self.voice
        hits = sorted(VOICES_DIR.glob("en_*.onnx")) if self.target == "en" else []
        return hits[0] if hits else None


@dataclass
class Settings:
    """Everything one interpreter run needs, built from the command line."""
    target: str = DEFAULT_TARGET        # language the listener hears
    voice: Path | None = None           # Piper voice for `target`
    language: str = "auto"              # spoken language: auto or a hint like "de"
    prompt: str = ""                    # names/products to help Whisper
    glossary: Path = GLOSSARY_PATH      # corrections applied to the final text
    voice_native: bool = False          # also voice speech already in `target`
    model: str = "auto"
    device: str = "auto"
    compute: str | None = None
    beam: int = 1
    speed: float = 1.1
    max_lag: float = 10.0
    tts: bool = True
    duck: float = 0.3                   # meeting volume while the voice speaks (1 = off)
    source: str | None = None           # capture device (platform default if None)
    sink: str | None = None             # playback device (platform default if None)
    input_file: str | None = None
    realtime: bool = True               # feed --input-file at real-time speed
    out_wav: str | None = None
    save_transcript: bool = False       # opt-in: recording may need consent
    personal_use: bool = False          # allow parts whose licenses aren't verified
    chunking: ChunkerConfig = field(default_factory=ChunkerConfig)
