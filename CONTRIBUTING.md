# Contributing

Thanks for helping! The project goals are **fully local** (no cloud or paid APIs at runtime), **low delay**, and **easy to run** (`make install && make run`).

## Setup
```bash
make install        # dependencies, models, voice
make check          # unit tests (fast, no models needed)
make test FILE=clip.mp3 ARGS="--fast --no-tts"   # end-to-end on a file
```
Never commit meeting audio, transcripts or logs (`.gitignore` blocks `*.wav`, `*.mp3`, `*.txt`, `*.log`).

## Code layout
```
live_interpreter/
  cli.py          Command line. The only place that builds concrete classes and wires them together.
  config.py       Paths, UserConfig (.interpreter.conf from `make language`), Settings (one run).
  pipeline.py     Three threads joined by queues: capture → interpret → speak.
  chunker.py      SpeechChunker: energy VAD, cuts the stream at pauses. Pure, no I/O.
  interpreter.py  Interpreter: per chunk, decides what is shown and voiced. Depends on interfaces only.
  recognizer.py   Recognizer protocol + WhisperRecognizer (with a small model for language ID).
  translation.py  Translator: Passthrough (English) or ArgosTranslator (English → X).
  filters.py      Catches Whisper failures: hallucinations, untranslated German, prompt echoes.
  glossary.py     User corrections (glossary.cfg) applied to the final text, reloaded on change.
  tts.py          PiperSynthesizer.
  audio/          AudioSource / AudioSink / Ducker per platform (PulseAudio/PipeWire, macOS, files).
  languages.py    `language` command: finds voices and translation models and downloads them.
  console.py      Terminal output.
  licensing.py    Which languages/voices are license-verified; everything else needs --personal-use.
  transcript.py   Opt-in transcript file (--save-transcript).
tests/            pytest; models are replaced by fakes (see tests/test_interpreter.py).
```

Flow of one speech chunk:
```
AudioSource ─bytes→ SpeechChunker ─chunk→ Interpreter.process()
   detect language ─┬─ listener's language → transcribe → shown, not voiced
                    └─ other → Whisper translate → filters → Translator → Glossary → shown + voiced
                                                              → PiperSynthesizer → AudioSink
```

## Extending
Each part sits behind a small interface, so most features are one new class plus a line in `cli.py` or a factory:

| You want to add | Implement | Register in |
|---|---|---|
| Another speech engine (e.g. whisper.cpp, Vosk) | `Recognizer` protocol (`recognizer.py`) | `cli.run` |
| Another translation backend (e.g. NLLB) | `Translator` (`translation.py`) | `translator_for` |
| Another TTS engine | same `synth()`/`sample_rate` as `PiperSynthesizer` | `cli.run` |
| A platform (Windows, …) | `AudioSource` command and `AudioSink` | `audio.create_source` / `create_sink` |
| A new failure filter | function in `filters.py` + test | `Interpreter.process` |

Keep `Interpreter` free of I/O and model loading so it stays testable with fakes.

**Already evaluated** (on German news and meeting sentences → Turkish and Spanish, CPU):
direct translation models instead of the English pivot. MADLAD-400 3B makes up content (it swapped in other
politicians), M2M100 418M changes names, and NLLB-200 is licensed for non-commercial use only. A new translation
backend should beat the pivot route without making up content, and have a license that allows commercial use.

## Licensing
Contributions are accepted under the MIT license. Don't add dependencies or default models whose license blocks
commercial use. Mark anything without an explicit permissive license as unverified in `licensing.py`, update
THIRD_PARTY.md when you add a component, and use made-up example text and names in tests and docs.

## Style
- Python ≥ 3.9 (`from __future__ import annotations`), standard library + the dependencies in `pyproject.toml`.
- Small modules, one job each; comments explain *why*, not *what*.
- Add or update a test in `tests/` for logic changes; run `make check` before opening a PR.
- CI (`.github/workflows/check.yml`) runs the tests on Ubuntu and macOS with Python 3.9 and 3.12.
