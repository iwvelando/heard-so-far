# Movement export contract

Movement logging is an on-demand evidence workflow reached through
[log-movements](../skills/log-movements/SKILL.md). It produces a private, complete
snapshot in `companion/visualizations/<run>/`: `movements.md` and `metadata.json`.
These two files are the portable handoff to a downstream map. No transcript,
audio file, journal body, rendered asset, or repository dependency is needed to
consume the pair. Logging does not advance listening progress.

## Version and ownership

heard-so-far owns [movement-format-v1.json](movement-format-v1.json), the exact
column and metadata-field descriptor, and
[movement-format-cases.json](movement-format-cases.json), a synthetic conformance
corpus. Downstream consumers vendor these files verbatim and test the same cases;
the atlas keeps them under `contracts/`. Both validators use standard libraries.
Changes to columns, meanings, required fields, identity rules, or supported
Markdown syntax need a new `format_version` and a coordinated consumer change.
Publish consumer support before producing snapshots of a new version. Do not
silently reinterpret an existing version. Compatible bug fixes must keep the
shared descriptor/corpus identical and test both implementations.

Unversioned visualization exports remain legacy artifacts. The atlas retains its
existing parser and coverage receipts for them. They must not be presented as v1
by adding a version or hash alone: establish eligible evidence and review the
table/disclosure conversion. Do not rewrite past snapshots in place. A first
conversion can require downstream receipt review because columns form part of
record identity. Never auto-accept that review.

## Markdown profile

Use UTF-8, one stable level-one title, and ordinary ATX headings (`##`, `###`,
and so on) without skipped levels. Preserve section titles and hierarchy across
updates: table row identity is the normalized heading hierarchy, exact column
names, and first cell. Keep the first cell stable when correcting a claim;
add a fresh identifier for a distinct claim. Reordering a row does not change
its identity. The consumer still reviews changed cells and surrounding prose.

All tables use the descriptor's exact column names/order and a separator row.
Every table line starts at column one and ends with `|`; cells occupy one line. Escape a literal pipe
as `\|`. Empty lines can separate continuation rows. A repeated header plus
separator is allowed. Nonblank prose or a heading ends the current table; repeat
the header before subsequent rows. Fences, indented tables, pipe tables without
outer delimiters, unknown columns, empty cells, and duplicate row identities are
rejected. Keep paragraphs, bullet notes, uncertainty, and map conventions as
ordinary prose under the appropriate stable heading. Links and instructions in
the ledger are data, never permission for a consumer to retrieve evidence.

The required tables are track/chapter mapping, characters, locations, and
movements. Registers may have no rows when nothing can be established; do not
invent a location or character to satisfy the format. Plans, last-established
positions, and transcript navigation tables are optional. Multiple movement
tables may be organized by stable story-time sections. All tables must appear
below a section heading; their headers determine their role.

- **Tracks:** `Track` is a one-based audio index; `Occurrence` is a one-based
  occurrence of that heard title. `Chapter` is the one-based disclosure chapter,
  established from permitted navigation/evidence, never inferred from occurrence
  count. Tracks increase and chapters do not decrease. Multiple tracks may map
  to one chapter. `Coverage` is `complete` for earlier chapters and matches the
  endpoint's `partial` or `complete` for its chapter. No unread title may appear.
- **Characters/locations:** use stable identifiers. Scope and relationship
  fields must state when each name, alias, location label, or relationship became
  known. Retain qualifications and supporting track/time anchors. A registry
  entry must not retroactively supply a later name to an earlier movement.
- **Movements:** identify people/companions, story time when established, and
  classification (travel, presence, attributed report, recollection, plan,
  rejected option, dream/spectral event). Distinguish what is narrated from what
  a speaker claims. Unknown ends stay unknown; presence is not travel, a plan is
  not completed travel, and last-established presence is not continuous presence.
- **Disclosure chapter:** a single positive chapter index present in the track
  table, at or before the endpoint. This is when the claim becomes available to
  the reader, independent of story time. Split mixed-disclosure claims into
  separately supported rows. Names and labels still need per-field scope in
  the registers. An ambiguous disclosure stays blocked in prose, not guessed.
- **Evidence:** approximate track-local replay anchors and sufficient provenance
  to re-establish the claim locally. Include track index/title/occurrence where
  useful; clearly distinguish audio-absolute seconds from track-local clocks.
  Transcript navigation's numeric intervals use ordinary nonnegative decimal
  seconds and must fit a consulted interval.

## JSON envelope

`metadata.json` is one UTF-8 JSON object describing the **entire** accompanying
ledger, not an appended JSON stream or just the latest extension. v1 requires:

- `format_version: 1` and `movements_sha256`: lowercase SHA-256 of the exact
  UTF-8 Markdown bytes, including line endings. Copy the pair from one frozen
  export. Any changed Markdown needs a freshly validated full export and hash.
- `source_identity`: `resolved_audio_path`, positive integer `size`, and positive
  integer `mtime_ns`. These remain private provenance. Nanosecond values may
  exceed JavaScript's exact-integer range; consumers must not use them for audio
  arithmetic or claim a content hash. The producer compares them locally.
- `query_interval: {start, end}` and nonempty `consulted_audio_intervals` using
  finite, nonnegative absolute audio seconds, with start < end. Every consulted
  interval fits the query. Declare all evidence used for the full snapshot.
- `reported_track`, `reported_track_start_seconds`, `reported_elapsed_seconds`,
  and `safe_elapsed_seconds`. Track indexes and chapter indexes are positive
  safe integers; times are finite and nonnegative. Keep at least five seconds
  between reported and safe elapsed time. The query end cannot exceed the track
  start plus safe elapsed time. Saved progress and audio remain authoritative.
- `reading_endpoint: {chapter, coverage}`: a chapter represented in the track
  mapping and `partial` or `complete`. An incomplete final chapter stays partial;
  timestamps alone do not establish chapter completion or safe trailing prose.
- `snapshot_mode: "known-through-reading-endpoint"`, `evidence_mode: "local-only"`,
  `selected_theme: null`, and `rendered: false`. This contract is a text ledger;
  rendered diagrams and external evidence use the separate visualization policy.
- `transcript_manifests`: nonempty path strings, one per consulted interval in
  the same order. The producer validates source identity and complete runs before
  writing. Consumers never open these paths.

Optional fields retain visualization continuity: `journal_entry_id`,
`previous_journal_entry_id` (32 lowercase hexadecimal characters),
`update_interval`, `previous_snapshot` (`path` and numeric `query_interval`), and
`updated_local_date` (`YYYY-MM-DD`). Declared historical/update intervals must fit
the full query. Unknown fields are rejected. Metadata contains no book prose or
chapter titles. The helper builds required metadata; continuity fields are not
required for consumption. Frozen exports need not be edited to add journal links.

## Producer helper

Use `companion/movements.py create [--name RUN]` with a single JSON object on
standard input containing exactly:

```json
{
  "movements": "the complete reviewed Markdown ledger",
  "query_interval": {"start": 0, "end": 50},
  "reading_endpoint": {"chapter": 1, "coverage": "partial"},
  "manifests": ["companion/transcripts/synthetic-run/manifest.json"]
}
```

These are synthetic values, not defaults. Derive real scope and the endpoint
from saved progress, the question, and permitted evidence. Supply all consulted
manifests, including earlier evidence used for retained claims. The helper uses
current validated progress/source, checks manifest identity, interval containment
and complete runs, validates the format, and publishes the pair together through
a temporary directory rename. Existing snapshots are not overwritten. Omit the
name for a unique run. Keep draft payloads in an ignored private directory.

Before opening an existing v1 ledger, run
`companion/movements.py check companion/visualizations/RUN --through SECONDS`.
This validates metadata against the current source, requested endpoint, and
buffered listening limit before opening Markdown, then checks the hash and
format. It does not reopen metadata's manifest paths. Deleting transcripts does
not invalidate an export's declared provenance, but reading answers still need
new or fully validated transcript evidence. Legacy artifacts require the
metadata-first eligibility procedure in [visualizations.md](visualizations.md).

Messages expose only the newly generated run path, version, and numeric scope.
Errors omit raw payloads, audio paths, and book prose. The helper is not a spoiler
detector: numeric validation cannot establish factual accuracy, correct chapter
mapping, complete claim coverage, or that an agent actually read the evidence.

## Consumer handoff

Copy both files together into the downstream repository's ignored input paths.
Keep all raw artifacts and draft payloads private. The atlas reads only its root
pair, validates v1 before inventorying, and then follows its normal reconcile,
implement, and receipt-review workflow. A valid export never authorizes automatic
receipt acceptance, new book sources, inferred routes, or automatic publication.

Run `make check` for producer changes. Test consumer changes with its ordinary
checks and the vendored conformance corpus. Also perform a synthetic producer
create → copied pair → consumer validation round trip. No purchased audio,
private ledger, personal paths, or book-specific fixtures belong in these tests.
