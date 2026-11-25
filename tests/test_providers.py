import sys
from argparse import Namespace
from types import SimpleNamespace

import pytest

from dev_workbench.providers import discover


@pytest.mark.parametrize("source_settings, url_prefix", [
    ({}, "git@gitlab.example.org:"),
    ({"clone_protocol": "https"}, "https://gitlab.example.org/"),
])
def test_gitlab_reads_all_pages_without_provider_cli(tmp_path, monkeypatch, source_settings, url_prefix):
    token = tmp_path / "token"
    token.write_text("test-token\n")

    def projects(**options):
        assert options == {"iterator": True, "with_shared": False, "include_subgroups": True}
        for path in ("group/first", "group/sub/second"):
            yield SimpleNamespace(path_with_namespace=path,
                                  http_url_to_repo=f"https://gitlab.example.org/{path}.git",
                                  ssh_url_to_repo=f"git@gitlab.example.org:{path}.git")

    class Client:
        def __init__(self, url, private_token):
            assert url == "https://gitlab.example.org"
            assert private_token == "test-token"
            self.groups = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, name, lazy):
            assert (name, lazy) == ("group", True)
            return SimpleNamespace(projects=SimpleNamespace(list=projects))

    monkeypatch.setitem(sys.modules, "gitlab", SimpleNamespace(Gitlab=Client))
    source = dict(provider="gitlab", host="gitlab.example.org", namespace="group", include_subgroups=True, **source_settings)
    assert discover(source, Namespace(token_file=token)) == [
        ("first", f"{url_prefix}group/first.git"),
        ("sub/second", f"{url_prefix}group/sub/second.git"),
    ]


def test_github_does_not_return_partial_results(tmp_path, monkeypatch):
    token = tmp_path / "token"
    token.write_text("test-token")

    def repositories():
        yield SimpleNamespace(name="first", clone_url="https://github.com/org/first.git",
                              ssh_url="git@github.com:org/first.git")
        raise RuntimeError("second page failed")

    class Client:
        def __init__(self, base_url, auth):
            assert base_url == "https://api.github.com"
            assert auth == "test-token"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get_organization(self, name):
            assert name == "org"
            return SimpleNamespace(get_repos=repositories)

    monkeypatch.setitem(sys.modules, "github", SimpleNamespace(Github=Client, Auth=SimpleNamespace(Token=str)))
    with pytest.raises(RuntimeError, match="second page failed"):
        discover(dict(provider="github", namespace="org"), Namespace(token_file=token))
