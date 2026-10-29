import json

from live_interpreter.audio.ducking import LoopbackDucker


class FakePactl:
    def __init__(self, volume=(65536, 32768), owner=42):
        self.inputs = [{"index": 7, "owner_module": owner,
                        "volume": {"front-left": {"value": volume[0]},
                                   "front-right": {"value": volume[1]}}}]
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        if args[:3] == ("-f", "json", "list"):
            return json.dumps(self.inputs)
        return ""


def ducker(tmp_path, pactl, level=0.3):
    modules = tmp_path / "modules"
    modules.write_text("42\n41\n")              # loopback module first, null sink second
    return LoopbackDucker(level, pactl=pactl, modules_file=modules)


def test_ducks_relative_to_current_volume_and_restores_it(tmp_path):
    pactl = FakePactl(volume=(65536, 32768))
    d = ducker(tmp_path, pactl)
    d.duck()
    assert pactl.calls[-1] == ("set-sink-input-volume", "7", "19660", "9830")
    d.restore()
    assert pactl.calls[-1] == ("set-sink-input-volume", "7", "65536", "32768")


def test_duck_twice_keeps_the_original_level(tmp_path):
    pactl = FakePactl()
    d = ducker(tmp_path, pactl)
    d.duck()
    d.duck()                                    # back-to-back lines
    d.restore()
    assert pactl.calls[-1] == ("set-sink-input-volume", "7", "65536", "32768")


def test_no_loopback_means_no_changes(tmp_path):
    pactl = FakePactl(owner=99)
    d = ducker(tmp_path, pactl)
    d.duck()
    d.restore()
    assert all(c[0] != "set-sink-input-volume" for c in pactl.calls)


def test_missing_modules_file_is_harmless(tmp_path):
    d = LoopbackDucker(0.3, pactl=FakePactl(), modules_file=tmp_path / "missing")
    d.duck()
    d.restore()
