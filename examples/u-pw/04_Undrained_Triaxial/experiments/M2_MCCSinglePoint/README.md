# M2 MCC Single-Point Prototype

M2 is a standalone material-point prototype, not a DualSPHysics case.

The executable scripts and retained outputs live in:

```text
src/papers/u-p/mcc_single_point/
```

This experiment directory exists only to keep the triaxial workflow index aware
of the M2 step. No GenCase, DualSPHysics, PartVTK, CPU SPH, or GPU simulation
is run here.

Key retained outputs:

- `m2_mcc_test_summary.csv`;
- `m2_mcc_isotropic_path.csv`;
- `m2_mcc_drained_triaxial_path.csv`;
- `m2_mcc_undrained_path.csv`;
- `m2_mcc_yield_consistency.csv`;
- `m2_mcc_return_iterations.csv`;
- SVG/PNG figures under `figures/`.

M2 verifies the standalone MCC return mapping before any future M3 CPU
`SoilConstitutiveModel=3` integration.
