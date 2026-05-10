# Final CPU Before GPU Report

Date: 2026-05-11

This report closes the current "u-pw full CPU reproduction preparation" pass.
No GPU/CUDA files were modified. No long CPU runs were started.

## Commits Created In This Pass

| Commit | Purpose |
|---|---|
| `4200ecc` | Record current pre-GPU reproduction work status. |
| `495397d` | Audit u-pw paper cases against current implementation. |
| `85bf3ef` | Add full CPU implementation backlog for u-pw reproduction. |
| `8aed0ef` | Reclassify reduced smokes as incomplete strict reproduction. |
| `048faac` | Design production pore pressure boundary treatment. |
| `e42b8e6` | Design triaxial loading and confinement workflow. |
| `84b17fb` | Document constitutive model gaps for u-pw reproduction. |
| `2c896ac` | Document effective stress initialization strategy. |
| `4b9ebd6` | Update full CPU case smoke matrix. |

## Completed In This Pass

Documentation / planning:

- full paper case audit;
- full CPU implementation backlog;
- stricter reduced-smoke reclassification for 03-06;
- production pore-pressure boundary design;
- triaxial loading/confinement design;
- triaxial DP-vs-MCC constitutive gap;
- sensitive clay / strain-softening plan;
- effective-stress initialization plan;
- GPU port plan updated to show GPU coding is blocked.

Source code:

- no source files were modified in this pass.

Computations:

- no new long runs were executed;
- no new CPU smoke runs were executed in this pass.

## Completed CPU Features From Earlier Passes

- PR pressure-only baseline;
- `PorePress` double state and output;
- PR pressure-rate with compression-positive volumetric sign;
- `dt_pore`;
- top drained and bottom no-flux layer corrections;
- hydraulic gravity separated from mechanical body gravity;
- excess feedback mode;
- difference-gradient feedback operator;
- `PorePressureShepard`;
- `HydromechDampingXi`;
- material hydromech constants moved into `StSoilCte`;
- `PorePressureModel=2` hard error;
- `BodyGravityStopTime`;
- CPU `PorePress` restart;
- boundary ghost diagnostics only;
- corrected-gradient PR diagnostics only;
- failed `PorePressureAccelSymCorr` diagnostic removed;
- source-side `TopLoad*` removed in favor of native `AccInput`.

## Case Status Under Strict Reproduction Gate

| Case | Current status | Strict reproduction status |
|---|---|---|
| 01 1D consolidation / Terzaghi | Pressure-only baseline and historical diagnostics exist. | Pressure-only smoke is strong; strict coupled external-load Terzaghi still needs boundary/loading decisions and postprocessing. |
| 02 Self-weight Scenario 1 | Stage A/B restart workflow exists and has passed short smoke earlier. | Close to strict 1D smoke, but boundary treatment and SI comparison still need formalization. |
| 02 Self-weight Scenario 2 | Gravity-on workflow exists and historical long diagnostic exists. | Good reduced/1D line; strict reproduction still needs paper-compatible boundary and plotting lock. |
| 03 Cryer | Reduced PR smoke exists. | Not strict: missing paper geometry, drained curved boundary, boundary ghost/MLS, center-pressure postprocessing. |
| 04 Undrained triaxial | Reduced DP/u-pw AccInput smoke exists. | Not strict: missing axial control, confinement, validated `p'`-`q`, and DP-vs-MCC decision. |
| 05 Retrogressive slope | Reduced wedge smoke exists. | Not strict: missing sensitive clay / softening, initial state, production boundaries, GPU-scale run. |
| 06 Sainte-Monique | Reduced placeholder smoke and data README exist. | Not strict and data-blocked: missing field topography, zoning, calibration, initial state, GPU workflow. |

Reduced smoke is not strict reproduction complete.

## Deferred / Blocked Features

GPU-pre blockers under the user's full CPU gate:

- production pore-pressure boundary treatment decision and prototype;
- Cryer paper geometry, drained boundary, and center-pressure analysis;
- triaxial loading/confinement workflow and stress-path analysis;
- triaxial material decision: DP approximation vs MCC;
- sensitive clay / strain-softening decision for 05/06;
- field data inventory and initial-state workflow for Sainte-Monique.

Deferred large features:

- full MCC implementation;
- sensitive clay / remolding / destructuration implementation;
- production MLS boundary treatment for arbitrary geometry;
- production corrected-gradient PR operators;
- full field-scale GPU runs;
- long-time parameter sensitivity.

## Frozen / Excluded For Future GPU Planning

If GPU work is later allowed, the following are explicit exclusions from the
first passive G1 scope:

- no `PorePressureAccelSymCorr`;
- no source-side `TopLoad*`;
- no production simple ghost Laplacian from CPU-BG3;
- no production corrected-gradient PR operator from CPU-CG1;
- no PPE;
- no MCC / sensitive clay in PR core G1.

## GPU Readiness Decision

GPU G1 is **not allowed yet** under the user's current full CPU completion
standard.

The earlier reduced-smoke gate is superseded. The current branch is valuable and
well documented, but strict CPU preparation still has unresolved paper-case
blockers, especially Cryer boundary treatment and triaxial loading/confinement.

## Recommended Next Step

Do not start CUDA work.

The next practical CPU task should be one of:

1. BND-2a: planar mirror/Dirichlet boundary diagnostic prototype design and
   targeted short diagnostics;
2. CASE-1/CASE-2: extract exact Cryer and triaxial parameters from the paper PDF
   using a proper PDF text extraction workflow or manual review;
3. POST-2/POST-3: add Cryer center-pressure and triaxial stress-path scripts so
   strict smoke metrics are well defined before new physics is added.

## Dirty-State Note

At the time this report was written, `git status --short` still showed
pre-existing untracked reference/example files outside the current u-pw
documentation work, including legacy example CSV files, a main paper PDF, and
reference/source folders. They were intentionally not touched or committed.

## Post-Report Softening Update

After this report, a CPU-only reduced sensitive-clay softening path was added
for the retrogressive slope smoke workflow:

- `Softening` is now a soil material switch under
  `<execution><special><soils>`.
- The CPU Drucker-Prager stress update can use the paper-style exponential
  peak-to-residual strength law driven by `Kplastic`.
- Micro tests and the reduced 05 retrogressive slope softening smoke completed
  with `code=0`, `excluded=0`, and no NaN/Inf.

This removes the immediate reduced-smoke material plumbing gap for case 05. It
does not complete full strict retrogressive or Sainte-Monique reproduction:
calibrated initial states, field geometry, production boundary treatment,
longer GPU-scale runs, and possibly a fuller remolding/destructuration model
remain open.
