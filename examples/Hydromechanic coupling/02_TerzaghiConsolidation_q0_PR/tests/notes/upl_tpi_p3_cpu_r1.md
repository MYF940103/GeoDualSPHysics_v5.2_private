# P3 CPU pressure helper r1

Author-only private candidate; not prepared, built or run. New file `tests/support/upl_tpi_p3_cpu_r1.h` is a complete clone of the final P2 CPU header with a local third pressure defect and independent round2 evidence. Actual `outputs/upl_tpi_p2_CPU_r1_source/upl_tpi_cpu_r1.h` and its final author header were read and confirmed byte-identical before authoring. No original source or P2 artifact is changed.

The namespace remains `upl_tpi_cpu_r1`; future source substitution must retain destination include name `upl_tpi_cpu_r1.h`. The private host State changes; no public JSph class, virtual/device structure or material/HG layout is changed. All consuming host TUs must be recompiled together. No source preparation or ABI/build acceptance is claimed here.

## Selection and unchanged arithmetic

Only B alpha=.5/beta0 is admitted by the private helper, with explicit `UPL_TPI_P3_ROWS_R1=3`. A returns false before reading the new selector. A's original finite-Kw path is untouched in the future glue; an actual A native regression is still required. C is rejected. Future owners must clear inherited P2/P1 selectors rather than mislabeling this new schema.

Predict, SolveBeta0, ID map/periodic ownership, mechanical half guess, J capture, Row, PrepareFinal and readonly HG arithmetic remain the original P2 expressions. S=-k*sum(w) is the positive leading-LP preconditioner, not the full residual Jacobian. Each update is an actual defect correction using a freshly recomputed full Rgamma at the current actual float pressure; no S, residual, sign, coefficient, epsilon or row is fitted/removed.

At one fixed solid endpoint:

`q1 = float(pn + .5*(pn-previous))` after actual original BC;
`p1 = BC(float(q1 + R1(q1)/S1))`;
`q2 = actual validated p1`, `p2 = BC(float(q2 + R2(q2)/S2))`;
`q3 = actual validated p2`, `p3 = BC(float(q3 + R3(q3)/S3))`.

The original source TimeStep, dt=tD/1000, force/load/drainage policy, spatial operators, SPR/AV/HG/damping and physical Kw/k are unchanged. This is three finite defects, not a converged implicit solve, literal paper LF or second-order scheme. The independently reviewed small matrix model is not SPH stability/physics acceptance; 20us is not introduced.

## Actual lifecycle and APIs

Old array-based APIs remain; no GPU View or public class member is added. New signatures are:

- `ValidateProvisionalEndpoint(owner,np,id,code,p,p0,j,Drained)` for actual rounds1 and2 only.
- `NextEndpoint(owner,np,id,code,pos,velrhop,sigma,kappa,p0,q,j,time,step,dt,hg)` after a validated round1 or2; it calls Endpoint and CaptureHG once internally.
- `EndpointPhase()` returns2/3/4 for actual pressure rounds1/2/3.

Begin/Corr/CaptureJ remain once per complete step. The first Endpoint and CaptureHG are still outer calls. For each of three iterations: actual force, DtVariable, CheckHG, PrepareFinal, release scratch, WriteFinal, original pressure BC. For rounds1/2 keep endpoint and temporary true through BC, then ValidateProvisionalEndpoint clears endpoint only. For round3 the outer glue clears endpoint and temporary before BC, sets the real final drained mask and calls Commit once. The scalar global clock and Nstep advance only in their original outer location after the loop.

ValidateProvisionalEndpoint requires a successful write and complete core/HG checks, validates every native J/P0 and actual pressure raw/+0 under the genuine drainage mask before copying any evidence. Only then does it deep-capture firstRows or secondRows independently. It never writes previous/finalP/history. A failed row, BC or invariant aborts; error evidence and the current provisional pressure remain, with no history rotation or retry.

NextEndpoint verifies that actual current q exactly equals the corresponding p1/p2 captured after BC. It checks all errors were observed and the current record deep-copied before clearing seen/rowError/masks/prepared. It snapshots new core and readonly HG once. No unseen error is reset. An exception is terminal and cannot rearm the transition.

Commit is only legal at round3 after both provisional validations and both transitions. It validates all final pressure/J/P0 values before the sole previous=pn/finalP=p3 rotation. A duplicate write, transition, skipped stage or extra commit is rejected by real cumulative counts.

## Evidence and counts

For N completed updates and M soil owners:

- Begin/Corr/J and final pressure-history Commit each N.
- Endpoint calls and actual writes each3N.
- First and second validations each N; provisional validations and endpoint transitions each2N.
- Readonly core checks21*M*N and HG history/rate checks6*M*N, plus every Stats/RateInfo field bit check retained at all three endpoints.
- Original physical HG remains2N forces/N predictor/N corrector/2N rates, with old cache/dt/spin gates. Extra forces use the exact readonly current-J mass/add expression and never update HG memory.

FirstEndpointRecord remains the same host record type, but firstRows and secondRows are separate vectors. Each stores actual q, raw, BC value, S/R/theta, source/endpoint/final masks, J states and priorFinalP. Both priorFinalP values remain the old committed final, never fabricated as p1/p2. Saved verifies q2=first actualBC and q3=second actualBC.

New sidecars are `UplTpiP3CpuR1.policy.json/.csv/.summary.json`, stage `upl_tpi_p3_cpu_r1`. CSV remains32 columns except the old validation flag becomes `provisional_endpoint_validation_count`:0 on the real initial round0 record,2 on every committed round1/2/3 record. One real initial row per ID is retained; later saves emit three independent rows per ID. Total rows=M*(3*saved_frames-2). The complete schema is the literal header in the new helper.

Policy/summary explicitly retain cold-history/no full restart, unchanged source clock, no staged load, stale prior-final fields, directly captured two provisional BCs and actual q2/q3. They reject paper-literal LF, second-order, true-implicit and physical acceptance. The final native PorePressRate is the original scaled R3 evaluated at actual p2, not R(p3) and not actual dp/dt. The endpoint theta is not substituted for the unique mechanical J-integration theta.

## Required later review

This author stage does not wire the helper into JSphCpuSingle or generate a new source tree. Root review must pair it with the new five-phase dt helper and a separately reviewed local three-iteration glue. No co-include with P2 is allowed. All original22 arrays/IDs/clock/signed/ledger/drainage/HG/elastic/material guards remain mandatory, and the original pressure/top/bottom/100Pa budgets remain unchanged. A successful build or fixture would not accept a physical window or full run.
