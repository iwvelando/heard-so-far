# heard-so-far: implementation notes

Start with the project-root README.md for setup and Makefile commands.
AGENTS.md contains the authoritative reading protocol; progress.json is the sole
saved listening position and is intentionally ignored by Git.

- position.py validates progress and displays only chapter titles already begun.
- transcribe_section.py creates fresh, offline, bounded transcripts by default.
  Its --through option is relative to the last selected track. An explicit --name
  resumes compatible existing output; routine queries should omit it.
- transcripts/<run>/manifest.json records the audio fingerprint and core interval.
  chunk_*.json retains raw ASR, transcript.txt selects core words by timestamp
  midpoint, and boundaries.json retains overlapping readings for inspection.
- user_corrections.json contains user-verified, passage-specific corrections.
  Preserve raw ASR and do not turn these into global substitutions.
- journal.py records prepared reading answers from JSON on stdin. Its `list` and
  `read` commands require `--through` in absolute audio seconds and validate the
  current progress. Metadata excludes archived prose and gates access by source,
  requested scope, and evidence endpoint. See AGENTS.md for the input fields and
  automatic workflow. `journal/` is private, ignored, and survives cleanup.
- transcript_io.py validates chunk timing and complete extraction coverage for
  journaling and checks resumed chunks before their words are processed. It does
  not certify the accuracy of ASR or generated answers.
- check_public.py checks the public file inventory before staging and in CI.
- Historical pilot outputs may exist in ignored directories; the executable
  pilot has been retired. End-of-clip invented continuations are one reason for
  overlapping chunks and boundary checks; errors can also occur elsewhere.
- LOCAL_ONLY.md explains the instruction and runtime controls and their limits.

No transcript index is required. Regenerate evidence by default for each
query. If reusing old output, validate source, complete chunk coverage, and the
current question/progress boundaries before reading its story text.

Generated transcripts are unverified ASR, not canonical editions. Do not trust a
prior summary simply because it was generated or approved in another conversation.
