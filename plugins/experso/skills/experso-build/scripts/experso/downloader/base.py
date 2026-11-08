from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

# Called once per finished video file, from the downloader's thread.
EmitVideo = Callable[[Path], None]


@dataclass
class Post:
    """One downloaded item (a post, a video, ...) with all its text, ready for
    extraction. Built by the downloader that knows its own file layout."""
    id: str                      # stable, unique within the profile; used for file names
    url: str | None
    date: str                    # ISO date, e.g. 2026-11-05
    kind: str | None             # e.g. "reel", "carousel", "image"
    caption: str                 # "" if none
    transcripts: list[tuple[str, str]] = field(default_factory=list)  # (file name, text)
    metrics: dict = field(default_factory=dict)  # likes, comments, views (None if unknown)
    images: list[str] = field(default_factory=list)  # absolute paths: slides, cover frames


class Downloader(ABC):
    """A source of videos (an Instagram profile, a YouTube channel, ...).

    Implementations download into the directory they are given and call
    `emit(path)` for each video as soon as it is completely written, so the
    transcriber can start on it while the download continues.
    """

    name: str  # registry key, e.g. "instagram"

    def __init__(self, **options):
        self.options = options

    @abstractmethod
    def download(self, target: str, dest: Path, emit: EmitVideo,
                 max_items: int | None = None, known: set[str] | None = None) -> int:
        """Download `target` into `dest` (the profile's cache). Return the number
        of new items.

        Must be incremental: skip items already on disk AND items whose Post.id
        is in `known` (processed in an earlier run; their files may have been
        deleted by `experso clean`), stopping early where the source allows.
        Emit every video in `dest` that belongs to a processed item, even if it
        was already on disk; the orchestrator skips ones already transcribed.
        """

    @abstractmethod
    def iter_posts(self, dest: Path) -> Iterator[Post]:
        """Yield every downloaded item in `dest` with its caption and
        transcripts (skip "[no audio]" transcripts), oldest first."""
