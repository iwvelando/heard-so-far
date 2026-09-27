"""The speech model and the reviewed revision of its weights."""

MODEL = "mlx-community/whisper-large-v3-turbo"
REVISION = "a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb"


def snapshot_dir(root):
    return root / ".cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots" / REVISION


def local_path():
    """Return the cached pinned snapshot; callers decide whether the hub is offline."""
    from huggingface_hub import snapshot_download

    try:
        return snapshot_download(MODEL, revision=REVISION)
    except OSError as error:
        raise SystemExit(
            f"Pinned speech model {MODEL}@{REVISION[:12]} is unavailable ({error}). "
            "Run make download-model during setup."
        ) from error
