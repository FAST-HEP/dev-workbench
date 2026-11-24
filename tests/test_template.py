import tomllib
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]


def test_default_guidance_and_pinned_package():
    config = yaml.safe_load((ROOT / "copier.yml").read_text())
    defaults = {name: config[name]["default"] for name in ("commit_convention", "ai_label", "package_ref")}
    env = Environment(loader=FileSystemLoader(ROOT / "template"), undefined=StrictUndefined)
    answers = dict(defaults, workspace_name="lz", package_repository="https://example.org/dev-workbench.git")
    guidance = env.get_template("AGENTS.md.jinja").render(**answers)
    assert "Conventional Commits" in guidance
    assert "`AI` label" in guidance
    pixi = tomllib.loads(env.get_template("pixi.toml.jinja").render(**answers))
    assert pixi["pypi-dependencies"]["dev-workbench"]["rev"] == "v0.1.0"


def test_custom_commit_convention_and_disabled_label():
    env = Environment(loader=FileSystemLoader(ROOT / "template"), undefined=StrictUndefined)
    guidance = env.get_template("AGENTS.md.jinja").render(
        workspace_name="test", commit_convention="project commit style", ai_label=""
    )
    assert "project commit style" in guidance
    assert "label" not in guidance
