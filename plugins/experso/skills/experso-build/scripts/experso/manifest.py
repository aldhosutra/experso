"""Per-profile manifest (state/manifest.json): which posts have been downloaded,
transcribed and extracted, so incremental runs keep working after `experso clean`
deletes the cached media and transcripts."""
import json
import time
from pathlib import Path

from .paths import Profile


class Manifest:
    def __init__(self, profile: Profile):
        self.path = profile.manifest
        self.data = {"handle": profile.handle, "posts": {}, "history": []}
        if self.path.exists():
            self.data = json.loads(self.path.read_text())

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, ensure_ascii=False))
        tmp.replace(self.path)

    def post(self, post_id: str) -> dict:
        return self.data["posts"].setdefault(post_id, {})

    def mark(self, post_id: str, **fields):
        self.post(post_id).update(fields)

    def known(self, field: str = "downloaded") -> set[str]:
        return {k for k, v in self.data["posts"].items() if v.get(field)}

    def log(self, step: str, **info):
        self.data["history"].append({"step": step, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), **info})
