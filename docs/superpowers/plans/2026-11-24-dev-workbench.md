# Dev Workbench Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to execute the tasks in order.

**Goal:** Bootstrap new workspaces and adopt existing checkouts through a pinned Python CLI.

**Architecture:** Keep manifest, Git operations, and provider discovery separate. The CLI orchestrates review and writes, and the Copier template generates workspace policy and Pixi wiring.

**Tech Stack:** Python 3.13+, Git, TOMLKit, PyGithub, python-gitlab, Pixi, Copier.

**Spec:** [Deployment design](../specs/2026-11-24-dev-workbench-design.md)

- [x] Test nearest manifest, remote matching, checkout retries, and path conflicts against temporary Git repositories. Implement manifest validation and Git-backed status and checkout commands.
- [x] Test full discovery before import, partial acceptance on stop, and confirmation for bulk additions. Implement provider discovery, credential selection, and one atomic manifest update.
- [x] Test default and overridden Copier guidance. Add the template, package entry point, Pixi tasks, and fresh/adopted workspace instructions.
- [x] Build and install a wheel in a separate consumer environment, then run the installed CLI.
- [x] Run Copier end to end with default and overridden guidance.
- [ ] Verify Pixi dependency resolution and a pinned Git install when package downloads are available.
- [ ] Run authenticated live pilots against LZ GitLab and a GitHub organisation. Adopt the pinned package in FAST-HEP and DICE after a release is available.
