# Dev Workbench

Bootstrap and manage multi-repository development workspaces with Pixi. Dev Workbench records the repositories you choose in `.dev-workbench.toml`, discovers projects on GitHub and GitLab, and reports the state of local checkouts.

## Start a workspace

Once a release tag is available, generate a workspace with Copier.

```sh
copier copy --vcs-ref <release-tag> https://github.com/FAST-HEP/dev-workbench.git <workspace-dir>
```

When prompted, use `https://github.com/FAST-HEP/dev-workbench.git` as the package repository and the release tag as the package revision. Copier creates a Pixi manifest, an empty repository inventory, and starter `AGENTS.md` guidance. You can override the Conventional Commits and `AI` review label defaults during setup.

## Adopt an existing workspace

Add `dev-workbench` to your Pixi manifest under `[pypi-dependencies]`, using the Git URL and a pinned `rev`. Create `.dev-workbench.toml` at the workspace root. Existing tasks, guidance, and checkout paths can stay in place.

```toml
[[repositories]]
path = "analysis"
url = "git@codeberg.org:example/analysis.git"

[[sources]]
name = "lab"
provider = "gitlab"
host = "gitlab.example.org"
namespace = "research/physics"
include_subgroups = true
```

Use `provider = "github"` and the organisation name as `namespace` for GitHub discovery. Individual repositories can use any Git host.

```sh
pixi run dev-workbench discover lab --token-file /path/to/token
pixi run dev-workbench checkout
pixi run dev-workbench status
```

Discovery prompts you to accept, skip, or stop at each candidate. Use `--all` for a single confirmation. Discovery updates the inventory. Checkout is a separate step that clones missing repositories using your normal Git credentials. With `--token-file`, discovery works without `gh` or `glab`.

## Development

Run `pixi run test`. See the [deployment design](docs/superpowers/specs/2026-11-24-dev-workbench-design.md) for pilot scope and verification criteria.
