import json

from dev_workbench.cli import main


def test_planning_check_supports_both_index_forms(tmp_path, monkeypatch, capsys):
    (tmp_path / ".dev-workbench.toml").touch()
    tasks = tmp_path / "tasks"
    first = tasks / "2026-11-25-first"
    second = tasks / ".finished/2026-11-25-second"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (second / "notes.md").touch()
    index = tasks / "INDEX.md"
    index.write_text(
        "| Notes | Tracked in | Status |\n"
        "| --- | --- | --- |\n"
        "| `2026-11-25-first` | | draft |\n"
        "| [Second](.finished/2026-11-25-second/notes.md) | | done |\n"
        "| No local notes | | done |\n\n"
        "| Repository | Notes |\n"
        "| --- | --- |\n"
        "| repo | ignored |\n"
    )
    monkeypatch.chdir(first)
    assert main(["planning", "check", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "index_present": True,
        "roadmap_present": False,
        "diagnostics": [],
    }


def test_planning_check_reports_local_defects(tmp_path, monkeypatch, capsys):
    (tmp_path / ".dev-workbench.toml").touch()
    tasks = tmp_path / "tasks"
    (tmp_path / "notes.md").touch()
    (tasks / "2026-11-25-unindexed").mkdir(parents=True)
    (tasks / "INDEX.md").write_text(
        "| Notes | Tracked in | Status |\n"
        "| --- | --- | --- |\n"
        "| [Missing](2026-11-25-missing/notes.md) | | draft |\n"
    )
    (tasks / "roadmap.yaml").write_text(
        "nodes:\n"
        "  first:\n"
        "    depends_on: [second, unknown]\n"
        "    sources: [2026-11-25-unindexed]\n"
        "  second:\n"
        "    soft_depends_on: [first]\n"
        "    sources: [missing.md, notes.md, repo#42]\n"
    )
    monkeypatch.chdir(tmp_path)
    assert main(["planning", "check", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["roadmap_present"]
    assert {issue["code"] for issue in report["diagnostics"]} == {
        "missing-index-path",
        "unindexed-task",
        "unknown-dependency",
        "dependency-cycle",
        "unindexed-roadmap-source",
        "missing-roadmap-source",
    }
    assert sum(issue["code"] == "missing-roadmap-source" for issue in report["diagnostics"]) == 1
    assert main(["planning", "check"]) == 1
    summary = capsys.readouterr().out
    assert all(issue["message"] in summary for issue in report["diagnostics"])
