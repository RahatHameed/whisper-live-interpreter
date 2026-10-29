# Third-party components and licenses

The project is intended for personal, private use. The code in this repository is MIT-licensed (see [LICENSE](LICENSE)). It does **not** ship any third-party code or models. They are installed or
downloaded on your machine by `make install` / `make language`, and each comes with its own license.
If you distribute or sell a product that **bundles** them, you must follow their licenses too.

*This is a summary to help you check; it is not legal advice. Verify the licenses yourself before commercial use.*

## Software (installed with pip)
| Component | Used for | License |
|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | speech recognition / translation | MIT |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | model runtime | MIT |
| [piper-tts](https://github.com/OHF-Voice/piper1-gpl) | text to speech | **GPL-3.0-or-later** |
| [SentencePiece](https://github.com/google/sentencepiece) | tokenizer for translation models | Apache-2.0 |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime), [NumPy](https://numpy.org) | runtime | MIT, BSD |

**piper-tts is GPL-3.0.** Using it as an installed dependency, as this project does, is fine. If you distribute a
package or installer that *includes* piper-tts, the GPL applies to that distribution (for example, you must provide
its source code). To avoid this, keep it as a separate install step, or swap in another TTS engine
(see "Extending" in [CONTRIBUTING.md](CONTRIBUTING.md)).

## Models (downloaded)
| Model | Used for | License |
|---|---|---|
| OpenAI Whisper (`medium`, `base`, … via [Systran](https://huggingface.co/Systran)) | recognition, translation to English, language ID | MIT |
| [Argos Translate](https://github.com/argosopentech/argos-translate) packages (en → X) | translation to non-English languages | **no explicit license** on the model packages (the Argos software is MIT/CC0); trained on mixed web corpora (OPUS, CCMatrix, WikiMatrix, …): **personal use only** |
| [Piper voices](https://huggingface.co/rhasspy/piper-voices) | the spoken voice | **one license per voice**, see below |

## Voices
Every Piper voice carries the license of the recordings it was trained on (see each voice's `MODEL_CARD`).
Many are **research-only or non-commercial**, for example the popular `en_US-lessac` voice and the Turkish
`tr_TR-dfki` voice, and many others were fine-tuned from lessac, which makes their status unclear.

## What `make language` allows
A language is **verified** only if every part it needs has an explicit license that allows any use. Right now that's
**English only**: Whisper (MIT) plus `en_US-ljspeech-medium` (public domain recordings, trained from scratch).

Every other language needs an Argos translation model (no explicit license), so `make language` refuses it unless
you confirm personal use (`make language TO=de PERSONAL=1`), and `make run` repeats the reminder at every start.
For those languages it still picks the voice with the cleanest license, listed in
[`live_interpreter/licensing.py`](live_interpreter/licensing.py) (checked 2026-10-29):

| Language | Voice | Dataset license |
|---|---|---|
| Catalan | ca_ES-upc_ona-x_low | CC BY-SA 3.0 ES |
| Dutch | nl_BE-rdh-medium | CC0 |
| English | en_US-ljspeech-medium | public domain (verified) |
| French | fr_FR-mls-medium | CC BY 4.0 |
| German | de_DE-mls-medium | CC BY 4.0 |
| Greek | el_GR-rapunzelina-medium | CC0 |
| Italian | it_IT-serena-medium | CC BY 4.0 |
| Norwegian | no_NO-nvcc-medium | CC0 |
| Spanish | es_ES-carlfm-x_low | public domain |
| Swedish | sv_SE-nst-medium | CC0 |
| Ukrainian | uk_UA-ukrainian_tts-medium | CC0 |

CC BY voices require attribution when you share their output: credit the dataset (e.g. "Multilingual LibriSpeech,
CC BY 4.0") and the voice. To verify another language, both its translation model and its voice need an explicit,
permissive license; add them to `licensing.py` with the source of that information.
