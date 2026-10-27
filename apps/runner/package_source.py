"""Create a minimal Ubuntu source bundle; never install or execute the runner."""

from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parents[2]
RUNNER_FILES = (
    "README.md", "pyproject.toml", "uv.lock", "requirements.lock",
    "install-dedicated-ubuntu.sh", "fieldnote-runner.service",
    "Dockerfile.python", "Dockerfile.cpp", "Dockerfile.cpp-runtime",
    "acceptance_dedicated.py", "runner_service/__init__.py",
    "runner_service/main.py",
)


def package(destination: Path) -> int:
    paths = [ROOT / "apps/runner" / name for name in RUNNER_FILES]
    for folder in ("coding", "coding-private"):
        paths.extend(sorted((ROOT / "content" / folder).glob("*.json")))
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise ValueError("Bundle sources must be existing regular files, not symlinks")
    if any(parent.is_symlink() for path in paths for parent in path.parents if parent != ROOT.parent):
        raise ValueError("Bundle source directories must not be symlinks")
    # Exclusive creation prevents replacing an existing archive or following a
    # destination symlink. Add individual files only, never directory recursion.
    with destination.open("xb") as output:
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for path in paths:
                archive.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
    return len(paths)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    count = package(args.destination)
    print(f"Created {args.destination}: {count} allowlisted source/content files; no runner execution.")
