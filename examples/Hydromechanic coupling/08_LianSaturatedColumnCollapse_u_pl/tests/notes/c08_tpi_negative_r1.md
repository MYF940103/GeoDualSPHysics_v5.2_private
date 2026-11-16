# C08 M0/TPI negative-pressure candidate — author preparation r1

Only new author assets are support/c08_tpi_negative_r1.h, support/c08_tpi_negative_prepare_r1.py and this design. No public or historical frozen source, XML/BAT, program/PRE, object, native data, active ψ−5 job, or completed result is changed. Author does not execute the generator, build, program/help, solver, reader, VTK, Git or SHA. Root must fully read these files and separately authorize preparation only; later builds and each bounded physical job require separate review. Existing output or receipt prevents overwrite/retry. This is not a server/formal package.

## Explicit numerical model

OFF is absent C08_TPI_NEGATIVE (or empty); it executes the original finite-Kw explicit midpoint path without private allocations/files. ON must be exact1. ON additionally requires C08_TPI_NEGATIVE_BETA to be exact0 or0.04, with beta units1/m. Root independently chooses beta0 implementation versus beta.04 diagnostic; the generator selects neither and starts nothing. Alpha is fixed.5. C08_HG_OPT_H18, C08_HG_CACHED_H18 and the earlier C08_HG_H18 must all be absent and HourglassCpu/SoilHourglassXi zero. HG is not used in this large-deformation candidate.

ON replaces the finite-Kw pressure equation with an M0 TPI extension. Beta0 ON is ordinary M0/TPI, **not** the old finite-Kw model; only OFF is the old model. Actual committed p_n and p_(n−1) are ID-owned float histories. The helper keeps the true double extrapolate

pAlpha = double(pn) + .5 * (double(pn) − double(previous)).

The solid predictor uses its once-cast float guess, with existing true Dirichlet priority. Original full Symplectic mechanics/material/J updates still run exactly once. After the existing completed RunCellDivide, an extra genuine force pass evaluates the actual new geometry/J/sigma and float q, under the original source clock n and original AS/AV/wall/acceleration assembly. This extra pass is not a material update or a velocity kick. It produces actual double endpoint Rgamma and the declared raw-LP split diagonal S. No new RunCellDivide, plane projection/NoPen, Shepard, material return or J advance occurs inside this extra pass.

Rgamma = −gamma_ref * theta_endpoint + k_i * lap(q) + chain(q,J,a),
S_LP = −k_i * sum(w_ij),
c = (pn < 0 ? beta : 0) / dt,
p_raw = q + [Rgamma + c * (pAlpha − q)] / (S_LP + c).

The c*(pAlpha−q) compensation is retained: actual float/source-BC q need not equal the true double history extrapolate. The local negative branch uses old **total** pn<0 only, inside the admitted plastic case; pn=0 uses beta0 as an explicitly selected tie rule. No hidden current-plastic/κ threshold is added. The code never clamps negative p. True Dirichlet rows override the row. Every unconstrained S and denominator must be finite/strictly positive; no epsilon, row exclusion or regularizing sign repair is introduced. Raw pressure is cast to float once on final commit.

The current pair-symmetric C/Eta²/raw-FS/variable-k chain spatial row is deliberately retained. S_LP is its raw-LP split, not the full Taylor/chain/coupled Jacobian. The other pressure-dependent terms are explicitly evaluated at the actual endpoint q and source acceleration. Therefore this is an M0/TPI **original-space Symplectic-endpoint extension**, not literal Lian Ci-only Eq33, the paper LF schedule, a global implicit solve, or a proven second-order/stable method. Finite-Kw original rates and all original necessary-step checks remain evaluated as implementation guards even though their explicit pressure updates are skipped on ON. No storage/J equation is silently changed to d(Mp)/dt.

## History, PRE and boundaries

C08 is limited to real bed-last schema2/law2 same-material handoff: source7060, keepfalse/retire original IDs1805..2059, receiver6805 with1805 fixed IDs0..1804 and5000 soil IDs2060..7059, Wendland H/dp1.8, dp.04, dt5us, event10s/source completed2M. Only after the existing real RunGravityPreloadRelease succeeds does Init create new cold pressure history previous=actual pn. It does **not** assign/reset pressure, P0, sigma, kappa, J, density or positions. The old PRE has no5us pressure history; cold start is explicit and is not full-state TPI restart. Source/candidate material contracts must still match via the original loader.

The original schema2 CPU base is logs/c08_preload_schema2_ReleaseCPU_r1.build.json and its archived full_source.zip; it contains FunFixedPlaneContact.h and both ComputeSymplecticPre/Corr plane-contact paths. The generator changes only private JSphCpu.cpp/JSphCpuSingle.cpp overlays plus the new helper, leaving the class/CTE ABI and all other frozen objects unchanged. It must prove every literal anchor count exactly once and retain original compiler/link source compatibility. Its output is source only; no build is authorized here. It does not carry HG/cached-material/private GPU objects into the CPU candidate.

During temporary pAlpha geometry/ghost evaluation, only the original **completed positive-FS cap** is bypassed, as in the earlier X0 prototype. True Dirichlet enforcement and periodic logic are not bypassed. Release Shepard staysOFF from the real release; the third force does not filter. After final p_raw is written, call the original ApplyPorePressureBoundaries directly, retain the original completed-only p<=0 free-seepage rule and rotate full pressure history exactly once. The ghost fields may reflect the last real force's q, as declared; the next original force reconstructs them. No new hydraulic reaction closure is claimed. ReactionClosed remainsfalse.

Snapshot every soil's actual x/v/sigma/kappa/P0/J/q before the third force and require all seven typed objects bitwise unchanged after it. Ace/theta/rate/ghost scratch may be recomputed. Record theta_half used by original J integration separately from endpoint theta used by the pressure row; saved PoroThetaLastStage may now be endpoint theta and must not be relabelled half-step theta. Failed row/force/final boundary does not rotate pressure history or invent a new saved native state. The original stage/core/finite/material/geometry/ledger/natural-step gates remain active.

The helper allows at most600000 new updates as an outer implementation bound, never automatically runs that many. Root must separately admit a much shorter first window and actual owner/nsteps cap; nominal13s is not a guarantee of exactly600000 scalar-clock steps. No extra half, otherψ or source PRE is admitted.

## Evidence, outputs and minimum tests

Reuse c08_tpi_row_r1, c08_tpi_coupled_r1, old beta0 CPU X0 and actual fixed-state C08 row evidence. Prior CPU X0 observed about45% extra loop time and mixed error indicators; do not promise a free speedup. The no-AV constant-negative-branch growth counterexample does not prove the real compression-only AV C08 fails. AV is waveform/direction dependent, not one fixed damping coefficient. Neither success nor failure is assumed.

Needed before any C08 physical admission: double pAlpha/float q compensation; beta0 and negative/zero/positive old-p branch; row scaling/units/denominator rejection; cold history, reorder/retire and failed-transaction no-commit; old OFF all22/clock/signed exact prefix; true PRE P0/J/kappa inheritance; constant/variable-k hydraulic products; same committed mechanics and actual endpoint field invariance. CPU build/debug/component evidence precedes any isolated GPU work. A fixed-state row alone cannot accept a trajectory.

The private policy/summary explicitly records M0, alpha, beta units/branch, cold-start and no exact restart/literalLF/global implicit/ReactionClosed/physical acceptance. C08TpiNegative.csv records all5000 soil histories only at actual saves for the separately admitted short window: source/actual clock, pn/previous/double pAlpha/actual float q, direct double S/R, effective beta/denominator, raw/final pressure, Jn/Jhalf/Jfull, theta_half/endpoint, BC flags and one-per-step counters. This is a bounded implementation diagnostic; do not produce an unreviewed large full3s CSV chain or claim snapshots recover unsaved stages. Original native22 and original IDs/clock/signed/P0/J/kappa/FS/ledger checks remain separate mandatory review.

Future prepare-only command after root review: D:/anaconda3/python.exe -X utf8 -B tests/support/c08_tpi_negative_prepare_r1.py --execution-authorized . It must create a fresh outputs/c08_tpi_negative_r1_build and logs/c08_tpi_negative_r1.prepare.json, never invoke a build or solver. Root must inspect source_diff and confirm current archived-source anchors and the new helper before any build admission.

## Pre-prepare author corrections

Root static review found these issues before any generator/build/run consumed this author draft. They were corrected in place under explicit root authorization: reject all three known HG activation environment variables (including the earlier C08_HG_H18); true Dirichlet rows report effective beta0/beta_activefalse and are never counted as actual beta rows; retain old negative sign counts separately; require positive finite half J; require exactly7×5000×commits endpoint typed-field bit checks; fix the corCalls member spelling consistently. No old X0/frozen/public file changed and no physical output was produced. Root must re-read the corrected regions before freezing this draft.
