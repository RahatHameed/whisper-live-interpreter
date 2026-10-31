"""Opt-in transcript of what was shown, one file per session.

Off by default: recording a meeting may need the participants' consent
(see the checklist in README.md).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from .interpreter import Line


class TranscriptWriter:
    def __init__(self, folder: Path, target: str):
        folder.mkdir(mode=0o700, exist_ok=True)
        self.path = folder / time.strftime("%Y-%m-%d_%H%M%S.md")
        self.target = target
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)   # private file
        self.file = os.fdopen(fd, "a", encoding="utf-8")
        self.file.write(f"# Transcript {time.strftime('%Y-%m-%d %H:%M')} (you hear: {target})\n\n")
        self.file.flush()

    def __call__(self, line: Line) -> None:
        source = line.language if line.native else f"{line.language}→{self.target}"
        self.file.write(f"- `{time.strftime('%H:%M:%S')}` ({source}) {line.text}\n")
        self.file.flush()                       # nothing lost if the program is killed

    def close(self) -> None:
        self.file.close()
