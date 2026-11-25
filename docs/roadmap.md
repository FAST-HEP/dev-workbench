# Dev Workbench roadmap

Dev Workbench helps people and coding agents work across multi-repository
projects. The FAST-HEP dev workspace's `[feature.scripts.tasks]` provides
examples of workflows to generalize. LZ and FAST-HEP have exercised discovery
and local adoption respectively. Use adopted workspaces to check that each
new capability works with both standalone clones and submodules.

## Command output

Every operational command must offer human-readable output by default and
machine-readable output through `--json`. Render both from the same result
data and preserve the exit code across formats.

- **Human output** should make the outcome, affected repositories, and any
  action needed easy to scan. Use colour only when appropriate for the stream.
- **JSON output** should put one parseable value on stdout, with stable field
  names and types. Send progress, prompts, and diagnostics to stderr and
  exclude credentials from both streams. Document each command's result
  shape, including empty results and partial failures.
- **Interactive decisions** still require the command's normal confirmation.
  For discovery and local import, provide a read-only preview for automation
  and report accepted, skipped, and conflicting entries as structured data.
  Adding JSON output must preserve the existing review and save behaviour.

Current `status --json` and `checkout --json` are the starting point. Keep
the existing status array, fields, and exit semantics compatible when
extending it. Include both output modes in acceptance checks for each change.

## 1. Richer workspace status

Extend `dev-workbench status` using FAST-HEP's `git-status` task
(`scripts/dev/git-status-summary.py`) as the reference. Use the accepted
manifest inventory, including when invoked from a child checkout.

- Show each repository's checkout state, branch or detached HEAD, tracked
  change count, untracked count, and ahead/behind counts for its configured
  upstream. Count changed paths with Git's porcelain output and define how
  renames and untracked directories count.
- Report no upstream and unavailable comparison data explicitly. An
  ahead/behind result describes local Git refs at the time of the check.
- Keep status read-only and local. Missing paths, occupied paths, remote
  mismatches, and Git errors remain visible even when details are unavailable.
- Verify clean and dirty checkouts, no upstream, detached HEAD, and
  ahead/behind using temporary Git repositories. Compare the human summary
  against the JSON result and smoke-test it in FAST-HEP and LZ.

## 2. Structured inventory and project context

- Bring `discover` and `import-existing` up to the output rule. Start with
  read-only candidate previews, then report the outcome of interactive review.
- Evaluate `repo-index` next. Start with an inventory-scoped index of package
  metadata and Pixi tasks. Use the FAST-HEP symbol, test, profile, and registry
  indexes to identify optional extensions and the project-specific inputs they
  need.
- Evaluate `repo-scan`, the HSF prototype at
  `/storage/Workspace/HSF/repo-scan` (reviewed at `2adff3a`), for optional
  per-repository analysis. It scans Python imports and C++ includes without
  building or running the target project, and can render a D2 overview.
  Compare its structured findings with the workspace index and assess which
  details help people and agents navigate the repositories. Keep generated
  reports local.
- Evaluate the read-only parts of `roadmap` and `roadmap-check` once a second
  workspace has a comparable planning format. Keep issue mirroring
  (`tasks-sync`) as a separate capability with explicit provider credentials
  and a preview of local file changes.

## 3. Multi-repo validation and release planning

- Use `snapshot` and `snapshot-run` to design an isolated way to test a
  selected set of revisions together. Start with a plan showing repositories,
  revisions, and the proposed environment. Keep FAST-HEP package selection
  and environment details in its workspace.
- Evaluate `release-plan`, `release-check`, and `release-validate-dry` as
  candidates for reusable planning and validation. FAST-HEP's `releases.json`,
  release order, and workshop smoke tests are inputs supplied by that workspace.
- Treat generated changelog drafts, Dependabot synchronization, and other
  multi-repo edits as later candidates. Start by reporting proposed changes.

## 4. Operations that change checkouts or remotes

Keep submodule initialization and updates, cleanup execution, version edits,
tagging, branch pushes, and release publishing in the existing FAST-HEP scripts
while the read-only milestones are developed. Evaluate each operation
separately. Any future destructive operation requires a dry run and interactive
confirmation, and must preserve dirty checkouts and untracked files.
