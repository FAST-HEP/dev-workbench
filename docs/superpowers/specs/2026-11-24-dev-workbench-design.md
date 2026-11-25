# Dev Workbench deployment design

Dev Workbench gives multi-repo workspaces a shared way to discover, register, check out, and inspect repositories. LZ is the fresh-bootstrap pilot. FAST-HEP and DICE are the adoption pilots.

## Deployment approaches

- **Copier only.** One template can bootstrap a workspace, but copying shared scripts makes each workspace responsible for merging tooling updates.
- **CLI only.** A single installed tool could bootstrap and run a workspace. This puts starter-file generation and its maintenance inside the CLI.
- **CLI package plus Copier (selected).** Copier generates a starter workspace. A versioned Python package supplies executable behaviour and upgrades independently. Existing workspaces can use the package without applying the template.

Start with a tagged Git release installed as a PyPI dependency through Pixi. Each workspace commits its resolved `pixi.lock`. The package repository must be readable wherever the pilots run. Revisit package-index publishing once distribution needs are known.

Copier generates `.dev-workbench.toml`, a minimal `pixi.toml`, starter `AGENTS.md`, and ignore rules for local `tasks/` notes. These files become workspace-owned after bootstrap. Existing workspaces add the dependency, a manifest, and whichever Pixi task wrappers they want. They retain ownership of their current files, planning conventions, and checkout paths.

During setup, Copier defaults the generated `AGENTS.md` to Conventional Commits and the `AI` label for AI-assisted pull requests and merge requests. Users can override the commit convention and rename or disable the label independently. The starter records the selected rules as guidance.

## Manifest and checkout

Commit `.dev-workbench.toml` at the workspace root. Commands use the nearest enclosing manifest, including when invoked from a managed checkout. The manifest records discovery sources and their settings, plus the accepted inventory of repository URLs and workspace-relative paths. Users can write or edit the inventory directly. Credentials and token-file paths stay outside it.

Checkout operates on the accepted inventory. Clone missing repositories, recognise matching checkouts, and report occupied paths and mismatched remotes. Recognise SSH and HTTPS URLs for the same repository as equivalent. Rerunning checkout after a partial failure should pick up missing repositories without fetching, pulling, or changing existing checkouts. Git handles checkout authentication. FAST-HEP can register its existing submodules first and move to standalone clones in a separate migration that preserves the paths used by editable installs.

## Discovery and import

Support individual repositories, GitHub organisations, and GitLab groups on configurable hosts. GitLab subgroup traversal is opt-in per source. Import records SSH clone URLs by default. Sources can set `clone_protocol = "https"` to use HTTPS for new entries. Explicit clone URLs also support Codeberg. Forgejo organisation discovery can follow the pilots.

Complete all API pages before presenting changes. A failed page aborts the discovery run before any import. Show additions, conflicts, and entries that disappeared from discovery. Leave disappeared entries and their checkouts in place pending review.

Prompt for each eligible addition with `y` to accept, `n` or Enter to skip, and `s` to stop successfully and save choices already accepted. Skipped and unreviewed candidates can reappear on the next run. Save accepted choices in one manifest write. With `--all`, confirm the eligible count and source first. For example, “Add all 18 repositories from gitlab.example.org/group to .dev-workbench.toml? Checkouts happen separately. [y/N]” If confirmation is needed and no terminal is available, exit before writing. Import changes the manifest. Checkout is a separate command.

## Authentication

Use PyGithub and python-gitlab for discovery. Select credentials explicitly for each authenticated discovery run and show the target host. Offer three options.

1. Use the active `gh` or `glab` credential. Warn that the active token may have broad permissions and that environment credentials can take precedence over a saved login.
2. Supply a dedicated fine-grained token for this run. Use the least permissions needed for discovery and verify which token options the target GitLab instance supports.
3. Supply `--token-file PATH` for the run. Read it directly and keep the path and token out of the manifest.

The provider CLIs are optional and serve the first authentication option. Local status and checkout use local Git state and Git authentication. A remote server with Pixi, Git, and a token file can run discovery without either provider CLI.

## Pilot acceptance

- **LZ.** Generate the workspace with Copier, discover a GitLab group, review and save an inventory, and run checkout twice. Include a case with existing matching checkouts and a conflicting path. Verify explicit repository entries and opt-in subgroup discovery.
- **FAST-HEP and DICE.** Pin the same package release in each workspace and run a read-only status task against registered existing checkouts. Verify FAST-HEP submodule recognition without converting any checkout.
- **Clean remote server.** Run authenticated discovery using `--token-file` against LZ’s GitLab host and a GitHub organisation with neither `gh` nor `glab` installed. Exercise multiple pages and verify that a page failure produces no manifest changes.
- **TUI integration.** Return structured repository status from shared Python code so a future read-only TUI can use the same implementation as the CLI. TUI screens, destructive actions, and replacing FAST-HEP’s dashboard are separate work.

Roadmap tooling, issue sync, and push automation are outside the first release.

Implementation planning can settle the exact TOML field names, command names, status output schema, and test fixtures.
