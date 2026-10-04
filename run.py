"""Create a local environment and run the app with one command (standard library only)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
SUPPORTED = {(3, 11), (3, 12)}

# Executed by the project environment, not the Python used to start this launcher.
DEPENDENCY_CHECK = r"""
import importlib.metadata as metadata
from pathlib import Path
import re
import sys
if sys.version_info[:2] not in {(3, 11), (3, 12)}:
    sys.exit(2)
for line in Path('requirements.txt').read_text().splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    name, version = line.split('==', 1)
    name = re.sub(r'\[.*\]', '', name)
    try:
        if metadata.version(name) != version:
            sys.exit(1)
    except metadata.PackageNotFoundError:
        sys.exit(1)
"""


def environment_python(root: Path) -> Path:
    folder = root / ".venv"
    return folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def prepare(root: Path) -> Path:
    folder = root / ".venv"
    python = environment_python(root)
    if not folder.exists():
        print("Creating the project's Python environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(folder)
    if not python.is_file():
        raise RuntimeError(
            "The existing .venv is incomplete. Rename it, then run this command again. "
            "Your data and .env settings will stay in the project folder."
        )
    probe = subprocess.run([str(python), "-c", DEPENDENCY_CHECK], cwd=root)
    if probe.returncode == 2:
        raise RuntimeError(
            "The existing .venv uses an unsupported Python. Recreate it with Python 3.11 or 3.12."
        )
    if probe.returncode not in {0, 1}:
        raise RuntimeError(
            "The project environment could not be checked. Recreate .venv and try again."
        )
    if probe.returncode == 1:
        print(
            "Installing the pinned dependencies. The first setup needs internet access...",
            flush=True,
        )
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                "requirements.txt",
            ],
            cwd=root,
            check=True,
        )
    # Exclusive creation preserves all existing user settings and API keys.
    try:
        fd = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "wb") as target:
            target.write((root / ".env.example").read_bytes())
        print(
            "Created .env with free defaults. Paid API usage is disabled.", flush=True
        )
    return python


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--setup-only",
        action="store_true",
        help="Install dependencies without launching the app.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Check the local Ollama service and model without generating text.",
    )
    mode.add_argument(
        "--smoke-test",
        action="store_true",
        help="Generate a tiny synthetic response using local Ollama only.",
    )
    args = parser.parse_args(argv)
    if sys.version_info[:2] not in SUPPORTED:
        print(
            "Use Python 3.11 or 3.12. On Windows, try: py -3.12 run.py", file=sys.stderr
        )
        return 2
    try:
        python = prepare(ROOT)
        if args.setup_only:
            print("Setup complete. Run python run.py to start the app.")
            return 0
        command = (
            [str(python), "local_ai_check.py"]
            if args.check or args.smoke_test
            else [str(python), "app.py"]
        )
        if args.smoke_test:
            command.append("--generate")
        return subprocess.run(command, cwd=ROOT).returncode
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(
            f"Setup failed: {exc}\nNo app data was removed. Fix the reported problem and rerun python run.py.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
