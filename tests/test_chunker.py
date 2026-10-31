import numpy as np

from live_interpreter.chunker import SAMPLE_RATE, SpeechChunker, iter_frames


def tone(seconds, amplitude=8000):
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.int16)


def silence(seconds):
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.int16)


def chunks_of(audio):
    chunker = SpeechChunker()
    data = audio.tobytes()
    pos = 0

    def read(n):
        nonlocal pos
        out, pos = data[pos:pos + n], pos + n
        return out

    out = [c for f in iter_frames(read, chunker.frame_size) if (c := chunker.feed(f)) is not None]
    last = chunker.flush()
    return out + ([last] if last is not None else [])


def test_cuts_at_pauses():
    audio = np.concatenate([silence(1), tone(2), silence(1), tone(3), silence(1)])
    lengths = [len(c) / SAMPLE_RATE for c in chunks_of(audio)]
    assert len(lengths) == 2
    assert 2 <= lengths[0] < 3 and 3 <= lengths[1] < 4


def test_long_speech_is_capped():
    lengths = [len(c) / SAMPLE_RATE for c in chunks_of(tone(25))]
    assert len(lengths) >= 3
    assert max(lengths) <= 10.1                 # max_chunk 6 s + 4 s hard cap


def test_silence_and_clicks_produce_nothing():
    click = tone(0.06)
    assert chunks_of(np.concatenate([silence(2), click, silence(2)])) == []
