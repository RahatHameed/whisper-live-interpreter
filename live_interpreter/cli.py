"""Command line. This is the only place that builds the concrete parts and wires
them together; everything else receives its dependencies.

    python -m live_interpreter [run] [options]     # live interpreter (default)
    python -m live_interpreter language [code]     # choose the language you hear
"""
from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path

from . import console, pipeline
from .audio import create_ducker, create_sink, create_source, missing_tools
from .chunker import ChunkerConfig, SpeechChunker
from .config import GLOSSARY_PATH, ROOT, TRANSCRIPTS_DIR, Settings, UserConfig
from .glossary import FileGlossary
from .interpreter import Interpreter
from .transcript import TranscriptWriter
from .licensing import license_problems

COMMANDS = ("run", "language")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="live_interpreter",
                                     description="Local live interpreter into your language")
    sub = parser.add_subparsers(dest="command")

    lang = sub.add_parser("language", help="choose the language you hear")
    lang.add_argument("code", nargs="?", help="e.g. en, de, tr (asks if omitted)")
    lang.add_argument("--personal-use", action="store_true",
                      help="confirm personal use for a language whose licenses aren't verified")

    user = UserConfig.load()
    p = sub.add_parser("run", help="run the live interpreter")
    g = p.add_argument_group("languages")
    g.add_argument("--target", default=user.target,
                   help="language you hear (default from `make language`, else en)")
    g.add_argument("--language", default="auto",
                   help="spoken language: auto (detect per chunk) or a code like de, fr; "
                        "a code is used whenever detection disagrees")
    g.add_argument("--voice-native", action="store_true",
                   help="also voice chunks already spoken in your language")
    g.add_argument("--prompt", default="",
                   help="names/products to help recognition (avoid common German words)")
    g.add_argument("--glossary", type=Path, default=GLOSSARY_PATH,
                   help="corrections file, lines like 'Meyer => Maier' (re-read on change)")

    g = p.add_argument_group("speech model")
    g.add_argument("--model", default="auto", help="auto | small | medium | large-v3")
    g.add_argument("--device", default="auto", help="auto | cuda | cpu")
    g.add_argument("--compute", default=None, help="compute type (float16, int8, int8_float16)")
    g.add_argument("--beam", type=int, default=1, help="beam size (1 = fastest)")

    g = p.add_argument_group("voice")
    g.add_argument("--voice", type=Path, default=user.voice_path,
                   help="Piper .onnx voice file (must match --target)")
    g.add_argument("--speed", type=float, default=1.1, help="speech speed (1.0 = normal)")
    g.add_argument("--max-lag", type=float, default=10.0, help="skip spoken lines older than this (s)")
    g.add_argument("--no-tts", action="store_true", help="text subtitles only")
    g.add_argument("--duck", type=float, default=0.3,
                   help="meeting volume while the voice speaks, as a fraction (1 = off; Linux)")

    g = p.add_argument_group("audio")
    g.add_argument("--source", default=None,
                   help="capture device (Linux: meeting_out.monitor, macOS: BlackHole 2ch)")
    g.add_argument("--sink", default=None, help="Linux: headphone sink for the voice")
    g.add_argument("--min-chunk", type=float, default=1.0, help="min seconds per chunk")
    g.add_argument("--max-chunk", type=float, default=6.0, help="target max seconds per chunk")
    g.add_argument("--silence", type=float, default=0.5, help="pause (s) that ends a chunk")
    g.add_argument("--threshold-db", type=float, default=-45.0, help="min speech level in dBFS")

    g = p.add_argument_group("testing")
    g.add_argument("--input-file", help="use an audio/video file instead of the meeting")
    g.add_argument("--fast", action="store_true", help="with --input-file: don't throttle to real time")
    g.add_argument("--out-wav", help="with --input-file: write the speech to a WAV instead of playing it")
    g.add_argument("--personal-use", action="store_true", default=user.personal_use,
                   help="allow parts whose licenses aren't verified (personal use only)")

    g = p.add_argument_group("transcript (off by default; may need participants' consent)")
    g.add_argument("--save-transcript", action="store_true",
                   help=f"save shown lines to {TRANSCRIPTS_DIR.name}/ (git-ignored, private files)")
    return parser


def settings_from(args: argparse.Namespace) -> Settings:
    return Settings(
        target=args.target, voice=args.voice, language=args.language, prompt=args.prompt,
        glossary=args.glossary,
        voice_native=args.voice_native, model=args.model, device=args.device,
        compute=args.compute, beam=args.beam, speed=args.speed, max_lag=args.max_lag,
        tts=not args.no_tts, duck=args.duck, source=args.source, sink=args.sink, input_file=args.input_file,
        realtime=not args.fast, out_wav=args.out_wav, save_transcript=args.save_transcript,
        personal_use=args.personal_use,
        chunking=ChunkerConfig(min_chunk=args.min_chunk, max_chunk=args.max_chunk,
                               silence=args.silence, threshold_db=args.threshold_db),
    )


def run(s: Settings) -> None:
    from .recognizer import WhisperRecognizer
    from .translation import translator_for
    from .tts import PiperSynthesizer

    problem = missing_tools(s.input_file)
    if problem:
        sys.exit(problem)
    if s.out_wav and not s.input_file:
        sys.exit("--out-wav only works with --input-file (meetings are never recorded)")
    if s.tts and not (s.voice and s.voice.exists()):
        sys.exit("No Piper voice found. Run `make language` or pass --voice path/to/voice.onnx")
    problems = license_problems(s.target, s.voice.stem if s.tts else None)
    if problems and not s.personal_use:
        sys.exit("Not verified for commercial use: " + "; ".join(problems) + ".\n"
                 "Use English (make language TO=en), or confirm personal use with "
                 f"make language TO={s.target} PERSONAL=1. See THIRD_PARTY.md.")
    try:
        translator = translator_for(s.target)
    except FileNotFoundError as e:
        sys.exit(str(e))

    console.log("For personal use. You are responsible for consent in meetings and for the "
                "licenses of downloaded models (README, THIRD_PARTY.md).")
    if problems:
        console.log("PERSONAL USE ONLY: " + "; ".join(problems))
    console.log(f"Loading Whisper '{s.model}' ...")
    recognizer = WhisperRecognizer(s.model, s.device, s.compute, s.beam)
    console.log(f"Whisper {recognizer.description}")
    if recognizer.warning:
        console.log(f"WARNING: {recognizer.warning}")
    interpreter = Interpreter(recognizer, translator, target=s.target,
                              expected=None if s.language == "auto" else s.language,
                              prompt=s.prompt, voice_native=s.voice_native,
                              glossary=FileGlossary(s.glossary), log=console.log)
    if s.glossary.exists():
        console.log(f"Glossary: {s.glossary.name} (edits apply immediately)")
    synth = PiperSynthesizer(s.voice, s.speed) if s.tts else None
    sink = create_sink(s.out_wav, s.sink) if s.tts else None
    ducker = create_ducker(s.duck, live=not (s.input_file or s.out_wav))

    transcript = TranscriptWriter(TRANSCRIPTS_DIR, s.target) if s.save_transcript else None
    if transcript:
        console.log(f"Saving transcript to {transcript.path.relative_to(ROOT)}. "
                    "Make sure the participants agree.")

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: (stop.set(), console.log("Stopping ...")))
    console.log(f"Ready. Listening ... (you hear: {s.target})")
    source = create_source(s.input_file, s.source, s.realtime)
    try:
        pipeline.run(source, SpeechChunker(s.chunking), interpreter, synth, sink, ducker,
                     s.max_lag, stop, on_line=transcript)
    finally:
        if transcript:
            transcript.close()


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in COMMANDS + ("-h", "--help"):
        argv.insert(0, "run")                   # `run` is the default command
    args = build_parser().parse_args(argv)
    if args.command == "language":
        from .languages import choose_language
        choose_language(args.code, args.personal_use)
    else:
        run(settings_from(args))
