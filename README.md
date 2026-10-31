# live-interpreter

Hear a live **spoken translation in your own language** while a meeting (MS Teams in the browser, or any audio) runs.
Fully local: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) recognizes and translates, [Piper](https://github.com/rhasspy/piper) speaks.
No audio or text leaves your computer, and no paid service or API key is needed.

- **Any spoken language in**: the language is detected per sentence (about 100 languages).
- **Your language out**: English by default; about 40 others for personal use (de, fr, es, it, tr, pl, nl, ru, uk, ar, zh, …).
- **People who already speak your language are not translated**: their lines are shown but not voiced.
- **The meeting audio is turned down while the translation speaks** (Linux), then back to your level.

> **Intended for personal, private use.** This is a hobby project, provided as is, without warranty.
> You are responsible for using it lawfully: get consent where meetings require it, follow your organisation's rules,
> and respect the licenses of the models and voices it downloads (see [Legal notes](#legal-notes)).
> It's an aid for following a conversation, not a certified interpreter.

Before using it in real meetings, go through the [checklist](#before-using-it-in-meetings).

```
Teams (browser) → MeetingOut ─┬─ loopback → headphones (original, quieter)
                              └─ capture → cut at pauses → Whisper (→ English)
                                   → [en → your language] → Piper → headphones
```

## Quick start (Linux)
```bash
make install      # audio tools (sudo apt), Python env, voice; asks which language you want to hear
make audio        # creates the MeetingOut sink, looped to your headphones
```
Then start the meeting (or a video) so the browser is playing audio, and:
```bash
make route        # moves the playing browser audio into MeetingOut
make run          # Ctrl+C to stop
make audio-undo   # restore normal audio when done
```
Still hearing only the original? The browser isn't in MeetingOut: run `make route` again while audio is playing
(or set it in **pavucontrol → Playback**). Browsers create their audio stream only while playing.

## Quick start (macOS)
Needs [Homebrew](https://brew.sh) and the Xcode command line tools (`xcode-select --install`, for `make`).

```bash
make install      # ffmpeg + BlackHole (virtual audio device) via brew, Python env, voice, your language
```
One-time audio setup (log out and back in first if BlackHole doesn't show up):
1. Open **Audio MIDI Setup** → **+** → **Create Multi-Output Device**.
   Tick your **headphones** (first) and **BlackHole 2ch**, and enable *Drift Correction* for BlackHole.
2. In **Teams → Settings → Devices → Speaker**, choose that **Multi-Output Device**.
   Keep the **system output on your headphones**: the translation plays there, and it must not go
   into BlackHole or it would be translated again.

Then `make run`. The interpreter listens on `BlackHole 2ch` (change with `ARGS="--source '<device>'"`).

> macOS support is new and not yet tested on a Mac. Please open an issue if something doesn't work.

## Commands
| Command | What it does |
|---|---|
| `make install` | One-time setup; asks for your language the first time |
| `make language` | Change the language you hear (`make language TO=tr` without asking) |
| `make run` | Live interpreter |
| `make run-de` | Live, for meetings in German (steadier than auto-detection) |
| `make run-fast` | Live with the `small` model: about half the delay, less accurate |
| `make subtitles` | Live, text only, no voice |
| `make test FILE=clip.mp3` | Try it on an audio/video file instead of a meeting |
| `make audio` / `make audio-undo` | Linux: create / remove the MeetingOut sink |
| `make route` | Linux: move the playing browser audio into MeetingOut |
| `make options` | All interpreter options |
| `make check` | Unit tests |

Variables: `LANG_IN=de` (spoken language hint), `MODEL=small`, `PROMPT="names, products"`, `ARGS="--speed 1.25"`.
Example: `make run LANG_IN=de PROMPT="Project Atlas, Nordwind"`.

## Tuning
| Problem | Try |
|---|---|
| Delay too high / backlog growing | `make run-fast`, `ARGS="--speed 1.25"` |
| Names or products misheard | Add them to the glossary (below), or `PROMPT="Name1, Product2"` (**names only**: common German words in the prompt make Whisper stop translating) |
| Language detected wrongly | `LANG_IN=de` (or the meeting's language) |
| Sentences cut mid-way | `ARGS="--silence 0.7 --max-chunk 8"` |
| Quiet speakers ignored | `ARGS="--threshold-db -50"` |
| Voice lags behind | `make subtitles` |
| You also want your own language voiced | `ARGS="--voice-native"` |
| Original too loud/quiet under the voice | `ARGS="--duck 0.15"` (quieter) … `--duck 1` (no ducking) |

Defaults: CPU → Whisper `medium` int8, NVIDIA GPU → `large-v3` float16. Don't use `large-v3-turbo` (it can't translate).
On a 16-core laptop CPU, `medium` takes about 3.3 s per chunk and `small` about 1.6 s (but it drops and garbles more).
The voice starts after the speaker's pause plus that time. Shorter chunks don't help: Whisper's cost per chunk is fixed.

## Glossary
Fix recurring mistakes in what you see and hear:
```bash
cp glossary.example.cfg glossary.cfg     # personal, git-ignored
```
Write one rule per line in **your** language, e.g. `Meyer => Maier` or `shopping basket => cart`.
Matching ignores case and only hits whole words. The file is re-read when it changes, so you can add a rule during a meeting
and it applies to the next sentence.

## Saving a transcript (opt-in)
`make run ARGS="--save-transcript"` writes every shown line to `transcripts/<date_time>.md`
(git-ignored, readable only by you). It's off by default: **recording a meeting may need the participants' consent**,
so go through the [checklist](#before-using-it-in-meetings) first.

## How it works and limits
- Whisper can only translate **into English**. For other languages, the English text is translated again by a
  small local [Argos Translate](https://github.com/argosopentech/argos-translate) model, so quality is a bit lower than for English.
- Translation can mangle names, jargon and overlapping speech. It is not an official interpreter, so don't rely on it for legal,
  contractual or safety-critical decisions.
- Downloads (once): Whisper models (~1.5 GB, in `~/.cache/huggingface`), a voice (~60 MB) and, for non-English, a
  translation model (~130 MB). After that it works offline.

## Before using it in meetings
- [ ] Check your organisation's policy on processing meeting audio with tools like this one.
- [ ] Check whether you may install software (Python packages, models) on the computer you use.
- [ ] Ask participants for consent where the policy or local law requires it.
- [ ] Do a dry run in a low-stakes meeting before relying on it.

If any answer is "not allowed", don't use it there; ask for an approved alternative (e.g. a human interpreter).

## Legal notes
- **Meeting audio is never stored.** It's processed in memory and discarded. `--out-wav` only works with test files.
  Transcripts are off unless you pass `--save-transcript`.
- **Only what you already hear is processed**: the audio your computer plays for you as a participant.
  Still, follow your organisation's rules, and tell participants if that's expected where you are.
- **Licenses are checked for you.** Only **English** (Whisper + the public-domain LJSpeech voice) is verified for any use.
  Other languages need a translation model without an explicit license and often a non-commercial voice, so
  `make language` refuses them unless you confirm personal use: `make language TO=de PERSONAL=1`.
  `make run` then reminds you at every start.
- Mentions of Microsoft Teams, YouTube and other products only describe compatibility. This project isn't affiliated
  with or endorsed by them.
- This is not legal advice. When in doubt, ask your legal or compliance team.

## License
The code is [MIT](LICENSE). The components it downloads have their own licenses: **piper-tts is GPL-3.0**, and
several voices and the non-English translation models are for personal use only. Details: [THIRD_PARTY.md](THIRD_PARTY.md).

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for the code layout and how to add a language engine, TTS or platform.
