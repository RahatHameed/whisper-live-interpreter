"""Turn the original meeting audio down while the translation speaks."""
from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

MODULES_FILE = Path.home() / ".cache" / "interp-audio-modules"     # written by setup_audio.sh


class Ducker(ABC):
    @abstractmethod
    def duck(self) -> None: ...

    @abstractmethod
    def restore(self) -> None: ...


class NoDucking(Ducker):
    def duck(self):
        pass

    def restore(self):
        pass


def _pactl(*args: str) -> str:
    return subprocess.run(["pactl", *args], capture_output=True, text=True, check=True).stdout


class LoopbackDucker(Ducker):
    """Linux: lowers the MeetingOut -> headphones loopback from setup_audio.sh to
    `level` x its current volume, and puts back exactly what was there before."""

    def __init__(self, level: float, pactl: Callable[..., str] = _pactl,
                 modules_file: Path = MODULES_FILE):
        self.level = level
        self.pactl = pactl
        self.modules_file = modules_file
        self.saved: tuple[str, list[int]] | None = None     # (sink-input index, raw volumes)

    def _loopback(self) -> tuple[str, list[int]] | None:
        try:
            module = self.modules_file.read_text().split()[0]   # first line: the loopback module
            for s in json.loads(self.pactl("-f", "json", "list", "sink-inputs")):
                if str(s.get("owner_module")) == module:
                    return str(s["index"]), [v["value"] for v in s["volume"].values()]
        except (OSError, IndexError, ValueError, KeyError, subprocess.CalledProcessError):
            pass
        return None                     # no loopback (not set up, or audio undone): nothing to duck

    def duck(self):
        if self.saved:
            return
        found = self._loopback()
        if found:
            index, volumes = found
            self.pactl("set-sink-input-volume", index, *(str(int(v * self.level)) for v in volumes))
            self.saved = found

    def restore(self):
        if not self.saved:
            return
        index, volumes = self.saved
        self.saved = None
        try:
            self.pactl("set-sink-input-volume", index, *(str(v) for v in volumes))
        except subprocess.CalledProcessError:
            pass                        # loopback was removed meanwhile
