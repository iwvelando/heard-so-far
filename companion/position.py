"""Resolve listening positions without displaying unread chapter titles."""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "companion/progress.json"


def seconds(value):
    parts = value.split(":")
    if len(parts) not in (2, 3) or any(not p.isdigit() for p in parts):
        raise ValueError("Use MM:SS or HH:MM:SS")
    nums = list(map(int, parts))
    if any(n >= 60 for n in nums[1:]):
        raise ValueError("Minutes/seconds after the first field must be below 60")
    result = 0
    for n in nums:
        result = result * 60 + n
    return result


def clock(value):
    n = round(value)
    return f"{n // 3600:02}:{n // 60 % 60:02}:{n % 60:02}"


def probe(audio):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_chapters", "-of", "json", str(audio)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)["chapters"]


def normalize(title):
    return re.sub(r"[\W_]+", " ", unicodedata.normalize("NFKC", title).casefold()).strip()


def match(chapters, title, elapsed, remaining, track=None, *, audio_file):
    if not normalize(title) or min(elapsed, remaining) < 0 or elapsed + remaining <= 0:
        raise ValueError("Provide a title and valid elapsed/remaining times")
    exact, partial = [], []
    for i, c in enumerate(chapters):
        duration = float(c["end_time"]) - float(c["start_time"])
        candidate = normalize(c.get("tags", {}).get("title", ""))
        if (normalize(title) in candidate
            and abs(duration - elapsed - remaining) <= 1
            and elapsed <= duration + 1 and (track is None or track == i + 1)):
            (exact if candidate == normalize(title) else partial).append(i)
    # A complete title wins over titles that merely contain it ("Chapter 1" vs "Chapter 10").
    matches = exact or partial
    if len(matches) != 1:
        raise ValueError(f"Expected one title/duration match; found {len(matches)}. Clarify the title or one-based track number.")
    i = matches[0]
    c = chapters[i]
    title = c["tags"]["title"]
    start, end = float(c["start_time"]), float(c["end_time"])
    return {
        "audio_file": audio_file, "track_index_1_based": i + 1, "track_title": title,
        "title_occurrence_1_based": sum(x.get("tags", {}).get("title") == title for x in chapters[:i+1]),
        "reported_elapsed_seconds": elapsed, "reported_remaining_seconds": remaining,
        "embedded_track_start_seconds": start, "embedded_track_end_seconds": end,
        "cutoff_audio_seconds": min(start + elapsed, end), "boundary_buffer_seconds": 5,
        "source": "Explicit user progress update; matched title plus elapsed + remaining to embedded audio chapter duration.",
    }


def load_progress():
    try:
        return json.loads(PROGRESS.read_text())
    except FileNotFoundError:
        raise SystemExit("No saved listening progress. Set it with make progress TITLE=... ELAPSED=MM:SS "
                         "REMAINING=MM:SS AUDIO=path (or position.py set ... --audio PATH).") from None


def resolve_audio(explicit, saved):
    audio_file = explicit or (saved or {}).get("audio_file")
    if not audio_file:
        raise ValueError("First setup requires --audio PATH (or make progress AUDIO=PATH).")
    return audio_file


def validate(p, chapters):
    i = p["track_index_1_based"] - 1
    if not 0 <= i < len(chapters):
        raise ValueError("Saved track index is invalid")
    c = chapters[i]
    start, end = float(c["start_time"]), float(c["end_time"])
    elapsed, remaining = p["reported_elapsed_seconds"], p["reported_remaining_seconds"]
    nums = [start, end, elapsed, remaining, p["cutoff_audio_seconds"], p["boundary_buffer_seconds"],
            p["embedded_track_start_seconds"], p["embedded_track_end_seconds"]]
    if not all(math.isfinite(n) for n in nums) or min(elapsed, remaining) < 0:
        raise ValueError("Invalid progress values")
    if (c.get("tags", {}).get("title") != p["track_title"]
        or abs(start - p["embedded_track_start_seconds"]) > .01
        or abs(end - p["embedded_track_end_seconds"]) > .01
        or abs((end - start) - (elapsed + remaining)) > 1
        or elapsed > end - start + 1
        or abs(min(start + elapsed, end) - p["cutoff_audio_seconds"]) > .01
        or p["boundary_buffer_seconds"] < 5):
        raise ValueError("Saved progress does not match the audiobook; resolve it before reading")
    return max(0, p["cutoff_audio_seconds"] - p["boundary_buffer_seconds"])


def visible_tracks(chapters, cutoff):
    counts = {}
    rows = []
    for i, c in enumerate(chapters):
        start, end = float(c["start_time"]), float(c["end_time"])
        if start >= cutoff:
            break
        title = c.get("tags", {}).get("title", "Untitled")
        counts[title] = counts.get(title, 0) + 1
        rows.append({"track": i + 1, "title": title, "occurrence": counts[title],
                     "duration": clock(end-start), "start_audio_seconds": start,
                     "end_audio_seconds": end, "completed": end <= cutoff})
    return rows


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show")
    update = sub.add_parser("set")
    update.add_argument("--title", required=True)
    update.add_argument("--elapsed", required=True, type=seconds)
    update.add_argument("--remaining", required=True, type=seconds)
    update.add_argument("--track", type=int)
    update.add_argument("--audio", help="Local audiobook path; required on first setup, then defaults to the saved source")
    update.add_argument("--language", help="Optional speech-language code; otherwise detect the language automatically")
    args = parser.parse_args()
    if args.command == "set":
        saved = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else None
        try:
            audio_file = resolve_audio(args.audio, saved)
        except ValueError as error:
            parser.error(str(error))
        chapters = probe(ROOT / audio_file)
        p = match(chapters, args.title, args.elapsed, args.remaining, args.track, audio_file=audio_file)
        p["language"] = args.language or ((saved or {}).get("language") if (saved or {}).get("audio_file") == audio_file else None)
        validate(p, chapters)
        # Invoke 'set' only for an explicit user update; never infer progress from a query.
        temporary = PROGRESS.with_suffix(".tmp")
        temporary.write_text(json.dumps(p, indent=2) + "\n")
        temporary.replace(PROGRESS)
    else:
        p = load_progress()
        chapters = probe(ROOT / p["audio_file"])
    safe_end = validate(p, chapters)
    print(json.dumps({"progress": p, "safe_audio_end_seconds": safe_end,
                      "begun_tracks": visible_tracks(chapters, p["cutoff_audio_seconds"])}, indent=2))


if __name__ == "__main__":
    main()
