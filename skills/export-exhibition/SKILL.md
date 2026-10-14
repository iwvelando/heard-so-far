---
name: export-exhibition
description: Prepare or update a curated exhibition export from local, heard audiobook passages and user-selected artworks. Use when adding works to a public fan exhibition; not for ordinary reading answers or automatic publication.
---

# Export a curated exhibition

Read the repository's AGENTS.md and [export contract](../../spec/exhibition.md).
The public product is a curated fan exhibition. Private questions, agent answers,
generation conversations, and listening timestamps are not public content.
Selected user feelings or interpretations may accompany their individual artworks.
Do not manufacture first-person reflections or turn generic agent prose into the
user's voice. Artwork creation dates are optional and omitted in version 1.

## Establish the permitted material

Run the normal position and correction checks. Never advance progress because a
visitor is expected to have finished the book. The creator's listening endpoint
still limits every source passage available to the agent. Use only local book
evidence. Validate an existing selection's source and numeric scope before reading
its prose; run `exhibition.py check` first. If progress was rewound or the source
changed, do not open the old body. Start a scoped selection or ask for the intended
source. Fresh transcripts remain the default; deliberate reuse requires the usual
fingerprint, coverage, quality, and overlap checks.

Discover private selections under `companion/visualizations/exhibition/` using
filenames and metadata first. If none exists, obtain asset locations from the user.
Read prompt files only within their established scope. Another agent may be editing
those files: consume them as input without rewriting them. Journal records can help
locate a specific, relevant reflection only through the normal gated journal tools;
never bulk-import conversations.

## Curate the update

Keep stable work IDs and distinguish exhibition reconstructions from personal
interpretations. Verify each new book claim in a permitted passage. Separate
in-book attribution from the novel's authorship and the digital maker. Preserve
group credits, uncertain spellings, invented titles, and unspecified visual details.
Templates for unenumerated groups are not asserted counts of individual artworks.
Missing visual information is a reason to defer a reconstruction or explicitly
label a chosen interpretation, never to research the book online.

Maintain a private placement inventory alongside the selection when planning a
larger exhibition. Identify every prompt by stable ID and keep the input file hash,
source fingerprint and scope. Distinguish individual descriptions from templates
for unenumerated groups: a template does not determine an object count. Mark
imported prompt locations as candidates until checked against primary passages.
Keep depiction time separate from the chapter of disclosure, and record composites,
retrospectives and invented counterfactuals explicitly. Recheck changed prompts;
do not let a stale inventory become evidence. For placeholders, reserve a medium
and approximate footprint rather than inventing missing artwork. Treat their size
as a design estimate. Public placeholders belong in an explicit curator preview,
not the normal visitor collection.

When the recipient has a room plan, preserve its reservation IDs and explicit
work-to-position mapping. Replace a placeholder in place by attaching the stable
work ID and marking the asset ready; do not regenerate positions from catalog
order. Keep asset readiness separate from evidence for the placement. Check new
footprints and viewing points against circulation, including with all placeholders
visible. A group bay can expand deliberately as its actual works become known.
Export public geometry separately from the private source-to-reservation audit;
never copy the inventory wholesale. Run the recipient's layout and browser checks
after updating both catalog and plan.

Update the private selection defined by the export contract. Keep evidence intervals,
source paths, and review notes private. Personal image descriptions may describe the
visible art without asserting that all its details occur in the book. Any factual
scene explanation still needs transcript evidence. Review every public field and
the selected image itself before setting `reviewed: true`; that flag records the
agent's review within the user's authorized curation scope, not an extra permission
requirement. Do not quote the user's private words unless they selected them for use.

For spatial or visual changes, honor the conversation's theme choice. Keep artwork
masters untouched; preserve aspect ratios. Distinguish a frame already in an image
from a separate modeled frame. Each extension should retain source files and allow
later asset replacements without renaming the work.

## Prepare and hand off

From the companion root, run:

```sh
.venv/bin/python companion/exhibition.py check --input companion/visualizations/exhibition/selection.json
.venv/bin/python companion/exhibition.py export --input companion/visualizations/exhibition/selection.json --output companion/visualizations/exhibition/exports/UNIQUE_RUN
```

Choose a new output name for every export. Inspect `catalog.json` and all assets.
Only those public files may be copied to the explicitly identified exhibition
repository. Do not copy the private selection, audit records, source transcripts,
journal, prompts, or audio. The helper never writes to that repository itself.
When a local update is authorized, prefer the recipient's validated installer if
it has one. Preview the reviewed bundle, map each new work to an explicit existing
reservation, then apply locally. Check that unrelated works, positions, and
candidate/verified placement status stay intact. An installer's structural checks
do not replace the source review above. Run the recipient project's checks and
visual inspection after installation. Report works added, replaced, and deferred.
Publishing, pushing, or changing repository visibility needs authorization for that
action; preparing a local preview does not imply it.

The public entrance warns that the exhibition contains spoilers and is intended for
people who have finished the book. Do not add visitor listening-position controls.
The warning protects ordinary entry, not direct access to public source or assets.
