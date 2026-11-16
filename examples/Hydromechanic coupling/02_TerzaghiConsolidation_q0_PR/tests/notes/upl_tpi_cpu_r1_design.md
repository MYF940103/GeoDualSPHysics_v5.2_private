# P1 beta0 CPU author draft

2026-11-17, Asia/Tokyo. This is an unbuilt private implementation draft. It
does not install an algorithm, expose XML, qualify a benchmark, resume the
suspended C08 source or admit any solver. The prepare generator must be read and
independently admitted before use. Nothing in this note is physical acceptance.

## Files and scope

- `upl_tpi_cpu_r1.h`: reusable beta0 pressure prediction, ID-owned full-step
  history, row arithmetic, lifecycle checks and read-only elastic-HG adapter.
- `upl_tpi_cpu_r1_prepare.py`: prepare-only generator for two private CPU TUs,
  the final-A frozen headers/sources and a source-difference receipt.
- `tests/notes/upl_tpi_cpu_r1_design.md`: numerical contract, implementation
  boundaries and build needs. The helper/generator alone are in `tests/support`.

Only these three new author files are changed. No existing source, project,
XML/BAT, output, PRE, native record or old receipt is modified. There is no beta
implementation and no negative-pressure clipping. The helper has no C08
material, ID range, source step or time-step constant. Case02 fixture restrictions
are in the separate overlay qualification, not the helper.

## Exact base and build requirements

The A reference is the completed Case02 constant-k full2Tv run
`logs/upl_bigstep_2tv_CPU1_r1.run.json`, not a C08 schema2 program. Its actual
program is `outputs/upl_spr_av_ReleaseCPU_r1/DualSPHysics5.2CPU_win64.exe`;
its build is `logs/upl_spr_av_ReleaseCPU_r1.build.json` and the final flat
265-file snapshot is `outputs/upl_spr_av_ReleaseCPU_r1_source`.

The A build has 86 objects, including main. A private Release build must retain
84 and replace only `JSphCpu.obj` and `JSphCpuSingle.obj`; the C08 87/85 count
does not apply. Original Release objects are under
`src/VS/Intermediate/upl_spr_av_ReleaseCPU_r1`. Original CL/link recipes are the
two `logs/upl_spr_av_ReleaseCPU_r1_{CL,link}.command.tlog` files. No class layout
or original header changes are made, so the prototype must not mix a current
public/C08 class ABI with these objects.

The old Debug receipt points to its then-canonical program. An archived Debug
program/PDB survives in `outputs/upl_spr_av_base_r1`, but that folder's
`JSphCpu.cpp` is the pre-edit 266363-byte file, not final-A's 267740-byte file.
There is no matching retained Debug object closure here. Therefore Debug must
compile all 86 final-A sources independently using the authoritative Visual
Studio CPU project/DebugCPU recipe, into new OutDir/IntDir. Do not reuse Release
objects or silently substitute the current canonical program. The current
project's additional `JSphCpu_mdbc.cpp` is absent from final A and must not be
added to that old flat implementation. The separate build author records the
private target mapping and exact 86-source closure without editing the public
project. Default MSVC C++14 is sufficient for this helper.

Prepare writes a new `outputs/upl_tpi_cpu_r1_source` with the 265 final-A files
(only two TUs patched), plus the private header: 266 compile/source/header files.
`source_diff.json` is additional provenance, not a compilation unit. It also
writes `logs/upl_tpi_cpu_r1.prepare.json`. Existing destinations are rejected.
The root prepare-only admission freezes the exact author/base inputs by
path/size/mtime. Identity uncertainty is resolved by the root before admission;
the generator does not perform repeated SHA scans.

The generator accepts only `--execution-authorized --admission PATH`. Its root
admission schema is `stage="upl_tpi_cpu_r1.prepare_admission"`, `passed=true`,
`prepare_only=true`, `inputs=[{path,bytes,mtime_ns}, ...]`. All consumed three
author files, the A build/program/XML and 265 snapshots must appear. The prepare
receipt carries `source_root`, `base_build`, `base_program`, `base_xml`,
`base_source_entries`, `files` (266), `changed_sources` (2), `private_header`,
`source_diff`, `author_files` and zero builder/program/solver/native invocations.

## Three schemes and time levels

Environment `UPL_TPI_CPU_R1` is a private prototype selector. Missing, empty or
exact `A` leaves the original finite-Kw code path and allocates no history
vectors. Exact `B` selects alpha=.5; exact `C` selects alpha=0. Other values fail.
It is not a public XML parameter or an independently configurable alpha.

A uses the unchanged finite capacity `M=gamma*n/Kw` with the existing predictor
and corrector pressure-rate expressions. B/C are M0 approximations, not just
different integrators for that finite-M equation. Their own appropriate theory
and finite-Kw/M0 model differences remain separate acceptance questions.

For a complete-step material pressure `pn` and its genuine previous committed
complete-step pressure `previous`, both half-mechanical and endpoint guesses are

`q_half = q_guess = pn + alpha*(pn-previous)`.

The extrapolate is evaluated in double, cast once to the actual float pressure,
and passed through the original pressure boundary policy. The actual post-BC
float half/endpoint values are separately recorded. B changes the entire
pressure-history prediction relative to C, not just the final row's neighbors.
The C prediction explicitly takes pn alone; previous history is retained for
audit but does not enter its numerical prediction.

The endpoint pressure update is

`pnew = q_actual + Rgamma(q_actual)/S`,

where `Rgamma=-gamma*theta_endpoint+k*lap` is captured directly in double before
the original float pressure-rate store and `S=-k*sum(original_pair_weights)`.
Here S is the positive leading-LP preconditioner, not the full derivative of
the discrete Taylor/inertial-feedback residual. The update is one defect
correction; a fixed point with nonzero S satisfies Rgamma=0. It is not full
Jacobi based on the complete discrete Jacobian or a converged implicit solve.
No residual is reconstructed from the quantized float rate. No diagonal epsilon,
omitted row or fitted correction is introduced. A true drained row has priority
and returns exactly zero. Constant k is the only admitted overlay configuration.
The native `PorePressRate` field still contains the original Kw/n-scaled endpoint
residual diagnostic. B/C do not integrate it as their actual pressure time
derivative; it must not be used to accept or reconstruct B/C dp/dt.

The existing Symplectic mechanics and J integrations remain. B/C do not call a
second solid/material/J update. In this endpoint extension, force geometry is
the completed endpoint while its source clock is the original n clock. The
original `theta_half` that integrated J and the separately evaluated endpoint
theta are both retained; they are not interchangeable. This arrangement is not
literal paper LF, a converged global implicit solve or a claimed second-order
method. The independent P1 math review finds beta0 small-step consistency in a
stable fast Schur block but generally only first-order temporal behavior.

## ID ownership and atomic commit

Initialization records every original native normal fixed/soil ID and its role.
Storage is indexed by ID, not by the cell-sorted slot. Re-mapping validates every
native owner after sorting; periodic copies resolve to their existing owner and
never carry independent pressure history. New/lost/duplicate IDs or changed
roles fail. Initial `previous=pn` is explicitly a cold start, not exact history.

At a source-clock boundary transition, the original predictor force can project
newly drained native pressure to zero before Begin. That actual float pressure
is the pn used for the next integration. Only a zero change certified by the
original `IsHydroMechDrainedParticle` predicate at the original source geometry
is permitted relative to the last committed/saved pressure; all other changes
fail. The sourceDrained mask is recorded separately. Old saved pressure, the
preceding committed history and P0 are not retroactively rewritten. Thus native
readers continue to see the original saved final state, while the sidecar
records the next step's actual source-clock post-BC pn. At tD the original
pre-open policy remains; t>tD or a changed FS identity uses that same original
predicate, not a new time comparison here.

`PorePressPrec` is only the current pn snapshot. It is not used as pn-1. P0 is
captured independently and must remain byte-identical. Each successful whole
step rotates `previous=pn` once, after the endpoint row, original final pressure
BCs and all lifecycle checks. Rejected endpoint evaluation rotates nothing and
cannot produce a new SaveData. This is not complete-state restart support.
Before any history rotation, Commit requires every actual non-drained pressure
byte-identical to its raw row result and every true-Dirichlet pressure
byte-identical to +0.f, while retaining the J/P0 checks. An arbitrary finite
post-row pressure replacement is not an accepted boundary operation.

The original scalar `TimeStep += stepdt` and native zero-based steps are kept.
The helper verifies the true scalar sequence, not step*dt. Initial and genuine
saved states are logged only after the existing native SaveData. It never
rewrites metadata, signed dterror, count/header fields or native arrays.

The extra endpoint force is surrounded by seven per-soil typed bit checks:
position, velocity/density, all six double stresses, kappa, P0, J and pressure
guess. Scratch rates/accelerations and legitimate boundary ghosts are not
mislabelled as committed soil state. Row errors are collected per ID inside the
existing independent receiver loop and rejected serially before any pressure
or history write. There is no new OMP exception in that loop.

## HG and the endpoint force

The frozen `JSphHourglassCpu` phase machine permits two real force calls and two
history updates. Blindly invoking a third `CorrectorForce` would fail its phase
guard; silently dropping HG from the endpoint acceleration would change the
Darcy source. Neither is done.

The original predictor/corrector HG transitions remain untouched. The endpoint
branch reads `GetHistory(id) const`, documented in the frozen header as Q/Mref,
not current physical acceleration. It uses the exact frozen `ParticleMass` and
`AddHistory` order:

`actualMass=(mass/rhopZero)*(rhopZero-waterRho+waterRho*J)`;
`scale=mass/actualMass`;
`ace.x=float(double(oldAceX)+scale*history.x)` (likewise z).

No algebraic cancellation of mass/actualMass is used. This is single-J inertia
at the actual endpoint, using the committed HG history after its original
corrector update. It does not evaluate a new HG rate, advance/cache/replace HG
history, or increment the original HG force counters. Every HG history/rate
vector and every explicit stats field are captured and required unchanged
across the endpoint force. The snapshot also captures all 15 explicit double
fields of `GetRateInfo()` (netx, netz, condition, skew, form, lambda, tau,
ratepower, workerror, rmax, sumrate, meandxx, rmsdxx, meandiv, rmsdiv) and requires
each field byte-identical afterward; no structure-padding comparison is used.
No HG class or public API is changed. An independent
arithmetic fixture must still validate this adapter against the frozen formula;
authoring it is not numerical qualification or exact HG restart evidence.

## Admitted overlay boundary and outstanding checks

The overlay alone is limited to the fresh 1040-native Case02 fixture, 40 fixed
and 1000 soil, original full-A dt `6.250143051147461e-6`, and an endpoint no later
than .15s. It retains Wendland h/dp1.8, dp.01, constant k1e-4, original material,
HG.1/SPR1/AV.1/eta.04, FreeSlip x-periodic boundary, normalized band load and
actual fixed-grid opening. The helper itself has no such material/ID constants.

The existing force/rate/necessary-step checks are not removed in this P1 same-dt
prototype. They do not establish a general TPI stability bound or prove that
the finite-Kw diffusion restriction is the right final M0 restriction. That
decision follows the independent coupled modal/stability review and same-dt
implementation qualification, not a silent deletion here.

Before physical runs: root source-difference review; pure prediction/row/history
and reordered/periodic/invalid-row/failed-commit fixtures; read-only HG arithmetic
fixture; default-OFF actual native prefix against the true final-A program;
Debug full isolated build; then only separately admitted short CPU jobs with
original native IDs/22 arrays/clocks/signed-ledger/drainage/HG safety. No automatic
half chain, mid/full2Tv, Cryer, GPU, C08 source or formal solver follows from this
author draft, preparation or compilation. Changes across A/B/C are not 5-Pa
half/backend equality errors or theoretical truth.
