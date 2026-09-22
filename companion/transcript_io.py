"""Check extraction coverage without returning any book text to the caller."""
import json
import math


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Invalid extraction time")
    return value


def windows(manifest):
    start, end = finite(manifest["section_start"]), finite(manifest["section_end"])
    core, context = finite(manifest["core_seconds"]), finite(manifest["context_seconds"])
    if not 0 <= start < end or core <= 0 or context < 0:
        raise ValueError("Invalid extraction interval or chunk configuration")
    cursor = start
    while cursor < end:
        next_end = min(cursor + core, end)
        if next_end <= cursor:
            raise ValueError("Chunk duration is too small")
        yield {"core_start": cursor, "core_end": next_end,
               "clip_start": max(start, cursor - context),
               "clip_end": min(end, next_end + context)}
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
    if not all((folder / name).is_file() for name in ("transcript.txt", "boundaries.json")):
        raise ValueError("Transcript is incomplete: final outputs are missing")
