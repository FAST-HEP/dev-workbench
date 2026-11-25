# Dev Workbench development

Read the [deployment design](docs/superpowers/specs/2026-11-24-dev-workbench-design.md) before changing bootstrap, discovery, authentication, import, or checkout. This file guides development of the package. The Copier template supplies separate starter guidance for adopting workspaces.

## Workspace operations

- Resolve the workspace from the nearest enclosing `.dev-workbench.toml`. Use its accepted inventory to scope operations. Preserve dirty checkouts and untracked files.
- Keep status and discovery previews read-only. Import writes the manifest. Checkout clones missing repositories and reports existing matches or conflicts.
- Exercise Git operations against temporary repositories in tests. If destructive commands are added later, provide a dry run and require interactive confirmation before execution.
- Require explicit credential selection for authenticated discovery. Keep tokens out of command arguments, logs, manifests, and commits. Use the credential options in the deployment design.

## Command output

- Give every operational command human-readable output by default and a documented `--json` mode. Render both from the same result data and preserve exit codes across formats.
- In JSON mode, emit one parseable result on stdout. Send prompts, progress, and diagnostics to stderr. Preserve interactive confirmation requirements.

## Development and planning

- Once Pixi tasks exist, use the relevant tasks for verification. For packaging changes, verify the pinned package from a separate consumer workspace.
- Keep durable designs in `docs/` and local planning notes in `tasks/`. Read [the planning guide](docs/planning.md) before changing the task index, roadmap, or issue sync. Update the relevant command documentation when behaviour changes.
- Consult the [roadmap](docs/roadmap.md) when planning new commands or adapting FAST-HEP scripts.

## Commits and reviews

- Use Conventional Commits. Keep each commit to one logical change.
- Use the `AI` label on pull requests and merge requests with AI-assisted changes.
