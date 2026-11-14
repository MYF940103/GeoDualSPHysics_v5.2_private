# Frozen Part300 pressure-row component — author-only

New files are `tests/support/c08_h18_pressure_row_r1.cpp`, its `_build.py` and this note. Outputs, if independently admitted later, are fresh `tests/outputs/c08_h18_pressure_row_r1{,_build}` and `tests/logs/c08_h18_pressure_row_r1.*`. Authoring executes no imports, build, force/component, solver, native decode, VTK, hash or Git. Production equations, parameters, public files, canonical programs, original PRE and all retained outputs remain unchanged.

Root must fully read these files plus `c08_pressure_integration_scope_r1.md` before separately admitting a build and then one component. Build permission does not admit execution. A source/compile/component failure preserves its first evidence and partial outputs; there is no retry/overwrite or automatic next action.

## Actual source and unmodified lifecycle

The single input is already completed and independently decoded full3 AS0.5/n2.55 Part300, actual12.999999999592434 s/completed2600000, native301/6805 IDs/22 arrays. Its original source/PRE/material/roles and all retained ledger, P0, primary-state/clock and signed-native evidence remain required through the existing late-RHS build closure. This component neither repeats that decoding nor reconstructs GPU force substages.

The entry inherits the completed `c08_h18_late_rhs_r1.cpp` fixture through a fresh generated include. Only protected access and diagnostic AppInfo name change in that include; original force objects are not rebuilt or hooked. It initializes the genuine PRE handoff and one release, restores Part300 by ID, then calls the original CPU corrector-mode force/Darcy exactly once, without advancing time or material history. Primary5000 soil states and6805 roles are checked unchanged before/after. Original independent Part300 force can differ from unsaved GPU stages; no backend bit-equivalence is asserted.

The whole neighbour stencil method is copied **bytewise** from the already qualified polynomial fixture `c08_h18_quadratic_r1.cpp`, including kernel weights, currentJ volumes, pair-C/Eta and disabled-wall checks. The builder verifies this full method before compiling. It compiles one new entry and links86 unchanged original DebugCPU physical objects with160 archived headers and the authoritative VS tlog/library recipe. No public physical TU, VS project or canonical program changes.

## Complete frozen pressure row

For the inherited stencil, let `w_j=-native_pair_weight` and `g_j=C_i gradW_ij`, `V_j=V0 J_j`. Define `chi=1` for actual FS receivers, otherwise0, and freeze actual `Lx`, `gradJ`, acceleration, theta, k and k'=dk/dJ from the one original force. Then

`u=-(1-chi)*k*Lx + k'*gradJ`

`A_j=k*w_j + V_j dot(g_j,u)`

`S=sum A_j; N=sum A_j*p_j; P=sum A_j*(p_j-p_i)`

`B=-gamma*theta + rho*k*(Da+chi*a_i.Lx) + rho*k'*gradJ.a_i`

`M=gamma*n/Kw; rowRate=(B+P)/M`.

All pressure Taylor/variable-k-chain coefficients are in A; they are not also added to B. `N-S*p_i=P` is checked under a declared binary64 reassociation envelope. The original source-ordered full rate must still match its actual final float write bitwise. Both the expanded native row and original decomposition are checked against the **unchanged late-RHS operation-count rate envelope**, not a new physical tolerance. `M`, `S`, units and all original signs are retained. Negative A or nonpositive S are reported rather than clamped.

For the native row, current wall pressures and accelerations are frozen/lagged. The full6805 mathematical operator includes wall coefficients; the5000-soil block moves their actual N_wall to the known source. `-S_wall/M` is the expected soil-only response to a unit constant shift with unchanged wall values; this is not a constant-null failure or a physical wall-removal experiment. There is no implicit wall solve, full coupled Jacobian, CSR/global matrix or pressure-state replacement.

Seven manufactured local pressure jets (constant, x, z, x²/2, xz, z²/2, harmonic) assign analytic continuation values to **all** fixed and soil donors at their actual current coordinates. They never write solver pressure. The complete row is independently reconciled with LP/Taylor/chain assembly; full constant pressure gives zero pressure-operator response. For variable k, the conditional local product-rule reference is `k*Laplacian(p)+k'*dot(actual_frozen_gradJ,analytic_gradp)`; gradJ itself is a numerical field, so this is not an exact continuum k-gradient truth. Raw-FS retains its original omitted Taylor term and its boundary error is descriptive, not silently repaired or subjected to an invented interior accuracy gate.

## Algebraic time shadows, not a new integrator

For h=5e-6,5e-7,5e-8 s, explicit increment is h*rowRate. With current p as the declared base and the same frozen B/N, diagonal BE and midpoint shadows are

`delta_BE=h*rowRate/(1+h*S/M)`

`delta_mid=h*rowRate/(1+0.5*h*S/M)`.

These native-state columns use **N(p_n), not a genuine predicted midpoint N(p_h)**; they are labelled `lagged_N_midpoint` and are only local algebraic frozen-row shadows, not global implicit solutions or replacements for the original symplectic midpoint. If a future component uses real p_h, its diagonal-CN numerator is `h*(R_h + S*(p_h-p_n)/M)`, not simply `h*R_h`. The smaller widths are arithmetic h→0 observations, not extra physical half/coarse trajectories. Exact-zero/nonfinite denominators yield explicit undefined flags/blank shadow values; negative finite denominators are retained and separately flagged. No epsilon clipping is introduced. The finite-increment identities and whole-row rescalings by1/gamma and receiver volume V are checked using binary64 arithmetic-only envelopes; these do not relax any original physical guard.

A separate six-row `coupled_CN.csv` tests a normalized two-node **constant** matrix: M=(2,3), S=(6,3), A12=6, A21=3, p_n=(2,-1), B=0. For the analytic explicit predictor `p_h=p_n+h*L*p_n/2`, diagonal-CN uses the actual manufactured neighbour p_h. Its exact rational Taylor defect is `delta-h*L*p_n-h²*L²*p_n/2 = -h³*s_i*(L²*p_n)_i/[4*(1+h*s_i/2)]`, with s_i=S_i/M_i. The declared arithmetic identity checks local second-order consistency only for this manufactured constant matrix. It proves nothing about full time-varying/coupled order and does not fabricate missing adjacent GPU histories. Three decimal widths(.01,.001,.0001) are normalized arithmetic inputs, not physical C08 runs.

There is no beta, TPI, incompressible-capacity removal or invented adjacent GPU pressure history in this component. Passing its checks cannot select a physical scheme, admit other psi/PRE/half/long runs or prove repair of negative pressure, clumping or the complete collapse.

## Outputs and later independent commands

After root full review, build only:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_pressure_row_r1_build.py --execution-authorized`

The inherited executable basename is deliberately `C08H18LateRhsR1.exe` inside the **new pressure_row build directory**; receipt/source identities distinguish it. After a separate successful build/root component admission, one absolute-path invocation may use:

`tests/outputs/c08_h18_pressure_row_r1_build/C08H18LateRhsR1.exe --check --native tests/outputs/c08_h18_n255_full3_r1/native_r1 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 tests/outputs/c08_h18_n255_full3_r1/c08_h18_n255_full3_r1 tests/outputs/c08_h18_pressure_row_r1`

Expected outputs:5000 native row records,35000 manufactured records,15000 algebraic shadow records,28 manufactured summaries and6 standalone coupled-CN records, ordinary Run.out plus completion. All original5000 final-float rate checks must pass. Force time and row-plus-CSV-output time are separately measured; neither is a controlled full-run CPU/GPU benchmark. The transient per-receiver vector stores only that receiver's stencil; no global matrix or new production particle arrays are allocated. Root must inspect future CSV/PNG analysis before any numerical/physical decision.
