"""Small Makefile helpers. Arguments travel through env, not shell interpolation."""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from locking import exclusive

ROOT = Path(__file__).resolve().parents[1]


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing {name}. See make help or README.md.")
    return value


def clean(folder):
    # Only constant, explicit derived-data roots are accepted by callers.
    if folder.is_symlink() or folder.resolve() != folder.absolute():
        raise SystemExit(f"Refusing to clean a symlinked path: {folder}")
    if folder.exists():
        shutil.rmtree(folder)
    print(f"Cleared {folder.relative_to(ROOT)} (generated files only)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["progress", "transcribe", "doctor", "clean-transcripts", "clean-audio", "clean-cache"])
    args = parser.parse_args()
    if args.command == "progress":
        cmd = [sys.executable, str(ROOT / "companion/position.py"), "set",
               "--title", required("TITLE"), "--elapsed", required("ELAPSED"), "--remaining", required("REMAINING")]
        for env_name, flag in [("TRACK", "--track"), ("AUDIO", "--audio"), ("SPEECH_LANGUAGE", "--language")]:
            if os.environ.get(env_name):
                cmd += [flag, os.environ[env_name]]
        subprocess.run(cmd, cwd=ROOT, check=True)
    elif args.command == "transcribe":
        cmd = [sys.executable, str(ROOT / "companion/transcribe_section.py"),
               "--first-track", required("FIRST"), "--last-track", required("LAST")]
        if os.environ.get("THROUGH"):
            cmd += ["--through", os.environ["THROUGH"]]
        subprocess.run(cmd, cwd=ROOT, check=True)
    elif args.command == "doctor":
        print(f"Platform: {platform.system()} {platform.machine()}; Python: {platform.python_version()}")
        print(f"Interpreter: {sys.executable}")
        for tool in ["ffmpeg", "ffprobe", "uv", "git"]:
            print(f"{tool}: {shutil.which(tool) or 'not found'}")
        print(f"Progress saved: {(ROOT / 'companion/progress.json').exists()}")
        model = ROOT / ".cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots"
        print(f"Model snapshot directory present: {model.exists()} (not an integrity check)")
    else:
        folders = {"clean-transcripts": ROOT / "companion/transcripts",
                   "clean-audio": ROOT / "companion/audio", "clean-cache": ROOT / ".cache"}
        with exclusive():
            clean(folders[args.command])


if __name__ == "__main__":
    main()
