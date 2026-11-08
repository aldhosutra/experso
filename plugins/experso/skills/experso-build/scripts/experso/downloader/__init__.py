"""Downloader registry. To add a source, write a Downloader subclass in this
folder and add a line here ("name": "module:ClassName"). Modules are imported
only when used, so one source's dependencies aren't needed for another."""
from importlib import import_module

from .base import Downloader

REGISTRY = {
    "instagram": "instagram:InstagramDownloader",
}


def get_downloader(name: str, **options) -> Downloader:
    if name not in REGISTRY:
        raise SystemExit(f"Unknown source {name!r}. Available: {', '.join(REGISTRY)}")
    module, cls = REGISTRY[name].split(":")
    return getattr(import_module(f".{module}", __name__), cls)(**options)
