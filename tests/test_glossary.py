import os

from live_interpreter.glossary import FileGlossary, Glossary, parse


def test_parse_ignores_comments_and_blank_lines():
    rules = parse("# header\n\nAcme => ACME   # brand\nbad line\n => nothing\n")
    assert rules == [("Acme", "ACME")]


def test_whole_words_case_insensitive():
    g = Glossary([("acme", "ACME"), ("KI", "AI")])
    assert g("The Acme shop uses KI.") == "The ACME shop uses AI."
    assert g("Acmeville and skiing stay.") == "Acmeville and skiing stay."


def test_longer_phrase_wins():
    g = Glossary([("model", "Modell"), ("KI model", "AI model")])
    assert g("The KI model is new.") == "The AI model is new."


def test_umlauts_and_punctuation():
    g = Glossary([("Grün-Süd", "Grün Süd")])
    assert g("Team Grün-Süd.") == "Team Grün Süd."
    assert g("Team Grün-Südwest.") == "Team Grün-Südwest."     # umlauts count as word characters


def test_file_is_reloaded_when_changed(tmp_path):
    path = tmp_path / "glossary.cfg"
    g = FileGlossary(path)
    assert g("Atlass") == "Atlass"              # no file yet
    path.write_text("Atlass => Atlas\n")
    assert g("Atlass") == "Atlas"
    path.write_text("Atlass => Atlas 2\n")
    os.utime(path, (1, 1))                      # force a new mtime even within the same second
    assert g("Atlass") == "Atlas 2"
    path.unlink()
    assert g("Atlass") == "Atlass"
