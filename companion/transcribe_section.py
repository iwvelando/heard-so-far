"""Transcribe a completed section in overlapping chunks, bounded by progress."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

from position import seconds, validate
from locking import exclusive
from transcript_io import validate_chunk

ROOT = Path(__file__).resolve().parents[1]
os.environ["HF_HOME"] = str(ROOT / ".cache/huggingface")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
MODEL = "mlx-community/whisper-large-v3-turbo"


def clock(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-track", type=int, required=True)
    parser.add_argument("--last-track", type=int, required=True)
    parser.add_argument("--name", default=None, help="Omit for a fresh, uniquely named transcription")
    parser.add_argument("--through", type=seconds, help="Stop at MM:SS or HH:MM:SS within the last track")
    args = parser.parse_args()
    if args.name is None:
        args.name = "query_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    if not args.name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Use a simple output name")
    progress = json.loads((ROOT / "companion/progress.json").read_text())
    audio = ROOT / progress["audio_file"]
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_chapters", "-of", "json", str(audio)],
        check=True, capture_output=True, text=True,
    ).stdout)
    chapters = probe["chapters"]
    if not 1 <= args.first_track <= args.last_track <= len(chapters):
        raise ValueError("Invalid track range")
    safe_end = validate(progress, chapters)
    section_start = float(chapters[args.first_track - 1]["start_time"])
    section_end = float(chapters[args.last_track - 1]["end_time"])
    if args.through is not None:
        last_start = float(chapters[args.last_track - 1]["start_time"])
        if not 0 < args.through <= section_end - last_start + 1:
            raise ValueError("--through is outside the last track")
        requested_end = min(last_start + args.through, section_end)
        if requested_end > progress["cutoff_audio_seconds"] + .001:
            raise ValueError("Requested material has not been heard")
        section_end = min(requested_end, safe_end)
    elif section_end > safe_end:
        raise ValueError("Section has not been completely heard; use --through for an explicit partial recap")
    if section_end <= section_start:
        raise ValueError("No permitted audio in this request")
    folder = ROOT / "companion/transcripts" / args.name
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_audio": progress["audio_file"], "source_size": audio.stat().st_size,
        "source_mtime_ns": audio.stat().st_mtime_ns, "model": MODEL,
        "language": progress.get("language"),
        "first_track": args.first_track, "last_track": args.last_track,
        "section_start": section_start, "section_end": section_end,
        "core_seconds": 600, "context_seconds": 20,
        "review_status": "Unverified ASR. Review overlaps, names, and suspicious passages.",
    }
    manifest_path = folder / "manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise ValueError("Existing output belongs to a different transcription configuration")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    import mlx_whisper
    begun = time.monotonic()
    core_start = section_start
    index = 0
    lines, boundaries, previous_words = [], [], []
    while core_start < section_end:
        core_end = min(core_start + 600, section_end)
        clip_start = max(section_start, core_start - 20)
        clip_end = min(section_end, core_end + 20)
        path = folder / f"chunk_{index:03}.json"
        if path.exists():
            chunk = json.loads(path.read_text())
            validate_chunk(chunk, {"clip_start": clip_start, "clip_end": clip_end,
                                   "core_start": core_start, "core_end": core_end})
        else:
            clip = folder / "working.wav"
            subprocess.run([
                "ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", str(clip_start),
                "-i", str(audio), "-t", str(clip_end - clip_start),
                "-map", "0:a:0", "-vn", "-ar", "16000", "-ac", "1", str(clip),
            ], check=True)
            result = mlx_whisper.transcribe(
                str(clip), path_or_hf_repo=MODEL, language=progress.get("language"), word_timestamps=True,
                verbose=None,
            )
            chunk = {"clip_start": clip_start, "clip_end": clip_end,
                     "core_start": core_start, "core_end": core_end, "result": result}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(chunk, indent=2) + "\n")
            tmp.replace(path)
            clip.unlink()
        words = []
        for segment in chunk["result"]["segments"]:
            kept = []
            for word in segment.get("words", []):
                a, b = clip_start + word["start"], clip_start + word["end"]
                words.append({"start": a, "end": b, "word": word["word"]})
                if core_start <= (a + b) / 2 < core_end:
                    kept.append((a, b, word["word"]))
            if kept:
                lines.append(f"[{clock(kept[0][0])}–{clock(kept[-1][1])}] " +
                             "".join(w[2] for w in kept).strip())
        if index:
            def nearby(ws):
                return [w for w in ws if abs((w["start"] + w["end"]) / 2 - core_start) < 10]
            boundaries.append({"boundary": core_start, "left": nearby(previous_words),
                               "right": nearby(words)})
        previous_words = words
        index += 1
        core_start = core_end
        print(json.dumps({"completed_chunk": index, "section_minutes_done": round((core_end-section_start)/60, 1),
                          "wall_seconds": round(time.monotonic()-begun, 1)}), flush=True)
    (folder / "transcript.txt").write_text(
        "UNVERIFIED ASR. Timestamps are absolute positions in the M4B.\n" +
        "Overlaps are selected by word midpoint; consult boundaries.json for disagreements.\n\n" +
        "\n".join(lines) + "\n")
    (folder / "boundaries.json").write_text(json.dumps(boundaries, indent=2) + "\n")
    print(f"Saved {len(lines)} timestamped passages to {folder.relative_to(ROOT)}/transcript.txt")


if __name__ == "__main__":
    with exclusive():
        main()
