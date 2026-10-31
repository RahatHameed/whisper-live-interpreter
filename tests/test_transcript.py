import stat

from live_interpreter.interpreter import Line
from live_interpreter.transcript import TranscriptWriter


def test_writes_private_file_with_source_languages(tmp_path):
    folder = tmp_path / "transcripts"
    t = TranscriptWriter(folder, target="en")
    t(Line(text="Good morning.", language="de", native=False))
    t(Line(text="Quick update.", language="en", native=True))
    text = t.path.read_text()                  # readable before close: flushed per line
    t.close()

    assert "(de→en) Good morning." in text
    assert "(en) Quick update." in text
    assert stat.S_IMODE(t.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
