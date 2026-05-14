# Global Development Timeline

This timeline compresses the u-pw branch into recoverable milestones. It is not
an exhaustive commit log; use git for exact diffs.

## Literature And Initial Direction

Key early work established the target u-pw formulation, PR pressure update,
feedback concepts, Cryer/1D/triaxial targets, and cleanup discipline.

Representative preserved materials:

- `papers/u-p/a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf`
- `papers/u-p/an_sph_framework_for_drained_and_undrained_loading.md`
- `papers/u-p/experimental_interface_registry.md`
- `papers/u-p/experimental_interface_cleanup_policy.md`

## Cryer Boundary Exploration

The Cryer route produced many drained curved-boundary prototypes:

- boundary-particle drained ghosts;
- MLS and shell flux corrections;
- corrected Laplacian modes;
- deprecated `CurvedDrainedBoundaryMode` variants.

Conclusion: useful for understanding boundary diffusion, but too broad and not
clean enough to carry forward as a production base.

## Triaxial DP Route

The DP feedback-off platen workflow reached the most usable triaxial reduced
route:

- explicit platen workflow;
- pairwise platen reaction diagnostics;
- high-strength and mild DP comparisons;
- reduced feedback-off validation package.

Conclusion: keep reports and postprocessing ideas. Do not keep all intermediate
XML variants as active examples.

## MCC Route

MCC progressed from Python/C++ single-point parity to CPU solver integration:

- parser/state/output skeleton;
- CPU stress-update branch;
- feedback-off platen MCC smokes;
- substepping/admissible return experiments;
- boundary-induced failure audits;
- smooth/fan-like layout feasibility.

Conclusion: CPU MCC is a working prototype, not clean validation. Boundary and
layout issues dominate. Keep the standalone material-point helper and final
caveated reports; archive most geometry variants.

## 1D Consolidation Route

The 1D route produced the strongest validation basis:

- L3c/L4 initial-pressure PR diffusion and boundary gate;
- CPU/GPU agreement for Level-1 diffusion/boundary validation;
- L5 feedback-on coupling gate with bounded pressure/velocity;
- L3b mechanical top-load prototype shown stable but not physically valid for
  strict Terzaghi loading generation.

Conclusion: this is the highest-value route to cherry-pick after rollback.

## Boundary And Time Integration

BND1 and TINT1/TINT2 clarified two important issues:

- generalized boundary operator mode `2` covers ordinary solid walls but fails
  feedback-on stability in 1D;
- end-step pore-pressure commit mode `1` is neutral and does not explain mode
  `2` instability.

Conclusion: do not promote mode `2` or time-integration mode `1`. Keep operator
`1` and L3c/L4/L5 gates as the reduced baseline unless a clean redesign is
planned.

## Interface Governance

INTF1 is the most important process milestone. It prevents repeating the same
mode-proliferation pattern:

- every new parameter must be categorized;
- failed experiments must be deprecated or deleted;
- no new mode family without cleanup;
- GPU status must be explicit.
