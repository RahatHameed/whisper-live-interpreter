"""Local live interpreter: hear any spoken language in your own language.

Pipeline (one thread per stage, connected by queues):

    AudioSource -> SpeechChunker -> Interpreter -> PiperSynthesizer -> AudioSink
                   (cut at pauses)  (Whisper + filters
                                     + optional en->X translation)

Everything runs locally; no audio or text leaves the machine.
"""

__version__ = "0.2.0"
