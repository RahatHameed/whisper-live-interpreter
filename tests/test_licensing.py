from live_interpreter.licensing import (PREFERRED_VOICES, VERIFIED_TRANSLATION, VERIFIED_VOICES,
                                       license_problems)


def test_preferred_voices_match_their_language():
    family = {"nb": "no"}
    for code, voice in PREFERRED_VOICES.items():
        assert voice.startswith(family.get(code, code) + "_"), voice


def test_english_with_ljspeech_is_verified():
    assert license_problems("en", "en_US-ljspeech-medium") == []
    assert license_problems("en", None) == []                # subtitles only


def test_unverified_parts_are_reported():
    assert license_problems("en", "en_US-lessac-medium")    # research-only licence
    assert len(license_problems("tr", "tr_TR-dfki-medium")) == 2
    assert license_problems("de", "de_DE-mls-medium")       # translation not verified


def test_every_verified_voice_is_a_preferred_voice():
    assert VERIFIED_VOICES <= set(PREFERRED_VOICES.values())
    assert VERIFIED_TRANSLATION <= set(PREFERRED_VOICES)
