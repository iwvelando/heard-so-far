# heard-so-far: behavioral contracts

These contracts guide development and review. The user-facing workflow belongs
in [README.md](../README.md); operational instructions for the agent belong in
[AGENTS.md](../AGENTS.md). Changes to behavior must keep those documents and the
relevant regression tests consistent. Describe the supported behavior directly,
without development history or migration narrative.

## Evidence and listening limits

- Local-only evidence is the default: the selected audiobook, automatic speech
  recognition (ASR) derived from it, and explicit user corrections tied to that
  source and passage. Model knowledge and generated answers are not evidence.
- External references require the explicit, scoped opt-in defined in
  [external-sources.md](external-sources.md). Technical setup documentation is
  separate from permission to retrieve book information.
- Only an explicit user update may advance listening progress or change books.
  A question or a character name must not be treated as evidence of advancement.
- Resolve title plus elapsed and remaining time against embedded audio chapter
  markers. Repeated titles remain distinct track entries. Missing or ambiguous
  progress must be resolved before accessing story text.
- The requested section can be narrower than the listening limit. A summary
  of an earlier chapter must not incorporate later material even if already heard.
- Extraction must stay within the requested interval and end at least five
  seconds before the saved listening position. Context for ASR must not cross
  those bounds. Do not extend into unheard audio to complete a sentence.
- Navigation output must not reveal titles of tracks not yet begun. It must not
  include publisher summaries, reviews, or other descriptive sidecar content.

`position.py` and `transcribe_section.py` enforce numeric boundaries. Choosing the
correct question scope and keeping prose within it also require agent judgment.

## Transcription and corrections

Fresh transcription is the default. Whole-section summaries require complete
coverage of that section; a few matching snippets are insufficient.

The transcription pipeline uses ten-minute core chunks with twenty seconds of
context at internal boundaries, clipped to the permitted extraction interval.
It retains raw chunks, a readable transcript, overlap comparisons, and a manifest
containing source identity and extraction settings. Spoken-word timestamps are
approximate; first and last words alone cannot establish continuous coverage.

Reused chunks must match the requested extraction envelope. Before accepting a
run for journaling, all required chunks and final outputs must exist. A manifest
alone is not a completed transcription. These checks establish structural
coverage, not recognition accuracy or proof that an agent read the evidence.

Corrections must be stored privately with their source and passage. They must
remain attributed to the user and must not silently rewrite raw ASR, become
global substitutions, or transfer between books. Uncertain names, dialect,
negation, and speaker attribution require explicit uncertainty or further local
inspection. A long sentence does not need terminal punctuation to contain a
usable clause.

## Visualizations

[visualizations.md](visualizations.md) defines the on-demand diagram workflow:
theme selection, snapshot semantics, evidence tables, rendering review, and
private artifacts. Visual labels and relationships must obey the same evidence
and listening limits as prose. This workflow does not require automatic
post-processing of every transcript or a persistent character database.

## Query journal

The journal supports continuity without making conversation history authoritative.
The agent records the exact question and prepared answer before sending each
eligible local-only reading response. Maintenance, unresolved clarification,
and external-source queries do not produce reading journal entries.

Required properties:

- Entries are private, excluded from Git, and isolated by local source identity.
  Identity uses the resolved audio path, size, and modification time; it is not
  an audio-content hash. Moving or changing the file selects a different journal.
- Entries retain numeric listening limits and a snapshot of every consulted
  transcript manifest. The snapshot makes the extraction interval available even
  if generated transcript files are later cleared.
- Metadata is checked before archived prose is opened. Source, requested scope,
  and all consulted evidence must fit both the new question and current progress.
  A record about an early chapter is ineligible if it consulted later evidence.
- Listing returns a small number of metadata records without archived questions,
  answers, or chapter titles. Reading returns only the permitted answer fields;
  a saved progress object must not expose a later chapter title.
- Metadata and body must agree. Missing, malformed, or inconsistent records
  must not be used. Publishing a record must not expose a partially written pair.
- Saved answers are passage locators, never primary evidence. Claims must be
  re-established from permitted audio or transcripts before answering again.
- Corrections produce new entries; prepared answers are not silently rewritten.
  Book notes must not be copied to automatically loaded agent memory, which would
  bypass eligibility checks.
- Cleanup preserves the journal. A failed journal write must not suppress the
  reading answer; the agent must briefly disclose the save failure.

`prepared` is a storage status, not proof of delivery or accuracy. Journaling is
an agent-invoked workflow rather than a post-response hook. The helper checks
declared source metadata and times; it cannot detect unreported outside sources,
determine whether prose contains a spoiler, or certify answer quality.

## Local operation and publication

Reading-time ASR loads cached model weights offline. Installing dependencies and
downloading a model are explicit setup operations. Neither a failed transcription
nor optional reference-page access authorizes uploading audio or enabling general
network access. Client-level restrictions and agent instructions are separate
controls; the agent shares a workspace with the original audio and can access it.

Cleanup must stay within designated generated-data directories, refuse unsafe
symlink paths, and coordinate with active transcription or model downloads.
Purchased media, progress, corrections, and journals must survive normal cleanup.

Public files must remain independent of any book or reader. Purchased material,
private answers, local paths, credentials, and machine-specific agent settings
must not be published. The public-file inventory catches unexpected paths, but
does not replace reviewing file contents.

## Verification

`make check` runs boundary, transcript-coverage, journal, cleanup, and public-file
checks using synthetic data. GitHub continuous integration (CI) runs those checks
without a speech model. It does not validate graphics processing unit (GPU)
inference, transcription quality, or agent compliance with prose instructions.

Changes to boundaries, eligibility, or cleanup need regression tests for the
failure they prevent. External-source behavior is an instruction-level contract;
review it with bounded examples and verify that the client actually enforces any
tool restrictions being claimed. Do not describe an untested policy as a hard
security boundary or a guarantee against spoilers.
