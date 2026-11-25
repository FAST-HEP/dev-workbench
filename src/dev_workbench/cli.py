"""Dev Workbench command line."""

import argparse
import json
import sys
from pathlib import Path

import tomlkit

from .providers import discover
from .workspace import (
    checkout,
    checkout_path,
    find_manifest,
    identity,
    overlaps,
    save_manifest,
    status,
    validate_inventory,
    validate_url,
)


def review(path, document, original, args):
    sources = [source for source in document.get("sources", [])
               if source.get("name", source["namespace"]) == args.source]
    if len(sources) != 1:
        raise ValueError("Select exactly one configured source by name or namespace.")
    source = sources[0]
    if source.get("clone_protocol", "ssh") not in ("ssh", "https"):
        raise ValueError("clone_protocol must be ssh or https.")
    try:
        discovered = discover(source, args)
    except Exception as error:
        raise ValueError(f"Discovery failed ({type(error).__name__}). No repositories were imported.") from None
    repositories = document.setdefault("repositories", tomlkit.aot())
    known = {identity(repo["url"]): repo for repo in repositories}
    paths = validate_inventory(path.parent, repositories)
    seen = {identity(url) for _, url in discovered}
    additions = []
    for name, url in sorted(discovered):
        validate_url(url)
        if identity(url) in known:
            continue
        target = checkout_path(path.parent, name).resolve()
        if overlaps(target, paths):
            print(f"Conflict: {name} ({url})")
            continue
        candidate = {"path": name, "url": url, "source": args.source}
        if status(path.parent, candidate)["state"] not in {"missing", "present"}:
            print(f"Conflict: {name} ({url})")
            continue
        additions.append(candidate)
        paths.add(target)
        known[identity(url)] = candidate
    for repo in repositories:
        if repo.get("source") == args.source and identity(repo["url"]) not in seen:
            print(f"Missing from discovery: {repo['path']}")
    for candidate in additions:
        print(f"Add: {candidate['path']} ({candidate['url']})")
    if not additions:
        return 0
    if not sys.stdin.isatty():
        raise ValueError("Import confirmation requires a terminal.")
    accepted = []
    if args.all:
        location = source.get("host", f"{source['provider']}.com")
        if input(f"Add all {len(additions)} repositories from {location}/{source['namespace']} "
                 f"to {path.name}? Checkouts happen separately. [y/N] ").strip().lower() == "y":
            accepted = additions
    else:
        for candidate in additions:
            while True:
                answer = input(f"Import {candidate['path']}? [y/N/s] ").strip().lower() or "n"
                if answer in {"y", "n", "s"}:
                    break
            if answer == "s":
                break
            if answer == "y":
                accepted.append(candidate)
    if accepted:
        for candidate in accepted:
            repositories.append(candidate)
        save_manifest(path, document, original)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="dev-workbench", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "checkout"):
        commands.add_parser(command).add_argument("--json", action="store_true")
    discovery = commands.add_parser("discover")
    discovery.add_argument("source")
    discovery.add_argument("--all", action="store_true")
    auth = discovery.add_mutually_exclusive_group()
    auth.add_argument("--token-file", type=Path)
    auth.add_argument("--auth", choices=("cli", "prompt"))
    args = parser.parse_args(argv)
    try:
        path = find_manifest(Path.cwd())
        original = path.read_text(encoding="utf-8")
        document = tomlkit.parse(original)
        if args.command == "discover":
            return review(path, document, original, args)
        action = status if args.command == "status" else checkout
        repositories = document.get("repositories", [])
        validate_inventory(path.parent, repositories)
        reports = [action(path.parent, repository) for repository in repositories]
        if args.json:
            print(json.dumps(reports, indent=2))
        else:
            for report in reports:
                print(f"{report['path']}: {report['state']}")
        allowed = {"present", "missing"} if action is status else {"present"}
        return int(any(report["state"] not in allowed for report in reports))
    except (ValueError, OSError, KeyError, EOFError) as error:
        print(f"dev-workbench: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
