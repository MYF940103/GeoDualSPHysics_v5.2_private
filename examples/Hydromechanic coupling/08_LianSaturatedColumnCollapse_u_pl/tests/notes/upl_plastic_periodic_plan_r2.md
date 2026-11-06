# Bounded dynamic-plastic periodic candidate r2

Author-only, unapplied and unexecuted. Root reported material checkpoint `369e244dbea82b465e61e9d2e1d81e188476efca`. This r2 supersedes the source proposal in r1; both r1 files remain unchanged. Root identified two r1 defects before application: its base-class predicate referenced derived-only fields, and its initializer rejections would block supported elastic MaterialReturn=1 cases.

## Minimal source proposal

`upl_plastic_periodic_plan_r2.source.patch` changes only `src/source/JSph.h`, `JSph.cpp`, `JSphCpu.cpp` and `JSphGpu.cpp`. One protected method uses only fields actually declared in JSph: public HydroMech/HydroMechDynamicSeepage plus the narrow geometry, constant-material and disabled-option conditions. It does not reference DynamicPorePressure or PorosityFeedback, which belong to the derived classes. Their existing initialization checks and public-master setup remain authoritative.

There is **no initializer change or new blanket MaterialReturn rejection**. Every previously supported elastic kappa=0 configuration, including the accepted MaterialReturn=1 GPU elastic gravity-container startup, retains its existing admission and old kappa=0 branch. A false narrow predicate is not an error; it simply leaves the original elastic-only corrector gate in force. Softening/HG/SPR/container/free-seepage restrictions are not relaxed.

The narrow predicate matches MaterialReturn=1, public dynamic hydromechanics, no walls, XZ periodicity, zero gravity, constant conductivity model/Ck0, coh==coh_r with n_coh=0, dlt=0 and psiDecay=0, no HG/SPR/damping/viscosity/load/drainage/free-seepage. Existing independent validation still enforces fresh 2D DP_PS Symplectic, fixed phi, valid float material parameters, corrected gradients and supported rectangular periodic translations; it is not duplicated in this predicate.

CPU corrector evaluates the predicate once. For a native normal fluid with a kappa array, the matched branch accepts **only finite kappa>=0**; the unmatched branch retains the original literal `kappa!=0` rejection. The same J update and finite J>1-n0 check run in both branches. No kappa is reset, repaired or sanitized.

GPU passes NULL to the existing optional kplastic argument **only for corrector && narrow predicate**; predictor and all unmatched configurations retain Kplasticg. The existing kernel uses that pointer only in the corrector kappa=0 check, while independently retaining its full J finite/domain test. This waiver relies on the real preceding ConsistentDev Cor kernel and checked MaterialErrorg: the production wrapper checks the actual material status before calling ComputeSymplecticPorosity(true,dt). Its core rejects nonfinite/negative input kappa and nonfinite unsuccessful output before commit. A direct private call bypassing that material stage is not a validated plastic lifecycle. No CUDA kernel/API/array is added.

The patch contains no change to J/cache/material arithmetic, Pre old-kappa restoration, Cor kappa commit, pressure/position ordering, periodic sorting/copies or status handling. J remains total kinematics `Jdot=J*theta`, not a function of deviatoric plastic kappa. Existing J/n/rho/range/finite, strict positive-k decay-domain and current-step/DtMin guards remain.

## One proposed same-physics short pair

The r1 numerical prototype is retained; neither the input nor an owner is created here.

| Item | Proposal |
|---|---|
| Native geometry | 32x32 soil IDs0..1023, no boundary particles; dp=.04 m, h=float(.048), x/z cell centers (index+.5)*dp, y=0, XZ periods1.28 m |
| Initial fields | J=1, p=p0=0, effective stress=0, kappa=0, native rho cache=rho0; vx=float(sin(2*pi*z/1.28)) m/s, vy=vz=0 |
| Float material | E=20e6 Pa, nu=.33, rho0=2072.5, n0=.35, rhow=1000, Kw=1e9, coh=coh_r=5000, phi=25 degrees converted to original float radians; n_phi=n_coh=dlt=psiDecay=0, MaterialReturn=1 |
| Hydraulic/operators | k=float(2e-4), ConductivityModel0/Ck0, Wendland, corrected stress/pore gradients and pair divergence; HG/SPR/viscosity/damping/shifting/artificial stress/Shepard off |
| Boundaries | zero gravity; no walls/load/drainage/free-seepage; report actual FS2/3 counts, expected empty |
| Single time grid | dt=2^-19 s, DtMin=1e-8, CFL=.2, PoreDtSafety=.1; 128 updates, save completed[0,32,64,96,128], expected Step[0,31,63,95,127] |
| Actual runs | one fresh CPU1 and one fresh GPU from identical seed/input floats, e.g. upl_plastic_periodic_CPU_r1/GPU_r1; no old-control rerun or half chain |

Use the existing fluidvelocity/onlypos initializer with 32 row-filtered constant values to install these sine samples; do not add a production sine initializer or caller force override. Both backends consume the same precomputed float row table. Verify actual Part0, IDs and periodic owners. Derive volume from actual seed float MassFluid/RhopZero (expected mass float(3.316)); do not replace it with ideal dp squared.

Every existing necessary step/domain guard must pass in the actual runs; this plan does not certify dt admissibility. Do not clip, uplift DtMin or silently substitute another dt. Require finite nonnegative and nondecreasing native kappa plus actual nonzero kappa by the last save. If coverage or a numerical gate fails, retain that first result and report it without automatically raising amplitude, time or tolerance.

After real typed exits and Run counts, inspect the actual saved clocks/signed dt error, IDs and typed fields, J/n/V/rho/k/cache, material status and actual FS counts. Describe per-frame CPU/GPU p, xyz/v, total-stress, kappa and ledger RMS/max differences without new 5 Pa/bit-identity/energy-decay/convergence gates. Initial continuous theta is zero, but do not enforce later theta=0, J=1, p=0 or an analytic sinusoidal trajectory. The elastic-reference timestep screen remains a necessary screen, not a plastic coupled-spectrum proof.

Nonzero-kappa admission remains limited to this constant-strength, zero-dilation radial prototype. Existing elastic kappa0 scopes are preserved. Apex/Invalid/NonConverged failure handling remains mandatory; spatial softening, nonzero dilation, apex/cap flow, restart, plastic walls/gravity/HG/free surfaces and TPI remain held. No claim of continuum accuracy, spatial convergence, localization regularization or full plastic dissipation is made.

Root must review/apply before fresh authoritative default CPU Debug and GPU Debug builds and any separately authorized short runs. This authoring performed no live engine edit, build, target/solver/decoder, SHA or Git action and left all accepted programs/results protected.
