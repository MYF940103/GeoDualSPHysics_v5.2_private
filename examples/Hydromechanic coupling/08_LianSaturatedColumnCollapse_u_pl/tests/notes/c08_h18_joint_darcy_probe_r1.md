# C08 joint-Darcy zero-advance manufactured probe r1

Only author preparation of `support/c08_h18_joint_darcy_probe_r1.cpp`, `support/c08_h18_joint_darcy_probe_r1_build.py` and this note is authorized here. Root must fully review and separately admit build/component. No source/parameter/Q policy, original physical object, original PRE/native/CSV, XML/BAT or former receipt is changed. No solver, reader, new PRE, half, trajectory, filter, material return, AS recomputation, or time integration is added.

## Closed geometry / numerical scope

Actual geometry is **original AS03 P29 and P30**. Preserve the passed power-probe fourteen-state Restore/CellDivide route (original P28–34, then radial P28–34), but only original P29/P30 execute one original CPU force each. The remaining12 are sorting-only; radial receives no force, manufactured evaluation or physical comparison. All5000 original soil IDs and6805 total owners remain present; retired255 stay retired. Both native91 streams/22fields/actual signed11-column clocks, frozen source/program/PRE and original source checks remain protected. No n*dt clock, retiming, ID rewrite or new native decode is used.

Bare control mechanically reuses the passed source-literal gradient body and existing original gradient/soil CSVs, already corroborated by the passed power probe. For each of10000 actual bare soil rows, compare58 scalar bits of true CPU Ace/R/θ/FS/C/Rσ and literal raw/G1 gradient/pass-θ against the old frozen controls:580000 checks, plus internally10000θ/60000Rσ bits. Old14-route sort order is retained, but equality is tested, not presumed. Every MFG leg restores all defined primary/C/FS/force scratch by ID and checks it before continuing. Ignored BoundMode and undefined OFF/ignored velocity/Ace scratch are not read or fabricated. Predictor pointers remain their genuinely initialized completed-state values; nothing is artificially set null.

The original two bare DtVariable(false) results and separated force/wave/pore/k-gradient necessary5us gates are kept. No manufactured state borrows old AceMax as a stability certificate. All actual source finite/rank/J/rate-overflow gates remain intact; manufactured rates never enter a time update.

## Three fixed instantaneous fields

Let b be the **actual stored float Gravity converted to double**, rho_w the original1000kg/m³, gamma_ref=rho_w*9.80665, p*=0. The fixed coefficients are B=1000Pa/m², A=1000Pa/m³, xc=2m. They are not fitted to case data.

* H: p1=0.
* N: p1=(B/2)z², gradp1=(0,0,Bz).
* X: p1=A(x−xc)z², gradp1=(Az²,0,2A(x−xc)z).

For all sampled coordinates the declared continuous fields are p=p*+rho_w b·x+p1, a_s=−gradp1/rho_w, **Ace=a_s−b**. Therefore gradp+rho_w Ace=0 continuously. Gravity is included once; gamma_ref is not substituted for body acceleration. The bed z=0 has a_s=0, and the quadratic/cross excess head has the intended even normal extension. These are spatial manufactured data, not a mechanical/free-surface/material initial-boundary-value solution.

Each real-wall leg resets all temporary J to1, theta to0 and physical velocity to0, with soil rho cache matching J1. Fixed velocity cache follows original State policy RhopZero, not derived ghost rho. Original P0, κ and soil sigma history are retained; P0 is not used to construct p. Old Rσ is not relabelled manufactured stress rate. AS and momentum are not recomputed for these supplied accelerations. No strain/J/position/velocity/plastic step is committed.

## Actual lifecycle and two separate oracles

For each of2 geometries×3fields:

1. Restore captured actual bare state in memory. Assign the manufactured fields and call the original **ComputeFreeSurfaceTracking** once. It genuinely runs dynamic wall stage1, current constant-J-weighted soil Ci/freshFS and wall-C reconstruction. Native-J Ci is not reused for a constant-J manufactured field. Then assign analytic soil Ace.
2. Call original **ComputeDynamicPorePressureRateCpu** once. Its stage2 extends Ace with the unchanged Q rule and evaluates the actual full rate on all5000. DynamicWall/Conductivity/FS flags, Ck2, pair-C, Eta² and kernel are unchanged.
3. Re-evaluate the full current RHS with the passed exact-neighbor Assemble and original source-ordered expressions. **Only this actual branch reads Ratec and asserts float bits.** All30000 actual rows retain the original float/expanded/donor-partition budgets; no new loose tolerance is substituted.
4. Hold the same current J/C/FS/quadrature fixed. Replace **only fixed p/Ace** by the declared analytic extension, leaving soil fields unchanged. Evaluate the same source-literal expressions as a separate analytic oracle. Do not call original Rate (which would overwrite these ghost accelerations), disable DynamicPoreWall (which would remove boundary neighbors), or write generated oracle values into Ratec to satisfy a native assertion. No actual-native bit truth is claimed for these30000 generated float outputs.
5. Restore the captured original state and all defined scratch; bit-check restoration before the next field/baseline. Geometry/codes/sorting and original clock never advance.

Original wall APIs are bound archive `outputs/c08_preload_schema2_source_r1/full_source.zip`, CPU mDBC1121–1205(stage1),1210–1232(matrix),1238–1258(Ace); CPU ComputeFreeSurfaceTracking supplies the actual lifecycle. The original rate3174–3277 automatically calls stage2 and includes raw-FS receiver-Ace and product-rule k-chain terms. No ApplyBoundaries/positive projection/Shepard/PreInteraction is added to a manufactured leg. Whole-domain FS/side/corner values remain reported without pretending the manufactured field satisfies every external physical boundary condition.

### Honest call accounting

*14 Restore/CellDivide,12 dry states;
*2 actual bare forces, containing2 actual original Darcy calls;
*6 manufactured original Darcy API calls;
*total **8 original Darcy API calls**;
*6 literal evaluations that reconcile those actual manufactured fields, plus6 analytic-ghost literal evaluations;
*60000 manufactured row outputs,12 summaries,2 actual clock rows;
*zero material/filter/RV/physical steps.

Do not describe this as14 actual API calls. The copied pure-expression include has no Ratec read or native assertion. It mechanically retains old lap/chain/literal, seven pieces/expanded/partition and magnitude/dbudget expressions. The explicit actual-only reconciliation gate and independent analytic float conversion are visible in CPP.

## Constant J and k: retain actual roundoff

Soil J=1 makes original GetDynamicConductivity return k0 exactly. Real MLS may leave tiny wall J−1 roundoff even when supplied constant J. It is retained, measured and not clamped away. The current manufactured C/FS is built with that actual quadrature. Analytic p/Ace oracle intentionally shares those J/C/FS values, so it isolates pressure/acceleration ghost extension; it is not a second independently regenerated analytic geometry.

All GJ and pressure/Ace chain terms remain in the rate, including any tiny ghost-J residual. This is not physical variable-k validation or permission to omit the chain. The source gradient-speed is a J/C-only property; the analytic comparison carries the real-leg value because J/C is unchanged, not because a new API call ran. Mathematical input constants, actual ghost roundoff and float pressure/Ace storage errors are recorded separately.

## Cohorts and scientific output

All5000 rows are always written, including FS, corners, negative pressures and below-bed saved positions. The predeclared analytic **legal_flat_bed** flag requires0<z<=2H, x in[.5,3.5], current FSinner, no current FS2/3 neighbor within the original2H support, at least one actual fixed donor, and all such donors are flat+Z/NoSlip bed. This does not move to improve results. **interior_no_wall** is FSinner, no nearbyFS and zero fixed donors. Empty cohorts remain empty. These are descriptive legal-domain labels, not acceptance masks that delete the other output.

Outputs under exclusive `outputs/c08_h18_joint_darcy_probe_r1`:

* manufactured.csv:60000 rows. Current/native FS, cohort/support labels, declared/stored p/Ace and quantization errors, original P0, actual J/n/V/rho/k/theta, Ci, LP/Lx/Gp/Da/GJ, full raw-FS/source chain/literal rate, all7 channels and numeric remainder. Plane-C condition-infinity is descriptive; if determinant is exactly0 its value is blank with defined=false, never clamped. This is correction-matrix conditioning, not unobserved MLS-fit conditioning.
* summary.csv:12 actual/oracle groups, whole5000 and legal-bed/interior rate RMS/absmax, allFS counts and real wall-J roundoff. No arbitrary5Pa or continuous-zero gate is used: nonzero manufactured rates are measured truncation/quantization/ghost-closure results.
* walls.csv:all genuinely active wall p/Ace/J/C, exact analytic references/errors, normal andslip, for both oracles. Source original MLS finite first-order fit gate remains the authority; no new fake MLS determinant proof is exported.
* baseline.csv:2 actual controls and original separated necessary bounds; restore_route.csv:14 actual routes; selected_clocks.csv:2 complete native signed clock rows.
* completion.json:separate actual/API/literal/generated counters, original arithmetic ratios and no physical acceptance.

This closes a missing joint pressure-plus-acceleration manufacturing question. It does not choose a new spatial operator, remove Eta, flip Q, admit TPI/β, prove conservation/energy/contact reaction, or prove a cause of clumping/early arrest.

## Future root-only build/execution

One new DebugCPU entry links86 untouched original physical objects (87total),160archived headers and7original runtimes using the passed authoritative CL/link recipes. Only8 narrow generated includes are needed; no new physical TU is compiled. Public ABI/source and canonical programs remain unchanged. Builder checks exclusive new paths, existing source/receipt stats and exact source anchors; no SHA scan.

After full independent review root may separately invoke the builder once with `--execution-authorized`, then the fresh executable with `--check -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_SHORT_SEED FRESH_TAG_OUT`. Nothing automatically executes the next stage. Failures preserve the actual first error, partials and bindings; no blind re-run/rebuild occurs. Author wrote only these new assets and performed static text checks; no prepare/build/component/solver/native/reader/Git was executed.
