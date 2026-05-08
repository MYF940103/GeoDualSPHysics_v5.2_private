# Review: 1D consolidation stability for the GeoDualSPHysics u-pw PR prototype

Date: 2026-05-08

This review is based on the implementation notes currently available in
`src/papers/u-p`. No PDF files were present in that folder during this review,
so the comparison below relies on the markdown notes and the formulas already
transcribed there.

## 1. Executive conclusion

The current GeoDualSPHysics CPU prototype has already passed the pressure-only
hydraulic sanity check:

- double-precision `PorePress`;
- full saturated PR rate,
  `dp/dt = Kw/n [ div(vs) + k/(rho_w g) lap(p) + k lap(z) ]`;
- `dt_pore`;
- top drained and bottom no-flux layer corrections;
- pressure-only 1D diffusion benchmark;
- excess-pressure feedback mode;
- difference-gradient feedback operator.

The remaining instability in coupled Terzaghi-style loading is therefore most
likely not caused by the pressure diffusion operator alone. The literature notes
point to four higher-priority missing ingredients:

1. kinematic damping / dynamic relaxation for coupled loading;
2. boundary pore-pressure ghost or MLS extrapolation, especially for drained and
   no-flux boundaries;
3. an effective-stress-consistent two-stage initial/loading procedure;
4. a less impulsive loading mechanism, ideally traction/plate-like rather than
   direct acceleration of top material particles.

Continuing to tune only `TopLoadRampEnd` or `q0` is unlikely to be the best next
step.

## 2. Literature comparison table

| Work / notes | Formulation | SPH type | Pore-pressure solve | Feedback to mechanics | Effective stress | Terzaghi / consolidation? | Main relevance |
|---|---|---|---|---|---|---|---|
| Bui & Fukagawa 2009 | single-layer soil-water coupled SPH | WCSPH-like explicit SPH | explicit pressure-rate | yes, pressure-difference term | Drucker-Prager effective stress | soil-water coupled prototype; not the most detailed Terzaghi recipe in notes | early PR-like update; pressure-difference feedback avoids constant-pressure force |
| Bui 2011 | elastoplastic saturated slope SPH | explicit SPH | prescribed pore pressure in slope context | yes, pressure-difference term | effective stress | no primary 1D consolidation focus | confirms difference form `p_j - p_i` for pore pressure feedback |
| Bui & Fukagawa 2013 | hydrostatic pore-water pressure | explicit SPH | hydrostatic `p_w`; no seepage evolution | yes, improved pressure-difference term | effective stress | no Terzaghi PR diffusion | shows standard gradient is unstable near surfaces; recommends damping for initial stress |
| Blanc & Pastor 2012 | mixed stress-velocity-pore pressure | fractional step / Taylor SPH | pressure correction / FS | yes | effective stress | coupled geomechanics benchmarks | major solver redesign; useful for stabilization concept, not a small patch |
| Morikawa & Asai 2022 | one-point two-phase u-w-p | ISPH | PPE / projection | yes | effective stress | saturated benchmarks likely, but requires PPE | robust strong coupling via pressure solve and implicit Darcy drag |
| Lian et al. 2023 | single-layer u-pl | SPH with TPI | pressure evolution with TPI | yes | Terzaghi effective stress | yes: consolidation validation | TPI reduces water-bulk-modulus time-step stiffness; negative pressure stabilization |
| Lian et al. 2021 | seepage in unsaturated porous media | single-layer seepage SPH | head diffusion | deformation coupling not primary | not primary | seepage benchmark, not Terzaghi mechanics | better diffusion operators and seepage boundary treatment |
| Lian et al. 2024 | unsaturated three-phase | single-layer coupled SPH | pressure/saturation evolution, adaptive two-timescale | yes | suction-dependent | rainfall/slope, not first Terzaghi target | two-timescale coupling and suction stability risks |
| u-pw PR/PPE target paper | u-pw; PPE and PR variants | single-layer / one-point SPH | PR explicit or PPE projection | yes | effective stress | yes: 1D Terzaghi consolidation | main target; reports need for artificial viscosity + kinematic damping |

## 3. 1D consolidation parameters from the u-pw notes

The target u-pw notes list the 1D Terzaghi setup as:

| Parameter | Value |
|---|---:|
| Column height `H` | `1.0 m` |
| Width | `0.1 m` |
| Particle spacing `Delta` | `0.01 m` |
| Young's modulus `E` | `2e6 Pa` |
| Poisson ratio `nu` | `0.3` |
| Water bulk modulus `Kw` | `2e8 Pa` |
| Porosity `n` | `0.3` |
| Hydraulic conductivity `k` | `1e-3 m/s` |
| Time step | `1e-6 s` |
| Top hydraulic BC | drained / zero pore pressure |
| Bottom and lateral hydraulic BC | undrained / no-flux |
| Load | `q0 = -10 kPa` at top |

The analytical solution in the notes is the classic one-dimensional Terzaghi
series:

```text
p_w(z,t) = sum_j [2 p0 / M] sin(M z / H) exp(-M^2 Tv)
M = 0.5 (2j - 1) pi
Tv = c_v t / H^2
c_v = k (1-nu) E / ((1+nu)(1-2nu) rho_w g)
```

This analytical comparison assumes a well-defined 1D consolidation problem:
uniform initial excess pore pressure or load-generated excess pressure, drained
top, no-flux bottom/lateral, and mechanically consistent loading.

## 4. Loading methods in the notes

| Work | Loading method found in notes | Implication for current code |
|---|---|---|
| u-pw target paper | `q0=-10 kPa` applied at top | Notes do not specify a simple acceleration-on-particles trick. Treat this as a traction/load boundary, not necessarily body force. |
| Bui 2009 / Bui 2011 | geotechnical effective-stress SPH, loads mostly through gravity, boundary stress, slope configuration | Supports pressure feedback, but not our current top-layer acceleration method. |
| Bui & Fukagawa 2013 | gravity loading with damping for initial stress; hydrostatic pore pressure | Strong hint that initial stress and damping stages matter. |
| Blanc & Pastor 2012 | fractional-step coupled solve | Loading handled inside a different stabilized mixed formulation. |
| Lian 2023 u-pl | consolidation validation with stabilized pressure integration | Suggests top load should be part of a stabilized coupled setup, not an impulsive local acceleration. |

Current GeoDualSPHysics experiments used two approximations:

1. source-side `TopLoad`: acceleration applied to top material layer;
2. DualSPHysics `AccInput`: native external acceleration on `mkfluid=1`.

The AccInput isolation result showed that even `q0=-1 Pa` can produce coupled
growth once PR feedback participates. Therefore the load application may not be
the only issue. However, neither approach is a true traction boundary or loading
plate.

## 5. Initial-condition handling in the notes

| Theme | Literature signal | Current status |
|---|---|---|
| Effective stress | u-pw/u-pl formulations use effective stress and Terzaghi relation | `Sigmac` is treated as effective stress; feedback is added separately. |
| Hydrostatic baseline | Bui 2013 and current u-pw notes distinguish hydrostatic pressure/elevation | Implemented with `HydraulicGravity` and `ExcessPorePress`. |
| Static equilibrium | Bui 2013 uses damping during initial stress generation | Current coupled tests start from geometry/relaxed dry states or hydrostatic pressure, but not a saturated effective-stress equilibrium generated with damping. |
| Body gravity | Terzaghi-style case may set body gravity to zero while retaining hydraulic `g` | Implemented via `HydraulicGravity`. Need nonzero `speedsound` in XML. |
| Excess pressure | Terzaghi comparison can use uniform initial excess pressure, or loading-generated excess pressure | Uniform profile implemented. Coupled loading-generated excess remains unstable. |
| Undrained loading stage | User's proposed two-stage route is physically sensible, but notes do not show that an explicit undamped acceleration load is stable | Needs damping/quasi-static control. |

## 6. Boundary-condition handling in the notes

| Boundary issue | Literature treatment | Current prototype |
|---|---|---|
| top drained | impose pore pressure Dirichlet, free surface zero pore pressure | layer correction: excess pressure set to zero in top layer |
| bottom no-flux | impose zero normal pressure gradient | minimal layer correction using reference-layer mean excess |
| lateral no-flux | undrained lateral boundaries | current 1D case uses x-periodic, so lateral no-flux is avoided |
| boundary particles carrying `p_w` | u-pw notes: dummy/boundary particles and MLS extrapolation for pore pressure | not implemented |
| ghost / mirror | Bui 2013 and u-pw notes imply boundary `p_w` needs reconstruction | not implemented |
| corrected gradient | u-pw operators use corrected gradient | only diagnostic `PorePressureAccelSymCorr`; not used in PR operators |
| constant pressure feedback | Bui 2009/2011/2013 use pressure-difference feedback to avoid constant-pressure spurious force | implemented as `PorePressureFeedbackOperator=1` |

The boundary gap is still significant. The pressure-only benchmark can pass with
layer corrections, but coupled feedback and Terzaghi loading are more sensitive
to boundary consistency.

## 7. Stabilization methods reported in the notes

| Stabilization | Where it appears | Meaning for current prototype |
|---|---|---|
| artificial viscosity | u-pw target paper compares it in 1D consolidation | May stabilize, but can distort consolidation response. Needs isolated tuning. |
| kinematic damping | u-pw target paper says it improves 1D consolidation; useful magnitude roughly 10-50 times `dt` in the tested setup | Highest-priority next experiment. Current coupled tests did not include a targeted kinematic damping stage. |
| damping for initial stress | Bui & Fukagawa 2013 | Needed to build static/saturated equilibrium before coupled analysis. |
| TPI | Lian 2023 u-pl | Reduces explicit pressure stiffness caused by `Kw`; future path if PR remains stiff. |
| PPE / projection | Morikawa & Asai 2022, Blanc & Pastor 2012 | More stable for incompressibility but requires global solver and robust pressure BCs. Not the current PR-only target. |
| adaptive/two-timescale | Lian 2024 | Useful long-term, especially for seepage/unsaturated coupling. |
| corrected gradient | u-pw target paper, Blanc & Pastor | Important for operator consistency, but our symmetric corrected feedback diagnostic did not remove constant-pressure boundary fake force. |
| boundary ghost / MLS | u-pw target paper | Likely needed before strict Terzaghi comparison. |
| small fixed dt | u-pw target paper uses `dt=1e-6 s` | Our `dt_pore` is even smaller for `k=1e-3`, but mechanical-feedback stiffness still appears. |

## 8. Similar instability signals in the notes

The notes do not quote the exact same failure mode, but they describe closely
related risks:

- the u-pw target paper explicitly states that stabilization is necessary in
  coupled 1D consolidation;
- artificial viscosity alone can stabilize but may introduce error;
- kinematic damping improves agreement, while excessive damping overdamps;
- explicit pressure updates are tightly restricted by `Kw`, `n`, `k`, and `h`;
- boundary pressure treatment is critical;
- standard pore-pressure gradients can be unstable near submerged/free surfaces;
- PPE can also be unstable through `a*(k,dt)` if used carelessly.

Our observed failure has the signature of explicit strong coupling:

```text
small load -> small velocity perturbation
-> DivVel term in PR equation
-> large Kw/n * DivVel pore-pressure rate
-> feedback acceleration
-> larger velocity perturbation
```

This is exactly the loop that kinematic damping, implicit/TPI pressure updates,
or projection methods are meant to control.

## 9. Comparison with the current implementation

Current implementation:

- PR explicit update;
- `PorePressRate = Kw/n [DivVel + k/(rho_w g) LapPorePress + k LapZ]`;
- pressure-only diffusion passed;
- feedback uses excess pressure mode and difference-gradient operator;
- top drained and bottom no-flux layer corrections;
- hydraulic gravity separated from body gravity;
- source `TopLoad` and native `AccInput` both tested;
- coupled loading still unstable.

Most likely missing items, ranked:

| Rank | Candidate | Assessment |
|---:|---|---|
| 1 | A. damping / dynamic relaxation | Strongest literature signal. u-pw notes explicitly say coupled 1D consolidation needs artificial viscosity + kinematic damping. |
| 2 | E. effective-stress-consistent initialization | Current dry/hydrostatic/excess states are not a fully saturated static equilibrium under load. |
| 3 | C. boundary pore-pressure ghost / MLS | Required by u-pw notes for pressure BCs; layer corrections are only first-order hacks. |
| 4 | F. time-step / substepping | `dt_pore` alone does not stabilize the mechanical-pressure feedback loop. May need pressure/mechanics subcycling or smaller coupled dt. |
| 5 | B. top load method | AccInput reduced ambiguity but did not solve instability. A true traction plate may still be needed for strict Terzaghi. |
| 6 | G. water bulk modulus / compressibility | `Kw=2e8` makes `Kw/n` very stiff. Literature alternatives include TPI or lower-compressibility test cases. |
| 7 | D. implicit / semi-implicit coupling | Strong future solution; Lian 2023 TPI and PPE/FS methods point this way. |
| 8 | H. switch from PR to PPE | Not recommended now because the user's target is PR-only and PPE requires major infrastructure. |

## 10. Recommended next code experiments

### Experiment 1: targeted kinematic damping for coupled u-pw PR

Add a CPU-only damping option that can be enabled only for hydromechanical
coupled tests. Keep it separate from artificial viscosity and DensityDT.

Suggested minimal parameter set:

```xml
<parameter key="HydromechDamping" value="0" />
<parameter key="HydromechDampingCoeff" value="0" />
<parameter key="HydromechDampingStart" value="0" />
<parameter key="HydromechDampingEnd" value="0" />
```

First diagnostic:

- body gravity = 0;
- hydraulic gravity = `(0,0,-9.81)`;
- `PorePressureInit=1`;
- `PorePressureFeedback=1`;
- `PorePressureFeedbackMode=1`;
- `PorePressureFeedbackOperator=1`;
- no top drained during loading;
- very small AccInput load;
- sweep damping coefficient around the literature hint: order `10-50 * dt` in the paper's notation, but map carefully to the code's acceleration/velocity damping form.

Acceptance criterion:

- no excluded particles;
- `DivVel` remains bounded;
- excess pore pressure grows smoothly;
- damping can be switched off for pressure-only benchmarks.

### Experiment 2: static saturated equilibrium / dynamic relaxation stage

Before imposing Terzaghi load, generate a saturated equilibrium:

1. body gravity optional, hydraulic gravity active;
2. hydrostatic pore pressure;
3. feedback mode = excess or total depending on the intended equilibrium;
4. damping active;
5. run until velocities and `DivVel` are small;
6. restart from this state for loading.

This follows the Bui & Fukagawa 2013 message: generate initial stresses with
damping before the actual analysis.

### Experiment 3: boundary pore-pressure ghost treatment

Replace top/bottom layer corrections with particle-consistent boundary values:

- top drained: ghost/boundary `p_excess=0`;
- bottom/lateral no-flux: mirror/extrapolated `p_excess`;
- use MLS or mDBC-compatible extrapolation;
- include boundary values in Laplacian and feedback diagnostics.

This is probably required before a strict Terzaghi comparison.

### Experiment 4: lower-stiffness coupled toy problem

Before returning to `Kw=2e8`, test a deliberately softened system:

- lower `Kw`;
- smaller `q0`;
- longer ramp;
- damping on;
- compare qualitative response only.

This isolates whether the instability is the explicit `Kw/n * DivVel` loop.

### Experiment 5: future TPI / semi-implicit pressure update

If damping and boundary ghost treatment are insufficient, consider a PR-compatible
TPI-like pressure update inspired by Lian 2023 before considering PPE.

## 11. What not to do next

Do not immediately:

- keep extending the `q0` ladder;
- tune `TopLoadRampEnd` alone;
- switch to PPE;
- run long Terzaghi comparisons with the current coupled response;
- mix DensityDT, shifting, artificial viscosity, and damping all at once;
- treat layer-based top/bottom pore-pressure corrections as final boundary
  conditions.

## 12. Practical next step

The most defensible next source task is:

```text
Phase 4m: CPU-only hydromechanical kinematic damping / dynamic relaxation
```

with strict scope:

- no PR formula change;
- no feedback operator change;
- no stress update change;
- no GPU;
- damping is optional and off by default;
- output damping acceleration or velocity damping diagnostic.

Then rerun:

1. AccInput-only mechanical check;
2. hydromech PR feedback off;
3. feedback on with difference-gradient operator;
4. very small top load with damping sweep.

Only after a bounded coupled loading response should we return to strict
Terzaghi analytical comparison.
