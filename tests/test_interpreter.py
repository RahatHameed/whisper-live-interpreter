import numpy as np

from live_interpreter.interpreter import Interpreter
from live_interpreter.translation import Passthrough, Translator

AUDIO = np.zeros(16000, dtype=np.float32)


class FakeRecognizer:
    """Returns canned results and records how it was called."""

    def __init__(self, language="de", confidence=0.95, translations=None, transcript=""):
        self.language, self.confidence = language, confidence
        self.translations = list(translations or ["Hello."])
        self.transcript = transcript
        self.calls = []

    def detect_language(self, audio):
        return self.language, self.confidence

    def translate(self, audio, language, prompt=""):
        self.calls.append(("translate", language, prompt))
        return self.translations.pop(0)

    def transcribe(self, audio, language, prompt=""):
        self.calls.append(("transcribe", language, prompt))
        return self.transcript


class Upper(Translator):
    def __call__(self, english):
        return english.upper()


def make(recognizer, target="en", translator=None, **kw):
    return Interpreter(recognizer, translator or Passthrough(), target=target,
                       log=lambda _: None, **kw)


def test_foreign_speech_is_translated_and_voiced():
    line = make(FakeRecognizer(translations=["Good morning."])).process(AUDIO)
    assert line.text == "Good morning." and not line.native


def test_speech_in_listener_language_is_shown_not_voiced():
    rec = FakeRecognizer(language="en", transcript="Quick update.")
    line = make(rec).process(AUDIO)
    assert line.native and line.text == "Quick update."
    assert rec.calls == [("transcribe", "en", "")]


def test_unsure_detection_is_not_treated_as_native():
    rec = FakeRecognizer(language="en", confidence=0.6)
    assert not make(rec).process(AUDIO).native


def test_voice_native_flag_voices_everything():
    rec = FakeRecognizer(language="en")
    assert not make(rec, voice_native=True).process(AUDIO).native


def test_non_english_target_goes_through_translator():
    rec = FakeRecognizer(language="de", translations=["Good morning."])
    line = make(rec, target="tr", translator=Upper()).process(AUDIO)
    assert line.text == "GOOD MORNING."


def test_native_speech_skips_translator():
    rec = FakeRecognizer(language="tr", transcript="Günaydın.")
    line = make(rec, target="tr", translator=Upper()).process(AUDIO)
    assert line.native and line.text == "Günaydın."


def test_expected_language_overrides_detection():
    rec = FakeRecognizer(language="nl", confidence=0.9)
    make(rec, expected="de").process(AUDIO)
    assert rec.calls[0] == ("translate", "de", "")


def test_german_output_with_prompt_is_retried_without_prompt():
    rec = FakeRecognizer(translations=["Die Kunden und der Support.", "The customers and support."])
    line = make(rec, prompt="Kunden").process(AUDIO)
    assert line.text == "The customers and support."
    assert rec.calls[1] == ("translate", "de", "")


def test_untranslated_german_is_dropped():
    rec = FakeRecognizer(translations=["Die Kunden und der Support."])
    assert make(rec).process(AUDIO) is None


def test_glossary_applies_after_translation_and_to_native_lines():
    fix = lambda text: text.replace("Atlass", "Atlas")   # noqa: E731
    rec = FakeRecognizer(translations=["Atlass is paused."])
    assert make(rec, target="tr", translator=Upper(), glossary=fix).process(AUDIO).text \
        == "ATLASS IS PAUSED."                              # rules are in the listener's language
    rec = FakeRecognizer(language="en", transcript="Atlass is paused.")
    assert make(rec, glossary=fix).process(AUDIO).text == "Atlas is paused."


def test_prompt_echo_and_hallucination_are_dropped():
    assert make(FakeRecognizer(translations=["Stiftung, Kranich"]), prompt="Nordwind Stiftung, Kranich") \
        .process(AUDIO) is None
    assert make(FakeRecognizer(translations=["Thank you."])).process(AUDIO) is None
