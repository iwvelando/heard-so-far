"""Prevent cleanup from removing files during transcription or model setup."""
from contextlib import contextmanager
import fcntl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def exclusive():
    with (ROOT / ".companion.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another transcription, download, or cleanup is active; retry after it finishes.")
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
