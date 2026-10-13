# reels-inbox

Instagram reels shared from an iPhone, turned into caption + timestamped transcript + frames so
Claude can read, summarize and judge them. See [SETUP.md](SETUP.md).

- `scripts/process_reel.py` downloads one reel (yt-dlp), transcribes it (faster-whisper on the
  GitHub runner's CPU) and writes `reel.md` plus a frame every 2 seconds.
- `.github/workflows/ingest.yml` runs it when the shortcut fires a `reel` repository_dispatch and
  stores the result as a temporary artifact named `reel-<date>-<id>`. Nothing is committed.
- Each artifact still listed is a reel Claude hasn't summarized yet. Claude deletes it after
  summarizing; unreviewed ones expire after 90 days.
