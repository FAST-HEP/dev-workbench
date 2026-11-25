# Local planning

Keep task notes, the index, roadmap data, and issue mirrors under the ignored
`tasks/` directory. Put shared work in its owning repository's issue. The
issue becomes authoritative once a local task has a tracking issue. Keep
durable designs and documentation in the appropriate repository.

| Path | Purpose |
| --- | --- |
| `tasks/AGENTS.md` | Workspace-specific guidance for planning work |
| `tasks/YYYY-MM-DD-<slug>/` | Local notes and supporting material. A workspace can include a repository name in the slug. |
| `tasks/INDEX.md` | A Markdown table with `Notes`, `Tracked in`, and `Status` columns |
| `tasks/roadmap.yaml` | Optional dependency graph for work that needs sequencing |
| `tasks/ROADMAP.md` | Generated roadmap, when the workspace uses one |
| `tasks/issues/` | Generated local issue mirror, when configured |

When a task has a tracking issue, add its URL to the index and put
`> Tracked in: <URL>` near the top of the task note. Record the current status
in the index. Update the index if a task moves, including into `tasks/.finished/`.
For generated mirrors, use the workspace's sync command.

## Validate the local files

Run `dev-workbench planning check` for a terminal report or
`dev-workbench planning check --json` for structured results. The command uses
the workspace containing the nearest manifest and reads local files only.

Use a backticked folder name or a relative Markdown link in the index's
`Notes` column. For a work item without local notes, use a plain-text
description. The check reports missing referenced paths and dated task folders
that have no index entry. Additional tables are supported alongside the index.

A roadmap uses a top-level `nodes` mapping keyed by task ID. Each node can
declare `depends_on` and `soft_depends_on` as lists of node IDs, and `sources`
as a list of local paths or issue references. Local paths resolve relative to
`tasks/` first, then the workspace root. Issue URLs and references such as
`repo#42` are accepted without contacting the provider. Node metadata such as title, status,
priority, and issue remains workspace-owned. The check detects unknown
dependency IDs, cycles, and missing or unindexed local task sources. It does
not require a roadmap from workspaces that only use an index.

JSON reports contain `index_present`, `roadmap_present`, and a `diagnostics`
array with `code`, `path`, and `message` fields. Exit status is 0 for a
valid plan and 1 for validation errors.

## Bootstrap and adoption

Copier creates `tasks/AGENTS.md` and an empty `tasks/INDEX.md`. Its ignore
rules keep both files local, and template updates preserve existing copies.
The root guidance points agents to `tasks/AGENTS.md`. Existing workspaces can
keep their planning files, add `/tasks/` to their root `.gitignore`, and copy
the [starter guidance](../template/tasks/AGENTS.md) into `tasks/AGENTS.md`
if they have no local guidance yet. Add a pointer in the root `AGENTS.md` to
read it before creating or updating tasks.
