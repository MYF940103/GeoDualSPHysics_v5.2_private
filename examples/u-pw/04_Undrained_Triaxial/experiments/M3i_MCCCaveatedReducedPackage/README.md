# M3i Caveated MCC Reduced Package

M3i-revised is a reporting package only. It does not run GenCase,
DualSPHysics, GPU, or PartVTK, and it does not modify source.

Run the package builder:

```powershell
py -m py_compile .\build_m3i_reduced_package.py
py .\build_m3i_reduced_package.py
```

Outputs:

- `m3i_case_inventory.csv`
- `m3i_summary_metrics.csv`
- `m3i_mcc_state_summary.csv`
- `m3i_return_status_summary.csv`
- `m3i_boundary_failure_evidence.csv`
- `m3i_geometry_route_summary.csv`
- `m3i_reaction_stress_path_summary.csv`
- `m3i_pore_pressure_summary.csv`
- `m3i_no_go_decision_table.csv`
- `figures/*.svg`
- `figures/*.png`

The package freezes the current MCC route as a CPU-only, feedback-off,
caveated reduced prototype. Clean MCC validation, full feedback, custom
fan-like solver import, and GPU remain deferred.
