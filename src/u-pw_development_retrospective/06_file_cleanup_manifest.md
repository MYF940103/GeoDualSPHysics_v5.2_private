# File Cleanup Manifest

Generated inventories:

- `archive_manifests/papers_u-p_file_inventory.csv`
- `archive_manifests/papers_u-p_prefix_inventory.csv`
- `archive_manifests/papers_u-p_cleanup_recommendations.csv`

## papers/u-p Policy

Keep:

- PDFs and original reference material;
- literature conversion markdowns;
- final reports for each major route;
- interface registry and cleanup policy;
- final roadmaps and decision audits.

Archive:

- intermediate per-task source audits;
- repeated failed-case reports;
- superseded task prompts;
- transient planning stubs after a final package exists.

Delete candidates after external backup:

- duplicated task prompts that are fully superseded by final reports;
- generated scratch reports that are not referenced by any package;
- temporary diagnostic notes with no unique data.

Do not delete before rollback:

- `experimental_interface_registry.md`;
- `experimental_interface_cleanup_policy.md`;
- `tint2_interface_constraint.md`;
- source/reference PDF;
- any final package report referenced by `00_index.md`.

## Current papers/u-p Snapshot

At freeze time:

```text
markdown files: 342
PDF files: 1
other/extensionless: 2
```

Large prefix groups include Cryer, GPU, MCC, T4/T5 triaxial, L3/L4/L5, BND1,
TINT1/TINT2, and interface-governance reports. See the CSV inventories for the
full list.

Cleanup recommendation snapshot:

```text
KEEP_REFERENCE: 4
KEEP_FINAL: 12
ARCHIVE_PROMPT: 2
ARCHIVE_DEV_RECORD: 227
ARCHIVE: 98
```

## Cleanup Action Taken In PRE-ROLLBACK-1

No `papers/u-p` files were deleted in this step. Only inventories and
retrospective documents were added.
