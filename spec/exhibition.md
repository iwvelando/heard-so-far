# Curated exhibition exports

An exhibition export is an explicitly selected public collection, prepared from
private local evidence. It is not a journal export. The consumer may be a public
website and repository from its first release. The helper stages the selected
catalog and images locally; it never publishes, pushes, or modifies the consumer.

The conversational workflow is: ask the agent to add selected artworks, review the
new captions and attribution, and preview the updated collection. The reusable
[export skill](../skills/export-exhibition/SKILL.md) coordinates those steps. Direct
helper commands are an alternative.

## Private selection, version 1

Selections and staged exports live under the ignored
`companion/visualizations/exhibition/`. A selection has exactly these top-level
fields: `version: 1`, `source` (resolved audio `path`, `size`, `mtime_ns`),
`scope_end` (absolute buffered audio seconds), `title`, `author`, and `works`.
Validate source and numeric scope before using a stored selection as a locator.
The source identity is a local file fingerprint, not a content hash.

Each work contains:

- `public`: the explicitly reviewed visitor-facing fields below.
- `reviewed`: the boolean `true` after content and image review.
- `evidence`: a list of objects with `manifest`, `start`, and `end`. The times are
  absolute audio seconds. An exhibition reconstruction needs at least one passage.
  A personal artwork described only as visible interpretation can have an empty
  list; factual scene claims still require evidence through the agent workflow.
- `asset_source`: a local PNG path for an image work. It is omitted for a supported
  procedural object. An object may instead include `reference_asset_source`, an
  explicitly reviewed PNG for its inspection panel; it never replaces the model.
- Alternatively, `panel_assets`: an ordered list of 2–24 objects, each with exactly
  `title`, `alt`, and `asset_source`. These form one montage with one stable work
  ID and one placement. Review every image and caption; list order is presentation
  order. It cannot be combined with `object` or another asset source. Export emits
  public `panels` with `title`, `alt`, and a hashed `image` path; the work's `image`
  repeats the first panel's path as its collection cover. Original pixels remain
  separate, and every panel receives the usual metadata and privacy validation.
- Optional `private_note`: review rationale, unresolved details, or provenance
  that must not enter the public catalog.

The required public fields are `id`, `title`, `collection`, `medium`, `description`,
`attribution`, `credit`, `note`, and `alt`, all nonempty strings. `id` is a stable,
unique lowercase hyphenated slug. `collection` is `exhibition` or `interpretation`.
The optional `object` field accepts the procedural display identifiers listed in
`companion/exhibition.py` (`OBJECTS`). The consumer must support each identifier.
These include vessels, cases, figures, reliefs and installation studies. It is an asset capability, not a claim about the
current book. Image works receive a generated `image` field during export. Objects with a
reference receive `referenceImage`; an object cannot also supply `asset_source`.
References use the same metadata, checksum, source-review, and privacy checks as
artworks. The public `alt` describes the reference when present.

Image works may specify `frame`: `gallery` (default), `none`, `walnut`, `aluminum`,
or `fence-slats`. Use `none` when framing is already present in the pixels; explain
interpretive display choices in the note. Objects cannot specify a frame.

Wall inscriptions may supply `wallText`, containing 1–200 nonblank public
characters, with `frame: none` and `asset_source`. The exported `image` is an
inspection reference; the gallery renders the reviewed wording directly on a
wall. This cannot be combined with an object, montage or object reference.
Review the wording against its passage separately from the image, whose imagined
architecture is not a claim about the exhibition. Typeface and wrapping are
display interpretations.

An optional `placement` object has exactly `room` (stable lowercase slug), `label`
(visitor-facing grouping), and `note` (basis or limitation), all nonempty strings.
It requires passage evidence even for a personal interpretation. Room placement
is distinct from the chapter in which a scene is disclosed. Retrospectives and
composites may use a separate interpretation grouping until their story chronology
is verified; never infer an unread room from a sequence of dates. Physical slots
in the consumer remain independent of catalog order.

There are no public fields for questions, answers, transcripts, prompts, source
paths, listening positions, or generation conversations. An interpretive note is
curated prose, not an automatic excerpt of those sources. Do not silently rewrite
the user's feelings or claim agent-written text was supplied by the user.

## Validation and output

`companion/exhibition.py check --input PATH` validates without writing output.
`companion/exhibition.py export --input PATH --output NEW_DIRECTORY` stages an
immutable bundle. Run both with `.venv/bin/python` from the project root.

The helper validates saved progress against the audio, selection source identity,
numeric scope, each consulted manifest's fingerprint and complete chunk coverage,
and each passage interval. The complete consulted extraction must fit the scope.
This does not prove recognition accuracy or that a person reviewed the passage.
Quality flags, overlaps, and attribution remain agent review requirements.

Public keys are allowlisted; unexpected fields fail rather than being copied.
Only explicitly named PNG assets are accepted. Embedded text and Exchangeable
Image File Format (EXIF) metadata, truncated chunks, or trailing bytes cause a
refusal. Originals remain untouched. Output names combine the work ID and a hash,
so local source filenames and paths do not leak through asset names. Existing
output directories are never overwritten. Failed validation produces no bundle;
successful output is installed as one directory after preparation.

The public bundle contains only `catalog.json` (`version`, `title`, `author`,
`works`) and `assets/`. Source fingerprints, scope, manifest paths, private notes,
and review flags stay in the private selection. Inspect the final bundle before
copying it to a public repository. The allowlist cannot detect private prose placed
inside an allowed caption, infer a spoiler from a picture, or establish rights to
publish it. Review remains necessary.

The public site may assume visitors have finished the book and require explicit
spoiler acceptance in a foyer. The creator's unfinished reading still constrains
agent evidence and newly prepared work. No arbitrary visitor progress controls are
required. Public assets and source remain directly accessible outside the foyer.

Test source changes, rewound progress, missing chunks, unsupported fields, metadata
inside images, evidence beyond the endpoint, duplicate IDs, and preserved exports
with synthetic inputs. Never put book-specific selection records in tracked tests.

Panel groups may set `presentation: variants` for alternate realizations of one
work. The default (or `sequence`) is an ordered montage. Variants must be labeled
as alternatives throughout the consumer, without implying an original series.
Object studies must disclose simplification; still references and silent audio
stations must not be described as completed films or recordings.
