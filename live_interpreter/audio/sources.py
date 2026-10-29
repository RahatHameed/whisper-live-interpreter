"""Where the meeting audio comes from: raw s16le, mono, 16 kHz on a subprocess stdout."""
from __future__ import annotations

import shutil
import subprocess

from ..chunker import SAMPLE_RATE

LINUX_DEVICE = "meeting_out.monitor"     # created by setup_audio.sh
MACOS_DEVICE = "BlackHole 2ch"           # brew install --cask blackhole-2ch
PCM_OUT = ["-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"]


class AudioSource:
    def __init__(self, cmd: list[str]):
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)

    def read(self, n: int) -> bytes:
        return self.proc.stdout.read(n)

    def close(self) -> None:
        self.proc.terminate()


def file_source(path: str, realtime: bool = True) -> AudioSource:
    """An audio/video file, by default fed at real-time speed like a meeting."""
    cmd = ["ffmpeg", "-loglevel", "error"] + (["-re"] if realtime else [])
    return AudioSource(cmd + ["-i", path] + PCM_OUT)


def pulse_source(device: str) -> AudioSource:
    """Linux (PulseAudio or PipeWire): a sink monitor."""
    return AudioSource(["parec", f"--device={device}", "--raw", f"--rate={SAMPLE_RATE}",
                        "--channels=1", "--format=s16le", "--latency-msec=50"])


def avfoundation_source(device: str) -> AudioSource:
    """macOS: an input device such as BlackHole, read through ffmpeg."""
    return AudioSource(["ffmpeg", "-loglevel", "error", "-f", "avfoundation",
                        "-i", f":{device}"] + PCM_OUT)


def create_source(input_file: str | None, device: str | None, realtime: bool = True) -> AudioSource:
    from . import MACOS

    if input_file:
        return file_source(input_file, realtime)
    if MACOS:
        return avfoundation_source(device or MACOS_DEVICE)
    return pulse_source(device or LINUX_DEVICE)


def missing_tools(input_file: str | None) -> str | None:
    """A hint if a command-line tool this run needs isn't installed."""
    from . import MACOS

    if (input_file or MACOS) and not shutil.which("ffmpeg"):
        return "ffmpeg not found: run `make install`"
    if not input_file and not MACOS and not shutil.which("parec"):
        return "parec not found: sudo apt install pulseaudio-utils"
    return None
