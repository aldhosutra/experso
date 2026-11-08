"""experso ingest: download a profile and transcribe its videos, in parallel.

    experso ingest HANDLE [--source instagram] [--transcriber mlx-whisper]
                   [--language id] [--model HF_REPO] [--max-items N] [--login IG_USER]
    experso list transcribers            # which transcriber fits this machine

Files go to .experso/HANDLE/cache/. Each video gets <video>.transcript.txt next
to it; videos with no audio track get "[no audio]". Incremental: posts recorded
in the manifest are skipped even after `experso clean` removed their files, and
videos in the cache without a transcript are transcribed first.

A background thread downloads and queues finished videos; the main thread
transcribes them (MLX uses the GPU from the thread that started it).
"""
import argparse
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path


from ..manifest import Manifest
from ..paths import Profile
from ..downloader import REGISTRY as DOWNLOADERS, get_downloader
from ..transcriber import REGISTRY as TRANSCRIBERS, describe_all, get_transcriber

DONE = object()


def transcript_path(video: Path) -> Path:
    return video.with_suffix(".transcript.txt")


def has_audio(media: Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=index", "-of", "csv=p=0", str(media)],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.rename(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?",
                    help="profile/channel to download, e.g. an Instagram username")
    ap.add_argument("--list-transcribers", action="store_true",
                    help="show each transcriber's OS/hardware support and whether it runs here")
    ap.add_argument("--source", default="instagram", choices=list(DOWNLOADERS))
    ap.add_argument("--transcriber", default=next((n for n, i in TRANSCRIBERS.items() if not i.problems()),
                                                  next(iter(TRANSCRIBERS))), choices=list(TRANSCRIBERS))
    ap.add_argument("--language", default=None, help="e.g. en, id (default: auto-detect)")
    ap.add_argument("--model", default=None, help="transcriber model override")
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--login", default=None, help="Instagram: saved session username")
    args = ap.parse_args(argv)
    if args.list_transcribers:
        print(describe_all())
        return
    if not args.target:
        ap.error("target is required")

    dl = get_downloader(args.source, login=args.login)
    profile = Profile(args.target).ensure()
    dest = profile.cache
    manifest = Manifest(profile)
    known = manifest.known("downloaded")
    tr = get_transcriber(args.transcriber, language=args.language, model=args.model)

    q: queue.Queue = queue.Queue()
    for v in sorted(dest.glob("*.mp4")):  # catch up on earlier runs
        if not transcript_path(v).exists():
            q.put(v)

    stats = {"new_items": 0, "transcribed": 0, "no_audio": 0, "failed": 0, "download_error": None}

    def download_thread():
        try:
            stats["new_items"] = dl.download(args.target, dest, q.put, args.max_items, known)
        except Exception as e:
            stats["download_error"] = repr(e)
            print(f"[{args.source}] ERROR: {e!r}", flush=True)
        finally:
            q.put(DONE)

    start = time.time()
    t = threading.Thread(target=download_thread, daemon=True)
    t.start()

    while (v := q.get()) is not DONE:
        out = transcript_path(v)
        if out.exists():
            continue
        try:
            if not has_audio(v):
                write_atomic(out, "[no audio]\n")
                stats["no_audio"] += 1
                print(f"[transcribe] {v.name}: no audio track", flush=True)
                continue
            result = tr.transcribe(v)
            write_atomic(out, result.text + "\n")
            stats["transcribed"] += 1
            print(f"[transcribe] {v.name} ({result.language}) {len(result.text)} chars "
                  f"| queue {q.qsize()} | {time.time() - start:.0f}s", flush=True)
        except Exception as e:
            stats["failed"] += 1
            print(f"[transcribe] FAILED {v.name}: {e!r}"[:500], flush=True)

    t.join()
    # Record every post now in the cache, so later runs skip it even after clean.
    ts = time.strftime("%Y-%m-%d")
    for post in dl.iter_posts(dest):
        if not manifest.post(post.id).get("downloaded"):
            manifest.mark(post.id, downloaded=ts, url=post.url, date=post.date, kind=post.kind)
    manifest.log("ingest", new_items=stats["new_items"], transcribed=stats["transcribed"],
                 failed=stats["failed"])
    manifest.save()
    print(f"DONE in {time.time() - start:.0f}s: {stats['new_items']} new items, "
          f"{stats['transcribed']} transcribed, {stats['no_audio']} without audio, "
          f"{stats['failed']} failed"
          + (f", download error: {stats['download_error']}" if stats["download_error"] else ""),
          flush=True)
    sys.exit(1 if stats["download_error"] or stats["failed"] else 0)


if __name__ == "__main__":
    main()
