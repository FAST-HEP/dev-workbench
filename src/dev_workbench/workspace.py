"""Manifest and local Git operations."""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import tomlkit

MANIFEST = ".dev-workbench.toml"


def find_manifest(start):
    for directory in (start, *start.parents):
        candidate = directory / MANIFEST
        if candidate.is_file():
            return candidate
    raise ValueError(f"No {MANIFEST} found above {start}")


def identity(url):
    if "://" in url:
        parsed = urlsplit(url)
        if parsed.hostname:
            return parsed.hostname.lower(), parsed.path.strip("/").removesuffix(".git")
    match = re.fullmatch(r"(?:[^@/:]+@)?([^/:]+):(.+)", url)
    if match:
        return match[1].lower(), match[2].strip("/").removesuffix(".git")
    return str(Path(url).resolve())


def checkout_path(root, path):
    relative = Path(path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"Expected a workspace-relative checkout path: {path}")
    destination = root / relative
    if destination.resolve() == root or not destination.resolve().is_relative_to(root):
        raise ValueError(f"Checkout path escapes the workspace: {path}")
    return destination


def overlaps(path, paths):
    return any(path == other or path in other.parents or other in path.parents for other in paths)


def validate_inventory(root, repositories):
    paths: set[Path] = set()
    for repository in repositories:
        path = checkout_path(root, repository["path"]).resolve()
        if overlaps(path, paths):
            raise ValueError(f"Overlapping repository paths: {repository['path']}")
        validate_url(repository["url"])
        paths.add(path)
    return paths


def validate_url(url):
    if not url:
        raise ValueError("Repository URL is empty.")
    if "://" in url:
        remote = urlsplit(url)
        if remote.password is not None or (
            remote.scheme in {"http", "https"} and (remote.username is not None or remote.query)
        ):
            raise ValueError("Use a repository URL without embedded credentials.")

def git(*args):
    return subprocess.run(["git", *map(str, args)], capture_output=True, text=True)


def status(root, repository):
    path = repository["path"]
    url = repository["url"]
    destination = checkout_path(root, path)
    report = {"path": path, "url": url, "state": "missing"}
    if not destination.exists() and not destination.is_symlink():
        return report
    top = git("-C", destination, "rev-parse", "--show-toplevel")
    if top.returncode or Path(top.stdout.strip()).resolve() != destination.resolve():
        return dict(report, state="occupied")
    remote = git("-C", destination, "remote", "get-url", "origin")
    if remote.returncode or identity(remote.stdout.strip()) != identity(url):
        return dict(report, state="remote-mismatch")
    changes = git("-C", destination, "status", "--porcelain")
    if changes.returncode:
        return dict(report, state="git-error")
    return dict(report, state="present", dirty=bool(changes.stdout))


def checkout(root, repository):
    report = status(root, repository)
    if report["state"] != "missing":
        return report
    destination = checkout_path(root, repository["path"])
    result = git("clone", "--", repository["url"], destination)
    if result.returncode:
        return dict(report, state="clone-failed")
    return status(root, repository)


def save_manifest(path, document, original):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(tomlkit.dumps(document))
            stream.close()
            if path.read_text(encoding="utf-8") != original:
                raise ValueError("Manifest changed during review. Run discovery again.")
            temporary.chmod(path.stat().st_mode & 0o777)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
