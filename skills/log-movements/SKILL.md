---
name: log-movements
description: Log or extend character movements from permitted local audiobook evidence and export a versioned movements.md and metadata.json pair for a downstream map.
---

# Log character movements

Read root `AGENTS.md` and [the movement contract](../../spec/movements.md).
Use this repo-local workflow when asked to log, record, update, or export character
movements. It produces evidence ledgers, not rendered diagrams; no theme question
is needed unless the user also requests a visualization.

Establish saved progress and this request's scope through `position.py show`.
Do not infer listening advancement. Apply the normal local-only transcription,
correction, and trailing-cutoff rules. If the endpoint is ambiguous, resolve it
before reading book prose. Do not use outside references or model memory.

When extending a saved ledger, check its metadata before reading its body:

```sh
.venv/bin/python companion/movements.py check companion/visualizations/RUN --through SECONDS
```

Use this for v1 snapshots. For an unversioned artifact, follow the metadata-first
eligibility checks in `spec/visualizations.md`; the helper deliberately rejects
it as a v1 export. Ineligible artifacts must not be read for continuity. Eligible
old rows and journals locate passages; they do not replace transcript evidence.

Re-establish every retained or changed claim from permitted local transcripts,
using fresh transcription by default. Inspect manifests, complete extraction
coverage, quality flags, and relevant overlaps as required by `AGENTS.md`. Record
all consulted manifests for the full snapshot. Review corrections and duplicate
claims before appending. Preserve stable section paths and first-cell IDs; do not
renumber old rows or merge uncertain aliases merely to make a cleaner map.

Write a **complete cumulative ledger**, using the contract's exact headers.
Separate travel, presence, plans/rejected options, reports, historical disclosures,
and dreams/spectral events. Keep unknown origins/destinations, uncertain names,
attribution, and companions explicit. Supply numeric disclosure chapters and a
track/chapter table; repeated tracks are not extra chapters. Split claims whose
disclosure differs. Scope registry labels individually. Keep the final chapter
partial when evidence is partial. Do not invent geography or complete an unheard
trailing thought.

Save a draft JSON payload under ignored `companion/visualizations/` with
`movements`, `query_interval`, `reading_endpoint`, and `manifests`, as described
in the contract. Publish a new frozen pair with:

```sh
.venv/bin/python companion/movements.py create --name RUN < PRIVATE_PAYLOAD.json
.venv/bin/python companion/movements.py check companion/visualizations/RUN --through SECONDS
```

Use literal quoted heredocs or a private JSON file for prose; never interpolate
it into shell code. `create` derives provenance from current progress and checked
manifests. It does not overwrite a previous snapshot. Review the exported ledger
against the evidence; helper success validates structure and scope, not facts.
If validation fails, fix the draft or evidence and retry; never weaken boundaries
or mark an unsupported claim complete. Migrating legacy headers requires a
reviewed new snapshot, not an in-place edit or automatic downstream acceptance.

Follow the normal private query-journal workflow for the final reading answer.
Report the frozen pair's location and actual scope/remaining uncertainties. The
pair is the downstream handoff; do not send transcripts or provenance paths to
the consumer, copy facts into public docs/agent memory, or publish an atlas as
part of logging unless the user separately asks. Downstream map updates continue
to use their own content review and receipt workflow.
