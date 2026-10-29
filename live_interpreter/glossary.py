"""Fixed corrections applied to the final text, e.g. misheard names or product terms.

File format (one rule per line, `#` starts a comment):

    Meyer => Maier
    shopping basket => cart

Matching ignores case and only hits whole words/phrases; longer phrases win.
The file is re-read when it changes, so rules can be added during a meeting.
"""
from __future__ import annotations

import re
from pathlib import Path


def parse(text: str) -> list[tuple[str, str]]:
    rules = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if "=>" in line:
            wrong, right = (part.strip() for part in line.split("=>", 1))
            if wrong:
                rules.append((wrong, right))
    return rules


class Glossary:
    def __init__(self, rules: list[tuple[str, str]] | None = None):
        self._set(rules or [])

    def _set(self, rules):
        self.rules = sorted(rules, key=lambda r: -len(r[0]))
        self.replacements = {wrong.lower(): right for wrong, right in self.rules}
        self.pattern = re.compile(
            r"(?<!\w)(" + "|".join(re.escape(w) for w, _ in self.rules) + r")(?!\w)",
            re.IGNORECASE) if self.rules else None

    def __call__(self, text: str) -> str:
        if not self.pattern:
            return text
        return self.pattern.sub(lambda m: self.replacements[m.group(0).lower()], text)


class FileGlossary(Glossary):
    """A Glossary backed by a file that may not exist yet and may change while running."""

    def __init__(self, path: Path):
        self.path = path
        self.mtime: float | None = None
        super().__init__()

    def __call__(self, text):
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            mtime = None
        if mtime != self.mtime:
            self.mtime = mtime
            self._set(parse(self.path.read_text()) if mtime is not None else [])
        return super().__call__(text)
