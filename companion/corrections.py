"""Validate and record user-verified corrections tied to one source and passage.

Messages name entries by position only, never their text or track titles.
"""

import argparse
import json
import sys

from position import PROGRESS, ROOT, probe, seconds, validate

CORRECTIONS = ROOT / "companion/user_corrections.json"
TOP_LEVEL = {"source_audio", "corrections"}
REQUIRED = {"track", "track_title", "start", "end", "asr", "corrected", "attribution"}
OPTIONAL = {"note"}


def check_entry(item, chapters, safe_end):
    if not isinstance(item, dict):
        return ["must be an object"]
    problems = [f"unknown field {key!r}" for key in sorted(set(item) - REQUIRED - OPTIONAL)]
    problems += [f"missing field {key!r}" for key in sorted(REQUIRED - set(item))]
    for key in ("asr", "corrected", "attribution", "track_title"):
        if key in item and (not isinstance(item[key], str) or not item[key].strip()):
            problems.append(f"{key!r} must be nonempty text")
    track = item.get("track")
    if "track" in item and (isinstance(track, bool) or not isinstance(track, int) or not 1 <= track <= len(chapters)):
        return problems + ["'track' must be a one-based track number in this audiobook"]
    try:
        start, end = seconds(str(item.get("start"))), seconds(str(item.get("end")))
    except ValueError:
        return problems + ["'start' and 'end' must be track-local MM:SS or HH:MM:SS"]
    if problems or track is None:
        return problems
    c = chapters[track - 1]
    track_start, track_end = float(c["start_time"]), float(c["end_time"])
    if track_start >= safe_end:
        return ["passage is beyond the buffered listening limit"]
    if c.get("tags", {}).get("title") != item["track_title"]:
        problems.append("'track_title' does not match that track")
    if start >= end:
        problems.append("'start' must be before 'end'")
    elif track_start + end > track_end + 1:
        problems.append("passage extends past the end of its track")
    elif track_start + end > safe_end:
        problems.append("passage is beyond the buffered listening limit")
    return problems


def check_file(data, chapters, audio_file, safe_end):
    if not isinstance(data, dict):
        return ["file must contain a JSON object"]
    problems = [f"unknown top-level field {key!r}" for key in sorted(set(data) - TOP_LEVEL)]
    if data.get("source_audio") != audio_file:
        # Corrections never transfer between books.
        problems.append("'source_audio' is missing or differs from the saved listening source")
    items = data.get("corrections")
    if not isinstance(items, list):
        return problems + ["'corrections' must be a list"]
    for n, item in enumerate(items, 1):
        problems += [f"correction {n}: {problem}" for problem in check_entry(item, chapters, safe_end)]
    return problems


def context():
    progress = json.loads(PROGRESS.read_text())
    chapters = probe(ROOT / progress["audio_file"])
    return progress["audio_file"], chapters, validate(progress, chapters)


def load(audio_file):
    if not CORRECTIONS.exists():
        return {"source_audio": audio_file, "corrections": []}
    return json.loads(CORRECTIONS.read_text())


def fail(problems):
    raise SystemExit("Invalid user corrections:\n" + "\n".join(f"- {p}" for p in problems))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("add", help="Append one correction supplied as JSON on standard input")
    args = parser.parse_args()
    audio_file, chapters, safe_end = context()
    data = load(audio_file)
    if args.command == "add":
        if not isinstance(data, dict) or data.get("source_audio") != audio_file:
            fail(["the corrections file belongs to a different source; do not transfer corrections"])
        data["corrections"] = [*data.get("corrections", []), json.load(sys.stdin)]
    problems = check_file(data, chapters, audio_file, safe_end)
    if problems:
        fail(problems)
    if args.command == "add":
        temporary = CORRECTIONS.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(CORRECTIONS)
    print(f"OK: {len(data['corrections'])} corrections for the saved source")


if __name__ == "__main__":
    main()
