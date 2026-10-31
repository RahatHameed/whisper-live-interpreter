import pytest

from live_interpreter.filters import echoes_prompt, is_hallucination, looks_german


@pytest.mark.parametrize("text", [
    "Wir haben die Tests und die Doku für das neue Modul noch nicht fertig.",
    "Die Kollegen aus dem Support melden sich morgen bei dem Kunden.",
    "Nachdem ein Kunde...",
])
def test_untranslated_german_is_detected(text):
    assert looks_german(text)


@pytest.mark.parametrize("text", [
    "We are asking for a review of the release plan.",
    "and the Sommerfest am Freitag in Berlin. Since 2019, the team has organised "
    "the event together with the works council.",
    "Plants die in the dark, said the gardener.",
    "20 to 30°C",
])
def test_english_is_not_flagged(text):
    assert not looks_german(text)


def test_prompt_echo():
    prompt = "Projekt Atlas, Nordwind Stiftung, Kranich"
    assert echoes_prompt("Stiftung, Kranich", prompt)
    assert not echoes_prompt("Kranich is closing stores", prompt)
    assert not echoes_prompt("Stiftung", "")


def test_hallucinations():
    assert is_hallucination("Thank you.")
    assert not is_hallucination("Thank you, Thomas, for the update.")
