# heard-so-far

An audiobook companion for what you've heard so far.

![A smiling snail wearing headphones carries an open book along a dotted listening trail.](assets/heard-so-far.svg)

heard-so-far grounds summaries and clarification in your locally owned audiobook.
It extracts the requested, already-heard material, transcribes on Apple silicon,
and gives a file-capable assistant timestamped evidence to answer from. It is an
early project under trial, not a guarantee against spoilers or automatic speech
recognition (ASR) errors. Book identity and reading progress are local
configuration, not repository defaults.

## Requirements

- macOS on Apple silicon with Metal access to its graphics processing unit (GPU).
- Python 3.11 or newer, `uv`, `ffmpeg`/`ffprobe`, and `make` installed locally.
- A locally readable audiobook with embedded chapter markers. No audio, book
  text, model weights, or publisher metadata is distributed with this repository.
- An agent powered by a large language model (LLM) that can read project
  instructions, run local commands, and inspect files. AGENTS.md is the shared
  protocol; CLAUDE.md imports it for Claude Code.

The direct ASR dependency is pinned; transitive dependencies are not locked yet.
There is no digital rights management (DRM) removal workflow and no non-Apple
inference backend in this prototype.

## Start with your assistant

Open a new task or chat in this project root using your preferred agent client.
The shared `AGENTS.md` contains the reading protocol; `CLAUDE.md` imports it for
Claude Code. You can handle setup, listening updates, and reading questions in
the conversation without running terminal commands yourself.

Store your audiobook and its metadata under the ignored `audiobooks/` directory,
or give the assistant another local path. Then tell it the file, the exact track
title from your player, and your elapsed and remaining time. For example:

> Help me set up heard-so-far for my audiobook at `audiobooks/book.m4b`.
> This is my first read. I'm in “Chapter Two,” with 12:34 elapsed and 23:45
> remaining. Save that position, then summarize what I've heard of this chapter
> using only the local audiobook transcription.

The assistant uses the local helpers to set up dependencies and the speech model
if needed, validate your position, save it, and transcribe the permitted section.
Initial dependency installation and the model download need network access; the
model weights are about 1.6 GB. Your agent client may require permission for setup
or local GPU access. Subsequent transcription uses the cached model offline.

Elapsed plus remaining time identifies a track when titles repeat. If the match
is still ambiguous, the assistant will ask for the track number or occurrence.
There is no default book or listening position in a fresh clone.

### Keep listening and asking

Tell the assistant when your position changes, then ask your question:

> I'm now at 20:00 elapsed with 16:19 remaining in “Chapter Two.” Update my
> position and recap what happened since my last question.

If you haven't advanced, just ask a question; the assistant uses your saved
position until you explicitly update it. It generates fresh transcripts by
default and checks the evidence before answering. Outside book sources are used
only if you explicitly opt in as described below.

Use a chat per chapter or listening session, keeping related follow-ups together.
The assistant keeps a private journal of local-only questions and answers so a
new chat can pick up useful context. You do not need to manage it yourself.

If something was misheard, give the correction in the conversation:

> At about 08:15, the narrator says “this here's about,” not “this year's about.”
> Please use that correction for this passage.

The assistant should save your correction for that book and passage and apply it
when answering relevant questions. It should keep uncertain wording or spelling
explicit rather than silently guessing.

To change books, provide the new audio path and position. The workspace maintains
one active book at a time; corrections stay with their book. Transcription detects
language automatically, or you can tell the assistant which language to use.

## Optional: cross-reference a source you choose

Local-only reading is the default. If you want a wiki or other reference alongside
the audiobook, explicitly authorize a specific page for your question:

> For this question, compare the local transcript with this chapter-summary page:
> [paste the page address]. It covers only Chapter Two, which I've finished.
> Use only that page, don't follow links, and keep the answer within Chapter Two.

Choose a page limited to material you've heard, or paste a bounded excerpt.
Whole-book pages, navigation panels, and character biographies can contain
spoilers. A page address or section anchor alone does not establish a safe
boundary; if the scope is unclear, the assistant should ask for an excerpt
instead of opening it to find out.

The assistant should distinguish the page's claims from the audiobook and cite
the page when using it. This opt-in does not authorize a general web search or
change your saved listening position. Your agent client must permit access to
the page; the project does not automatically change its permissions.

Web-assisted answers are excluded from the local-only journal. Start a fresh
chat when returning to local-only reading, so the outside reference is no longer
part of the conversation's context. See the [source policy](spec/external-sources.md)
for the full protocol and its limits.

## Alternative: use the commands yourself

These are the same helpers the assistant uses. Run them from the repository root
if you prefer to manage setup and progress directly:

```sh
make setup
make download-model
make doctor

make progress TITLE='Your current track title' ELAPSED=12:34 REMAINING=23:45 AUDIO='audiobooks/book.m4b'
make position
```

`make progress` validates and saves your position; `make position` displays the
saved position and tracks already begun. `AUDIO` is required on first setup.
Later updates retain that path unless you provide a new one. If a repeated title
and duration are still ambiguous, add `TRACK=N`, the track index counting from
one. Add `SPEECH_LANGUAGE=es`, for example, to specify Spanish instead of automatic
detection; that choice is retained for the same source.

To transcribe manually, `FIRST` and `LAST` are the **inclusive track indexes in
the audio file, counting from one**. They refer to the `track` values shown by
`make position`, not chapter numbers printed in a title. Tracks with duplicate
titles still have distinct indexes. For example:

```sh
# Transcribe tracks 1 and 2 in full.
make transcribe FIRST=1 LAST=2
# Transcribe only track 3, ending 12 minutes and 34 seconds into that track.
make transcribe FIRST=3 LAST=3 THROUGH=12:34
```

These are illustrative values; choose indexes and times within your saved
progress. `THROUGH` is an elapsed time within `LAST`, in `MM:SS` or `HH:MM:SS`, not
an absolute position in the whole audiobook. Requests beyond progress fail; an
unfinished track requires an explicit partial endpoint. A five-second buffer is
kept before the saved listening point. Reading-time model loading uses
`HF_HUB_OFFLINE=1` so it cannot fetch missing weights.

## Privacy and practical limits

Audio transcription runs locally. If your assistant uses a hosted model, the
text it reads enters that provider's model context. Local-source answers do not
mean that the entire conversation happens offline.

Purchased audio, transcripts, listening progress, corrections, and the query
journal are excluded from Git by the project's ignore rules. Keep book files in
`audiobooks/` or another ignored location, and avoid sharing book content in
public issues or chat exports.

The assistant can mishear speech, invent details, or mishandle a spoiler boundary.
Replay anchors and your corrections help you check its answers. The project
supports one audio file with embedded chapter markers; chapter order must follow
audio order. Recordings without markers and multi-file books are not supported.

For stricter local-only tool settings, see [the configuration notes](companion/LOCAL_ONLY.md).
They explain the optional Codex template and what must be configured separately
in other agent clients.

## Clearing generated files

Ask the assistant to clear generated transcripts and audio samples, or run
`make clean`. Your audiobook, listening position, corrections, journal, and
cached speech model are kept. The assistant can transcribe again when needed.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and contribution guidance,
[spec/](spec/README.md) for the project's behavioral contracts, and
[the implementation guide](companion/README.md) for the helper scripts.

## License

Project code and documentation are available under the [MIT license](LICENSE),
using the [standard MIT terms](https://opensource.org/license/mit).
This does not license or distribute your audiobook, transcripts of purchased
material, third-party dependencies, or separately downloaded model weights.
