"""Check extraction coverage without returning any book text to the caller."""

import json
import math
from itertools import pairwise


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Invalid extraction time")
    return value


def windows(manifest):
    """Yield chunk envelopes; chunks and their context never cross a track start."""
    start, end = finite(manifest["section_start"]), finite(manifest["section_end"])
    core, context = finite(manifest["core_seconds"]), finite(manifest["context_seconds"])
    if not 0 <= start < end or core <= 0 or context < 0:
        raise ValueError("Invalid extraction interval or chunk configuration")
    breaks = sorted({finite(track["start"]) for track in manifest.get("tracks", [])})
    edges = [start] + [value for value in breaks if start < value < end] + [end]
    for part_start, part_end in pairwise(edges):
        cursor = part_start
        while cursor < part_end:
            next_end = min(cursor + core, part_end)
            if next_end <= cursor:
                raise ValueError("Chunk duration is too small")
            yield {
                "core_start": cursor,
                "core_end": next_end,
                "clip_start": max(part_start, cursor - context),
                "clip_end": min(part_end, next_end + context),
            }
            cursor = next_end


def validate_chunk(chunk, expected):
    if any(abs(finite(chunk[key]) - value) > 1e-6 for key, value in expected.items()):
        raise ValueError("Chunk timestamps do not match the requested extraction")
    if not isinstance(chunk["result"]["segments"], list):
        raise ValueError("Chunk has no valid ASR segments")


def validate_run(folder, manifest):
    for index, expected in enumerate(windows(manifest)):
        path = folder / f"chunk_{index:03}.json"
        if not path.is_file():
            raise ValueError("Transcript is incomplete: a required chunk is missing")
        validate_chunk(json.loads(path.read_text()), expected)
    outputs = ["transcript.txt", "boundaries.json"] + (["quality.json"] if "tracks" in manifest else [])
    if not all((folder / name).is_file() for name in outputs):
        raise ValueError("Transcript is incomplete: final outputs are missing")


def coverage_gaps(words, start, end, threshold=15):
    """Return stretches of at least `threshold` seconds with no kept word, edges included."""
    gaps, cursor = [], start
    for word_start, word_end in sorted(words) + [(end, end)]:
        if word_start - cursor >= threshold:
            gaps.append({"start": cursor, "end": word_start, "seconds": round(word_start - cursor, 1)})
        cursor = max(cursor, word_end)
    return gaps


def repeated_runs(lines, minimum=3):
    """Return runs of at least `minimum` consecutive lines with identical normalized text."""

    def key(text):
        return "".join(ch for ch in text.lower() if ch.isalnum())

    runs, index = [], 0
    while index < len(lines):
        stop = index + 1
        while stop < len(lines) and key(lines[stop][2]) == key(lines[index][2]):
            stop += 1
        if stop - index >= minimum and key(lines[index][2]):
            runs.append({"start": lines[index][0], "end": lines[stop - 1][1], "count": stop - index})
        index = stop
    return runs


def local_label(moment, tracks):
    """Name the track containing an absolute time and the position within it."""
    for track in tracks:
        if track["start"] <= moment < track["end"]:
            offset = int(moment - track["start"])
            hours, minutes, secs = offset // 3600, offset // 60 % 60, offset % 60
            clock = f"{hours}:{minutes:02}:{secs:02}" if hours else f"{minutes:02}:{secs:02}"
            return f"track {track['track']} {clock}"
    return None
