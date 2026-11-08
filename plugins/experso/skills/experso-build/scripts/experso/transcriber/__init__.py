"""Transcriber registry.

To add a transcriber: write a Transcriber subclass in this folder, then add a
TranscriberInfo entry below describing where it runs. The info lives here (not
on the class) so `run.py --list-transcribers` can show and check it without
importing heavy dependencies.
"""
import importlib.util
import platform
import shutil
import sys
from dataclasses import dataclass, field
from importlib import import_module

from .base import Transcriber, Transcript

OS_NAMES = {"darwin": "macos", "linux": "linux", "win32": "windows"}


@dataclass(frozen=True)
class TranscriberInfo:
    impl: str                      # "module:ClassName" inside this package
    summary: str
    os: tuple[str, ...]            # subset of "macos", "linux", "windows"
    arch: tuple[str, ...] | None   # e.g. ("arm64",); None = any
    accel: str                     # what hardware it uses
    packages: tuple[str, ...]      # importable Python modules it needs
    binaries: tuple[str, ...] = ("ffmpeg",)
    languages: str = "multilingual (99 languages, auto-detect)"
    default_model: str = ""
    notes: str = ""
    install: str = ""

    def problems(self) -> list[str]:
        """Reasons it can't run on this machine (empty list = OK)."""
        out = []
        this_os = OS_NAMES.get(sys.platform, sys.platform)
        if this_os not in self.os:
            out.append(f"needs {'/'.join(self.os)}, this is {this_os}")
        machine = platform.machine().lower()
        if self.arch and machine not in self.arch:
            out.append(f"needs {'/'.join(self.arch)} CPU, this is {machine}")
        out += [f"missing Python package {p!r}" for p in self.packages
                if importlib.util.find_spec(p) is None]
        out += [f"missing program {b!r}" for b in self.binaries if shutil.which(b) is None]
        return out


REGISTRY: dict[str, TranscriberInfo] = {
    "mlx-whisper": TranscriberInfo(
        impl="mlx_whisper:MlxWhisperTranscriber",
        summary="OpenAI Whisper on the Apple Silicon GPU via MLX",
        os=("macos",),
        arch=("arm64",),
        accel="Apple Silicon GPU (Metal)",
        packages=("mlx_whisper",),
        default_model="mlx-community/whisper-large-v3-turbo",
        notes="Fastest choice on M-series Macs (~8-10 s per 1-min reel on an M1). "
              "large-v3-turbo needs ~2 GB RAM.",
        install="pip install mlx-whisper",
    ),
    "faster-whisper": TranscriberInfo(
        impl="faster_whisper:FasterWhisperTranscriber",
        summary="Whisper via CTranslate2: portable, CPU or NVIDIA GPU",
        os=("macos", "linux", "windows"),
        arch=None,
        accel="NVIDIA GPU (CUDA 12 + cuDNN 9) if present, else CPU (int8)",
        packages=("faster_whisper",),
        binaries=(),  # decodes audio itself via PyAV
        default_model="large-v3-turbo",
        notes="Use on Linux/Windows or Intel Macs. On a CPU it is several times "
              "slower than mlx-whisper; pick a smaller --model (small, medium) "
              "to speed up. Models ending in .en are English-only.",
        install="pip install faster-whisper",
    ),
}


def get_transcriber(name: str, **options) -> Transcriber:
    if name not in REGISTRY:
        raise SystemExit(f"Unknown transcriber {name!r}. Available: {', '.join(REGISTRY)}")
    info = REGISTRY[name]
    if problems := info.problems():
        raise SystemExit(f"Transcriber {name!r} can't run here: {'; '.join(problems)}."
                         + (f" Install: {info.install}" if info.install else "")
                         + "\nSee: python3 tools/run.py --list-transcribers")
    module, cls = info.impl.split(":")
    return getattr(import_module(f".{module}", __name__), cls)(**options)


def describe_all() -> str:
    lines = []
    for name, i in REGISTRY.items():
        problems = i.problems()
        status = "available here" if not problems else "NOT available here: " + "; ".join(problems)
        lines += [
            f"{name}  [{status}]",
            f"  {i.summary}",
            f"  OS:        {', '.join(i.os)}" + (f"  (CPU: {', '.join(i.arch)})" if i.arch else ""),
            f"  Hardware:  {i.accel}",
            f"  Languages: {i.languages}",
            f"  Model:     {i.default_model} (override with --model)",
            f"  Needs:     Python {', '.join(i.packages)}"
            + (f"; programs {', '.join(i.binaries)}" if i.binaries else ""),
            f"  Install:   {i.install}",
            f"  Notes:     {i.notes}",
            "",
        ]
    return "\n".join(lines)
