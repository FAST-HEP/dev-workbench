import json
import subprocess

from dev_workbench.cli import main


def git(*args):
    return subprocess.run(["git", *map(str, args)], check=True, capture_output=True, text=True)


def test_checkout_is_repeatable_and_status_finds_parent(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source"
    git("init", "--bare", source)
    root = tmp_path / "workspace"
    root.mkdir()
    (root / ".dev-workbench.toml").write_text(
        f'[[repositories]]\nurl = "{source}"\npath = "repos/example"\n'
    )
    monkeypatch.chdir(root)
    assert main(["checkout"]) == 0
    assert (root / "repos/example/.git").is_dir()
    assert main(["checkout"]) == 0
    monkeypatch.chdir(root / "repos/example")
    capsys.readouterr()
    assert main(["status", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["state"] == "present"


def test_checkout_preserves_occupied_destination(tmp_path, monkeypatch):
    (tmp_path / ".dev-workbench.toml").write_text(
        '[[repositories]]\npath = "local"\nurl = "https://example.org/a/b.git"\n'
    )
    (tmp_path / "local").mkdir()
    note = tmp_path / "local/note"
    note.write_text("keep")
    monkeypatch.chdir(tmp_path)
    assert main(["checkout"]) == 1
    assert note.read_text() == "keep"


def test_discovery_stop_saves_earlier_choices(tmp_path, monkeypatch):
    manifest = tmp_path / ".dev-workbench.toml"
    manifest.write_text('[[sources]]\nprovider = "github"\nnamespace = "example"\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    answers = iter(["", "y", "s"])
    monkeypatch.setattr("dev_workbench.cli.discover", lambda *args: [
        ("earliest", "https://github.com/example/earliest.git"),
        ("first", "https://github.com/example/first.git"),
        ("second", "https://github.com/example/second.git"),
    ])
    assert main(["discover", "example", "--token-file", "token"]) == 0
    assert 'path = "earliest"' not in manifest.read_text()
    assert 'path = "first"' in manifest.read_text()
    assert 'path = "second"' not in manifest.read_text()


def test_bulk_import_requires_confirmation(tmp_path, monkeypatch):
    manifest = tmp_path / ".dev-workbench.toml"
    original = '[[sources]]\nprovider = "github"\nnamespace = "example"\n'
    manifest.write_text(original)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("dev_workbench.cli.discover", lambda *args: [
        ("first", "https://github.com/example/first.git"),
    ])
    assert main(["discover", "example", "--all", "--token-file", "token"]) == 1
    assert manifest.read_text() == original


def test_discovery_failure_discards_partial_results(tmp_path, monkeypatch, capsys):
    manifest = tmp_path / ".dev-workbench.toml"
    original = '[[sources]]\nprovider = "github"\nnamespace = "example"\n'
    manifest.write_text(original)
    monkeypatch.chdir(tmp_path)

    def fail(*args):
        raise RuntimeError("unexpected secret")

    monkeypatch.setattr("dev_workbench.cli.discover", fail)
    assert main(["discover", "example", "--token-file", "token"]) == 1
    assert manifest.read_text() == original
    assert "unexpected secret" not in capsys.readouterr().err


def test_normalizes_ssh_and_https():
    from dev_workbench.workspace import identity

    assert identity("git@github.com:org/repo.git") == identity("https://github.com/org/repo")


def test_rejects_colliding_manifest_paths_before_checkout(tmp_path, monkeypatch):
    (tmp_path / ".dev-workbench.toml").write_text(
        '[[repositories]]\npath = "repos/example"\nurl = "git@example.org:repo.git"\n'
        '[[repositories]]\npath = "repos/example/nested"\nurl = "git@example.org:nested.git"\n'
    )
    monkeypatch.chdir(tmp_path)

    def unexpected(*args):
        raise AssertionError("checkout ran before inventory validation")

    monkeypatch.setattr("dev_workbench.cli.checkout", unexpected)
    assert main(["checkout"]) == 1


def test_import_existing_offers_declared_submodules_and_direct_checkouts(tmp_path, monkeypatch):
    root = tmp_path
    git("init", root)
    git("-C", root, "remote", "add", "origin", "https://example.org/team/workspace.git")
    (root / ".gitmodules").write_text(
        '[submodule "declared"]\n'
        '  path = nested/declared\n'
        '  url = ../declared.git\n'
    )
    (root / "nested/declared").mkdir(parents=True)
    nested_repo = root / "nested/ignored"
    git("init", nested_repo)
    git("-C", nested_repo, "remote", "add", "origin", "https://example.org/team/ignored.git")
    direct = root / "direct"
    git("init", direct)
    git("-C", direct, "remote", "add", "origin", "git@example.org:team/direct.git")
    (direct / "untracked").write_text("keep")
    manifest = root / ".dev-workbench.toml"
    manifest.touch()
    prompts = []

    def accept(prompt):
        prompts.append(prompt)
        return "y"

    monkeypatch.chdir(root)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", accept)
    assert main(["import-existing"]) == 0
    assert prompts == ["Import direct? [y/N/s] ", "Import nested/declared? [y/N/s] "]
    imported = manifest.read_text()
    assert 'url = "git@example.org:team/direct.git"' in imported
    assert 'path = "nested/declared"' in imported
    assert 'url = "https://example.org/team/declared.git"' in imported
    assert (direct / "untracked").read_text() == "keep"
    assert not (root / "nested/declared/.git").exists()
    assert main(["import-existing"]) == 0
    assert len(prompts) == 2
    assert manifest.read_text() == imported
