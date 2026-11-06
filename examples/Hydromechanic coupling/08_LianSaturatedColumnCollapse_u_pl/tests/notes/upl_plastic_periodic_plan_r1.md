# Bounded dynamic-plastic periodic candidate r1

Status: author-only proposal, unapplied and unexecuted. Root reported the integrated material checkpoint as `369e244dbea82b465e61e9d2e1d81e188476efca`. This proposal does not change a live source, input, program or retained result.

## Proposed source change

The accompanying `upl_plastic_periodic_plan_r1.source.patch` targets only `src/source/JSph.h`, `JSph.cpp`, `JSphCpu.cpp` and `JSphGpu.cpp`. It adds one shared derived predicate and no public input, persistent member, material array, CUDA kernel, kernel parameter or constitutive formula.

The predicate requires MaterialReturn=1 with the public dynamic model, native J feedback, no walls, XZ rectangular periodicity, zero gravity, constant conductivity, constant cohesion, zero dilation and zero dilation decay, and no HG/SPR/damping/viscosity/load/drainage/free-seepage. Existing configuration validation still independently enforces fresh 2D DP_PS Symplectic, fixed friction angle, material domains, corrected gradients, supported kernel/period translations and all excluded options. Those checks are not copied into the new predicate or relaxed. Constant-strength here is explicit `coh==coh_r && n_coh==0`; `dlt==0 && psiDecay==0` makes the first plastic flow isochoric. The old StrainSoftening admission remains unchanged.

Both observer initializers reject MaterialReturn=1 outside this narrow dynamic scope. MaterialReturn=0 keeps its old condition and calculations; material-only mode with the J observer disabled still returns before the new dynamic admission check. Other dynamic material combinations are held, rather than being silently admitted by allowing any nonzero kappa.

CPU corrector computes the predicate once, then bypasses only its old native-normal `kappa!=0` rejection when true. GPU host passes NULL to the existing optional kplastic argument only in the same scope. The existing GPU kernel reads that pointer solely for its corrector elastic-only rejection; it still executes every finite-J and saturated-domain check. The actual ConsistentDev Pre/Cor core validates finite/nonnegative input kappa and finite successful output, and its caller checks failure status before the later J corrector. NULL is not a generic waiver for invalid kappa or a new alternate update path. The two failure messages are updated to describe the admitted scope.

No J expression, floating-point operation order, density-cache calculation, material return, Pre kappa restoration, Cor kappa commit, pressure/position ordering, periodic copy/sort, finite/range check, initial-state check or error mechanism is changed. J remains total kinematics: `Jdot=J*theta`. Deviatoric plastic kappa is not a porosity surrogate.

## One proposed same-physics short CPU/GPU pair

This is the next proposed experiment, not execution authorization and not a manufactured analytic trajectory.

| Item | Frozen proposal |
|---|---|
| Geometry | 32 x 32 native soil samples, no fixed/moving/floating samples; dp=.04 m, h=float(.048 m), rectangular XZ periods 1.28 m |
| Coordinates | x,z cell centers `(index+.5)*dp`, y=0; material IDs 0..1023 |
| Initial fields | J=1, p=p0=0, effective stress=0, kappa=0, native density cache=rho0 |
| Initial velocity | `vx=float(sin(2*pi*z/Lz))` m/s, vy=vz=0; amplitude 1 m/s, tangent varies smoothly along z |
| Material | E=float(20e6) Pa, nu=float(.33), rho0=float(2072.5), n0=float(.35), rhow=float(1000), Kw=float(1e9), coh=coh_r=float(5000), phi=float(25 degrees in radians), n_phi=n_coh=dlt=psiDecay=0, MaterialReturn=1 |
| Mobility | constant k=float(2e-4) m/s; ConductivityModel=0, Ck=0 |
| Operators | one retained Wendland selection, corrected stress/pore gradients and pair divergence; HG/SPR/artificial viscosity/damping/shifting/artificial stress/Shepard all off |
| Boundaries | XZ periodic; gravity=0, no walls, load, drainage or free-seepage; actual native FS2/3 count must be reported and expected empty |
| Time | one resolution only: dt=2^-19 s, DtMin=1e-8 s, CFLnumber=.2 and PoreDtSafety=.1 retained from the startup candidate; 128 updates; save completed [0,32,64,96,128], expected saved Step [0,31,63,95,127] |
| Execution | one fresh CPU1 run and one fresh GPU run from the identical initial float data; no old-control rerun or half-step chain |

The existing XML fluid-velocity initializer supports position-filtered operations, not a sine expression. A future test-only preparer can write 32 row-filtered constant velocities equal to the sine samples above, using the existing `fluidvelocity/onlypos` machinery. Thus all grid samples share one precomputed float table across CPU/GPU; no production initializer or caller force hook is needed. Inspect the actual resulting Part0 values and periodic ownership rather than assuming the intended profile was installed. This preparation is not authored by the present two-file proposal.

Use actual float mass from the seed (`float(rho0*dp*dp)`, expected float(3.316) for this 2D sampling), not an ideal-volume replacement in later ledgers. Match both backends' XML, seed, material fields, native IDs and saved clocks. A fresh output tag such as `upl_plastic_periodic_{CPU,GPU}_r1` should be reserved only by a later reviewed owner.

## Required observations and limits

1. Before each actual stage, all existing current-step and DtMin necessary acoustic/diffusive bounds, strict positive-k decay domain, J>1-n0, physical rho range/cache, finite fields and material failure checks must pass. This plan does not predeclare that the selected dt passes. No clipping, DtMin uplift or automatic replacement step is allowed.
2. Require actual nonzero native kappa by the final save, with finite/nonnegative and nondecreasing saved native kappa. Otherwise the plastic spatial coverage is not achieved; preserve that first result and report it rather than silently increasing velocity or time.
3. Seal actual typed exits and Run updates/counts; then inspect the actual native frames, all IDs and all available typed fields, signed dt error and scalar saved clocks. Ledger n/V/rho/k must use actual J and float material constants. Pressure, velocity, material displacement, effective/total stress, kappa and J remain visible for every native sample, including extrema.
4. Describe CPU/GPU per-frame RMS/max differences for p, xyz/v, total stress, kappa and J/n/rho/k. No new 5 Pa, bit-identity, energy-decay or convergence gate is introduced. Existing individual native/material/domain checks remain necessary.
5. At the initial continuous velocity field theta is zero, but subsequent momentum and plastic projection can change the motion. Do not impose later theta=0, J=1, p=0, uniform kappa, or an analytic sinusoidal trajectory. Do not equate the elastic reference-modulus timestep screen to a proof for the plastic coupled spectrum.
6. Preserve ApexNeeded/Invalid/NonConverged failure handling. This first constant-strength, zero-dilation radial case does not admit softening, nonzero dilation, apex/cap flow, restart, walls, gravity, HG, general free surfaces or TPI. It does not prove continuum accuracy, spatial convergence, localization regularization or complete plastic dissipation.

After root review/application, build the default CPU Debug and GPU Debug into new isolated closures; only then prepare and separately authorize the two short actual runs. No build, target, solver, decoder, old raw scan, SHA or Git action was performed to author this proposal. Existing Cryer/column/container/free-seepage results and programs remain protected.
