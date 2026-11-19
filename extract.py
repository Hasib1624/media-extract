#!/usr/bin/env python3
"""Extract text data (metadata, transcript, comments) from YouTube and other
yt-dlp-supported video/post URLs (X/Twitter, Reddit, TikTok, Facebook, Vimeo...).
Never downloads the media itself.

Usage:
  extract.py URL [URL ...] [-o out_dir] [--comments N] [--no-transcript] [--lang en]
  extract.py --file urls.txt
Output: <out_dir>/<id>.json and <id>.transcript.txt per URL (default ./out).
"""
import argparse, json, re, sys, tempfile, urllib.request
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("yt_dlp missing: install with `pipx install yt-dlp` or `pip install yt-dlp`")

FIELDS = ["id", "title", "description", "uploader", "uploader_id", "channel",
          "channel_url", "upload_date", "duration", "view_count", "like_count",
          "comment_count", "tags", "categories", "webpage_url", "extractor_key",
          "thumbnail", "chapters"]


def vtt_to_text(vtt: str) -> str:
    out, prev = [], None
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line and line != prev:
            out.append(line)
            prev = line
    return "\n".join(out)


def get_transcript(info, lang):
    for source in ("subtitles", "automatic_captions"):
        tracks = info.get(source) or {}
        key = next((k for k in tracks if k == lang or k.startswith(lang + "-")), None)
        if not key:
            continue
        fmt = next((f for f in tracks[key] if f.get("ext") == "vtt"), None)
        if fmt:
            with urllib.request.urlopen(fmt["url"], timeout=30) as r:
                return source, vtt_to_text(r.read().decode("utf-8", "replace"))
    return None, None


def extract(url, out_dir, n_comments, want_transcript, lang):
    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "noplaylist": True, "ignoreerrors": False}
    if n_comments:
        opts["getcomments"] = True
        opts["extractor_args"] = {"youtube": {"max_comments": [str(n_comments)]}}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    data = {k: info.get(k) for k in FIELDS}
    if n_comments:
        data["comments"] = [
            {k: c.get(k) for k in ("author", "text", "like_count", "timestamp", "parent")}
            for c in (info.get("comments") or [])[:n_comments]]
    out_dir.mkdir(parents=True, exist_ok=True)
    vid = re.sub(r"[^\w.-]", "_", str(info.get("id")))
    if want_transcript:
        src, text = get_transcript(info, lang)
        data["transcript_source"] = src
        if text:
            (out_dir / f"{vid}.transcript.txt").write_text(text, encoding="utf-8")
    (out_dir / f"{vid}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return vid, data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--file", help="text file with one URL per line")
    ap.add_argument("-o", "--out", default="out")
    ap.add_argument("--comments", type=int, default=0, metavar="N")
    ap.add_argument("--no-transcript", action="store_true")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args()
    urls = list(a.urls)
    if a.file:
        urls += [l.strip() for l in Path(a.file).read_text().splitlines() if l.strip() and not l.startswith("#")]
    if not urls:
        ap.error("no URLs given")
    fails = 0
    for u in urls:
        try:
            vid, d = extract(u, Path(a.out), a.comments, not a.no_transcript, a.lang)
            print(f"OK   {vid}  {d['title']!r}  transcript={d.get('transcript_source')}")
        except Exception as e:
            fails += 1
            print(f"FAIL {u}: {str(e).splitlines()[-1]}", file=sys.stderr)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
