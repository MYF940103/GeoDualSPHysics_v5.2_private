# M3j Boundary Return Failure Localization Audit

## Objective

M3j-B audits whether the remaining mild-MCC return failures are spatially tied
to the platen/specimen interface and edge rings.  This stage does not modify
source and does not run a new simulation.

Inputs:

- M3d2 failed-return records;
- M3f failed-return records;
- M3h failed-return records.

Generated outputs:

- `m3j_failed_particle_boundary_locations.csv`
- `m3j_failed_region_summary.csv`
- `m3j_failed_particle_maps.svg/png`

## Normalized Geometry Metrics

For every failed particle record, M3j computes:

- `r/R`, using `R=0.03 m`;
- `z/H`, using `H=0.10 m`;
- distance to bottom platen;
- distance to top platen;
- distance to lateral boundary;
- distance to the nearest cap/lateral edge corner;
- boundary class.

The retained failed-particle CSV files do not contain full neighbor clouds
after cleanup, so neighbor count and local particle distribution metrics are
marked as unavailable in `m3j_unavailable_diagnostics.csv`.  A dense very-short
diagnostic run would be needed for actual neighbor-count statistics.

## Region Classification

M3j uses:

- bottom cap zone: `z <= 0.015 m`;
- top cap zone: `z >= 0.085 m`;
- lateral/edge ring: `r >= 0.020 m`;
- measurement core: `r <= 0.010 m` and `0.025 <= z <= 0.075 m`.

The important distinction is whether a failed particle is near:

- bottom fixed platen;
- top prescribed platen;
- lateral surface;
- cap/lateral edge corner;
- interior ring;
- measurement core.

## Aggregate Localization

Across M3d2/M3f/M3h retained records, failures concentrate in boundary and
platen-adjacent regions.

Largest groups from `m3j_boundary_audit_summary.csv`:

| source | boundary class | failed records | `-3` records | `-1` records |
| --- | --- | ---: | ---: | ---: |
| M3f | edge_corner | 2236 | 879 | 1357 |
| M3f | interior_ring | 966 | 661 | 305 |
| M3h | edge_corner | 946 | 218 | 728 |
| M3d2 | edge_corner | 768 | 104 | 664 |
| M3f | top_cap_zone | 656 | 648 | 8 |
| M3f | bottom_cap_zone | 647 | 455 | 192 |
| M3f | lateral_surface | 495 | 247 | 248 |
| M3h | bottom_cap_zone | 260 | 111 | 149 |
| M3d2 | bottom_cap_zone | 198 | 40 | 158 |

Measurement-core failed records are rare:

- M3f measurement core: 42 records;
- M3d2 measurement core: 6 records;
- M3h measurement core: 5 records.

This is not a random full-specimen return failure.  It is dominated by
edge/cap/platen-adjacent locations.

## Line-Search Failure Locations

For `ReturnStatus=-3`, the most important groups include:

- M3f ramp-improved-adaptive top cap zone: 358 records;
- M3f ramp-improved-adaptive interior ring: 279 records;
- M3f improved-adaptive interior ring: 274 records;
- M3f ramp-improved-adaptive edge corner: 269 records;
- M3f improved-adaptive top cap zone: 268 records;
- M3f ramp-improved-adaptive bottom cap zone: 193 records;
- M3f half-speed-adaptive edge corner: 152 records;
- M3h half-speed-adaptive-line edge corner: 152 records.

The half-speed and quarter-speed routes reduce final failures, but transient
failures still occur in edge/cap-adjacent locations.

## Distance Interpretation

The failed records have typical normalized locations:

- edge-corner groups: `r/R ~= 0.74` to `0.89`;
- bottom cap-zone groups: `z/H ~= 0.05` to `0.09`;
- top cap-zone groups: `z/H ~= 0.95` to `0.98`;
- lateral-surface groups: `r/R ~= 0.70` to `0.78`.

These are precisely the locations where the prescribed/fixed platens and the
lateral confinement/free-surface selection meet the deforming material.

## Conclusion

Failed MCC returns are concentrated near boundary/platen/edge regions.  The
dominant locations are:

1. edge corners;
2. bottom cap zone near the fixed platen;
3. top cap zone near the prescribed platen;
4. adjacent interior/lateral rings.

The evidence supports a boundary-induced local strain path interpretation and
does not support a global MCC return mapping collapse.
