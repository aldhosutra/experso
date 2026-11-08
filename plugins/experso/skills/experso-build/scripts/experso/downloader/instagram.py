import json
import re
from pathlib import Path
from typing import Iterator

import instaloader

from .base import Downloader, EmitVideo, Post

KINDS = {"clips": "reel", "carousel_container": "carousel", "feed": "image", "igtv": "igtv"}


class InstagramDownloader(Downloader):
    """Public (or logged-in) Instagram profile posts via Instaloader.

    Options: login=<IG username> to use a session saved with
    `instaloader --login <user>`.
    """

    name = "instagram"

    def download(self, target: str, dest: Path, emit: EmitVideo,
                 max_items: int | None = None, known: set[str] | None = None) -> int:
        known = known or set()
        L = instaloader.Instaloader(dirname_pattern=str(dest), compress_json=False)
        if self.options.get("login"):
            L.load_session_from_file(self.options["login"])

        profile = instaloader.Profile.from_username(L.context, target)
        L.download_profilepic(profile)
        new = 0
        for i, post in enumerate(profile.get_posts()):
            if max_items is not None and i >= max_items:
                break
            base = L.format_filename(post, target=profile.username)
            if base in known:  # processed earlier; its files may have been cleaned
                downloaded = False
            else:
                downloaded = L.download_post(post, target=profile.username)
            # Like --fast-update: the first already-downloaded non-pinned post
            # means everything older is on disk too.
            if not downloaded and not post.is_pinned:
                print("[instagram] reached already-downloaded posts, stopping", flush=True)
                break
            new += bool(downloaded)
            # format_filename gives only the file name. A single video is
            # <base>.mp4, carousel videos are <base>_1.mp4, <base>_2.mp4, ...
            for v in sorted(set(dest.glob(base + ".mp4")) | set(dest.glob(base + "_*.mp4"))):
                emit(v)
        return new

    def iter_posts(self, dest: Path) -> Iterator[Post]:
        # Post metadata files are <date>_UTC.json; the profile's is <user>_<id>.json.
        for meta in sorted(dest.glob("*_UTC.json")):
            base = meta.name[: -len(".json")]
            node = json.loads(meta.read_text(encoding="utf-8")).get("node", {})
            caption_file = dest / f"{base}.txt"
            caption = caption_file.read_text(encoding="utf-8").strip() if caption_file.exists() else ""

            def slide_no(p: Path) -> int:
                m = re.search(r"_(\d+)\.transcript\.txt$", p.name)
                return int(m.group(1)) if m else 0

            files = {dest / f"{base}.transcript.txt"} | set(dest.glob(f"{base}_*.transcript.txt"))
            transcripts = []
            for t in sorted((f for f in files if f.exists()), key=slide_no):
                text = t.read_text(encoding="utf-8").strip()
                if text and text != "[no audio]":
                    transcripts.append((t.name, text))

            likes = node.get("like_count")
            if likes is None:
                likes = (node.get("edge_media_preview_like") or {}).get("count")
            comments = node.get("comment_count")
            if comments is None:
                comments = (node.get("edge_media_to_comment") or {}).get("count")
            views = next((node[k] for k in ("video_view_count", "play_count", "view_count")
                          if node.get(k) is not None), None)
            # Carousel slides are <base>_N.jpg (silent video slides also get one);
            # a reel has one cover frame <base>.jpg. Slides often carry the real content.
            jpgs = {dest / f"{base}.jpg"} | set(dest.glob(f"{base}_*.jpg"))
            images = [str(p) for p in sorted((p for p in jpgs if p.exists()),
                                             key=lambda p: int(re.search(r"_(\d+)\.jpg$", p.name).group(1))
                                             if re.search(r"_(\d+)\.jpg$", p.name) else 0)]
            code = node.get("shortcode") or node.get("code")
            yield Post(
                id=base,
                url=f"https://www.instagram.com/p/{code}/" if code else None,
                date=base[:10],
                kind=KINDS.get(node.get("product_type"), node.get("product_type")),
                caption=caption,
                transcripts=transcripts,
                metrics={"likes": likes, "comments": comments, "views": views},
                images=images,
            )
