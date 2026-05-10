# Current Pre-GPU Reproduction Work Status

Date: 2026-05-11

## Current Git State

Current HEAD at preflight:

```text
c5374e3 Add full CPU case completion report
```

`git status --short` shows no tracked source modifications from the current
work. It does show pre-existing untracked files outside this phase, including:

- several example input CSVs under `examples/`;
- `src/papers/u-p/a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf`;
- reference / auxiliary source trees such as `src/source_DualSPHysics+/` and
  untracked `src/source/*` reference files.

These untracked files are not removed or modified in this phase.

## Source Documents Checked

The following planning and notes files exist and were inspected by heading /
keyword scan for the current phase:

- `src/papers/u-p/u_pw_parameters.md`
- `src/papers/u-p/u_pw_sph_implementation_notes.md`
- `src/papers/u-p/supporting_information_implementation_notes.md`
- `src/papers/u-p/review_1d_consolidation_stability.md`
- `src/papers/u-p/gpu_port_plan.md`
- `src/papers/u-p/cpu_pre_gpu_freeze_plan.md`
- `src/papers/u-p/cpu_case_smoke_completion_plan.md`
- `src/papers/u-p/porepress_restart_plan.md`
- `src/papers/u-p/pore_pressure_boundary_ghost_plan.md`
- `src/papers/u-p/corrected_gradient_pr_operator_plan.md`
- `examples/u-pw/README_reproduction_plan.md`

## PDF Availability

The main paper PDF is present locally:

```text
src/papers/u-p/a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf
```

No separate Supporting Information PDF was found in `src/papers/u-p`; only the
markdown note `supporting_information_implementation_notes.md` exists.

No local PDF text extractor such as `pdftotext` or `mutool` was found. The
`python` command resolves to the Windows Store shim rather than a usable Python
runtime. Therefore this phase does not perform new PDF text extraction or OCR.
The audit will cite the existing markdown notes and explicitly flag any values
that are not present in those notes.

## Completed CPU Function Nodes

The CPU branch currently includes:

- PR pressure-only pore-pressure update path;
- double `PorePress` state;
- `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ` diagnostics;
- pore-pressure timestep restriction `dt_pore`;
- hydrostatic and analytical/uniform excess initialization;
- top drained and bottom no-flux layer corrections;
- hydraulic gravity separated from mechanical body gravity;
- excess-pressure feedback mode;
- difference-gradient feedback operator;
- `PorePressureShepard` regularization;
- `HydromechDampingXi`;
- `BodyGravityStopTime`;
- CPU `PorePress` restart;
- boundary ghost diagnostics, not production;
- corrected-gradient PR diagnostics, not production;
- source-side `TopLoad*` removed in favor of native `AccInput`;
- `PorePressureModel=2` hard error for unsupported PPE.

## Why GPU Is Still Blocked

The previous reduced smokes are useful execution checks, but they are not strict
paper reproductions. GPU coding remains blocked until the full paper case audit
and implementation backlog clarify which missing strict features are GPU-entry
blockers and which can be deferred.

Known strict gaps include:

- particle-consistent drained/no-flux pore-pressure boundaries;
- lateral and curved no-flux treatment for non-1D cases;
- strict Cryer geometry and center-pressure postprocessing;
- triaxial axial loading, confinement, and stress-path output;
- MCC or equivalent calibrated material model if required by the paper;
- sensitive clay / strain softening for retrogressive and field cases;
- field topography, material zoning, and calibration for Sainte-Monique.

## This Automation Plan

This round will:

1. audit all paper cases against the current implementation;
2. create a full CPU implementation backlog;
3. reclassify reduced smokes as reduced execution checks, not strict
   reproductions;
4. auto-select the next CPU milestone only after the audit/backlog is written;
5. avoid GPU coding entirely.

Explicitly forbidden in this round:

- no CUDA / GPU source changes;
- no `JSphGpu*` or `JCellDivGpu*` edits;
- no `.cu` edits;
- no long CPU parameter sweeps or long-duration runs;
- no deletion of formal XML/BAT/README/notes/scripts/results.
