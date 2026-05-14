# Case Cleanup Manifest

Generated inventories:

- `archive_manifests/examples_u-pw_file_inventory.csv`
- `archive_manifests/examples_u-pw_module_summary.csv`
- `archive_manifests/examples_u-pw_case_recommendations.csv`
- `archive_manifests/examples_u-pw_heavy_dirs_manifest.csv`
- `archive_manifests/examples_u-pw_heavy_files_manifest.csv`
- `archive_manifests/heavy_output_summary.txt`

## examples/u-pw Policy

Keep:

- XML definitions for final or representative cases;
- BAT/run scripts required to replay final gates;
- analysis scripts;
- extracted CSV summaries;
- figures;
- README/notes.

Archive:

- intermediate failed variants needed only to explain a report;
- deprecated Cryer/MCC/triaxial experiment directories;
- diagnostic dense-output cases after extracted CSV/figures exist.

Delete candidates:

- `_out/`;
- `data/`;
- `PartCsv_*`;
- `.bi4`;
- `.vtk`;
- `Run.out`;
- temporary logs.

## Current examples/u-pw Snapshot

At freeze time:

```text
01_1D_Consolidation: 713 files, 26989658 bytes
02_SelfWeight_Consolidation: 446 files, 19578513 bytes
03_Cryer_Problem: 795 files, 110114422 bytes
04_Undrained_Triaxial: 1716 files, 90452199 bytes
05_Retrogressive_Slope: 30 files, 68182 bytes
06_Sainte_Monique: 9 files, 18170 bytes
```

Heavy outputs identified before cleanup:

```text
heavy output directories: 5
heavy output files: 190
heavy output file bytes: 82283969
```

Case recommendation snapshot:

```text
KEEP_REPLAY: 5
KEEP_PACKAGE: 2
KEEP_CAVEATED: 1
ARCHIVE_DEPRECATED: 21
ARCHIVE: 84
```

## Cleanup Action Taken In PRE-ROLLBACK-1

The heavy-output manifests were created before deletion. Then the listed heavy
outputs were removed from `examples/u-pw`.

Cleanup summary:

```text
deleted actions: 195
remaining heavy dirs: 0
remaining heavy files: 0
```

Action log:

```text
archive_manifests/heavy_output_cleanup_actions.csv
archive_manifests/heavy_output_cleanup_summary.txt
```

The cleanup includes tracked historical run logs as well as untracked raw
solver outputs. They are preserved in the manifest by path, timestamp, and size,
but not copied because they are generated/heavy artifacts.

Do not delete final CSV summaries, figures, XML, BAT files, scripts, reports,
or reference material.
