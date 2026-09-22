"""Private query records; metadata is checked before archived prose is opened.

This is an agent-invoked helper, not an automatic post-response hook. Records
contain prepared answers, not proof that a response was delivered or is correct.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import uuid

from position import ROOT, PROGRESS, probe, validate
from transcript_io import validate_run


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Audio times must be finite, nonnegative seconds")
    return value


def interval(value):
    start, end = number(value["start"]), number(value["end"])
    if start >= end:
        raise ValueError("Scope must have start < end")
    return {"start": start, "end": end}


def context():
    progress = json.loads(PROGRESS.read_text())
    audio = (ROOT / progress["audio_file"]).resolve()
    safe_end = validate(progress, probe(audio))
    stat = audio.stat()
    source = {"path": str(audio), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    # A conservative local identity, not a hash of the audio's contents.
    source_id = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    return progress, source, source_id, safe_end


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def record(payload, ctx):
    progress, source, source_id, safe_end = ctx
    scope = interval(payload["scope"])
    if scope["end"] > safe_end:
        raise ValueError("Query scope exceeds the buffered listening limit")
    for field in ("question", "answer"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise ValueError(f"A nonempty {field} is required")
    paths = payload["manifests"]
    if not isinstance(paths, list) or not paths:
        raise ValueError("Include every consulted transcript manifest")
    evidence = []
    for name in paths:
        path = (ROOT / name).resolve()
        manifest = json.loads(path.read_text())
        if ((ROOT / manifest["source_audio"]).resolve() != Path(source["path"])
            or manifest["source_size"] != source["size"]
            or manifest["source_mtime_ns"] != source["mtime_ns"]):
            raise ValueError("Transcript manifest belongs to a different or changed source")
        span = interval({"start": manifest["section_start"], "end": manifest["section_end"]})
        if span["end"] > scope["end"]:
            raise ValueError("Consulted transcript extends beyond this query's scope")
        validate_run(path.parent, manifest)
        evidence.append({"manifest_path": str(path), "manifest": manifest})
    entry_id = uuid.uuid4().hex
    metadata = {"version": 1, "id": entry_id, "source_id": source_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "scope": scope,
                "evidence_end": max(item["manifest"]["section_end"] for item in evidence)}
    # A user's current track may be later than the requested section. Keep only
    # numeric listening limits here, never that later track's title or prose.
    body = {"metadata": metadata, "source": source,
            "progress": {"cutoff_audio_seconds": progress["cutoff_audio_seconds"],
                         "safe_audio_end_seconds": safe_end},
            "question": payload["question"], "answer": payload["answer"],
            "evidence": evidence, "status": "prepared"}
    folder = ROOT / "companion/journal" / source_id
    folder.mkdir(parents=True, exist_ok=True)
    # Publish the metadata/body pair together; interrupted writes stay invisible.
    with tempfile.TemporaryDirectory(prefix=".pending-", dir=folder) as temporary:
        staging = Path(temporary)
        write_json(staging / "meta.json", metadata)
        write_json(staging / "entry.json", body)
        staging.rename(folder / entry_id)
    return metadata


def permitted(metadata, source_id, limit, entry_id):
    return (metadata["version"] == 1 and metadata["id"] == entry_id
            and metadata["source_id"] == source_id
            and interval(metadata["scope"])["end"] <= limit
            and number(metadata["evidence_end"]) <= metadata["scope"]["end"])


def entries(ctx, through):
    _, _, source_id, safe_end = ctx
    limit = min(number(through), safe_end)
    folder = ROOT / "companion/journal" / source_id
    rows = []
    for path in folder.glob("*/meta.json"):
        if not re.fullmatch(r"[0-9a-f]{32}", path.parent.name):
            continue
        try:
            metadata = json.loads(path.read_text())
            if permitted(metadata, source_id, limit, path.parent.name):
                # No chapter names, questions, answers, or other archived prose.
                rows.append({key: metadata[key] for key in
                             ("id", "created_at", "scope", "evidence_end")})
        except (OSError, ValueError, KeyError, TypeError):
            continue  # Incomplete or invalid metadata is never eligible.
    return sorted(rows, key=lambda row: row["created_at"], reverse=True)


def read_entry(ctx, through, entry_id):
    if not re.fullmatch(r"[0-9a-f]{32}", entry_id):
        raise ValueError("Invalid journal entry ID")
    _, source, source_id, safe_end = ctx
    folder = ROOT / "companion/journal" / source_id / entry_id
    metadata = json.loads((folder / "meta.json").read_text())
    if not permitted(metadata, source_id, min(number(through), safe_end), entry_id):
        raise ValueError("Journal entry is outside the current source or query limit")
    body = json.loads((folder / "entry.json").read_text())
    if body["metadata"] != metadata or body["source"] != source:
        raise ValueError("Journal body does not match its metadata")
    evidence_ends = []
    for item in body["evidence"]:
        manifest = item["manifest"]
        span = interval({"start": manifest["section_start"], "end": manifest["section_end"]})
        if ((ROOT / manifest["source_audio"]).resolve() != Path(source["path"])
            or manifest["source_size"] != source["size"]
            or manifest["source_mtime_ns"] != source["mtime_ns"]):
            raise ValueError("Archived evidence does not match the source")
        evidence_ends.append(span["end"])
    if not evidence_ends or max(evidence_ends) != metadata["evidence_end"]:
        raise ValueError("Archived evidence does not match the declared time limit")
    # Return only answer fields: a stored progress object may name a track
    # beyond this query's scope and must not enter the caller's context.
    return {key: body[key] for key in ("metadata", "question", "answer", "evidence", "status")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("record", help="Read question/answer/scope/manifests JSON from stdin")
    listing = commands.add_parser("list", help="Show eligible metadata only, newest first")
    listing.add_argument("--through", required=True, type=float, help="Current query endpoint in absolute audio seconds")
    listing.add_argument("--limit", type=int, default=5)
    reading = commands.add_parser("read", help="Check metadata before opening one entry")
    reading.add_argument("id")
    reading.add_argument("--through", required=True, type=float)
    args = parser.parse_args()
    try:
        ctx = context()
        if args.command == "record":
            result = record(json.load(sys.stdin), ctx)
        elif args.command == "list":
            if args.limit < 1:
                raise ValueError("Limit must be positive")
            result = entries(ctx, args.through)[:args.limit]
        else:
            result = read_entry(ctx, args.through, args.id)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Journal unavailable: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
