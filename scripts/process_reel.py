"""Turn one Instagram reel into something Claude can read: caption, transcript, frames.

Usage:
    python scripts/process_reel.py <reel-url>
    python scripts/process_reel.py --video local.mp4 [--url <original-url>]   # skip download

Output goes to $OUT_DIR/<date>-<id>/ (reel.md + frame JPEGs). The workflow uploads that
folder as a temporary GitHub Actions artifact instead of committing it, so nothing about the
reel stays in the repo; Claude deletes the artifact after summarizing. The video is never kept.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REELS_DIR = Path(os.getenv("OUT_DIR", str(ROOT / "out")))

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
FRAME_EVERY = float(os.getenv("FRAME_EVERY", "2"))  # seconds between frames
MAX_FRAMES = int(os.getenv("MAX_FRAMES", "45"))
FRAME_WIDTH = 540


def download(url: str, workdir: Path) -> tuple[Path, dict]:
    from yt_dlp import YoutubeDL

    opts = {
        "format": "b[ext=mp4][height<=720]/bv*[height<=720]+ba/b",
        "outtmpl": str(workdir / "video.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    cookies = os.getenv("IG_COOKIES_FILE")
    if cookies and Path(cookies).is_file() and Path(cookies).stat().st_size > 0:
        opts["cookiefile"] = cookies
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    if info.get("_type") == "playlist":
        info = (info.get("entries") or [None])[0] or {}
    videos = [p for p in workdir.glob("video.*") if p.suffix not in {".part", ".json"}]
    if not videos:
        raise RuntimeError("download finished but no video file was found")
    return max(videos, key=lambda p: p.stat().st_size), info


def duration_of(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"].get("duration") or 0)


def extract_frames(video: Path, out_dir: Path, duration: float) -> list[tuple[float, str]]:
    """One frame every FRAME_EVERY seconds (spread out evenly past MAX_FRAMES) so on-screen text isn't missed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = max(1, min(MAX_FRAMES, round(duration / FRAME_EVERY))) if duration else 1
    frames = []
    for i in range(n):
        t = round(duration * (i + 0.5) / n, 1) if duration else 0.0
        name = f"frame-{i + 1:02d}.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video),
             "-frames:v", "1", "-vf", f"scale={FRAME_WIDTH}:-2", "-q:v", "4", str(out_dir / name)],
            check=True,
        )
        if (out_dir / name).exists():
            frames.append((t, name))
    return frames


def transcribe(video: Path, workdir: Path) -> tuple[list[dict], str]:
    """Whisper on the runner's CPU. Returns (segments, detected language)."""
    # Decode with ffmpeg ourselves: faster-whisper's own decoder breaks on newer PyAV releases.
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        return [], "no audio"
    import numpy as np
    from faster_whisper import WhisperModel

    audio = np.frombuffer(proc.stdout, dtype=np.float32)
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio, vad_filter=True)
    out = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments if s.text.strip()]
    return out, info.language


def fmt_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-")[:40] or "reel"


def write_reel(url: str, info: dict, duration: float, segments, language, frames, out_dir: Path, shared_at):
    caption = (info.get("description") or "").strip()
    uploader = info.get("uploader") or info.get("channel") or info.get("uploader_id") or "unknown"
    lines = [
        f"# Reel by {uploader}",
        "",
        f"- **URL:** {url}",
        f"- **Shared:** {shared_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **Duration:** {duration:.0f}s",
        f"- **Spoken language:** {language}",
        "",
        "## Caption",
        "",
        caption or "_(no caption)_",
        "",
        "## Transcript",
        "",
    ]
    if segments:
        lines += [f"[{fmt_ts(s['start'])}] {s['text']}" for s in segments]
    else:
        lines.append("_(no speech detected)_")
    lines += ["", "## Frames", ""]
    lines += [f"![frame at {t:g}s]({name}) at {t:g}s" for t, name in frames]
    lines.append("")
    (out_dir / "reel.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--video", help="process a local video instead of downloading")
    args = ap.parse_args()
    if not args.url and not args.video:
        ap.error("give a reel URL or --video")
    url = (args.url or "").strip()
    if url:
        match = re.search(r"https?://\S+", url)
        url = match.group(0) if match else url

    shared_at = dt.datetime.now(dt.timezone.utc)
    workdir = Path(tempfile.mkdtemp(prefix="reel-"))
    try:
        if args.video:
            video, info = Path(args.video), {"id": Path(args.video).stem}
        else:
            video, info = download(url, workdir)
        reel_id = slug(str(info.get("id") or info.get("display_id") or "reel"))
        out_dir = REELS_DIR / f"{shared_at:%Y-%m-%d}-{reel_id}"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        duration = duration_of(video)
        frames = extract_frames(video, out_dir, duration)
        segments, language = transcribe(video, workdir)
        write_reel(url or str(video), info, duration, segments, language, frames, out_dir, shared_at)

        github_output = os.getenv("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"folder={out_dir.name}\n")
        print(f"saved {out_dir.name} ({len(segments)} transcript lines, {len(frames)} frames)")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
