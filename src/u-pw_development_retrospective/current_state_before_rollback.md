# Current State Before Rollback

Date: 2026-05-14

This file freezes the local state before any rollback or source cleanup. It is
intended as the first checkpoint for the u-pw retrospective archive.

## Git State

```text
repo root: D:/MYF/SPH/GeoDualSPHysics_v5.2
working directory: D:/MYF/SPH/GeoDualSPHysics_v5.2/src
branch: u-p
HEAD: 1b1c1f8d14473b7c20c01b701a211441e6907c18
HEAD subject: Add end-step pore-pressure integration experiment
git status --short count: 102 entries
```

Full snapshots:

- `snapshots/git_state_before_rollback.txt`
- `snapshots/git_status_before_rollback.txt`

Recommended tag command before rollback:

```powershell
git tag u-pw-pre-rollback-archive-20260514 1b1c1f8d14473b7c20c01b701a211441e6907c18
git push origin u-pw-pre-rollback-archive-20260514
```

The tag has not been created by this step. Create it only after confirming the
archive is satisfactory.

## Important Dirty/Untracked State

The worktree contains unrelated modified/untracked files outside the intended
retrospective scope. They are recorded in the status snapshot but were not
modified by this archive step.

Known unrelated modified file at freeze time:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/Visualization_Scenario1_2/Scenario2_G9b_Xi005/S2_G9b_VIS_T36_Def.xml
```

There are many unrelated untracked project files and generated/example assets.
Do not delete or stage them as part of rollback unless separately reviewed.

## Archive Manifests Created

```text
archive_manifests/papers_u-p_file_inventory.csv
archive_manifests/papers_u-p_prefix_inventory.csv
archive_manifests/examples_u-pw_file_inventory.csv
archive_manifests/examples_u-pw_module_summary.csv
archive_manifests/examples_u-pw_heavy_dirs_manifest.csv
archive_manifests/examples_u-pw_heavy_files_manifest.csv
archive_manifests/heavy_output_summary.txt
```

Summary at freeze time:

```text
papers/u-p: 342 markdown files, 1 PDF, 2 extensionless/other files
examples/u-pw modules: 6
heavy dirs under examples/u-pw: 5
heavy files under examples/u-pw: 190
heavy file bytes under examples/u-pw: 82283969
```

## Rollback Principle

Rollback should be done from git, not by manually deleting source files. Keep
this archive directory and the external backup copy until the new u-pw branch is
stable.
