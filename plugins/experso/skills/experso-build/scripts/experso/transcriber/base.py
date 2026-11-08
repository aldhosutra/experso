from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Transcript:
    text: str
    language: str | None = None


class Transcriber(ABC):
    """Turns one media file (with an audio track) into text.

    Load models in __init__ so they load once. The orchestrator calls
    `transcribe` from the main thread only, and only for files that have audio.
    """

    name: str  # registry key, e.g. "mlx-whisper"

    def __init__(self, language: str | None = None, model: str | None = None, **options):
        self.language = language  # None = auto-detect
        self.model = model        # None = implementation default
        self.options = options

    @abstractmethod
    def transcribe(self, media: Path) -> Transcript: ...
