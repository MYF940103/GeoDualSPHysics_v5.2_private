# Extra complete endpoint defect: minimal scalar implementation fixture

2026-11-17. Specification only; no component/script, solver, reader, build or scan is run.
No old file, frozen note, runtime or source is changed. C08 remains paused.
The staged-load2s result did not improve the top budget materially; it is not admitted full.
This proposed check uses the **original old-source-clock M0/P1 baseline**, not a stack
with staged load clocks. All four prospective forces retain actual source TimeStep=Tn
and its original load/drainage policy. Alpha=.5, beta0 and physical parameters remain.
This supersedes only the prospective staged-clock assumption in the earlier options note;
it does not rewrite that historical author or its mathematical results.

## Meaning and necessary assumptions

At a fixed committed endpoint, define R_gamma(g) as the original complete M0 row:
`k*(LP(g)-GPcorr(g) dot Lx+rho_w*Da(g))-gamma*theta`.
Leading S has units1/(m*s); R_gamma has unitsPa/(m*s), and R_gamma/S has unitsPa.
S is **not** the complete pressure Jacobian. The pressure force inside Da, Taylor
gradient and genuine pressure ghosts/Neumann closure must be recomputed from the
actual guess every round. Geometry/neighbours, v/sigma/J/n/rho/k/P0/material/HG
committed history remain fixed. If those change, this is not the same frozen-row iteration.

One correction is g1=float(g0+R(g0)/S0), then genuine BC; the second force reads
that actual g1 and computes g2=float(g1+R(g1)/S1), then genuine BC.
In linear notation T(g)=p_star+J*(g-p_star), two corrections give J^2 only before
intermediate float/BC effects. They do not create a Newton solve or generally
remove the O(dt) temporal lag. The ideal residual may shrink when the iteration is
contractive; actual nonnormal coupled row norms need not decrease monotonically.
Report both actual R/S values, g1,g2 and all BC masks, without assuming success.
Less pressure constraint defect does not establish better top settlement.
Raw R_gamma and the stored legacy rate have different units/scales from pressure;
use each row's actual R_gamma/S in Pa when reporting a preconditioned correction.
Do not reuse a5Pa half-step pressure budget as an unannounced residual tolerance.
An actual float increment can be zero while the nonzero double correction remains.

## Fixture A: hand-solvable complete row with leading S different from Jacobian

These are synthetic scalar units, **not new material inputs or a physical model**.
Let pn=4Pa, previous=0Pa, alpha=.5, so actual initial guess g0=6Pa. Set S=4,
k=1, gamma=8, theta=.25, Kw=16, n=.5 and split the complete lap as:

```
LP(g)=-4*g; TaylorContribution(g)=g/2;
rho_w*DaContribution(g)=3*g/4+18; GhostContribution(g)=3*g/4;
lap(g)=LP+TaylorContribution+rho_w*DaContribution+GhostContribution=18-2*g;
R_gamma(g)=lap(g)-8*.25=16-2*g=2*(8-g).
```

GhostContribution is a separate algebraic dependency for testing refreshed closure,
not a new term to add to the production equation; a real implementation already
contains its boundary dependence inside the original LP/gradient/Da operations.

| Real force input | LP | Taylor | Da | ghost | R_gamma | R/S | accepted output |
|---:|---:|---:|---:|---:|---:|---:|---:|
|6|-24|3|22.5|4.5|4|1|7|
|7|-28|3.5|23.25|5.25|2|.5|7.5|

The fixed point is8Pa; exact derivative is-2 while leading S is4. Using S=2
would incorrectly return8 at the first pass and is detected. Reusing stale Da
from the first pass gives second R=1.25 and output7.3125; stale Taylor gives
R=1.5/output7.375; stale ghost gives R=1.25/output7.3125. Reusing all three
non-LP terms gives R=0/output7. Those are explicit negative cases, not allowed results.
The valid second pass preserves all frozen nonpressure state and commits history
only once: new_previous=original pn_used, new_final=7.5, never previous=7.
A fixed-point input8 must stay8 in both passes. Sign-reversed source/pressure has
fixed point-8 and valid sequence-6,-7,-7.5; it must not be pressure-clipped.

## Fixture B: actual intermediate binary32 value, including FTZ

CPU/device expectations are distinct and must be tested against the actual policy.
For a normal rounding-sensitive case set S=1 and
`R(g)=3*2^-26-(g-1)/2`, with actual g0=1f. First raw double is1+3*2^-26,
which rounds to actual float1f (bits0x3f800000). Re-evaluating the second row from
that actual1f gives the same R and again actual1f. Feeding the unrounded double
to the next row instead would lead to float0x3f800001 after the second update.
This fixture must first demonstrate that sensitivity, then test the implementation.
Check both actual q and recomputed R in each round, not only the final float;
using an unrounded value only on the R side can otherwise leave the same final bits.

For a subnormal case use S=1, g0=+0, and `R(g)=2^-149-g/2`:

- CPU IEEE binary32: first output bits0x00000001; second raw value is1.5*2^-149,
  which ties to even bits0x00000002.
- Compiled GPU RN+FTZ: first actual output+0, second actual input therefore+0,
  recomputed R remains2^-149 and second output remains+0. Input float-to-double
  FTZ and output RN+FTZ must follow the real CUDA instructions, not host emulation.
- The sign-reversed case yields CPU bits0x80000001 then0x80000002; a genuine
  GPU signed-zero flush gives-0 at each nondrained write. Do not erase signs to
  manufacture a cross-backend equality. There is no new ULP/Pa allowance.

History is original endpoint binary32, and prediction uses those actual values;
the independent double linear J^2 analysis does not prove float iteration bit identity.
Nonfinite input/residual, nonpositive S or float overflow must reject before any
accepted pressure-history rotation. A partial second-force failure is preserved,
not restarted. This does not promise rollback of an already committed mechanical state.

## Fixture C: actual drainage clock and legacy rate semantics

Use the original admitted clock/FS predicate; full endpoint time alone does not open drainage.
The completed1000 event save is pre-open. Its FS2/FS3 pressure is not silently zeroed.
The next source step legitimately projects actual drained pn_used to positive0,
while the retained prior save and P0 remain untouched. Record that difference.
Every active true drained row returns positive0 in both corrections, even if its
inactive S/R inputs are unused. Negative0 or a nonzero value equal to an old final
is not positive0. A nondrained negative or signed-zero result must equal its own
actual raw conversion; no global clipping is allowed. Both endpoint BC observations
are genuine, not copied merely because their geometry should match.

In Fixture A, the original real-Kw legacy pressure rate is evaluated as
`Kw/n*(-theta+k/gamma*lap)`, giving16Pa/s at input6 and8Pa/s at input7.
After two forces the saved **last evaluated** rate is8, not4 (the hypothetical rate
at final7.5 was never evaluated), and not `(7.5-4)/dt=3.5/dt`.
Retain the frozen operation order/FMA/RN/FTZ and original float store when checking
bits; regrouping a separately rounded R_gamma into Kw*R/(n*gamma) is not a bit oracle.
This exact dyadic fixture proves semantics, not arbitrary non-dyadic arithmetic equivalence.
The production record must keep each round's actual q/S/R/lap/theta/rate and final pressure separately.

Only a future independently reviewed implementation could exercise these fixtures.
Four real force/bound phases and two read-only endpoint HG additions must be observed,
with one material/J/position/pressure-history commit. Signed intervals include every
actual force. Existing22 arrays/IDs/ledger/geometry/Dirichlet and physical budgets
remain unchanged. Fixture or normal-exit success cannot admit full2Tv or predict top accuracy.
