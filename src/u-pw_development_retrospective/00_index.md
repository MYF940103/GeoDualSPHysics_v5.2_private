# u-pw Development Retrospective Index

Date: 2026-05-14

This directory is a pre-rollback archive of the u-pw development branch. It is
not a new development package and should not be used to keep extending the
current experimental interface set.

## Files

- `current_state_before_rollback.md`: branch, HEAD, status snapshot, tag advice.
- `01_global_development_timeline.md`: high-level commit and task timeline.
- `02_successful_routes.md`: routes worth preserving or cherry-picking later.
- `03_failed_routes_and_lessons.md`: failed routes and lessons learned.
- `04_interface_cleanup_lessons.md`: parameter/interface governance lessons.
- `05_redevelopment_roadmap.md`: recommended clean rebuild strategy.
- `06_file_cleanup_manifest.md`: paper/reference cleanup and archive policy.
- `07_case_cleanup_manifest.md`: examples/u-pw cleanup policy and heavy outputs.
- `08_cherry_pick_after_rollback.md`: rollback and cherry-pick guidance.

Generated inventories:

- `archive_manifests/papers_u-p_file_inventory.csv`
- `archive_manifests/papers_u-p_prefix_inventory.csv`
- `archive_manifests/papers_u-p_cleanup_recommendations.csv`
- `archive_manifests/examples_u-pw_file_inventory.csv`
- `archive_manifests/examples_u-pw_module_summary.csv`
- `archive_manifests/examples_u-pw_case_recommendations.csv`
- `archive_manifests/examples_u-pw_heavy_dirs_manifest.csv`
- `archive_manifests/examples_u-pw_heavy_files_manifest.csv`
- `archive_manifests/heavy_output_summary.txt`
- `archive_manifests/heavy_output_cleanup_actions.csv`
- `archive_manifests/heavy_output_cleanup_summary.txt`

Source-control snapshots:

- `snapshots/git_state_before_rollback.txt`
- `snapshots/git_status_before_rollback.txt`

## External Backup

Recommended external copy target:

```text
D:/MYF/SPH/UPW_DEVELOPMENT_RETROSPECTIVE_20260514/
```

If the external copy exists, treat it as the rollback-safe copy. If it does not,
copy this directory there before destructive rollback.

PRE-ROLLBACK-1 copied this archive to the target above. See
`external_copy_status.txt` for the timestamp.

## Keep

Always keep:

- source/reference PDFs;
- literature conversion markdowns;
- final route reports;
- final CSV summaries and figures for validated gates;
- this retrospective directory.

## Avoid

Avoid carrying forward:

- deprecated Cryer modes and large boundary-mode families;
- failed MCC strict-validation geometry routes as active interfaces;
- failed mechanical top-load force-on-material route as validation;
- neutral time-integration modes unless explicitly replaying TINT2;
- raw `_out`, `data`, `PartCsv_*`, `.bi4`, `.vtk`, `Run.out`, and logs.
