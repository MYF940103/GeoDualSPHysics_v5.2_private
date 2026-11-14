# C08 six-state bed momentum / virtual-power observer r1

Author-only assets; root must independently review and admit build, then one component invocation. No physical parameter, public source, physical object, PRE, native result, or previous receipt is changed. No solver, reader, new trajectory, RV commit, material return, filter, or time advance is invoked by this component.

## Closed scope and sorting route

Tag: `c08_h18_bed_power_probe_r1`. Two actual GPU-native trajectories are `original` (AS03/AV.1 short91) and `radial` (new radial window91). Native22/layout/11-column clocks and their actual 6805 IDs remain unchanged. Four focus soil IDs are 6961/6962/7011/7012.

The previously executed gradient probe restored original Parts28–34, then radial Parts28–34. This new entry retains all **14** Restore/Copy/RunCellDivide calls in that order, but only Parts29,30,31 in each case execute the original CPU force. The other **8** states are explicit sorting-only route entries; no force is called for them. Exactly **6 force calls, 6 included Darcy calls, 6 DtVariable(false) calls** are allowed. No second Darcy or RV application is present. The original fixed5us natural/pore/k-gradient gates are kept. State times remain the true native scalar clocks, including original signed interval diagnostics; no n*dt substitution.

This route is necessary because archived JCellDivCpuSingle MakeSortFull/MakeSortFluid groups particles by cell while preserving current within-cell traversal order. Skipping all predecessor restores could change neighbor accumulation order. Restore resets all saved primary/FS/theta fields, rebuilds codes/cells and then recopies native fields. The skipped force would otherwise refresh BoundMode/ghost scratch/FS/C, but the next actual force does its genuine PreInteraction/ComputeFreeSurfaceTracking/DynamicPoreWall stage1. Ignored BoundMode and ignored scratch are never read. This is a source-based expectation, **not a promised bit result**: the existing six-state CPU controls below must falsify any surviving cache/order difference. A mismatch is a preserved diagnostic failure, not permission to loosen equality.

## Existing actual CPU controls and scope of bits

The passed `c08_h18_bed_gradient_review_r1.check.json` provides the previously sealed stat entries for control gradient.csv (87 columns), soil.csv (54), completion.json, and both trajectories' typed22/layout/clocks. Builder binds those old expected stats, allowing identical duplicate entries only; it does not replace historical bindings with current stats or rescan SHA.

Both complete 70000-row CSVs are streamed once; only the selected 30000 rows are retained. Every selected ID/time/step joins uniquely. For each soil row the new actual force is checked against old actual CPU output: Ace x/z float, actual float Darcy rate, double theta, fresh FS, nine double Ci entries and six float Rsigma components. The newly recomputed literal raw/G1 gradients (36 floats) and two per-pass double theta values also match the old source-literal controls. This is **58 scalar comparisons per row =1740000**, plus actual planar Ace y=+0. Independently the already-passed literal gradient body must reproduce current actual theta (30000 bits) and all six current Rsigma components (180000 bits). The pure momentum split has no preexisting exported truth and is explicitly not labelled bit-proven. Nothing here is GPU stage-force bit truth.

## Stage2 wall lifecycle: why the fresh fields are valid inputs

All source locations refer to frozen `outputs/c08_preload_schema2_source_r1/full_source.zip`, members `src/source/JSphCpu.cpp` and `JSphCpu_mdbc.cpp`.

* JSphCpu_mdbc.cpp1238–1258 ComputeDynamicPoreWallAccelerationCpu reads Ace+g, fits its mirror, and its write callback writes **Acec only** as Q(Ace+g)-g. The generic InterpolateBoundaryGhostFieldT146–294 uses local fit/retry state and only its supplied writer changes fields. Dynamic calls use recenter=false (JSphCpu.h300–302); local retry shifts do not rewrite persistent fit history.
* The same original force's stage1 has already reconstructed authoritative active-wall effective sigma, p/J, full derivative velocity, tangent mirror and Ci, even with SPR0. Stage2 does not change these fields; they are therefore the values used for the read-only momentum/gradient reconstruction after that force.
* This is an archived **write-set** argument. The observer does not possess a captured pre-stage2 snapshot and does not claim runtime pre/post stage2 bit proof. The output wall Ace is the actual post-stage2 hydraulic field, not a hypothetical velocity derivative. No boundary policy is altered here.

Active wall rows contain fresh sigma double and its force float cast, p/P0/J and derived n/V/rho, physical/full/tangent velocities, true BoundNormal, slip/mode, post-stage2 Ace and actual sorted index/NpbOk. Mode-OFF/ignored scratch is not exported as if defined. Summary counts retain active/inactive/ignored ownership.

## Source-literal momentum split and floating-point meaning

The builder copies JSphCpu.cpp2315–2322 verbatim into momentum_literal.inc. It uses original float raw kernel gradient and float-cast effective sigma, double pore-pressure sum, double Vj/rhoi and the original per-component float update:

`a_i += float[(Vj/rhoi) ((sigma_i+sigma_j) - (pi+pj)I) grad_i W]`.

For each original fluid/bound neighbor pass, three **independent float accumulators** call this identical literal: (1) original sigma and p =combined, (2) p=0 =effective-only, (3) sigma=0 =pressure-only. Physical arrays are never changed. Explicit split residual is double(combined)−double(effective)−double(pressure), at each component and in power. The original real force interleaves AV/AS and other terms; its mixed Ace cannot be subtracted to extract stress. The separated accumulators also change FP association relative to that mixed force. Consequently combined is a fresh pure-term literal evaluation, not a claim of an exact historical sub-sum of mixed Ace. Signed and sum-absolute residuals are descriptive, without a new physical or relaxed arithmetic gate.

The same source neighbor traversal, outer float support/Fac, J-derived volume, full-vs-tangent derivative selection and raw/G1 gradient reconstruction are reused. No Ci correction is silently applied to the raw momentum gradient.

## Conditional power definitions / signs

Let mi=rhoi Vi, vi be the saved float physical soil velocity, sigma the actual force float-cast effective tensor. For each fluid/bound pass:

* Literal nodal power: P_eff=Σ mi vi·a_eff, P_p=Σ mi vi·a_p, P_T=Σ mi vi·a_combined, plus explicit split-force power residual.
* Virtual effective power: W_eff(L0/L1)=−Σ Vi sigma:sym(Lraw/G1).
* Virtual pressure power: W_p(L0/L1)=+Σ Vi pi tr(Lraw/G1), and W_p(theta)=+Σ Vi pi theta_pass.
* All nine quantities have signed and Σabsolute per-node totals, in W/m for this 2D unit-width case. Off-diagonal sigma order is xy,yz,xz; contraction includes both velocity-gradient entries. There is no model-fitting, smoothing, missing-negative-value deletion, or forced cancellation.

These are conditional saved-state CPU quantities. Source float-vs-double quadrature, current mirror conditions and rounding affect identities. The wall pass is mirror strain / ghost-force accounting; it is **not a closed real-wall external work balance**. No complete coupled energy law, real GPU substage cause, actual boundary reaction closure, or error in J is concluded from a nonzero difference. The purpose is to test whether the previously observed large wall G1/raw virtual-work difference corresponds to an appreciable source-literal force/virtual-work discrepancy at the same six real saved states.

## Output and later root invocation

Fresh directory `outputs/c08_h18_bed_power_probe_r1` only:

* soil.csv:30000 rows, native state, actual mixed force/rate, force sigma cast, per-pass combined/effective/pressure/residual accelerations and nine powers/traces.
* focus.csv:24 rows, exactly the same schema, the four fixed material IDs.
* walls.csv:all genuinely active defined walls for the six states; no fabricated ignored scratch.
* power.csv:12 pass-state signed/absolute power summaries; metrics.csv:6 natural-step/rate/control summaries.
* selected_clocks.csv:6 complete original signed clock rows; restore_route.csv:14 route rows showing eight no-force states.
* completion.json:coverage counters, zero physical steps/material/filter/RV commits, no physical acceptance.

One new entry is compiled with the original DebugCPU recipe (/Od,/MTd,/RTC1,/fp:precise,/openmp,/std:c++17), 160 archived headers and7 runtimes, linked with **86 untouched original physical objects**. Seven generated fragments are bounded copies; only AppInfo name changes in shared91, while momentum_literal is a new verbatim archive excerpt. The parent independently reviews before invoking:

`D:/anaconda3/python.exe -B tests/support/c08_h18_bed_power_probe_r1_build.py --execution-authorized`

The built executable accepts only `--check -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1`, the original short seed and the exact fresh tag output. A failure preserves partials and the actual first comparison message. No automatic rebuild/retry/follow-on is included. Author performed no build, component, solver, reader, Git or hash scan.
