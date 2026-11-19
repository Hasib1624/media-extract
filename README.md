# media-extract

Extract metadata, transcripts and comments from YouTube and other yt-dlp-supported video/post URLs. Never downloads media.

```bash
python3 -m venv .venv && .venv/bin/python -m pip install yt-dlp
.venv/bin/python extract.py URL --comments 50 -o out
```

See `extract.py --help`.

If YouTube returns HTTP 429 on captions, add `--cookies-from-browser firefox`.
