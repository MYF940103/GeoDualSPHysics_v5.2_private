# Cohesion-softening periodic integration: bounded result

2026-11-06. Retained code base: `41fbfbd1f30f2bd09305b6f03163b42d095f1444`.
This stage changes only three host admission clauses, not the material equations or
Pre/Cor order: remove the constant-cohesion restriction from
`IsDynamicPorePlasticPeriodicConfig`, and condition the CPU/GPU initializer's
StrainSoftening rejection on that same narrow predicate. Fixed phi, zero dilation,
zero gravity, no walls/stabilizers and constant conductivity remain required.

The two physical input changes are coh_r=1000 Pa and n_coh=5; peak cohesion is5000 Pa.
The original1024-owner periodic lattice, actual GenCase BI4, frozen sine velocity
table, dt=2^-19 s,128 updates and five actual saved times are unchanged. Derived
companions are labelled as derivatives; GenCase and old controls were not rerun.

CPU Debug's default solution build passed. GPU HostDelta r1 compiled97 host objects
and adopted14 unchanged CUDA objects, but its direct Link target omitted the host
link inputs. Its genuine failed exit/logs are retained. The authoritative r2_link
repair adopted all111 objects, populated the missing host inputs and linked with
actual exit0; no host or CUDA recompile occurred in that repair. It is not described
as a new CUDA build. Canonical executables and protected old objects remain intact.

One CPU solver and one GPU solver completed128 updates/five frames; the sole GPU
target ran under memcheck, with zero errors/leaks. One new reader invocation per
backend passed1024 IDs/22 arrays,5120 J-ledger/cache checks,1024 initial-velocity
bit checks,4096 nondecreasing-kappa checks and all four signed time intervals.
Actual final time is0.000244140625 s; the signed negative dterror values were kept.

Both final states contain640 positive-kappa IDs. CPU/GPU maximum kappa is
0.00034550658892840147 /0.0003455066180322319. Their minimum cohesion, evaluated
descriptively from saved float kappa, is4993.095833526 /4993.095832944929 Pa.
Only about6.904 Pa strength loss is covered, not the full post-peak regime.

Across all five actual times, CPU/GPU maximum pressure-difference RMS is0.00436520742 Pa,
per-ID XYZ displacement difference4.83470294e-9 mm, effective-stress Frobenius
difference RMS0.00028439131 Pa, total-stress counterpart0.00770638073 Pa and
kappa difference8.73114914e-11. These are descriptive implementation comparisons,
not new half-step gates or theory errors. Initial cross-backend FSNormal/PosDiv
differences remain explicit; all22 fields are not claimed bitwise equal.

Against each retained same-backend constant-strength control, effective-stress
Frobenius difference RMS reaches5.12469238 Pa (CPU) /5.12469039 Pa (GPU).
The CPU aggregate final effective-stress RMS decreases4.28225491 Pa; this aggregate
change is distinct from RMS of matched-ID differences. No spatial accuracy gain is
inferred from that response. The2x3 PNG and all three CSVs were inspected by author
and root: legends, raw sample times, units and small observed strength loss are clear.

Evidence: `../logs/upl_plastic_softening_*` run/build/native receipts;
`../figures/upl_plastic_softening_pair_r1.png`, matching `_history.csv`,
`_differences.csv`, `_row_profile.csv` and `.check.json`. Analysis's original
QA-pending flag was not rewritten; the separate visual QA receipt and this root
review record the inspection. Raw BI4/typed exports, programs and source snapshots
remain local protected dependencies, not cloud Git data backup.

No half/reference chain, fitting, clipping, new pressure tolerance, full collapse,
localization, gravity-plasticity, restart or nonzero-dilation acceptance follows.
Next is the already planned bounded +/-dilation-and-decay integration; all current
material apex/derivative/convergence and J/time guards remain in force.
