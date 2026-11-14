# One original CPU step balance: author-only

New files are support/c08_h18_step_balance_r1.cpp, support/c08_h18_step_balance_r1_build.py and this note. They are frozen for root full-read. Authoring does not admit a build, Python import, component call, solver/native read or hash scan. No source, XML/BAT, PRE, public header, project, canonical executable, retained output or physical parameter is modified. A separate root admission must precede one build and then a separate admission must precede one exact component call. Physical acceptance remains false.

The completed three zero-step original CPU probes at Part30/60/90 qualified original force/RHS reproduction. They cannot measure integration or the completed pressure cap. This diagnostic restores only Part60 from the same original AS=.5, exponent=2.55, h/dp=1.8, dt=.000005, full91 typed22 native. Actual saved time is10.600004999683293s and tau=.60000499997728518s; actual completed count is2120001. It performs one CPU step from that state, rather than reconstructing a missing GPU substage or starting another trajectory. The original PRE loader/release and bedroles restore lifecycle are reused. All5000 soil IDs and1805 retained fixed IDs must remain present and normal; retired1805..2059 cannot reappear.

The builder reuses the unchanged c08_h18_storage_rhs_r1_build.py and its exact one-entry plus86 original DebugCPU-object link, including original JSphCpuSingle/JSphCpu. It generates a private shared.inc from frozen c08_h18_storage_rhs_r2.cpp with exactly two transformations: insert protected: after the Probe class opening, and rename its AppInfo diagnostic name. The includer renames the old unused main with a preprocessor macro. Map, Copy, Ledger, Restore, Assemble, headers and loader lifecycle are reused; the old three-probe Execute and main are never called. No physical translation unit is recompiled or instrumented. The generated include, actual sourceDependencies and unchanged current CPU source/header bytes versus schema2 archive are checked. Existing build closure and all source/native/PRE/runtime receipts remain bound by size/mtime. No SHA scan is introduced. The fixed executable basename remains C08H18StorageRhsR1.exe, as with r2; its unique program identity is outputs/c08_h18_step_balance_r1_build/C08H18StorageRhsR1.exe and its new build receipt.

After the existing loader/release checks, the derived StepProbe restores Part60 once. Its explicit call sequence reproduces JSphCpuSingle.cpp897–925 and the relevant outer loop1392–1418: dt=SymplecticDtPre; DemDtForce=dt*.5f; Interaction_Forces(Predictor); DtVariable(false); ComputeSymplecticPre(dt); PosInteraction_Forces(); DemDtForce=dt; RunCellDivide(true); Interaction_Forces(Corrector); DtVariable(true); ComputeSymplecticCorr(dt); PosInteraction_Forces(); SymplecticDtPre=min(ddtp,ddtc); completed RunCellDivide(true). Both original DtVariable calls and their necessary-bound rejections remain active. Moving/floating/HG/shifting/damping/relaxation/in-out/viscosity-ramp/DDT-ramp facilities omitted from this scope must be absent. No custom force, extra Darcy call, material-return substitute or extra boundary/contact call is made. Any genuine original material, wall, particle-domain or timestep failure remains failure and preserves partial output; there is no retry or gate relaxation.

TimeStep and Nstep remain exactly the restored values through both force stages and the completed divide, matching the original external ownership. Stage offsets0,dt/2,dt are descriptive columns, not solver-clock mutations. Only after completed-cap capture does the harness perform the original outer TimeStep+=dt, LastDt=dt, Nstep++. The diagnostic does not save a PART, call gauges or export another native file. The native completed count is installed as the next CPU iteration's Nstep, as in the retained restore harness; this diagnostic makes no claim of reproducing omitted previous-step CPU counters or GPU bits.

Original ComputeSymplecticPre preserves the scalar p_n and J_n bases in PorePressPrec/PoroJPrec. The half divide sorts them together with current arrays. Every half-stage capture checks their per-ID bits against restored p_n/J_n. Both predictor and corrector commits must match the literal original update bits:

Jh=Jn+(.5dt)Jn theta_n; J*=Jn+dt Jh theta_h;
ph=float(pn+(.5dt)Rn); p*=float(pn+dt Rh).

The half divide and both force calls must leave soil p/J unchanged. Completed divide must preserve J* and set pnext=0 only when current completed FS is2/3 and p*>0; every other pressure bit must remain p*. This observes the original completed-only cap after PRE buffers are freed. FS labels in non-force captures can be inherited or recomputed; force_h supplies the receiver grouping for all balance summaries. The completed FS classification need not equal force_h.

At each actual force, the reused Assemble reads the same original donor search, float kernel, actual C, p/J, theta, Ace and FS as the completed RHS probes. The literal source-ordered double rate must cast to exactly the actual float rate, with the retained final-cast allowance FLT_EPSILON*abs(literal)+float_denorm_min. With s=1-double(n0), nh=1-s/Jh, Kw=double(material Kw), define Dh=k/gamma*lap+chain/gamma. The original literal is Kw/nh*(-theta_h+k/gamma*lap+chain/gamma); no expanded custom rate is fed to the integrator.

For each soil ID, c=(Jh-s)/Kw, deltaJ=J*-Jn, deltap=pnext-pn, deltaCap=pnext-p*. The measured identity is:

deltaJ+c deltap = dt Jh Dh+c deltaCap+FP.

All terms are exported before aggregation. FP is explicitly predicted from measured source/add/cast operations, with the actual float Rh and source-ordered double Lh:

ej=(J*-Jn)-dt Jh theta_h;
ep=(p*-pn)-dt Rh;
erate=Rh-Lh;
esource=c Lh+Jh theta_h-Jh Dh;
FP=ej+c ep+dt c erate+dt esource.

The pressure double-add residual (pn+dt Rh)-pn-dt Rh and final float-cast residual p*-(pn+dt Rh) are exported separately; ep also retains subtraction/reassociation rounding. esource accounts for the actual floating porosity derivation/coefficient and source ordering instead of assuming their algebra is exact in double. Closure is deltaJ+c deltap-dt Jh Dh-c deltaCap-FP. Its predeclared arithmetic-only allowance is gamma128 times the sum of absolute source/state/update operands listed in the source plus128 double_denorm_min, where u=DBL_EPSILON/2 and gamma_m=m u/(1-m u). This covers double subtraction/reassociation; it is not a new physical tolerance and cannot be retuned after output. Strict original update/cap bit checks independently protect against a wrongly large arithmetic allowance.

The separate compression quadrature defect is E=Kw[log((J*-s)/(Jn-s))-(J*-Jn)/(Jh-s)]. Its mathematically identical log1p((J*-Jn)/(Jn-s)) evaluation avoids forming a ratio near1 before taking its logarithm. It is a computed floating-point diagnostic in Pa, including remaining arithmetic effects, without a new acceptance threshold or a claim of exact temporal truncation error. V0=MassFluid/RhopZero multiplies local balance terms. summary.csv reports their sums for all/interior/FS force_h receivers, sumV0 E and max abs E. Global arithmetic allowance adds propagated local budgets and gamma_(16(N+1)) times accumulated absolute weighted terms. These quantities diagnose one step and do not establish a boundary-flux conservation law, conserved water mass, mechanical energy closure or the full .9s pressure history.

NoPen plane projection remains inside both original integrator calls. Diagnostic displacement/velocity differences compare actual x/z and vx/vz with the original unprojected predictor/corrector formulas. They may include ordinary coordinate rounding. They are observations only: no extra contact correction, force reconstruction or reaction work is added. contact_reaction_closed is false; J/theta/p are not retrospectively corrected for projection. The stage split is therefore explicit even when a contact projection occurs.

Fresh component outputs are outputs/c08_h18_step_balance_r1/{stages.csv,balance.csv,summary.csv,completion.json,Run.out}. Expected rows are35000 stage records (restored_n,force_n,half_before_divide,half_after_divide,force_h,raw_full,completed_cap),5000 balances and3 summaries. Non-force rate/Ace fields are empty. Every stage records actual solver clocks, descriptive stage offset, primary J/p/P0, positions/velocities, FS/theta and PRE ownership/bases. balance.csv contains all update, hydraulic, cap, FP, E and contact-observation terms. Completion is only emitted after all rows/bit/arithmetic checks; actual successful owned call and unchanged protected inputs are still separately required.

Future build-only command after root full-read and separate admission:
`D:/anaconda3/python.exe -B tests/support/c08_h18_step_balance_r1_build.py --execution-authorized`

Future exact component command after successful build and separate execution admission:
`tests/outputs/c08_h18_step_balance_r1_build/C08H18StorageRhsR1.exe --check --native tests/outputs/c08_h18_as05_n255_r1/native_r1 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 tests/outputs/c08_h18_as05_n255_r1/c08_h18_as05_n255_r1 tests/outputs/c08_h18_step_balance_r1`

Commands are documented only and were not run during authoring. New work is limited to this one diagnostic step; no new trajectory, PRE, half-step chain, new physical parameter, policy or broad physical gate is admitted.
