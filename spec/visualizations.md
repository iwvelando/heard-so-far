# Family trees and relationship diagrams

This is an on-demand agent workflow for a requested visualization. It does not
add a transcript-processing stage or establish a canonical character database.
The [evidence contracts](README.md) and [external-source policy](external-sources.md)
apply to the diagram, evidence table, and every exported artifact.

## Theme and rendering

Before rendering, ask: "Would you prefer a high-contrast light or dark theme?"
Reuse a preference explicitly given in the current conversation. Do not infer it
from the host application's appearance. If the user delegates the choice, select
a high-contrast light theme and state that choice. If they have not answered,
continue permitted evidence work while waiting; do not silently select a theme.

Set the theme explicitly. Text, edges, arrowheads, node borders, group boundaries,
and edge-label backgrounds must remain distinguishable from their actual rendered
backgrounds. Color must not be the only way to distinguish relationship types,
status, or uncertainty. Provide a legend for line styles and direction; reserve
each style for a defined meaning or qualify individual edges explicitly.

Inspect the rendered output at its intended reading size. Check contrast,
clipping, crossed or obscured labels, and long labels shrinking the whole diagram.
Source syntax or a named theme alone does not establish legibility. Split a large
cast into smaller diagrams and move detailed qualifications to evidence notes.
Family structure and social relationships should be separate views when requested.

Mermaid is suitable when the client renders it legibly with the chosen styling.
If it does not, provide a locally rendered Scalable Vector Graphics (SVG) file or
another suitable local format with an explicit background and colors. Keep the
editable source when exporting. Never send book content to a hosted rendering
service. If no rendering or preview capability is available, disclose that the
visual result could not be verified and provide the evidence table regardless.

## Reading endpoint and story time

Every diagram must state its permitted reading endpoint and snapshot meaning:

- **Known through the reading endpoint** is the default. Include supported facts
  disclosed within that scope. A narrator's forward-looking aside is already
  heard material, but its later outcome must be labeled separately from current
  scene status. Do not silently discard it or treat it as an event already
  completed in that scene.
- **Status at a story moment** applies when the user requests that snapshot.
  Determine status as of that moment, using only permitted evidence. Keep later
  outcomes out of the scene-state labels, even when already disclosed by the
  narrator. State the scene-based interpretation; include a separate note about
  a later outcome only if relevant to the user's request and within reading scope.

Clarify an ambiguous request when those interpretations would materially change
the diagram. The question's endpoint must not exceed saved listening progress,
and the usual extraction buffer still applies. Story chronology never authorizes
reading ahead: an old friendship revealed in an unread chapter remains unavailable.

"Alive in the latest available scene," "last reported away," and "current status
not established" are different claims. Do not infer that an offstage character
is alive from the absence of a reported death. A death and its cause need separate
support; a reported diagnosis or suspected cause must retain its attribution.

## Evidence before layout

Read the complete relevant permitted sections when synthesizing across chapters.
Build a small evidence table for the requested people before drawing. Each
substantive node label, relationship edge, and status annotation needs a supporting
claim record. The record should include:

- A stable claim identifier for diagram references.
- The people involved and the narrow relationship, event, or status established.
- Attribution and uncertainty: narrated fact, named speaker's claim, or an
  explicitly unspecified connection. Avoid numerical confidence unsupported by
  the transcription process.
- The supporting transcript reference, absolute audio interval, and an approximate
  replay anchor using track title, occurrence or index, and time within the track.
- Story timing when established, including whether a claim is a narrator's
  disclosure of a later outcome.

Do not infer connecting ancestors, parent-side placement, marriage, romance,
birth order, or legal ownership from an ambiguous association. Uncertain spellings
and aliases must remain uncertain; do not merge people solely because their names
sound similar. Group nodes only when doing so preserves the relevant distinctions.
Separate an event from a character's interpretation, hope, or accusation about it.

The rendered diagram and evidence table must agree. An uncluttered presentation
does not justify dropping a qualification that changes a claim's meaning. Put
short claim identifiers in the diagram where useful and detailed explanations
in the accompanying table. Neither the table nor a diagram becomes primary
evidence for future factual answers.

## Private snapshots and continuity

Inline diagrams and evidence tables are part of the final answer and follow the
normal journal policy. Exported book artifacts belong under a unique run directory
in the ignored `companion/visualizations/`; public `assets/` is for generic project
art only. Preserve exports during `make clean`.

For an export, save editable source, the diagram, and evidence notes together.
Include a separate `metadata.json` containing no book prose or chapter titles:
source identity (resolved audio path, size, modification time), numeric query and
consulted-audio intervals, snapshot mode, selected theme, and evidence mode
(`local-only` or `external`). For a scene snapshot, keep its human-readable
description inside the scoped evidence notes. Record the associated journal entry
identifier when a local-only answer is successfully journaled.

Before opening a saved artifact's prose, validate its metadata against the current
audio, listening limit, and question endpoint. All consulted intervals must fit,
not just the depicted chapter. Check the linked journal through its metadata-gated
helper when available. Missing or inconsistent metadata makes the artifact
ineligible for reuse. External-source artifacts must not enter a local-only task.
These artifact checks are agent instructions; there is no dedicated validation
helper or automatic spoiler detector for visual files.

Keep snapshots separate as progress advances. A theme or layout revision may
reuse the same eligible evidence table without retranscription when no factual
scope changes. New facts or a broader endpoint require establishing the relevant
transcript evidence under the normal transcription policy. Facts must not migrate
from a later snapshot into an earlier one.

Labels, legends, tooltips, accessibility descriptions, and embedded source comments
must obey the same scope as visible nodes. Hiding a later fact visually does not
remove it from the artifact. Do not add book-specific examples to public docs or
automatically loaded agent memory.

## Review

Use synthetic examples to check instruction changes: a user-selected dark theme,
an unanswered theme question, an offstage relative with unknown status, an
attributed parentage claim, and a narrator's later-outcome aside. Confirm that
snapshot meaning, qualification, evidence references, and theme choice remain
consistent. Actual visual inspection is still required for each rendered output;
unit tests cannot prove readability or factual fidelity.
