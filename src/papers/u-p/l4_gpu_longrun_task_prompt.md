# Draft Task Prompt: L4 GPU Long-Run Initial-State Diffusion Validation

## Goal

Enter L4: GPU long-run initial-state 1D consolidation validation.

Background:

- L3c is the current clean PR diffusion/boundary gate.
- It uses `PorePressureInit=3`, `p_w0=|q0|=10 kPa`,
  `InitialStressMode=0`, `PorePressureFeedback=0`, no `AccInput`, and no
  `MechanicalTopLoad`.
- CPU/GPU L3c both completed with `code=0`, `excluded=0`, and `DtMin=0`.
- L3c avoids the L2/L3b dynamic pressure peak and matches the Terzaghi
  initial-state pressure scale.

Strict scope:

- Do not modify source.
- Do not change the mechanical loading route.
- Do not enable full feedback.
- Do not run damping/viscosity sweeps.
- Do not enter Cryer, triaxial, or MCC.

Tasks:

1. Create an L4 experiment directory under
   `examples/u-pw/01_1D_Consolidation/experiments/`.
2. Reuse the L3c consistent initial-state setup.
3. Extend the time window to a longer Terzaghi decay interval if runtime is
   acceptable.
4. Run CPU Release and GPU Release parity if feasible.
5. Postprocess:
   - pressure profiles versus Terzaghi analytical solution;
   - bottom excess pressure versus analytical solution;
   - volume-mean excess decay;
   - top drained residual;
   - bottom no-flux proxy;
   - CPU/GPU differences.
6. Generate paper-compatible SVG/PNG figures.
7. Write an L4 report that states clearly:
   - L4 validates Level-1 PR diffusion and hydraulic boundaries;
   - L4 does not validate mechanical top-load generation;
   - L4 does not validate full feedback.
8. Update README, notes, and `gpu_port_plan.md`.
9. Commit with:

```text
git commit -m "Add GPU long-run 1D consolidation diffusion validation"
```

Required final answers:

1. CPU/GPU `code=0/excluded=0/DtMin` status.
2. Analytical error over the longer run.
3. Top drained and bottom no-flux status.
4. CPU/GPU parity.
5. Whether L4 is a Level-1 validation only.
6. Whether L5 remains required for full mechanical reproduction.
