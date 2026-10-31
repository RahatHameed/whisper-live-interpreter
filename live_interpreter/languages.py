"""`language` command: choose the language you hear and download what it needs
(a Piper voice and, for non-English, an Argos en->X translation model).
Standard library only, so it also works before the models are loaded."""
from __future__ import annotations

import json
import shutil
import sys
import urllib.request
import zipfile

from .config import MODELS_DIR, ROOT, VOICES_DIR, UserConfig
from .translation import model_dir
from .licensing import PREFERRED_VOICES, VERIFIED_TRANSLATION, license_problems

VOICES_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
ARGOS_INDEX = "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json"
PIPER_FAMILY = {"nb": "no"}             # Argos code -> Piper language family
QUALITY = {"medium": 0, "high": 1, "low": 2, "x_low": 3}


def _open(url, timeout):
    # argos-net.com rejects urllib's default User-Agent
    req = urllib.request.Request(url, headers={"User-Agent": "live-interpreter/1.0"})
    return urllib.request.urlopen(req, timeout=timeout)


def _download(url, path):
    print(f"  downloading {path.name} ...", flush=True)
    tmp = path.with_name(path.name + ".part")
    with _open(url, timeout=60) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(path)


class Catalog:
    """Languages we can speak: English, plus every language with both an Argos
    en->X model and a Piper voice."""

    def __init__(self):
        with _open(VOICES_URL + "voices.json", timeout=30) as r:
            voices = json.load(r)
        with _open(ARGOS_INDEX, timeout=30) as r:
            self.argos = {p["to_code"]: p for p in json.load(r) if p["from_code"] == "en"}
        self.voices = voices
        self.by_family: dict[str, list] = {}
        for v in voices.values():
            self.by_family.setdefault(v["language"]["family"], []).append(v)
        self.names = {"en": "English"}
        for code, p in self.argos.items():
            if PIPER_FAMILY.get(code, code) in self.by_family:
                self.names[code] = p["to_name"]

    def voice_for(self, code: str) -> dict:
        """The voice with the cleanest license if known, else the best one available."""
        if PREFERRED_VOICES.get(code) in self.voices:
            return self.voices[PREFERRED_VOICES[code]]
        candidates = self.by_family[PIPER_FAMILY.get(code, code)]
        return sorted(candidates, key=lambda v: (QUALITY.get(v["quality"], 9), v["key"]))[0]

    def install_voice(self, voice: dict) -> str:
        VOICES_DIR.mkdir(exist_ok=True)
        for rel in voice["files"]:
            if rel.endswith((".onnx", ".onnx.json")):
                path = VOICES_DIR / rel.rsplit("/", 1)[-1]
                if not path.exists():
                    _download(VOICES_URL + rel, path)
        return str((VOICES_DIR / f"{voice['key']}.onnx").relative_to(ROOT))

    def install_translation(self, code: str) -> None:
        target_dir = model_dir(code)
        if code == "en" or target_dir.is_dir():
            return
        MODELS_DIR.mkdir(exist_ok=True)
        pkg = MODELS_DIR / f"en_{code}.argosmodel"
        _download(next(u for u in self.argos[code]["links"] if u.startswith("http")), pkg)
        with zipfile.ZipFile(pkg) as z:
            top = z.namelist()[0].split("/")[0]
            z.extractall(MODELS_DIR)
        pkg.unlink()
        (MODELS_DIR / top).rename(target_dir)


def choose_language(code: str | None = None, personal_use: bool = False) -> None:
    print("Fetching voice and translation catalogues ...")
    catalog = Catalog()
    current = UserConfig.load().target
    if not code:
        print("\nWhich language do you want to hear?")
        print("  Verified for any use: " + ", ".join(
            f"{c} ({n})" for c, n in sorted(catalog.names.items()) if c in VERIFIED_TRANSLATION))
        print("  Personal use only (add PERSONAL=1): " + ", ".join(
            f"{c} ({n})" for c, n in sorted(catalog.names.items()) if c not in VERIFIED_TRANSLATION))
        code = input(f"Your language [{current}]: ").strip().lower() or current
    if code not in catalog.names:
        sys.exit(f"'{code}' is not supported. Pick one of: {', '.join(sorted(catalog.names))}")

    voice = catalog.voice_for(code)
    problems = license_problems(code, voice["key"])
    if problems and not personal_use:
        sys.exit(f"{catalog.names[code]} is not verified for commercial use: " + "; ".join(problems)
                 + f".\nFor personal use only, confirm with: make language TO={code} PERSONAL=1")
    voice_path = catalog.install_voice(voice)
    catalog.install_translation(code)
    UserConfig(target=code, voice=voice_path, personal_use=bool(problems)).save()  # after downloads
    print(f"\nOK: you will hear {catalog.names[code]} (voice {voice['key']}). "
          f"Change it any time with: make language")
    if problems:
        print("Confirmed for PERSONAL USE ONLY: " + "; ".join(problems) + ". See THIRD_PARTY.md.")
