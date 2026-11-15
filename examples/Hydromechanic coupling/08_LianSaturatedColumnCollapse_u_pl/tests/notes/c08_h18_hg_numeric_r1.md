# Numeric-core Audit/Fast equivalence and finite2D spin-helper range

AUTHOR ONLY: four new assets c08_h18_hg_numeric_r1.hpp/.cpp/_build.py and this note. Old stage/math/source/program/output assets are unchanged. No build, program, decoder, analysis, solver, GPU, Git or SHA execution has been performed by the authors. Root independently admits build and then the one component. No automatic job or physical window follows.

## One numerical algorithm, two certificate modes

The new header has one template<bool Audit> Core/State implementation. Every center-value expression, operand grouping, native-ID/cell traversal, LS tensor/complete adjoint, row-memory update, event branch and rotation path is shared. Audit=true additionally propagates outward errors and checks certificates; Fast=false skips that expensive per-operation work. It does not replace the model with a second formula, use fast_math, change support/rank/finite/current mass/active-ID/5us checks, or clip a small computed residual to zero.

Common physical values and raw controls are distinguished from certificate metadata. lambda_raw, dt_ratio_raw and spin_raw are shared values; *_bound, Hi-derived lambda_upper/dt_ratio/spin_bound/max_omega_upper and certificate/op/event counters intentionally differ. Fast marks audited_enclosures=false and must not advertise passing Audit uncertainty-domain checks. The component compares values/branches on these already qualified inputs, not arbitrary unknown future states. Private State still enforces its short cumulative .01rad guard; public legacy HG and its .01 guard are completely untouched.

The existing exact-input constant-velocity-patch exception is shared: native velocity bits of every actual donor must match its receiver, then Audit checks the computed zero response before supplying an explicitly known zero drive. General affine/near-zero/underflow domains are not silently regularized.

## Only two genuine saved inputs, no new physical step

The builder first binds the actual passed c08_h18_plastic_hg_stage_r1 check/build/call/completion and its sealed stage_nodes.csv. It requires the previous220000 OFF field checks and420000 actual stress/kappa matches. It also binds the completed full301 native/review receipts and their original typed22/layout/clocks seals. No new reader or actual force/material call occurs.

The component reads existing typed Parts38/76 (actual completed2076001/2152001) and selects only ON/update0/n gamma from the existing60000-row stage table. All5000 soil IDs, true source clock and original stage inertia must match. Gamma is the previously executed same-input return result, not inferred from kappa. No material return is rerun. Config h/G/Bwen/xi/mass conventions are the same closed actual stage values; loaded volume/J/float native velocity are unchanged.

For each case, both template instantiations receive the SAME frozen n0 input and perform two predictor/full/commit generations. Full always begins from committed e, not predictor e. Only history changes: positions/velocities/pressure/J/kappa and source time/step are not advanced. These are frozen implementation trials, not more C08 updates or a reference trajectory.

All5000 forces, accepted row-history center values,18 node fields,43 directed-row fields, event/constant branches and common scalar metadata are compared internally bitwise. That includes P/L/D/gamma/t1/I/rotation/force data. The first mismatch reports source part, generation, phase, native ID or directed key, and field. No full edge trace CSV is written. Additionally each case's FIRST predictor force is compared bitwise with all5000 actual old ON/update0/n HG_Fx/Fz values recovered from17-digit CSV (20000 scalar checks total). This prevents two new modes sharing the same erroneous copy from passing only by self-comparison. It is a CPU stored-result implementation regression, not GPU/native binary proof.

Two extra scalar local fixtures (h0=1,z=-1,D1,T3,g0 andg.5) compare all ExactStep center values, t1/t2 and branch in both modes, using the already passed crossing/unloading formulas. They do not repeat the old27/basis suites or constitute another physics study.

value_comparison.csv has8 rows, including raw Audit/Fast wall-clock time of just these private subsystem evaluations. Audit is evaluated first, Fast second; cache/compiler/Debug effects are not controlled. These times must not be extrapolated into C08, Release or GPU speed, and the previous139s whole Debug+Audit physical component is not a production-performance estimate.

## Pure spin: meaningful intermediate and final references

Spin does not build any graph. Initial nonzero e=(.125,-.25), strict zero drive and g=.5 use the SAME two half-rotations with the same zero-drive ExactStep in between. It tests1024 repetitions in two closed sequences:

- constant full angle delta=ldexp(binary64(2pi),-10);
- variable/reversing motif delta*(-.25,1.25,1.5,1.5), repeated256 times.

Every half-angle is below .005rad. Each mode's e center/zero-drive branch is compared after every step. Audit errors are carried into its next step; Fast does not pretend to carry them. Checks at step256 (near pi/2) establish orientation/sign, while final near2pi checks accumulated error. A final whole turn alone would not detect a reversed sign. This helper has no cumulative-spin rejection; the actual private State retains .01. No finite-Omega field ODE, arbitrary moving geometry, DP/contact/Darcy coupling or large-rotation trajectory is thereby qualified.

The build PREPARES a two-row rotation_reference.csv before compilation; it never runs a component. Reference angles are the actual binary64 full-angle bit patterns, not ideal pi or a rounded n*dt clock. Fraction.from_float gives their exact rational sum for full1024 and quarter256 prefixes. A100-digit Decimal interval, with ROUND_FLOOR/ROUND_CEILING on every operation, evaluates128-index sine/cosine Taylor sums. Because |angle|<7, the omitted terms are decreasing there; the first omitted exact term bounds the alternating tail. That tail is added outward. No libm-ULP or Windows long-double assumption is used.

The same directed interval arithmetic rotates the exact initial e. Rounding the reference to binary64 produces an independently measured interval-to-reference error, rounded upward. CPP verifies its closed angle bits, checks its actual quarter/final states against those references plus Audit enclosures, and records actual coordinate errors/bounds and norm drift. It separately reports ordinary double angle accumulation; that value is not substituted for the exact sum of applied double increments.

## Build/run boundary and output

One new standalone DebugCPU/CRT entry is compiled with the original /Od /MTd /RTC1 /fp:precise recipe and MSVC14.36. No86-object physical closure, public headers, physical TU or third-party project library is linked. Root first admits the build; the builder only creates references, compiles and links. Input stats are verified before/after, with no SHA. Root must verify that consumed build/input seal before its separately owned component invocation. Runtime stamps additionally protect inputs during that call; they are not invented earlier provenance.

Future commands, NOT executed here:

    python support/c08_h18_hg_numeric_r1_build.py --execution-authorized
    C08H18HgNumericR1.exe --check CLOSED_FULL301_NATIVE CLOSED_STAGE_NODES CLOSED_ROTATION_REFERENCE FRESH_FIXED_OUT

The component refuses existing complete/partial output and writes only value_comparison.csv8 rows, spin.csv2 rows, unloading.csv2 rows, and completion.json; actual errors preserve failure.txt and partials. Full traces remain in memory. Binary64 RN and MXCSR RN/FTZ/DAZ are only checked, never changed.

A successful result can establish the checked refactor equivalence and pure-spin helper range only. Audit metadata are deliberately not bit-compared as physical values. actual physical updates/material/Darcy/solver/reader counts remain zero; coupled large-rotation accuracy/passivity, C08/GPU performance, long-window admission and physical_acceptance remain false. This is the last bounded implementation qualification before considering actual limited-window integration, not authorization to launch it or another ordinary toy chain.
