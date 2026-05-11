# Hydraulic Boundary Audit Milestone

Date: 2026-05-12

## Why This Audit Was Needed

The GPU self-weight Scenario 2 long runs showed the correct consolidation
trend, but the nominal analytical comparison retained a bottom excess-pressure
relative RMSE of about 7.6%. A calibrated effective time-factor reference
reduced this error to about 2.0%, suggesting that the main discrepancy is linked
to dynamic storage / apparent `cv` mapping rather than a simple boundary-layer
reset.

Even so, strict pore-pressure boundary consistency still required an audit,
because the PR pore-pressure operator originally used material-material
quadrature while mDBC/cDBC boundary particles did not carry production
hydraulic state. The audit therefore separated two questions:

- Is the Scenario 2 residual discrepancy boundary-controlled?
- Do we need a stricter hydraulic boundary path for future strict reproduction?

## Boundary Modes

### Mode 0: Legacy Layer Correction

`PorePressureBoundaryOperator=0` is the default production path. The PR
operators remain material-material. Top drained and bottom no-flux conditions
are enforced after pore-pressure update by layer projection:

- top drained: set top material layer to hydrostatic pressure, i.e. excess `0`;
- bottom no-flux: copy/reference a bottom material layer excess-pressure mean.

This path remains the default because it is stable, validated through Scenario 2
GPU runs, and gives the paper-compatible calibrated-reference line.

### Mode 1: Simple Virtual Ghost

`PorePressureBoundaryOperator=1` adds operator-level virtual boundary
contributions to `LapPorePress` and `LapZ`:

- top drained: excess-pressure Dirichlet ghost, `excess=0`;
- bottom no-flux: hydraulic-head / excess Neumann mirror, not zero total
  pressure gradient.

Mode 1 is implemented on CPU and GPU and has CPU/GPU parity. B5 showed that it
does not materially reduce the Scenario 2 long-run analytical discrepancy.
It remains experimental.

### Mode 2: CPU Hydraulic mDBC Boundary-Particle Prototype

`PorePressureBoundaryOperator=2` is the H1 CPU-only prototype. It reconstructs
hydraulic state at mDBC boundary-particle quadrature positions and adds those
boundary particles to `LapPorePress` / `LapZ`.

The prototype uses:

- mDBC projected boundary location `pos_b + BoundNormal_b`;
- top drained excess Dirichlet: `excess_b=0`;
- bottom head/excess Neumann reconstruction from nearby material excess;
- no zero-gradient condition on total pore pressure.

Mode 2 is unsupported on GPU and should hard error if requested.

## Comparison Table

| Mode | Boundary mechanism | CPU support | GPU support | Hydrostatic consistency | Pressure-only improvement | Self-weight improvement | Production status |
|---:|---|---|---|---|---|---|---|
| 0 | Legacy post-update top/bottom layer projection | Yes | Yes | Best/validated | Baseline | Baseline Scenario 2 line | Default production |
| 1 | Operator-level virtual ghost plus safety layer projection | Yes | Yes | Comparable to mode 0 | No material improvement in B5 | No material improvement in B5 | Experimental |
| 2 | CPU hydraulic mDBC boundary-particle quadrature prototype | Yes | No, hard error | Stable but slightly worse than mode 0/1 in H1 | No improvement in H1 short tests | No improvement in H1 short tests | CPU experimental only |

## H1 Result Summary

H1 confirmed that mode 2 really inserts boundary-particle hydraulic quadrature
into the PR operator. In the self-weight short run, the mode 2 log reported:

- bottom boundary contributions: 490;
- mDBC normals used: 490;
- reconstruction samples: 11900;
- fallback reconstructions: 0.

All H1 short runs completed with `code=0` and `excluded=0`, but mode 2 did not
improve the pressure-only diffusion or self-weight short metrics. Its
hydrostatic residual was also slightly larger than mode 0/1.

## Frozen Conclusions

- Mode 0 remains the default production path.
- Mode 1 remains an optional experimental CPU/GPU path.
- Mode 2 remains a CPU-only experimental hook.
- There is no current evidence supporting a GPU port of mode 2.
- Corrected-gradient PR production remains deferred.
- The Scenario 2 residual discrepancy is not primarily boundary controlled.

The calibrated-reference interpretation from A1/A2/P1 remains the preferred
Scenario 2 validation line for the current paper workflow.
