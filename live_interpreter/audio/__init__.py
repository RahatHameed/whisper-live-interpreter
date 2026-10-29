"""Platform audio I/O. To support a new platform, add an AudioSource and an
AudioSink and pick them in `create_source` / `create_sink`."""
import sys

MACOS = sys.platform == "darwin"

from .ducking import Ducker, LoopbackDucker, NoDucking  # noqa: E402
from .sinks import AudioSink, create_sink  # noqa: E402
from .sources import AudioSource, create_source, missing_tools  # noqa: E402


def create_ducker(level: float, live: bool) -> Ducker:
    """Duck the meeting loopback while speaking (Linux, live meetings, level < 1)."""
    if MACOS or not live or level >= 1:
        return NoDucking()
    return LoopbackDucker(level)


__all__ = ["MACOS", "AudioSink", "AudioSource", "Ducker", "create_ducker", "create_sink",
           "create_source", "missing_tools"]
