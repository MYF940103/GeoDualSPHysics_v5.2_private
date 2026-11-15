# C08 paired-C/bare CPU actual-MFG component r1

Status: author only. New support/c08_h18_paircbare_cpu_r1.cpp, its _build.py and this note are prepared for root's full review. No prepare/build/program/component/API/native/solver/VTK/PRE/Git/SHA action has been executed by the author. No public source, old component, program, object, input, snapshot or result is changed. A later passed component is implementation evidence, not physical admission or a reason to reuse an old failed tag.

## One isolated pressure weight, one new label

Starting from the full current schema2/law2 archive, the private JSphCpu.cpp has exactly one numeric line replacement:

old: w = Vj * d·(Gi+Gj) / (r² + Eta²)

new: w = Vj * d·(Gi+Gj) / r².

The original paired numerator, float-kernel evaluation, double neighbor geometry/volume and original support exclusion r²<ALMOSTZERO are unchanged. The source LP and Lx share this weight; Gp, acceleration divergence Da, gradJ/variable-k chain, raw-FS/Taylor multiplier, wall policies, force, stress, material and time integration expressions are untouched. The bare denominator never creates a new zero-distance division in this existing guarded loop; this statement is not a proof of conditioning or stability for an arbitrary geometry.

The independent Assemble helper receives exactly the same denominator-only change. The builder checks both new lines equal the original lines with only the denominator suffix replaced. It reverses the complete private physical source to the archived raw bytes, and separately reverses the helper weight after the diagnostic AppInfo label change. Seven other generated numeric fragments are copied unchanged; headers retain the complete archived160-header ABI. There is no source conditional weight or OFF variant. C08_H18_PAIR_C_BARE=1 closes the new entry's compile qualification only; the private physical source contains the direct denominator edit and no new physical branch/interface.

For a fixed geometry, common kernel and matching paired C values, the LP-only edge coefficient retains volume-weighted pair reciprocity: w_ij/Vj = w_ji/Vi in exact arithmetic. This is not a claim that the full Taylor-corrected variable-k operator, boundaries or coupled mechanics are reciprocal, dissipative or mass conservative. It does not prove equivalence to all of Lian's second-order discretization. Existing original-pair/Eta and receiver-C/bare actual-MFG outputs provide the two comparison axes; no result is assumed from the previous shadow analysis.

## Reused closed manufactured fixture

The new entry is a mechanical derivative of the passed Lstar CPU package with a new stage c08_h18_paircbare_cpu_r1 and --check-paircbare. It preserves the original14-restore ordering of the two retained trajectories so that cell sorting/defined wall caches can be checked against the existing CPU control;12 states only sort. Only original AS03 saved Parts29 and30 call the actual original force. This is a CPU saved-state recomputation, not the historical GPU substage force.

Each selected state then uses the same H/N/X fields, with constant J=1,theta=0 and the real C/FS/ghost lifecycle. Let b be the actual original body vector converted from float, p=ρw b·x+p1, a_s=−grad(p1)/ρw and Ace=a_s−b; then the intended continuous joint drive grad(p)+ρw Ace is zero. H has p1=0; N has p1=.5*1000*z²; X has p1=1000*(x−2)*z². Gravity enters once and fixed P0 remains an inherited reference, not the manufactured p. Negative manufactured pressures are not clipped.

Counts remain2 original force calls, each including one actual Darcy rate;6 additional actual manufactured rate API calls; and6 analytic-ghost expression oracles, for8 actual API rates total. There are60000soil rows in12 groups, actualProof30000 and analytic30000, plus12 summaries, actual active-wall rows,2 baselines,14 routes and2 original signed-clock rows. The analytic oracle changes only fixed p/Ace on the same manufactured J/C/FS/quadrature. It never calls the actual API or writes a fake Rate field to satisfy an actualProof guard. Real-wall J roundoff is retained, not reset after reconstruction. MFG velocities/accelerations are prescribed in memory and are not a manufactured stress equilibrium or a physical receiver time step.

Every actualProof group independently reconstructs the new source-ordered literal rate and requires all30000 real float API values to match float(literal) bits. The unchanged float-write, expanded-double and donor-partition arithmetic budgets remain exactly those in rhs_expression.inc and the passed entry: finite domain; original float budget FLT_EPSILON*abs(literal)+float_denorm_min; expanded budget that float budget plus the original counted double budget; and original partition-vs-expanded double budget. No new physical tolerance is substituted. Analytic generated-float rows obey the same arithmetic limits but have actual_API_rate_bit_reconciled=0. Failure must preserve actual data and first cause; no budget is relaxed or retry launched.

## Real control and output contract

The changed bare LP/Lx intentionally changes the rate. The old-rate58th scalar is not compared; the other57 upstream controls remain, giving570000 scalar bit checks over10000soil baseline records. These cover original AceXZ/planarY,theta,FS,C, six Rσ and raw/G1 gradients/pass theta. Additional internal literal reconstruction retains10000theta and60000Rσ bit checks. Original5us natural/force/wave/pore/k-gradient safety and all initial material/IDs22/ledger/P0/κ/FS/clock/geometry/source guards remain. There are zero physical steps, material returns, filtering, RV commits or GPU operations.

The old OFF SameFile function and its61MB six-file byte scan are removed, along with the old OFF mode and protected six-CSV comparison loop. Existing original MFG CSVs are only size/mtime-bound as fixture evidence by the builder; they are not re-read for an OFF byte comparison. Existing original native/gradient controls retain their established loader and safeguards. Completion explicitly records pair_C_bare_enabled=true, receiver_C_bare_enabled=false, external_CPU_rate_compared_to_old=false and old_full_CSV_byte_comparison_performed=false. It never reuses an old stage to pretend that this changed operator was an OFF regression.

The six source CSV names and column schemas stay manufactured.csv,summary.csv,walls.csv,baseline.csv,restore_route.csv,selected_clocks.csv. Every5000-ID group and negative/extreme value is retained for one later pure offline same-ID comparison with sealed original and receiver-C/bare tables. Legal flat-bed and interior masks stay the same predeclared fixture masks; empty cohorts remain empty and no scope is moved to improve a result. Continuous zero-drive residuals are scientific truncation measures, not a5Pa acceptance test or proof that globally side/FS-incompatible fields define a legal initial-boundary problem.

## Build-only and later independent root actions

Only one DebugCPU build is supported. The builder requires the passed original joint build/check and passed actual Lstar CPU_ON fixture (570k upstream/30k actual-rate bits); these are implementation prerequisites, not selection of receiver-C/bare physics. It uses the original authoritative MSVC14.36 CL/link recipes, /Od /MTd /RTC1 /fp:precise /openmp, current law2 archived headers and7 runtime companions. Link exactly85 retained original objects +1 newly compiled private JSphCpu +1 newly compiled entry =87. Build calls are two CL and one link; no component/help/test/solver is run automatically. Fresh output is tests/outputs/c08_h18_paircbare_cpu_r1_build and receipt logs/c08_h18_paircbare_cpu_r1.build.json; all existing complete/partial paths block overwrite. Necessary stat/byte source checks replace any SHA sweep.

Root-only future build command, after independent review/admission:

D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_paircbare_cpu_r1_build.py --execution-authorized

The separate future component uses C08H18PairCBareCpuR1.exe --check-paircbare with original -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1, the retained AS03 short seed and exclusive tests/outputs/c08_h18_paircbare_cpu_r1. This note does not admit or invoke it. Actual component/check receipts and numerical tables remain necessary before root decides any GPU Release implementation or dynamic window; there is no new half, PRE, matrix solve, long trajectory, parameter sweep or automatic other-psi step.
