# Contributing to heard-so-far

The shared reading protocol lives in AGENTS.md; CLAUDE.md imports it. Keep
instructions independent of any particular book, reader, or machine.

## Development checks

The boundary, journal, and cleanup tests use only Python's standard library and
synthetic data. On macOS or Linux, run them without installing MLX or any model:

```sh
make check PYTHON=python3
```

For actual transcription, follow README.md's Apple silicon setup. GitHub CI runs
the standard-library checks; it does not exercise Metal, model installation,
recognition quality, or an agent's compliance with the reading protocol.

Add regression tests when changing progress limits, extraction coverage, journal
eligibility, or cleanup. Use invented short passages and synthetic timestamps.
Never include purchased audio, transcripts, journal answers, publisher metadata,
personal paths, credentials, or private agent settings in tests, issues, or PRs.
Describe recognition problems with a synthetic example where possible.

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
