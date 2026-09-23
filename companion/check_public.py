"""Check Git's tracked and addable files against the reviewed public inventory."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

# This project is small and holds purchased media alongside source. Require an
# explicit review when adding public files; ignored local data never belongs here.
PUBLIC_FILES = set("""
.gitignore
.github/workflows/check.yml
AGENTS.md
CLAUDE.md
CONTRIBUTING.md
LICENSE
Makefile
README.md
assets/heard-so-far.svg
spec/README.md
spec/external-sources.md
spec/visualizations.md
companion/LOCAL_ONLY.md
companion/README.md
companion/check_public.py
companion/download_model.py
companion/journal.py
companion/local-only.config.toml
companion/locking.py
companion/position.py
companion/requirements.txt
companion/tasks.py
companion/test_journal.py
companion/test_position.py
companion/test_public.py
companion/test_tasks.py
companion/test_transcript_io.py
companion/transcribe_section.py
companion/transcript_io.py
""".split())


def check_paths(paths, root=ROOT):
    problems = []
    for name in sorted(set(paths)):
        if name not in PUBLIC_FILES:
            problems.append(f"Unreviewed public path: {name}")
            continue
        path = root / name
        if path.is_symlink():
            problems.append(f"Public files must not be symlinks: {name}")
        elif path.exists() and path.stat().st_size > 1_000_000:
            problems.append(f"Unexpectedly large public file: {name}")
    return problems


def main():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    )
    paths = result.stdout.decode().split("\0")
    paths = [path for path in paths if path]
    problems = check_paths(paths)
    if problems:
        raise SystemExit("\n".join(problems) + "\nReview these files before staging; do not automatically expand the allowlist.")
    print(f"Public inventory OK: {len(set(paths))} tracked/addable files. Review contents separately before committing.")


if __name__ == "__main__":
    main()
