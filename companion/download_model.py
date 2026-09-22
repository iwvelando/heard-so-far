"""Explicit one-time network setup, separate from offline reading commands."""
import os
from pathlib import Path

from locking import exclusive

ROOT = Path(__file__).resolve().parents[1]
os.environ["HF_HOME"] = str(ROOT / ".cache/huggingface")
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def main():
    if os.environ.get("HF_HUB_OFFLINE") == "1":
        raise SystemExit("Model download is a network setup step; HF_HUB_OFFLINE=1 is set.")
    from huggingface_hub import snapshot_download
    path = snapshot_download("mlx-community/whisper-large-v3-turbo")
    print(f"Model cached at {path}")


if __name__ == "__main__":
    with exclusive():
        main()
