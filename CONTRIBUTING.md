# Contributing to heard-so-far

The shared reading protocol lives in AGENTS.md; CLAUDE.md imports it. Keep
instructions independent of any particular book, reader, or machine.

Read [spec/README.md](spec/README.md) before changing behavior. It defines the
contracts for listening boundaries, evidence, journaling, and private data.
[The external-source policy](spec/external-sources.md) defines the explicit opt-in
and separation from local-only reading. Update the relevant contracts, agent
instructions, and regression tests together when behavior changes.
[The visualization contract](spec/visualizations.md) covers theme choice,
evidence, snapshot semantics, and review of diagrams.

Keep README.md focused on end-user instructions and expectations. Put operational
agent steps in AGENTS.md, contractual behavior in spec/, and code navigation in
companion/README.md. Describe the supported product without development history.
Expand acronyms on first use in each document.

## Development checks

The boundary, journal, and cleanup tests use only Python's standard library and
synthetic data. On macOS or Linux, run them without installing MLX or any model.
`make check` also checks formatting and lint rules with ruff, installed from the
hashed `companion/requirements-dev.txt`:

```sh
make setup-dev
make check
```

`make format` applies ruff's formatting and safe fixes. The ruff configuration is
in `ruff.toml`, so results don't depend on any user-level ruff settings.

For actual transcription, follow README.md's Apple silicon setup. GitHub
continuous integration (CI) runs
these checks and `make lock-check`; it does not exercise Metal, model installation,
recognition quality, or an agent's compliance with the reading protocol.

Add regression tests when changing progress limits, extraction coverage, journal
eligibility, or cleanup. Use invented short passages and synthetic timestamps.
Never include purchased audio, transcripts, journal answers, publisher metadata,
personal paths, credentials, or private agent settings in tests, issues, or pull requests.
Describe recognition problems with a synthetic example where possible. The
issue forms ask you to confirm this; report vulnerabilities privately as
described in [SECURITY.md](SECURITY.md).

## Pull requests and dependency updates

Changes reach `main` only through pull requests that pass both `Check` jobs, and
they are squash-merged. The pull request title and body become the commit message.

Dependabot proposes GitHub Actions and Python updates weekly. Actions updates
that change no major version merge automatically after `Check` passes. Majors
need a review, then a manual merge, by a person or by an agent once `Check` has
passed. Python updates are always merged by hand, because CI cannot run
mlx-whisper: on Apple silicon, run `make setup`, `make doctor`, and a short
transcription before merging.

## Dependencies

Direct dependencies are listed in `companion/requirements.in` (runtime) and
`companion/requirements-dev.in` (development tools). `make lock` compiles them
into hashed lockfiles, and `make setup` and `make setup-dev` install only what
those lockfiles pin. The runtime lock targets Apple silicon on macOS 14 or newer.
Commit a lockfile together with its `.in` file; CI runs `make lock-check` to
confirm they match. `make lock` keeps existing pins, so it changes only what an
edited `.in` file requires.

## Before a commit

`make check-public` checks Git's tracked and addable paths against a small reviewed
inventory in `companion/check_public.py`. Add a new path there only after reviewing
its purpose and contents. This catches accidental private files, including files
already tracked despite ignore rules; it is not a secret or copyright scanner.

Review `git status --short --untracked-files=all` and the proposed contents before
staging. Review `git diff --cached` before committing. Use explicit source paths
when staging; never force-add ignored files. Machine-specific excludes under
`.git/info/exclude` are local and are not distributed with a clone.

Contributions to the project code and documentation are under the MIT license
in LICENSE. Audiobooks, dependencies, and separately downloaded models retain
their own licenses and rights.
