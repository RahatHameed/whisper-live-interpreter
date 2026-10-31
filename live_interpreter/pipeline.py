"""The three stages, each on its own thread, connected by queues:

    capture  : AudioSource -> SpeechChunker          -> chunks queue
    interpret: chunks      -> Interpreter -> console -> speech queue
    speak    : speech      -> PiperSynthesizer       -> AudioSink (meeting audio ducked meanwhile)

`None` on a queue means "end of stream" and shuts the next stage down.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Callable

from . import console
from .audio import AudioSink, AudioSource, Ducker
from .chunker import SpeechChunker, iter_frames
from .interpreter import Interpreter, Line
from .tts import PiperSynthesizer


def capture(source: AudioSource, chunker: SpeechChunker, chunks: queue.Queue,
            stop: threading.Event) -> None:
    try:
        for frame in iter_frames(source.read, chunker.frame_size):
            if stop.is_set():
                break
            chunk = chunker.feed(frame)
            if chunk is not None:
                chunks.put((time.time(), chunk))
        last = chunker.flush()
        if last is not None:
            chunks.put((time.time(), last))
    finally:
        source.close()
        chunks.put(None)


def interpret(interpreter: Interpreter, chunks: queue.Queue, speech: queue.Queue | None,
              on_line: Callable[[Line], None] | None = None) -> None:
    try:
        while (item := chunks.get()) is not None:
            t_end, audio = item
            t0 = time.time()
            line = interpreter.process(audio)
            if line is None:
                continue
            now = time.time()
            console.show(line, interpreter.target, now - t_end, now - t0, chunks.qsize())
            if on_line:
                on_line(line)
            if speech is not None and not line.native:
                speech.put((t_end, line.text))
    finally:
        if speech is not None:
            speech.put(None)


def speak(synth: PiperSynthesizer, sink: AudioSink, ducker: Ducker, speech: queue.Queue,
          max_lag: float) -> None:
    try:
        while (item := speech.get()) is not None:
            t_end, text = item
            lag = time.time() - t_end
            if lag > max_lag and not speech.empty():
                console.log(f"(skipped spoken line, {lag:.0f}s behind; still shown above)")
                continue
            pcm = synth.synth(text, hurry=lag > max_lag / 2)
            ducker.duck()
            sink.play(pcm, synth.sample_rate)
            if speech.empty():          # keep it down between back-to-back lines
                ducker.restore()
    finally:
        ducker.restore()
        sink.close()


def run(source: AudioSource, chunker: SpeechChunker, interpreter: Interpreter,
        synth: PiperSynthesizer | None, sink: AudioSink | None, ducker: Ducker, max_lag: float,
        stop: threading.Event, on_line: Callable[[Line], None] | None = None) -> None:
    """Run until the source ends or `stop` is set. `on_line` also receives every shown line."""
    chunks: queue.Queue = queue.Queue()
    speech: queue.Queue | None = queue.Queue() if synth else None
    threads = [threading.Thread(target=capture, args=(source, chunker, chunks, stop), daemon=True),
               threading.Thread(target=interpret, args=(interpreter, chunks, speech, on_line),
                                daemon=True)]
    if synth and sink:
        threads.append(threading.Thread(target=speak, args=(synth, sink, ducker, speech, max_lag),
                                        daemon=True))
    for t in threads:
        t.start()
    try:
        for t in threads:
            while t.is_alive():
                t.join(0.5)
    except KeyboardInterrupt:
        stop.set()
