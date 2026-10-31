"""Terminal output: timestamped log lines and the subtitle lines."""
from __future__ import annotations

import time

from .interpreter import Line

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def show(line: Line, target: str, delay: float, asr: float, backlog: int) -> None:
    tag = (f"{DIM}--  (spoken in {line.language}, not voiced){RESET}  " if line.native
           else f"{BOLD}{target.upper()}{RESET}  ")
    stats = f"+{delay:.1f}s, asr {asr:.1f}s" + (f", backlog {backlog}" if backlog else "")
    print(f"{tag}{line.text}   {DIM}({stats}){RESET}", flush=True)
