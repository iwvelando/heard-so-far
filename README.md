# heard-so-far

An audiobook companion for what you've heard so far.

heard-so-far grounds summaries and clarification in your locally owned audiobook.
It extracts the requested, already-heard material, transcribes on Apple silicon,
and gives a file-capable assistant timestamped evidence to answer from. It is an
early project under trial, not a guarantee against spoilers or ASR errors. Book
identity and reading progress are local configuration, not repository defaults.

## Requirements

- macOS on Apple silicon with working Metal/GPU access.
- Python 3.11 or newer, `uv`, `ffmpeg`/`ffprobe`, and `make` installed locally.
- A locally readable audiobook with embedded chapter markers. No audio, book
  text, model weights, or publisher metadata is distributed with this repository.
- An agent that can read project instructions, run local commands, and inspect
  files. AGENTS.md is the shared protocol; CLAUDE.md imports it for Claude Code.

The direct ASR dependency is pinned; transitive dependencies are not locked yet. There is no
DRM-removal workflow and no non-Apple inference backend in this prototype.

## Initial setup

Run from the repository root:

```sh
make setup
make download-model
make doctor
```

The first two steps need network access. `download-model` fetches about 1.6 GB of
speech model weights, not book content. Reading-time transcription uses the cache
with `HF_HUB_OFFLINE=1`. The answering model is supplied by your agent client.
With a hosted model, permitted transcript excerpts enter that provider's model
context; local transcription does not make the entire conversation offline.

Store your audiobook and its metadata under the ignored `audiobooks/` directory,
or use another local path. Explicitly supply the source when setting your first
position; there is no default book:

```sh
make progress TITLE='Your current track title' ELAPSED=12:34 REMAINING=23:45 AUDIO='audiobooks/book.m4b'
make position
```

Elapsed plus remaining time identifies a track when titles repeat. If that is
still ambiguous, add the one-based `TRACK=N` reported by your player. No progress
is included in a clone; it must be explicitly established before a reading query.
Updates are validated against the embedded audio markers and saved locally.
Later updates retain the saved audio path unless you explicitly supply `AUDIO`.

Changing books requires setting a new `AUDIO` and listening position; no edits to
`AGENTS.md` or Python code are needed. The workspace maintains one active book at
a time. Corrections are specific to the source and passage they identify; do not
transfer them between books. The script assumes chapter order follows audio order.

Transcription detects language automatically. Add `SPEECH_LANGUAGE=es`, for example, to
the progress command to specify it. Later updates retain that choice for the same
source; changing sources resets it unless specified again. Recognition quality
depends on the language and recording. Recordings without embedded chapter markers
and multi-file books are not yet supported by the navigation workflow.

## Ask a reading question

Start a **new task in this project root**. The shared `AGENTS.md` directs it to
validate progress, transcribe a bounded section, read the evidence, and answer
without outside book sources. For example:

> Use the project's reading rules and saved progress. Summarize the opening
> section using only its local audiobook transcription.

Fresh transcripts are the default. For manual use:

```sh
make transcribe FIRST=1 LAST=2
make transcribe FIRST=3 LAST=3 THROUGH=12:34
```

These are illustrative values; first confirm your own permitted tracks with
`make position`. `THROUGH` is relative to the last
track. Requests beyond progress fail; an unfinished track requires an explicit
partial endpoint. A five-second buffer is kept before the saved listening point.

Outputs go to a new `companion/transcripts/query_*/` directory. The manifest
records the source fingerprint and extraction interval. Raw chunks, a readable
transcript, and overlapping-boundary comparisons are retained. The ten-minute
chunks receive 20 seconds of context at internal breaks, within the requested
section. Word timestamps and overlap selection still require judgment.

Use `transcribe_section.py` for reading queries. The early pilot entry point has
been retired so there is only one supported transcription path. User corrections
belong in the ignored `companion/user_corrections.json` file, not in tracked book
notes or a purported canonical character glossary.

### Query continuity

Use a task per chapter or listening session, keeping related follow-ups together.
`AGENTS.md` instructs the agent to save each transcript-grounded question and
prepared answer automatically in the ignored `companion/journal/`, along with
progress and source intervals. You do not need to maintain it manually. This is
an agent instruction, not a guaranteed post-response hook; interrupted tasks may
leave a prepared answer that was never delivered.

Future tasks can inspect a few eligible journal entries to locate passages,
then verify claims against transcripts. Archived answers are not source evidence.
The helper checks source identity and time limits before opening an entry's body.
It requires complete transcript chunks and final outputs before recording new
evidence. Archived progress titles are never returned with an earlier answer.
Journals survive transcript cleanup; references retain extraction metadata so
deleted evidence can be regenerated. Moving or modifying an audio file starts a
separate journal because identity uses its path, size, and modification time.
Keep book notes out of auto-loaded agent memory; only the journal checks whether
an entry fits the current question's scope before presenting its prose.

## Local-source controls

`AGENTS.md` forbids web searches, outside book sources, and unsupported literary
embellishment. `companion/local-only.config.toml` provides project defaults for
disabled web search and disabled sandbox command networking. To use those
defaults, copy it to `.codex/config.toml` in a trusted project, without overwriting
an existing configuration you need. That machine-local directory is ignored.
This template is specific to Codex. Other clients need their own network and tool
permissions; importing the reading instructions does not apply Codex settings.

Read [the enforcement notes](companion/LOCAL_ONLY.md) for limits: browser and
connector access are separate, the same-workspace agent can access raw files,
and instructions cannot remove an LLM's prior knowledge. GPU execution may need
separate permission in a sandboxed Codex session. These defaults are not a
verified, complete network isolation policy.

## Testing and cleanup

```sh
make test
make check-public
make clean-transcripts
make clean-audio
make clean
```

Tests use synthetic chapter data and no model download. Cleanup removes only
derived files in the named directories. `clean` preserves the purchased audio,
saved progress, user corrections, query journals, virtual environment, and cached model. Cleanup
and normal transcription share a lock to avoid deleting an active run's files.

`make clean-cache` separately deletes the model and dependency cache. Use it only
when you intend to download the model again before the next reading query.

`make check` runs both tests and the public-file check. On macOS or Linux, use
`make check PYTHON=python3` without a virtual environment or ASR dependencies.
GitHub CI uses that lightweight path. See [CONTRIBUTING.md](CONTRIBUTING.md) for
test expectations and review steps; CI does not test GPU inference or answer quality.

## Version-control boundaries

`.gitignore` excludes source audio, the `audiobooks/` directory and metadata,
generated audio/text, model caches, virtual environments, personal progress and
corrections, query journals, and local Codex config. If you store publisher metadata or other
book content elsewhere, add that location to the ignore rules before staging.
Do not force-add ignored material. Review `git status --short` and any staged diff
before a future commit. `make check-public` flags tracked or addable paths outside
the reviewed public inventory, including private files accidentally force-added
to Git. It does not replace reviewing the contents of permitted source files.

## License

Project code and documentation are available under the [MIT license](LICENSE),
using the [standard MIT terms](https://opensource.org/license/mit).
This does not license or distribute your audiobook, transcripts of purchased
material, third-party dependencies, or separately downloaded model weights.
