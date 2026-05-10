# CPU Pre-GPU Freeze Plan for the u-pw PR Prototype

This document defines the CPU-side work that should be frozen before starting GPU Phase G1. The GPU port plan already exists in `gpu_port_plan.md`; this note decides which CPU features must be completed, designed, deferred, or explicitly excluded before CUDA implementation starts.

Scope:

- Target formulation: u-pw PR only.
- PPE remains unsupported.
- CPU remains the reference implementation for hydromechanical behavior.
- GPU coding should start only after the CPU data model and production operator choices are stable.

## 1. CPU Features to Complete Before GPU G1

Priority order:

| Priority | Feature | Required before GPU G1? | Reason |
|---:|---|---|---|
| 1 | Remove or freeze failed diagnostics, especially `PorePressureAccelSymCorr` | Yes | It should not be ported. Keeping it in the active data model risks wasting GPU arrays, sorting, duplicate logic, and output bandwidth. |
| 2 | Mark or remove deprecated source-level `TopLoad*` path | Preferably yes | Formal external-load cases should use native `accinput`. GPU should not inherit a deprecated CPU-only load path unless there is a clear production use. |
| 3 | Decide Scenario 1 route: `BodyGravityStopTime` vs restart workflow | Yes for self-weight reproduction; at least design before GPU | Supporting Information Scenario 1 needs gravity-on generation followed by gravity-off dissipation. This affects time-dependent body force behavior or restart expectations. |
| 4 | PorePress restart | Yes before GPU restart design; can be implemented before or shortly after G1 if G1 is output-only | Restarting generated pore pressure is central for staged self-weight and external-load workflows. If omitted from the CPU baseline, GPU restart design will be incomplete. |
| 5 | Boundary pore-pressure ghost / MLS design | Design before G1; implementation before strict Cryer/Terzaghi GPU parity | Boundary treatment can introduce new arrays, kernels, reductions, and output diagnostics. Even if not implemented immediately, the chosen design should be known before GPU memory layout is frozen. |
| 6 | Corrected-gradient PR operator decision | Design before G1; implementation can be staged | The paper uses corrected gradients. If production PR operators will use correction matrices, GPU needs matrix storage or per-step matrix kernels. Do not start GPU PR kernels if the CPU operator is about to change globally. |
| 7 | Lateral no-flux | Can defer, but design should be noted | 1D current case avoids this via periodic lateral direction. Cryer, triaxial, and slope cases will need a non-periodic no-flux strategy. |
| 8 | MCC / softening / sensitive clay | No | These are constitutive/case-specific model layers. They should not block the PR core GPU port. |

Recommended immediate CPU freeze stance:

1. Keep `PorePressureAccelDiff` as the production feedback operator.
2. Keep `PorePressureAccel` only as an optional symmetric compatibility diagnostic.
3. Remove or freeze out `PorePressureAccelSymCorr` before GPU code starts.
4. Do not port source-level `TopLoad*`; use `accinput` for external-load cases.
5. Decide whether Scenario 1 will use restart or `BodyGravityStopTime` before coding GPU arrays.

## 2. Features That Affect GPU Array / Kernel Design

These features can change GPU memory, sorting, duplicate, reductions, or kernel signatures. They should be implemented or at least designed before GPU coding begins.

### Pore Pressure State and Restart

Affected GPU design:

- `PorePressg` type and precision.
- output fields and BI4 field naming.
- restart loader/copy path.
- sorting and periodic duplicate logic for `double` pore pressure.

CPU freeze need:

- confirm `PorePress` remains double;
- define whether restart restores total `PorePress`, excess pressure, or both through derived hydrostatic baseline;
- decide restart missing-field behavior.

### Boundary Pore-Pressure Ghost / MLS

Affected GPU design:

- possible boundary pore-pressure array;
- ghost/extrapolated pressure values;
- neighbor interactions involving material-boundary pairs;
- mDBC-compatible reconstruction state;
- additional reduction or matrix data if MLS is used.

CPU freeze need:

- decide whether ghost values are generated on the fly or stored;
- decide whether top drained and no-flux are layer corrections, ghost kernels, or hybrid corrections;
- define CPU reference metrics for boundary behavior.

### Corrected-Gradient PR Operators

Affected GPU design:

- per-particle correction matrix, likely 2x2 for 2D or 3x3 for 3D;
- matrix build kernel;
- matrix inverse/fallback handling;
- corrected `DivVel`, `LapPorePress`, and `LapZ` kernels;
- sorting/duplicate for correction matrices if persistent.

CPU freeze need:

- decide whether corrected gradients become production PR operators or remain diagnostics;
- define fallback policy for singular matrices;
- verify pressure-only and self-weight parity on CPU first.

### Feedback Operator

Affected GPU design:

- `PorePressureAccelDiff` is currently the production feedback operator.
- `PorePressureAccelSymCorr` should not be ported.
- symmetric `PorePressureAccel` can remain CPU-only unless operator-0 GPU compatibility is required.

CPU freeze need:

- keep `PorePressureFeedbackOperator=1` as recommended production mode for self-weight/Terzaghi-style cases;
- preserve `PorePressureFeedbackMode=1` for excess-pressure feedback.

### Shepard Regularization

Affected GPU design:

- temporary pressure buffer;
- material-material neighbor pass;
- possible excess-mode hydrostatic reconstruction;
- interval logic based on timestep counter;
- ordering relative to hydraulic boundaries.

CPU freeze need:

- keep ordering fixed:
  `PorePress update -> Shepard -> top drained -> bottom no-flux`;
- keep mode 1 as recommended for self-weight/Terzaghi-style cases.

### Hydromech Damping

Affected GPU design:

- acceleration addition before `AceMax` / timestep update;
- effective damping coefficient calculated from either `HydromechDampingCoef` or `HydromechDampingXi`.

CPU freeze need:

- keep `HydromechDampingXi` as the paper-compatible input;
- keep `HydromechDampingCoef` as direct low-level input.

## 3. Features That Can Be Added After GPU G1-G4

These should not block the first pressure-only GPU parity path.

| Feature | Earliest safe phase | Reason |
|---|---|---|
| PorePress restart | After G1 if G1 is passive output-only; before GPU staged Scenario 1 | Restart is not needed for initial pressure-only GPU array/output parity. |
| BodyGravityStopTime | After G1 if not used in pressure-only parity; before Scenario 1 | It affects mechanics, not passive pore-pressure output. |
| Boundary ghost / MLS implementation | After G4 if current layer corrections are kept for initial parity | Pressure-only 1D parity can use existing top/bottom layer corrections first. |
| Corrected-gradient PR production operators | After G4 if current CPU operators remain the baseline | Do not mix GPU porting with operator replacement unless CPU corrected operators are already validated. |
| Lateral no-flux | After G4 | Current 1D pressure-only case uses periodic lateral direction. |
| GPU pore-pressure restart | After G4/G5 | Needs stable output and update path first. |
| Full diagnostic reduction logging | After core kernels | Useful but not required for parity. |

## 4. Case-Specific Constitutive Features That Should Not Block PR Core GPU Port

These features are important for later paper cases, but they are not part of the hydromechanical PR core arrays and should not delay G1-G4.

| Feature | Needed for | Should block PR core GPU? | Notes |
|---|---|---|---|
| Modified Cam Clay | strict undrained triaxial reproduction if paper uses MCC | No | Implement as a separate constitutive-model phase. Current DP can remain an approximate smoke-test path. |
| Sensitive clay / strain softening | retrogressive slope and Sainte-Monique | No | Required for landslide realism, but not for 1D pressure diffusion or self-weight core validation. |
| Remolding / destructuration parameters | sensitive clay field cases | No | Should follow material model design, not PR core GPU memory design. |
| Production loading plate / traction boundary | external-load Terzaghi and triaxial | No for PR core; yes for strict external-load reproduction | Native `accinput` remains the experimental path for now. |

## 5. Recommended CPU Pre-GPU Milestones

### CPU-F1: Freeze Production Parameter and Output Surface

Goal:

- Confirm the formal parameter set.
- Mark deprecated/debug-only fields.
- Decide which diagnostics remain in production output.

Minimum smoke standard:

- `PorePressureModel=1` existing 1D pressure-only case runs.
- `PorePressureModel=2` gives a hard error.
- `SavePorePressure=1` writes the intended production fields.
- `PorePressureAccelSymCorr` is either removed or clearly excluded from GPU planning.

Exit criteria:

- `u_pw_parameters.md` matches implementation.
- GPU plan lists only production arrays for G1-G4.

### CPU-F2: Body Gravity Switch / Scenario 1 Route

Goal:

- Choose and implement one Scenario 1 route:
  - `BodyGravityStopTime`, or
  - restart from undrained stage with body gravity off and hydraulic gravity retained.

Minimum smoke standard:

- Self-weight undrained stage generates positive pore pressure with expected sign.
- After gravity-off transition, no NaN and `excluded=0`.
- `PorePress` is preserved across the transition if restart is used.
- Hydraulic gravity remains active after body gravity is disabled.

Exit criteria:

- Scenario 1 short run exists and is documented.
- The selected route is reflected in GPU design notes.

### CPU-F3: PorePress Restart

Goal:

- Restore `PorePress` from output/restart files for staged hydromechanical cases.

Minimum smoke standard:

- restart initial `PorePress` matches source frame within output precision;
- `ExcessPorePress` matches derived hydrostatic baseline after restart;
- stress, density, velocity, and `PorePress` are mutually continuous;
- dry/hydro restart continuity is not degraded.

Exit criteria:

- restart missing-field warning/error policy is documented;
- GPU restart requirement is defined.

### CPU-F4: Boundary Ghost / MLS Design

Goal:

- Design the production pore-pressure boundary treatment before GPU boundary kernels are written.

Minimum smoke standard for a CPU prototype or design-only freeze:

- uniform excess, no drained boundary: no boundary-induced pressure feedback spike;
- top drained: top layer excess remains zero after activation;
- bottom no-flux: bottom gradient proxy remains bounded;
- pressure-only diffusion is not degraded.

Exit criteria:

- decide layer correction vs ghost/MLS vs hybrid;
- list any new arrays required by GPU.

### CPU-F5: Corrected-Gradient PR Diagnostic / Decision

Goal:

- Decide whether corrected gradients will be production PR operators or deferred research diagnostics.

Minimum smoke standard:

- hydrostatic consistency test:
  `LapPorePress/(rho_w*g_h) + LapZ` remains near zero in interior;
- pressure-only diffusion profile does not worsen;
- self-weight short run remains stable;
- fallback count for singular matrices is reported if correction is used.

Exit criteria:

- if corrected PR operators are adopted, CPU implementation becomes the new reference before GPU kernels are written;
- if deferred, GPU G1-G4 explicitly port the current uncorrected CPU PR operators.

### CPU-F6: Cleanup Failed Diagnostics and Deprecated Paths

Goal:

- Remove dead CPU arrays and avoid GPU porting failed experiments.

Minimum smoke standard:

- build succeeds;
- pressure-only baseline unchanged;
- self-weight Scenario 2 short run unchanged within tolerance;
- no formal XML depends on removed parameters or outputs.

Recommended cleanup:

- remove `PorePressureAceSymCorrc` and `PorePressureAccelSymCorr` output;
- deprecate or remove source-level `TopLoad*` after `accinput` templates are stable;
- keep `PorePressureAccelDiff` as production feedback diagnostic.

### CPU-F7: GPU G1 Start Gate

GPU coding can start when:

- the production CPU array set is frozen;
- the production feedback operator is fixed as difference-gradient for formal coupled tests;
- Scenario 1 route is decided;
- boundary ghost/MLS and corrected-gradient decisions are documented;
- failed diagnostics are not part of the GPU target;
- pressure-only and self-weight CPU regression cases are available.

## 6. GPU Coding Should Wait Until CPU-F Milestones Are Done

`gpu_port_plan.md` is complete as a planning document, but CUDA implementation should not start immediately. Starting G1 before CPU-F decisions are frozen would risk:

- porting arrays that are later removed;
- duplicating a deprecated `TopLoad` path;
- implementing boundary kernels that are replaced by ghost/MLS soon after;
- writing uncorrected PR kernels just before CPU adopts corrected operators;
- omitting `PorePress` restart or Scenario 1 requirements from the GPU data model.

Recommended gate:

```text
Complete CPU-F1 through CPU-F6, or explicitly defer a milestone with a written design decision,
then start GPU G1.
```

If project schedule requires earlier GPU work, the safest limited start is:

```text
G1 passive PorePress GPU array + output only
```

but only if `PorePress` precision, output field names, sorting, and duplicate requirements are already frozen.

## 7. Current Recommendation

Before GPU G1:

1. Finish CPU-F1 parameter/output freeze.
2. Implement or decide the Scenario 1 route: `BodyGravityStopTime` or restart-based gravity switch.
3. Add or define `PorePress` restart.
4. Decide boundary ghost/MLS direction.
5. Decide whether corrected-gradient PR operators are production or deferred.
6. Remove failed `PorePressureAccelSymCorr` diagnostic from the production target.
7. Keep MCC, sensitive clay, and retrogressive softening as later constitutive-model phases rather than PR core GPU blockers.

