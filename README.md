# reels-inbox

Instagram reels shared from an iPhone, saved as caption + timestamped transcript + frames so
Claude can read, summarize and judge them. See [SETUP.md](SETUP.md).

- `scripts/process_reel.py` downloads one reel (yt-dlp), transcribes it (faster-whisper on the
  GitHub runner's CPU) and writes `reels/<date>-<id>/reel.md` plus frame JPEGs.
- `.github/workflows/ingest.yml` runs it when the shortcut fires a `reel` repository_dispatch.
- `reels/INDEX.md` lists every reel; `- [ ]` means Claude hasn't reviewed it yet.
