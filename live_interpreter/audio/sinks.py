"""Where the spoken translation goes: headphones, or a WAV file for tests."""
from __future__ import annotations

import os
import subprocess
import tempfile
import wave
from abc import ABC, abstractmethod
from pathlib import Path

HEADPHONE_SINK_FILE = Path.home() / ".cache" / "interp-headphone-sink"   # set by setup_audio.sh


def write_wav(path: str, pcm: bytes, rate: int) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


class AudioSink(ABC):
    @abstractmethod
    def play(self, pcm: bytes, rate: int) -> None:
        """Play raw s16le mono PCM; block until done."""

    def close(self) -> None:
        pass


class PulseSink(AudioSink):
    """Linux: paplay to a named sink (the headphones), never to MeetingOut."""

    def __init__(self, device: str | None):
        self.device = device

    def play(self, pcm, rate):
        cmd = ["paplay", "--raw", f"--rate={rate}", "--channels=1", "--format=s16le"]
        if self.device:
            cmd.append(f"--device={self.device}")
        subprocess.run(cmd, input=pcm, check=False)

    @staticmethod
    def default_device() -> str | None:
        if HEADPHONE_SINK_FILE.exists():
            return HEADPHONE_SINK_FILE.read_text().strip()
        try:
            return subprocess.check_output(["pactl", "get-default-sink"], text=True).strip()
        except Exception:
            return None


class AfplaySink(AudioSink):
    """macOS: afplay to the system output (keep it on your headphones)."""

    def play(self, pcm, rate):
        fd, path = tempfile.mkstemp(suffix=".wav")     # afplay can't read raw stdin
        os.close(fd)
        try:
            write_wav(path, pcm, rate)
            subprocess.run(["afplay", path], check=False)
        finally:
            os.remove(path)


class WavFileSink(AudioSink):
    """Append all speech to one WAV file instead of playing it."""

    def __init__(self, path: str):
        self.path = path
        self.wav = None

    def play(self, pcm, rate):
        if self.wav is None:
            self.wav = wave.open(self.path, "wb")
            self.wav.setnchannels(1)
            self.wav.setsampwidth(2)
            self.wav.setframerate(rate)
        self.wav.writeframes(pcm)

    def close(self):
        if self.wav:
            self.wav.close()


def create_sink(out_wav: str | None, device: str | None) -> AudioSink:
    from . import MACOS

    if out_wav:
        return WavFileSink(out_wav)
    if MACOS:
        return AfplaySink()
    return PulseSink(device or PulseSink.default_device())
