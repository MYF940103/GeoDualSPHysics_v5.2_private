# M3o Smooth / Fan-Like Layout Prototype

This directory contains an isolated geometry prototype for a smooth/fan-like
triaxial specimen layout.

Run:

```powershell
py -m py_compile .\generate_smooth_triaxial_layout.py
py .\generate_smooth_triaxial_layout.py
```

The script writes:

- `m3o_smooth_fan_layout_particles.csv`
- `m3o_smooth_fan_layout_params.json`
- `m3o_geometry_quality_metrics.csv`
- `m3o_support_neighbor_metrics.csv`
- `m3o_layout_comparison.csv`
- `figures/*.svg`
- `figures/*.png`

This is a geometry/support diagnostic only.  No solver case is run because a
direct low-risk arbitrary particle-cloud import route was not confirmed for the
current GenCase/DualSPHysics workflow.
