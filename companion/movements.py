"""Versioned, private movement snapshots. Never generate or certify book claims."""

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
import uuid
from pathlib import Path

from journal import context as journal_context
from transcript_io import validate_run

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "spec/movement-format-v1.json").read_text())


class MovementError(ValueError):
    """Safe diagnostics: fixed format messages and numeric line positions only."""


def require(condition, message):
    if not condition:
        raise MovementError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def integer(value):
    return number(value) and 0 < value <= 2**53 - 1 and int(value) == value


def text(value):
    return isinstance(value, str) and bool(value.strip())


def span(value):
    return (
        isinstance(value, dict)
        and set(value) == {"start", "end"}
        and number(value["start"])
        and number(value["end"])
        and value["start"] < value["end"]
    )


def inside(value, outer):
    return span(value) and value["start"] >= outer["start"] and value["end"] <= outer["end"]


def matches(pattern, value):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def validate_metadata(meta):
    require(isinstance(meta, dict), "Invalid movement metadata object")
    require(integer(meta.get("format_version")) and meta["format_version"] == 1, "Unsupported movement format_version")
    require(set(CONTRACT["required_metadata"]) <= set(meta), "Missing movement metadata field")
    require(
        set(meta) <= set(CONTRACT["required_metadata"] + CONTRACT["optional_metadata"]),
        "Unknown movement metadata field",
    )
    require(matches(r"[a-f0-9]{64}", meta["movements_sha256"]), "Invalid movements_sha256")
    identity = meta["source_identity"]
    require(
        isinstance(identity, dict)
        and set(identity) == {"resolved_audio_path", "size", "mtime_ns"}
        and text(identity["resolved_audio_path"])
        and integer(identity["size"])
        and number(identity["mtime_ns"])
        and identity["mtime_ns"] > 0
        and int(identity["mtime_ns"]) == identity["mtime_ns"],
        "Invalid movement source identity",
    )
    require(
        meta["evidence_mode"] == "local-only" and meta["snapshot_mode"] == "known-through-reading-endpoint",
        "Unsupported movement evidence or snapshot mode",
    )
    require(span(meta["query_interval"]), "Invalid movement query interval")
    intervals = meta["consulted_audio_intervals"]
    require(
        isinstance(intervals, list) and intervals and all(inside(value, meta["query_interval"]) for value in intervals),
        "Movement evidence exceeds query interval",
    )
    require(
        integer(meta["reported_track"])
        and number(meta["reported_track_start_seconds"])
        and number(meta["reported_elapsed_seconds"])
        and number(meta["safe_elapsed_seconds"])
        and meta["reported_elapsed_seconds"] - meta["safe_elapsed_seconds"] >= 5,
        "Invalid movement listening buffer",
    )
    require(
        meta["query_interval"]["end"] <= meta["reported_track_start_seconds"] + meta["safe_elapsed_seconds"],
        "Movement query exceeds listening endpoint",
    )
    endpoint = meta["reading_endpoint"]
    require(
        isinstance(endpoint, dict)
        and set(endpoint) == {"chapter", "coverage"}
        and integer(endpoint["chapter"])
        and endpoint["coverage"] in ("partial", "complete"),
        "Invalid movement reading endpoint",
    )
    manifests = meta["transcript_manifests"]
    require(
        isinstance(manifests, list) and len(manifests) == len(intervals) and all(text(value) for value in manifests),
        "Invalid movement transcript manifests",
    )
    require(
        meta["selected_theme"] is None and meta["rendered"] is False,
        "Movement ledger must be an unrendered text snapshot",
    )
    if "update_interval" in meta:
        require(inside(meta["update_interval"], meta["query_interval"]), "Invalid movement update interval")
    if "previous_snapshot" in meta:
        previous = meta["previous_snapshot"]
        require(
            isinstance(previous, dict)
            and set(previous) == {"path", "query_interval"}
            and text(previous["path"])
            and inside(previous["query_interval"], meta["query_interval"]),
            "Invalid movement previous snapshot",
        )
    for key in ("journal_entry_id", "previous_journal_entry_id"):
        if key in meta:
            require(matches(r"[0-9a-f]{32}", meta[key]), "Invalid movement journal identifier")
    if "updated_local_date" in meta:
        require(matches(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", meta["updated_local_date"]), "Invalid movement update date")


def validate_pair(source, meta):
    validate_metadata(meta)
    require(text(source), "Empty movement ledger")
    require(
        hashlib.sha256(source.encode("utf-8")).hexdigest() == meta["movements_sha256"], "Movement pair hash mismatch"
    )
    seen, roles, rows, headings = set(), set(), [], []
    table, title = None, False

    def cells(line):
        return [" ".join(value.split()) for value in re.split(r"(?<!\\)\|", line.strip()[1:-1])]

    def separator(line):
        return re.fullmatch(r"\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*", line) is not None

    lines = re.split(r"\r?\n", source)
    index = 0
    while index < len(lines):
        line = lines[index]
        heading = re.fullmatch(r"(#{1,6})\s+(.+?)\s*", line)
        require(not re.match(r"\s*(```|~~~)", line), f"Unsupported movement fence at line {index + 1}")
        if heading:
            level = len(heading[1])
            if level == 1:
                require(not title, "Movement ledger needs one stable title")
                title = True
            require(title and level <= len(headings) + 1, f"Invalid movement heading hierarchy at line {index + 1}")
            headings = headings[: level - 1] + [" ".join(heading[2].split())]
            table = None
        elif line.strip().startswith("|"):
            require(
                title and len(headings) >= 2 and line.startswith("|") and line.strip().endswith("|"),
                f"Invalid movement table at line {index + 1}",
            )
            following = lines[index + 1] if index + 1 < len(lines) else ""
            if table is None or separator(following):
                columns = cells(line)
                require(
                    separator(following) and following.startswith("|") and len(columns) == len(cells(following)),
                    f"Invalid movement table header at line {index + 1}",
                )
                table = next((rule for rule in CONTRACT["tables"] if rule["columns"] == columns), None)
                require(table is not None, f"Unsupported movement columns at line {index + 1}")
                roles.add(table["role"])
                index += 1
            else:
                require(not separator(line), f"Orphan movement separator at line {index + 1}")
                row = cells(line)
                require(
                    len(row) == len(table["columns"]) and all(text(value) for value in row),
                    f"Invalid movement row at line {index + 1}",
                )
                key = (tuple(headings), tuple(table["columns"]), row[0])
                require(key not in seen, f"Duplicate movement identity at line {index + 1}")
                seen.add(key)
                rows.append((table, row))
        else:
            require(not re.search(r"(?<!\\)\|", line), f"Unsupported movement pipe syntax at line {index + 1}")
            if line.strip():
                table = None
        index += 1
    require(
        all(rule["role"] in roles for rule in CONTRACT["tables"] if rule["required"]),
        "Missing required movement tables",
    )
    chapters, tracks = set(), set()
    previous_track, previous_chapter = 0, 0

    def positive(value):
        return matches(r"[1-9][0-9]*", value) and int(value) <= 2**53 - 1

    for table, row in rows:
        if table["role"] != "tracks":
            continue
        require(positive(row[0]) and positive(row[2]) and positive(row[3]), "Invalid movement track/chapter mapping")
        track, chapter = int(row[0]), int(row[3])
        require(
            previous_track < track <= meta["reported_track"]
            and previous_chapter <= chapter <= meta["reading_endpoint"]["chapter"]
            and track not in tracks,
            "Invalid movement track/chapter mapping",
        )
        coverage = (
            meta["reading_endpoint"]["coverage"] if chapter == meta["reading_endpoint"]["chapter"] else "complete"
        )
        require(row[4] == coverage, "Movement chapter coverage disagrees with endpoint")
        tracks.add(track)
        chapters.add(chapter)
        previous_track, previous_chapter = track, chapter
    require(meta["reading_endpoint"]["chapter"] in chapters, "Missing movement endpoint chapter mapping")
    for table, row in rows:
        if "Disclosure chapter" in table["columns"]:
            value = row[table["columns"].index("Disclosure chapter")]
            require(positive(value) and int(value) in chapters, "Movement disclosure has no permitted chapter mapping")
        if table["role"] == "transcripts":
            require(
                all(matches(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) for value in row[2:4]),
                "Invalid movement transcript navigation",
            )
            try:
                value = {"start": float(row[2]), "end": float(row[3])}
            except ValueError:
                raise ValueError("Invalid movement transcript navigation") from None
            require(
                any(inside(value, outer) for outer in meta["consulted_audio_intervals"]),
                "Movement transcript navigation exceeds evidence scope",
            )


def context():
    progress, source, _, safe_end = journal_context()
    identity = {"resolved_audio_path": source["path"], "size": source["size"], "mtime_ns": source["mtime_ns"]}
    return progress, identity, safe_end


def private_path(path):
    """Refuse symlinks anywhere in the designated private export tree."""
    base = ROOT / "companion/visualizations"
    require(
        ".." not in path.parts and path.is_relative_to(base) and path != base,
        "Movement snapshot must be inside companion/visualizations",
    )
    current = ROOT
    for part in path.relative_to(ROOT).parts:
        current = current / part
        require(not current.is_symlink(), "Movement snapshot path must not be a symlink")


def gate(meta, ctx, through):
    validate_metadata(meta)  # Validate metadata before opening any saved book prose.
    _, identity, safe_end = ctx
    require(number(through), "Invalid movement requested scope")
    require(meta["source_identity"] == identity, "Movement snapshot belongs to a different source")
    require(meta["query_interval"]["end"] <= min(through, safe_end), "Movement snapshot exceeds requested scope")


def check(folder, ctx, through):
    private_path(folder / "metadata.json")
    private_path(folder / "movements.md")
    meta = json.loads((folder / "metadata.json").read_text())
    gate(meta, ctx, through)
    source = (folder / "movements.md").read_bytes().decode("utf-8")
    validate_pair(source, meta)
    return {"format_version": 1, "query_interval": meta["query_interval"], "reading_endpoint": meta["reading_endpoint"]}


def create(payload, ctx, name):
    require(matches(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", name), "Invalid movement snapshot name")
    required = {"movements", "query_interval", "reading_endpoint", "manifests"}
    require(isinstance(payload, dict) and set(payload) == required, "Invalid movement export payload fields")
    progress, identity, safe_end = ctx
    scope = payload["query_interval"]
    require(span(scope) and scope["end"] <= safe_end, "Movement query exceeds buffered scope")
    paths = payload["manifests"]
    require(isinstance(paths, list) and paths and all(text(path) for path in paths), "Include all consulted manifests")
    intervals = []
    for name_path in paths:
        path = (ROOT / name_path).resolve()
        manifest = json.loads(path.read_text())
        require(
            str((ROOT / manifest["source_audio"]).resolve()) == str((ROOT / identity["resolved_audio_path"]).resolve())
            and manifest["source_size"] == identity["size"]
            and manifest["source_mtime_ns"] == identity["mtime_ns"],
            "Movement manifest belongs to a different source",
        )
        interval = {"start": manifest["section_start"], "end": manifest["section_end"]}
        require(inside(interval, scope), "Movement manifest exceeds query scope")
        validate_run(path.parent, manifest)
        intervals.append(interval)
    track_start = progress["embedded_track_start_seconds"]
    source = payload["movements"]
    require(text(source), "Empty movement ledger")
    meta = {
        "format_version": 1,
        "movements_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "source_identity": identity,
        "query_interval": scope,
        "consulted_audio_intervals": intervals,
        "snapshot_mode": "known-through-reading-endpoint",
        "evidence_mode": "local-only",
        "reported_track": progress["track_index_1_based"],
        "reported_track_start_seconds": track_start,
        "reported_elapsed_seconds": progress["reported_elapsed_seconds"],
        "safe_elapsed_seconds": max(0, safe_end - track_start),
        "reading_endpoint": payload["reading_endpoint"],
        "transcript_manifests": paths,
        "selected_theme": None,
        "rendered": False,
    }
    validate_pair(source, meta)
    folder = ROOT / "companion/visualizations" / name
    private_path(folder)
    require(not folder.exists(), "Movement snapshot already exists; create a new full snapshot")
    folder.parent.mkdir(parents=True, exist_ok=True)
    # Publish the pair together. No mutable latest pointer or partial overwrite.
    with tempfile.TemporaryDirectory(prefix=".pending-", dir=folder.parent) as temporary:
        staging = Path(temporary)
        (staging / "movements.md").write_bytes(source.encode("utf-8"))
        (staging / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        staging.rename(folder)
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    writing = commands.add_parser("create", help="Read full movement export JSON from standard input")
    writing.add_argument("--name", default=f"movements_{uuid.uuid4().hex}")
    checking = commands.add_parser("check", help="Validate metadata before opening a saved ledger")
    checking.add_argument("folder", type=Path)
    checking.add_argument(
        "--through", type=float, required=True, help="This query's endpoint in absolute audio seconds"
    )
    args = parser.parse_args()
    try:
        ctx = context()
        if args.command == "create":
            folder = create(json.load(sys.stdin), ctx, args.name)
            result = {"snapshot": str(folder.relative_to(ROOT)), "format_version": 1}
        else:
            result = check((ROOT / args.folder).absolute(), ctx, args.through)
    except MovementError as error:
        parser.exit(1, f"Movement export unavailable: {error}\n")
    except (OSError, ValueError, KeyError, TypeError):
        # Raw exceptions may contain book strings or local audio/manifest paths.
        parser.exit(
            1,
            "Movement export unavailable: invalid format, provenance, scope, or private output path. Inspect locally.\n",
        )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
