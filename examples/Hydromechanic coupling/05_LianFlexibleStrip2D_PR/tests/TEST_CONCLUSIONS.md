# Lian 2023 Flexible Strip 2D - Test Conclusions

This folder keeps only the reproducible test scripts and this conclusion note.
Generated solver outputs, diagnostic XML copies, run logs, VTK/CSV/PNG figures,
and temporary support JSON/PID/log files were intentionally removed before the
checkpoint.

## Status

- The Lian flexible strip validation path is paused/abandoned for now. The next
  validation target is Yao et al. (2025) 2-D consolidation.
- The code keeps `HydroMechTopLoadMode=3` (`TopStripVertical`) as an exploratory
  hard-coded strip-load option for the Lian setup, with the strip footprint
  fixed at `x=[0,1.25] m`.
- In this mode, drainage is applied only to the open top free surface outside
  the strip footprint. The strip footing area remains impermeable for the full
  simulation.

## Findings Preserved From The Short Runs

- The periodic boundary entry in the early Lian XML was inappropriate for this
  local strip-footing problem. Later tests used `PeriodicActive="None"`.
- The initial negative excess pore pressure field was traced to a GPU-side
  zero-gravity seepage issue: the vertical coordinate head contribution was
  still active when gravity was zero. The GPU kernel now only adds this head
  term when the gravity vector is non-zero.
- The 3 s GPU run after the GPU correction completed, used zero gravity,
  `HydroMechTopLoadMode="TopStripVertical"`, `HydraulicConductivity=0.001`,
  `TimeOut=0.05`, and `PeriodicActive="None"`.
- That 3 s exploratory run was very expensive, about 5386 s total runtime for
  3 s physical time, or about 1795 s runtime per physical second.
- The Lian result remained unsuitable as the main verification target because
  the case depends strongly on boundary-condition details, strip-footing drainage
  interpretation, and dynamic boundary response. It should not be treated as a
  validated benchmark result.

## Boundary Decision

Keep side and bottom support as mDBC with slip mode for any future restart of
this case. Periodic boundaries should not be used for the strip-footing case,
because they periodically repeat a local load and change the diffusion domain.
