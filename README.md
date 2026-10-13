# reels-inbox

Instagram reels shared from an iPhone, turned into caption + timestamped transcript + frames so
Claude can read, summarize and judge them. See [SETUP.md](SETUP.md).

- `scripts/process_reel.py` downloads one reel (yt-dlp), transcribes it (faster-whisper on the
  GitHub runner's CPU) and writes `reel.md` plus a frame every 2 seconds.
- `.github/workflows/ingest.yml` runs it when the shortcut fires a `reel` repository_dispatch and
  adds the result to the separate `inbox` branch as `reels/<date>-<id>/`. Nothing goes on main.
- Every folder on `inbox` is a reel Claude hasn't summarized yet. After summarizing, Claude
  rebuilds `inbox` as one fresh commit without those reels and force-pushes it, so their
  content is gone from the branch history too.
