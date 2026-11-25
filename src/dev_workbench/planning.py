"""Read-only validation for workspace-local planning files."""

import re
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import TypedDict
from urllib.parse import unquote

from yaml import YAMLError, safe_load  # type: ignore[import-untyped]

TASK_FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}-")
INDEX_HEADER = ("Notes", "Tracked in", "Status")
ISSUE_REFERENCE = re.compile(r"[^\s#]+#\d+(?:\s.*)?$")


class Diagnostic(TypedDict):
    code: str
    path: str
    message: str


class PlanningReport(TypedDict):
    index_present: bool
    roadmap_present: bool
    diagnostics: list[Diagnostic]


def add_diagnostic(diagnostics: list[Diagnostic], code: str, path: str, message: str) -> None:
    diagnostics.append({"code": code, "path": path, "message": message})


def local_target(tasks: Path, reference: str) -> Path | None:
    path = Path(reference)
    if not reference or path.is_absolute() or ".." in path.parts:
        return None
    target = tasks / path
    return target if target.resolve().is_relative_to(tasks) else None


def task_folder(reference: Path) -> Path | None:
    """Return the task directory portion of a path relative to tasks/."""
    parts = reference.parts
    offset = 1 if parts and parts[0] == ".finished" else 0
    if len(parts) > offset and TASK_FOLDER.match(parts[offset]):
        return Path(*parts[:offset + 1])
    return None


def index_paths(index: Path, tasks: Path, diagnostics: list[Diagnostic]) -> set[Path]:
    indexed: set[Path] = set()
    in_table = False
    found_table = False
    for number, line in enumerate(index.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line.startswith("|"):
            in_table = False
            continue
        cells = line.split("|")
        if tuple(cell.strip() for cell in cells[1:4]) == INDEX_HEADER:
            found_table = in_table = True
            continue
        if not in_table:
            continue
        notes = cells[1].strip()
        code = re.fullmatch(r"`([^`]+)`", notes)
        link = re.fullmatch(r"\[[^\]]*\]\(([^)]*)\)", notes)
        if code:
            reference = code[1]
        elif link:
            reference = unquote(link[1].split("#", 1)[0])
        else:
            continue
        target = local_target(tasks, reference)
        location = f"tasks/INDEX.md:{number}"
        if target is None:
            add_diagnostic(diagnostics, "invalid-index-path", location, f"Expected a local notes path: {reference}")
            continue
        if not target.exists():
            add_diagnostic(diagnostics, "missing-index-path", location, f"Notes path is missing: {reference}")
            continue
        folder = task_folder(target.relative_to(tasks))
        if folder is not None:
            indexed.add(folder)
    if not found_table:
        add_diagnostic(diagnostics, "missing-index-table", "tasks/INDEX.md",
                       "Expected an index table with Notes, Tracked in, and Status columns.")
    return indexed


def string_list(node, field: str, location: str, diagnostics: list[Diagnostic]) -> list[str]:
    values = node.get(field, [])
    if isinstance(values, list) and all(isinstance(value, str) and value for value in values):
        return values
    add_diagnostic(diagnostics, "invalid-roadmap-field", location, f"{field} must be a list of strings.")
    return []


def check_roadmap(roadmap: Path, tasks: Path, indexed: set[Path], diagnostics: list[Diagnostic]) -> None:
    path = "tasks/roadmap.yaml"
    try:
        graph = safe_load(roadmap.read_text(encoding="utf-8"))
    except YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        if mark is not None:
            path += f":{mark.line + 1}"
        add_diagnostic(diagnostics, "invalid-roadmap-yaml", path, "Could not parse the roadmap YAML.")
        return
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    if not isinstance(nodes, dict):
        add_diagnostic(diagnostics, "invalid-roadmap", path, "Expected a roadmap with a nodes mapping.")
        return
    sorter: TopologicalSorter[str] = TopologicalSorter()
    for name, node in nodes.items():
        if not isinstance(name, str) or not isinstance(node, dict):
            add_diagnostic(diagnostics, "invalid-roadmap-node", path, "Expected named roadmap node mappings.")
            continue
        location = f"{path} ({name})"
        sorter.add(name)
        for field in ("depends_on", "soft_depends_on"):
            for dependency in string_list(node, field, location, diagnostics):
                if dependency not in nodes:
                    add_diagnostic(diagnostics, "unknown-dependency", location, f"Unknown dependency: {dependency}")
                else:
                    sorter.add(name, dependency)
        for source in string_list(node, "sources", location, diagnostics):
            if source.startswith(("https://", "http://")) or ISSUE_REFERENCE.fullmatch(source):
                continue
            target = local_target(tasks, source)
            if target is None or not target.exists():
                workspace_target = local_target(tasks.parent, source)
                if workspace_target is None or not workspace_target.exists():
                    add_diagnostic(diagnostics, "missing-roadmap-source", location,
                                   f"Local source path is missing or invalid: {source}")
                    continue
                target = workspace_target
            folder = task_folder(target.relative_to(tasks)) if target.is_relative_to(tasks) else None
            if folder is not None and folder not in indexed:
                add_diagnostic(diagnostics, "unindexed-roadmap-source", location, f"Source task is not indexed: {source}")
    try:
        sorter.prepare()
    except CycleError as error:
        cycle = " -> ".join(error.args[1])
        add_diagnostic(diagnostics, "dependency-cycle", path, f"Dependency cycle: {cycle}")


def check_planning(root: Path) -> PlanningReport:
    tasks = root / "tasks"
    diagnostics: list[Diagnostic] = []
    index = tasks / "INDEX.md"
    roadmap = tasks / "roadmap.yaml"
    report: PlanningReport = {"index_present": False, "roadmap_present": False, "diagnostics": diagnostics}
    if tasks.is_symlink() or not tasks.resolve().is_relative_to(root):
        add_diagnostic(diagnostics, "invalid-task-directory", "tasks", "Expected a workspace-local tasks directory.")
        return report
    for file in (index, roadmap):
        if file.is_symlink() or (file.exists() and not file.is_file()):
            add_diagnostic(diagnostics, "invalid-planning-file", str(file.relative_to(root)), "Expected a regular local file.")
    report["index_present"] = index.is_file() and not index.is_symlink()
    report["roadmap_present"] = roadmap.is_file() and not roadmap.is_symlink()
    indexed = index_paths(index, tasks, diagnostics) if report["index_present"] else set()
    for parent in (tasks, tasks / ".finished"):
        if parent.is_symlink() or not parent.is_dir():
            continue
        for child in sorted(parent.iterdir()):
            folder = child.relative_to(tasks)
            if child.is_symlink() or not child.is_dir() or task_folder(folder) is None or folder in indexed:
                continue
            add_diagnostic(diagnostics, "unindexed-task", f"tasks/{folder}", "Task directory has no index entry.")
    if report["roadmap_present"]:
        check_roadmap(roadmap, tasks, indexed, diagnostics)
    return report
