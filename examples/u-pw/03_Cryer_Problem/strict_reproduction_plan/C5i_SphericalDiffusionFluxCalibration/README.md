# C5i Spherical Diffusion Flux Calibration

This directory contains post-processing only diagnostics for the Cryer
pressure-only spherical diffusion gate.

No DualSPHysics simulations are launched here. The script reads committed C5e,
C5f, C5g/C5h pressure-only diffusion CSV artifacts, solves a matching 1D
finite-volume radial diffusion reference problem, and compares the apparent SPH
drainage flux against that reference.

Run from this directory with:

```powershell
py -3 .\scripts\spherical_radial_diffusion_reference.py
```

The WindowsApps `python` shim may not execute scripts correctly on this machine;
use `py -3`.

Retained artifacts:

- `c5i_fv_reference_timeseries.csv`
- `c5i_fv_reference_profiles.csv`
- `c5i_sph_pressure_only_summary.csv`
- `c5i_radial_bin_profiles.csv`
- `c5i_volume_mean_decay.csv`
- `c5i_surface_shell_decay.csv`
- `c5i_effective_boundary_type.csv`
- `c5i_flux_ratio_metrics.csv`
- `c5i_geometry_flux_error_metrics.csv`
- `figures/*.png`
- `figures/*.svg`
