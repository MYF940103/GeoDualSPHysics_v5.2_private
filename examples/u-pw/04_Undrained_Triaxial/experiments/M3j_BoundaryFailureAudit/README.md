# M3j Boundary Failure Audit

Postprocessing-only audit using retained M3d2/M3f/M3h failed-return CSV
outputs. No new solver run, no source change, no GPU run, and no full feedback.

Run:

```powershell
py analyze_m3j_boundary_failure.py
```

Primary outputs:

- `m3j_failed_particle_boundary_locations.csv`
- `m3j_failed_region_summary.csv`
- `m3j_local_strain_path_comparison.csv`
- `m3j_platen_interaction_failure_timeline.csv`
- `m3j_boundary_audit_summary.csv`
- `m3j_failed_particle_maps.svg/png`
