# CryerProblem_PR

## Returned four-ratio formal comparison (2026-11-02)

The returned nu=.10/.20/.45 `release_nu*_r1_out` datasets are compared with the
previously reviewed nu=.30 `symc_nu030_out`, not the June legacy or dp=.002 runs.
All four actual GPU runs ended normally on RTX A6000, with1065 saved states each
and fixed dt=2^-20s. No physical solver was rerun for this analysis.

Formal products are under `figures/formal_validation/`:

- [Four-ratio log-Tv pressure comparison](figures/formal_validation/cryer_formal_four_nu_r1_log.png):
  finite-Kw theory and simulation at the same fixed18 initial material IDs,
  initially r0/a=.05, with one color per Poisson ratio.
- [Separate paper-limit comparison](figures/formal_validation/cryer_formal_four_nu_r1_paper_limit_log.png):
  incompressible-water, exact-center r=0 reference. It is not the same reference
  as the finite-Kw material-point comparison.
- [Pressure error, radial contraction and stress](figures/formal_validation/cryer_formal_four_nu_r1_state.png).
- [All4260 saved-state rows](figures/formal_validation/cryer_formal_four_nu_r1_native.csv),
  [dense analytical curves](figures/formal_validation/cryer_formal_four_nu_r1_theory.csv),
  and [peak/late-state metrics](figures/formal_validation/cryer_formal_four_nu_r1_metrics.csv).

Against the finite-Kw fixed18 reference, the Mandel-window sampled peak results are:

| nu | Peak amplitude error | Peak-time error | Final SPH p / Pa | Final theory p / Pa |
| --- | ---: | ---: | ---: | ---: |
| .10 | -0.7748% | +6.3962% | 133.7581 | 138.6112 |
| .20 | -0.9764% | +5.7821% | 51.8886 | 54.1062 |
| .30 | -1.0343% | +3.9789% | 17.6430 | 18.0477 |
| .45 | -0.5431% | -0.4179% | 2.5701 | 2.5002 |

The final nonzero pressure,especially nu=.10,is not by itself a numerical floor:
the corresponding analytical pressure is also nonzero at Tv approximately1.
Peak amplitude agreement does not erase phase lag or the very early opening
transient,most visible for nu=.45. The plots retain that transient without filtering.

Time is tau=t-2^-7s from drainage opening; the saved state at t=tD remains pre-open.
Every nu uses its own legacy cv=H*k/(rho_w*9.81) for the plotted Tv, while the
finite-storage reference uses its own cv_eff with9.80665 and finite Kw/n.
No time, pressure, radius or volume is fitted. Nonpositive tau stays in the CSV
but cannot be shown on a logarithmic x axis. Native peaks use saved samples with
Tv>=.005 through the actual endpoint; continuous analytical peaks are searched
in the predeclared Tv=.005.. .5 interval, which contains all four reference peaks.
Neighbouring save times describe sampling resolution, not a confidence interval.

The three new runs have full-series native reductions. Nu=.30 reuses its sealed
1065-frame native tables; all four initial/final states were independently decoded,
and all37173 initial soil rows/35 fields match across the four groups. The nu=.30
historical EXE/DLL identity is still unproven. Its adopted `symplectic_dt_s` table
column denotes the actual fixed-step runtime/clock contract, not a newly decoded
all-frame SymplecticDtPre field. None of this grants full-cycle half-step or
general physical acceptance; residual peak and late-decay errors remain recorded.

Reproduce the final figures from the sealed compact tables with
`python -B support/plot_cryer_formal_four_nu_r1.py --plot` in a fresh output label
(the script refuses to overwrite retained figures). Native extraction is a separate
read-only action, not part of any formal solver BAT.

## Three additional Poisson ratios (2026-11-01)

The additional actual-state and shell-quadrature audits found no accepted low-cost
correction. Keep the nu=.30 r2 release below unchanged. The separate
[nu=.10/.20/.45 Windows/RTX A6000 ZIP](Cryer_release_nu010_020_045_r1_Windows_RTXA6000.zip)
contains the three new formal root XML/BAT pairs, common verified executables,
runtime dependencies and execution receipts. See
[server instructions](support/README_cryer_nu_release_r1.md).

| nu | Independent root XML | GPU BAT |
| --- | --- | --- |
| .10 | `CaseCryerProblem_PR_release_nu010_r1_Def.xml` | `xCaseCryerProblem_PR_release_nu010_r1_win64_GPU.bat` |
| .20 | `CaseCryerProblem_PR_release_nu020_r1_Def.xml` | `xCaseCryerProblem_PR_release_nu020_r1_win64_GPU.bat` |
| .45 | `CaseCryerProblem_PR_release_nu045_r1_Def.xml` | `xCaseCryerProblem_PR_release_nu045_r1_win64_GPU.bat` |

Each full run uses its own physical endpoint through legacy Tv approximately1
and DeltaTv=.001 saves, with the original ramp/hold/drain history. Local RTX3050
smokes actually completed128 steps/two native frames each; original safety and
all35 initial fields passed. This is not closed-equilibrium, peak, full-half or
A6000 physical acceptance. Run the matching `--smoke --unattended` on the target
server before separately starting its full BAT. No local full run was started.

The three negative-launch guards passed; output data were not overwritten.
See [new numerical review](tests/notes/cryer_actual_budget_review_r1.md) and
[release review](tests/notes/cryer_nu_release_review_r1.md).
If a later numerical correction is accepted, all four nu groups require a new
version; do not silently replace these inputs or the accepted nu=.30 baseline.

## Selected portable release r2 (2026-11-01)

The bounded audit is complete. The selected scheme retains G1 plus Darcy symC,
with the recorded approximately1% peak-amplitude limitation, not a new numerical fix.
Use [the Windows/RTX A6000 package](Cryer_release_r2_Windows_RTXA6000.zip),
[server instructions](support/README_cryer_release_r2.md), and the independent root entry
`xCaseCryerProblem_PR_release_r2_win64_GPU.bat` /
`CaseCryerProblem_PR_release_r2_Def.xml`.
The external ZIP checksum is `Cryer_release_r2_Windows_RTXA6000.zip.sha256`.

The15 ZIP entries were checked byte-for-byte. A fresh extracted local RTX3050
smoke actually ran128 steps and saved2 native frames; original safety passed,
and all35 fields at both frames match the retained server startup exactly.
Existing-output, unknown-argument and changed-payload launches were rejected.
This is portable startup validation, not A6000/full-cycle/independent-half acceptance.
See [delivery review](tests/notes/cryer_release_review_r2.md).

Default dt=2^-20s and963370 steps match the returned full run, unlike the old
r1 package's intended2^-21s. No new local full run was launched; existing full
results need not be rerun merely for packaging. If a separate server reproduction
is desired, smoke and full are independent fresh starts with actual execution
receipts. The BAT generates and solves only; analysis and particles follow after copy-back.
Old formal data and r1 payloads remain unchanged.

## Current review and root organization (2026-11-01)

The returned `CaseCryerProblem_PR_symc_nu030_out` full run has been reviewed:
its actual dt is2^-20s,963370 steps,endpoint0.9187412261962891s (drainage-relative
legacyTv about1). Its fixed18-material-point peak amplitude error is about-1.034%
and peak timing about+3.979% against the finite-Kw,finite-radius reference.
The old r1 package below specifies2^-21s; do not confuse its intended input
with the actual returned run or infer historical server executable identity.

See [accuracy and cost decision](tests/notes/cryer_accuracy_decision_r1.md)
and [updated delivery plan](../validation/poromech_next_r7.json).
The retained-state density/deformation audit is now complete; see
[state-budget review](tests/notes/cryer_state_budget_review_r1.md).
Center density stops changing in saved states while stress and deformation
continue, but these CSV observations do not prove the cause of the peak deficit.
No safe, local low-cost correction has been demonstrated. The selected delivery
baseline therefore retains G1 plus Darcy symC and records the remaining errors;
it is not a strict1% or full-field accuracy claim and does not change any guard.
The independent r2 formal root XML/BAT and Windows/NVIDIA package are now prepared
with the retained baseline and explicit limitations, as described above.
Existing r1 inputs/package/output are retained historical evidence, not silently
upgraded or a reason to rerun completed results.

Root organization is deliberately conservative:

- All original nine XMLs and ten BATs remain, plus the r2 pair and three new nu pairs
  (now thirteen XMLs and fourteen BATs); old Poisson plotting scripts still depend on
  root XML/output paths. Legacy BATs contain existing-output deletion menus:
  do not invoke them for retained results.
- All ten root output folders, formal figures/CSVs, refinement, videos and
  both historical ZIPs remain. `support.zip` contains two script versions that
  differ from current loose copies; it is not a disposable duplicate.
- Three loose June short-test logs are archived byte-for-byte under
  `tests/logs/legacy_afterfix_short_root_r1/`; their paths, hashes and restoration
  instructions are in [the cleanup record](tests/notes/cryer_root_cleanup_r1.json).
  This removes root clutter, not large data or disk usage.

The dated sections below describe their original stages. They are not the
current run's dt/step-count or a full physical-acceptance statement.

## Current server candidate: symC, nu=0.30 (2026-10-30)

Use the NEW independent entry `xCaseCryerProblem_PR_symc_nu030_win64_GPU.bat`
and `CaseCryerProblem_PR_symc_nu030_Def.xml`. The self-contained Windows/RTX A6000
package and copy-back instructions are described in [support/README_server.md](support/README_server.md).
Old root inputs, outputs and dated descriptions below are historical and are
preserved, not silently upgraded. Their5us/no-ramp settings and deletion menu
are NOT this new entry. The new BAT refuses existing output and never deletes it.

The explicit optional `PoreDarcySymmetricCorr` is now implemented on CPU/GPU;
its default is OFF. ON changes only soil-soil Darcy contractions to use the
average of the two endpoint correction matrices. Momentum/load, compression,
boundary pairs, precision and time integration are unchanged. The server input
opts in; accepted case02/Lian inputs keep their original default behavior.

All four fresh Release implementation paths (CPU/GPU, default OFF/explicit ON)
reproduced their respective retained controls at69 matched native states and
all35 columns, including dterror, with0ULP difference. Independent readback
rechecked all276 pairs/359091180 values. Both new Debug2frame smokes passed;
GPU memcheck reported0errors/0bytes leaked. This is implementation acceptance,
not a new full physical or universal-operator claim. See
`tests/logs/cryer_darcy_switch_native_review_r1.check.json`.

The prior isolated symC peak/half comparison reduced the fixed18-ID center
peak error from about-2.44% to-0.99%, and sampled peak-time error from+10.31%
to+3.92%, against the unchanged finite-Kw, finite-radius quasistatic reference.
Those metrics are from the retained peak window, not a completed server run.
The new full decay remains pending and must be reviewed after copy-back.

The input retains dp=.0025,k=1e-5,nu=.30,raw confinement,grad1,damping.00004,
float pore pressure/density and double stress/positions. Ramp ends at2^-8s;
drainage opens at tD=2^-7s. Use tau=t-tD, not ramp end, for drained theory.
The full target is legacy Tv=1:1926740 steps of2^-21s, actual endpoint
0.9187412261962890625s. Output retains the65 closed-history states through tD,
then nominal Delta legacy Tv=.001 anchored at tD (about1065 frames total).
Fixed-step quantization requires using actual saved times in comparisons.
The two special timeout rates are intentionally different, not duplicate settings.

No new local full solver is launched for this handoff. Run the portable smoke
on the server first, then launch the full BAT independently. Return the whole
output folder and manifest; plotting/particles conversion is deferred until
copy-back. Existing legacy postprocessors have different defaults and an
incompressible/point-center reference; do not apply them blindly to this run.

## Peak-window half review (2026-10-29)

The fresh GPU half step completed294912steps through actual time.0703125s.
All577 saved native safety checks and577 exact-time coarse/half pairs passed
the original5Pa pressure-RMS and.005mm maximum material-displacement bounds.
Their maxima were1.510594Pa and.001008167mm. The69-state same-dt/same-cadence
prefix retained all35 native columns, including dterror, at0ULP without exclusions.
Both runs passed the five closed-state equilibrium diagnostics at Parts61-64.

This is not physical/full-cycle acceptance. The half-step Mandel peak is
12136.129286Pa at tau=.04638671875s, only2.111545Pa above the retained coarse
peak, with no sampled peak-time change. The finite-storage quasistatic reference
at the fixed18-ID initial radius r/a=.05 is12439.175960Pa at tau=.04205180203s:
the remaining peak errors are about-2.4362percent and+10.3085percent.
Density still differs with dt; passing the pressure/displacement screens does
not establish convergence of every state variable or identify density as a cause.

Use tau=t-2^-7s from drainage opening. Part64 at tD is pre-open; do not align
to ramp end or to the first saved already-drained state. Retain startup peaks
separately from the Mandel peak. Existing preload and temporal tests do not
support a loading-clock or dt-only explanation for the remaining peak error.

Offline reviewed products (native outputs and old evidence are preserved):

- [Pressure/startup/half comparison](tests/figures/cryer_preload_peak_half_review_r1_pressure.png)
- [Stress, tracked-shell motion, density and load](tests/figures/cryer_preload_peak_half_review_r1_state.png)
- [577-row comparison data](tests/figures/cryer_preload_peak_half_review_r1.csv)
- Review: `tests/logs/cryer_preload_peak_half_review_r1.check.json` and `.visual.json`.

Next remains bounded spatial consistency diagnosis of mechanical force,
compression source and Darcy diffusion together. No formal long run or symC
candidate is admitted by this completion notice. No production/formal input,
canonical executable, source, integration logic or equation changed in this review.

## Active diagnosis (2026-10-27)

Lian100s is delegated to the user server; local verification now proceeds here,
then to case01 self-weight. Current CPU Debug startup completed200steps/1ms,
five native frames with37173soil IDs, no exclusions/plasticity and5153real
drained nodes at0Pa. See `tests/notes/cryer_start_review_r1.md`.

This is not theory/full-cycle acceptance. The root5us fixed step bypasses the
automatic pore-diffusion control (configured dtw about2.97877us); the mechanical
`dterror` statistic does not certify that limit. A bounded Release2.5/1.25us
startup comparison comes next. Root formal XML/BAT and old results are unchanged;
do not run their existing-output deletion menu for retained data. Load-only
matrix correction was rejected by the frozen constant-stress balance audit;
static-plane SPR and 2D HG are not applied to this3D sphere.

The June22 retained root run did NOT use5us throughout despite its configuration
label: two native checkpoints reconstruct an initial5us followed by about2.97877us
under the old mandatory diffusion clip. July03 commit8af9ed55 changed that behavior.
Use actual saved times, not FixedDt times step, and do not call an old/current
comparison a double-stress-only experiment. See `tests/notes/cryer_dt_history_r1.md`.

The two bounded CPU Release startup runs (2.5/1.25us,0.5ms) also completed:
all per-run safety checks passed, but the predeclared5Pa pressure-RMS screen
did not (maximum56.380737Pa; maximum displacement difference3.03213e-6mm).
This is not solver failure or a full analytical comparison. The reviewed
history/radial PNGs and matching compact CSVs use prefix
`tests/figures/cryer_dt_short_review_r1_`; their visual receipt is
`tests/logs/cryer_dt_short_review_r1.visual.json`. No longer run is admitted
by this short screen. Next diagnose the abrupt inertial startup and temporal
sensitivity separately from the original pressure/stress-derivative spatial
consistency; do not silently relax the5Pa screen, change loading, or call
the old/new comparison a precision-only test.

This case validates the u-pw pore-pressure-rate formulation on Cryer's problem: a saturated poroelastic sphere with a drained exterior surface and a uniform inward normal pressure.

The active verification path uses `HydroMechInitMode=0` (`None`), `HydroMechTopLoadMode=2` (`FlexibleConfinement`) for the sustained confining pressure, and `HydroMechDrainage=1` to drain tracked exterior free-surface particles. The direct uniform pore-pressure initialization path is not used because it was not paired with a consistent 3D effective-stress and displacement initialization.

The formal release case is now a one-stage drained calculation. The older undrained-then-drained restart path was abandoned for the release configuration. The case applies `FlexibleConfinement` from `t=0`, keeps the exterior free surface drained from `t=0`, and compares the center pore-pressure history directly against Cryer's analytical sequence.

The retained validation record for the selected release settings is `refinement/notes/k1e5_dp0025_full_20260622.md`. The formal XML uses:

- `dp=0.0025`
- `k=1e-5 m/s`
- `HydroMechTopLoadMode=2` (`FlexibleConfinement`)
- `HydroMechTopLoadRampTime=0`
- `HydroMechDrainage=1`
- `HydroMechDrainageStartTime=0`
- `TimeMax=0.910928571429 s`, corresponding to `T_v=1`
- `TimeOut=0.000910928571429 s`, corresponding to `Delta T_v=0.001`

The first nonzero output is therefore `T_v=0.001`. Earlier values are not retained in the formal run because the high-resolution refinement tests showed strong startup oscillation below this range.

The current batch files run GenCase, the solver, and PartVTK only. They do not
run the Python analytical postprocessor or set `CRYER_TV_MIN`. Analytical
comparisons should exclude the saved `t=0` state explicitly, using
`CRYER_TV_MIN=0.001` for this default case. Before running
`support/postprocess_cryer.py`, set its `CRYER_*` inputs to match the selected
run: its legacy defaults (`dp=0.01`, `k=1e-3`) do not match the formal XML.

Run on Windows GPU release:

```bat
xCaseCryerProblem_PR_win64_GPU.bat
```

## High-resolution closed-ramp Poisson sweep

An additional high-resolution release-candidate sweep is prepared for the four
Poisson-ratio groups. These files keep the same `k=1e-5` and damping settings
as the retained validation runs, but use:

- `dp=0.002`
- `HydroMechTopLoadRampTime=0.0025 s`
- `HydroMechDrainage=1`
- `HydroMechDrainageStartTime=0.0025 s`
- postprocess time origin `CRYER_TL=0.0025 s`
- center sampling radius `r <= 1dp = 0.002 m`

The solver `TimeMax` in each XML/batch is `0.0025 s + T_v=1` for that
Poisson ratio. `TimeOut` remains `Delta T_v=0.001`.

Run the four GPU batches:

```bat
xCaseCryerProblem_PR_dp002_rampclosed_nu010_win64_GPU.bat
xCaseCryerProblem_PR_dp002_rampclosed_nu020_win64_GPU.bat
xCaseCryerProblem_PR_dp002_rampclosed_nu030_win64_GPU.bat
xCaseCryerProblem_PR_dp002_rampclosed_nu045_win64_GPU.bat
```

## Output locations and retained records

The default CPU/GPU entry points both target `CaseCryerProblem_PR_out`.
The Poisson-ratio and closed-ramp entry points use their own case-named
`*_out` directories. The default output layout is:

- `CaseCryerProblem_PR_out/data`
- `CaseCryerProblem_PR_out/particles`
- `CaseCryerProblem_PR_out/figures` (existing per-run analysis, not generated by the current BAT)

Retained formal comparison plots and their compact numerical tables are under
`figures/formal_validation/`. Parameter comparisons and load diagnostics are
under `figures/parameter_tests/` and `figures/diagnostics/` respectively.

The PartVTK commands in the default CPU/GPU batch files request:

```text
+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace
```

Open `CaseCryerProblem_PR_out/particles/PartFluid_*.vtk` in ParaView and inspect `FSType`, `FSNormal`, `PorePress`, and `HydroMechLoadAce`.

The Python postprocessor writes PNG/CSV and, when configured, JSON summaries
to the selected `CRYER_FIGDIR`; these are a separate step from PartVTK.

The geometry includes a tiny fixed boundary block far outside the kernel support of the sphere. It is only a solver guard for code paths that expect at least one boundary particle and does not interact with the poroelastic sphere.

Exploratory tests are documented under `refinement/notes/` and `tests/notes/`.
Their input, log, and result directories still exist; the presence of a
conclusion note does not mean the corresponding data have been deleted or
that the run passed every accuracy check. The older two-stage records are
historical, not the current default entry point.

Preserve the formal runs, the comparison inputs and summaries, and their
native BI4 data during file organization. Moving `refinement` or `support`
also requires checking the paths used by the existing scripts. A successful
solver exit is not evidence that the remaining peak/late-time errors have
been resolved. When an output directory already exists, BAT option 1 deletes
it; do not use that option for retained results.
