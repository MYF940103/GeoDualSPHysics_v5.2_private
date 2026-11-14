# H1.8 RV onset force/Darcy probe r1 — author-only

## Scope and files

Only new support/c08_h18_rv_onset_force_r1.cpp, support/c08_h18_rv_onset_force_r1_build.py and this note are authored. No prepare/build/program/probe/solver/reader/VTK/Git/SHA/queue was executed. Root must fully read them, finish the existing localization review and create its unique selection CSV before separately admitting the build. Building never invokes the component. A later component call is a separate root decision.

The closed states are the already certified original AS03 SHORT91 and new RV91 trajectories at Parts40/42/43/76/90. Aliases original and rv map respectively to “Retained original AS03” and “RV alpha0.1”. Completed steps are2080001/2084001/2086001/2152001/2180000; actual times are read from each unchanged11-column clock CSV, never n*dt. Both trajectories must have the same actual time at each selected part. In particular this is not the old full301 Part90, whose completed step2180001 differs from the short91 forced endpoint2180000.

Native inputs:

- outputs/c08_h18_as03_n255_r1/native_r1
- outputs/c08_h18_rv_window_GPU_r2/native_r1

The existing passed window/localization/native checks provide their program/source/PRE and native provenance. No new native tool is needed and no BI4 is decoded again. The new loader seeks only the five requested records per file:91 frames,6805 actual IDs,22 arrays,212 typed bytes per particle,12-byte header and8-byte time per record. It reads the exact existing array order/dtypes. SigmaState_ij is xy,yz,xz. Ten selected records are about14.4MB, not a scan of every raw native state. The original signed dterror field is copied as part of each selected original clock row and checked with its existing signed<=1e-14 rule, never made absolute or rewritten.

## Unique material-pair selection

Root writes only configs/c08_h18_rv_onset_force_r1.selection.csv, columns:

case,part,completed_step,time_s,id_i,id_j,selection_rule

The case is the TARGET alias original or rv. selection_rule carries SOURCE provenance as sourcealias:actual_rule from the passed localization selection table, for example rv:closest_final_pair only if that exact rule actually exists. The new component normalizes the unordered material IDs and verifies that (IDpair,sourcealias:rule) exists in figures/c08_h18_rv_localization_review_r1_representative_selection.csv. It does not demand that a pair was selected in the target case. Builder also binds the actual passed localization check and its catalog/selection stats.

Root may choose a subset of the at-most-eight representatives from four preregistered rules in each source case. Every root-selected unordered pair must appear in BOTH target trajectories at ALL five closed states; duplicate target case/part/IDpair rows are rejected. The actual row step/time must match the certified target native clock. No arbitrary native path, case, part, IDs or physical variant is exposed by CLI. Source provenance does not imply the pair is a neighbor in every target state.

A pair outside the actual RV graph remains in pairs/focus outputs: direct_neighbor=false, beta=0 and direct RV force=0. Its actual distance, fitted affine/residual velocity, all-neighbor RV relative acceleration and curvature remain reported. It is never discarded because it looks healthy or has moved beyond support.

## Source/build boundary

The builder reuses the already passed c08_h18_rvisc_force_r1 DebugCPU source closure and its actual CL/link calls: one new entry object plus86 original physical objects,160 archived private headers and7 runtime files. There is no new physical CPU/GPU TU or public-header/class ABI change, no MSBuild of the project and no replacement of a canonical executable. The build output is fresh outputs/c08_h18_rv_onset_force_r1_build; prior outputs/partials/logs refuse overwrite.

Six derived includes are emitted there only during the separately admitted build:

- shared91.inc: mechanical copy of the old frozen shared protected Probe prefix only, with AppInfo/tag/date, closed91/5-part constants, original clock-row capture and exact selected clock checks. The unused old Probe::Execute and old main are removed. Actual Map/Copy/Restore/Ledger/Unchanged/Assemble numerical bodies are retained.
- setup.inc, rhs_literal.inc, interior_mask.inc and rvisc_math.inc are exact old bytes. Setup initializes the original CPU case, loads the already certified same-material GPU PRE and performs only the one-time role retirement. It does not integrate a10s PRE or reset its histories.
- eigen.inc is the original archived CPU float ComputeSymmetricEigen3D body with only a diagnostic name change. It does not alter the linked physical artificial-stress implementation.

The compiler remains the original MSVC14.36 DebugCPU /Od /MTd /RTC1 /fp:precise /openmp /std:c++17 recipe withCPU1 runtime. The actual87 link objects and dependencies are checked; original physical objects are not recompiled. Metadata/source bindings use necessary size/mtime checks, not repeated source/object/BI4 SHA scans.

## Real CPU cell graph and zero-advance lifecycle

The original rvisc force component used an all-pairs Graph constructor. The new entry instead traverses the actual restored CPU DivData with nsearch::Init(...false...) / ParticleRange, accepting the same current RV double support r²<4H² and float(r²) Wendland kernel weight, current V/rho/tau and native-ID canonical beta multiplication. It checks unique directed membership and each genuine reverse edge, then canonicalizes unique edges before the UNCHANGED LS Fit/Evaluate math and budgets. Cost is cell-neighbor traversal plus edge sorting, not a5000² scan; it is not evidence of GPU bit-identical traversal or accumulation.

For each already saved state, the original loader assigns sigma/κ/J/p/P0/x/v by material ID, rebuilds the real CPU cells while suppressing only restoration-time cap/Shepard side effects, restores those original options and recopies the actual saved fields. Then:

1. One genuine original Interaction_Forces(SymCorrector), which includes one complete original Darcy rate, on this completed saved state. It recomputes wall ghosts, FS, C, theta and Rsigma according to the original CPU policy.
2. One unchanged complete Darcy recompute; all5000 rate float bits must equal the first CPU result. The original source-ordered literal, final-float and seven-channel arithmetic budgets are enforced in both passes.
3. Construct the CPU-cell RV graph; apply the unchanged alpha.1 Evaluate and once-final float Ace commit only after original rank/null/work/net/torque/commit certificates. Translation/centered full-affine/rotation controls use this same graph, no physical commit and no extra force/Darcy calls.
4. Recompute the COMPLETE original Darcy, including rebuilt real wall acceleration. Again enforce original literal/final-float/seven-channel budgets and original5us force/wave/pore/k-gradient necessary bounds.
5. Preserve all5000 primary sigma/κ/J/p/P0/x/v bits. Fresh FS, theta, C and original AS scratch remain fixed across the two Darcy legs and RV commit. All1805 wall role/physical fields and effective active-wall scratch checks retain their established scope; ignored modes/scratch are not read. Wall Ace may legitimately change when recomputed from changed soil Ace.
6. Free the original force scratch and restore the selected saved state before the next case/part. No position/velocity/J/pressure integration, constitutive return, filter or timestep/clock advancement is called.

This is an instantaneous original-CPU OFF-versus-added-RV comparison ON EACH existing trajectory, not an alternate trajectory without RV history. The saved RV state already contains its prior evolution; the component first recomputes bare original force and only then adds the current force-stage RV once. Native22 does not contain saved Ace, Rsigma or pore-rate arrays, so no new-state comparison to an unavailable GPU force-stage bit reference is invented. External_GPU_RHS_bit_rows=0;50000 CPU zero-change rate-bit checks and150000 source-literal reconciliations are real component gates. Saved PoroThetaLastStage and fresh CPU theta are distinct time-layer quantities; this component is not a replay of the GPU's previous half-stage.

## Outputs and interpretations

Exclusive new directory outputs/c08_h18_rv_onset_force_r1:

- soil.csv:50000 rows, current material/ledger and native/fresh FS; base/candidate Ace, ideal and float-committed RV increment; actual rates and all seven original RHS channels plus independent eighth numeric residual. The eighth is actual float rate minus seven-channel expanded sum, not a physical source.
- pairs.csv: one row per root selection, distance/rdot/curvature; direct-neighbor/beta and affine/residual radial velocities; direct-pair force/relative acceleration, ALL-neighbor ideal and committed RV relative acceleration, bare/candidate total rddot. A direct pair is not the complete force on either node.
- focus.csv: both material endpoints per selected pair; native p/P0/J/κ, saved/fresh FS, original CPU float total-stress eigenvalues and positive sum, double effective/total normal stress and ACTUAL original AS tensor n·R_AS·n, original/candidate rates and LS matrix. Eigenvalues use the same float input convention as the real CPU AS helper; n·R_AS·n is a tensor projection, not a separately isolated AS pair force.
- metrics.csv:10 rows, actual wall partitions, original/candidate rate norms, conditional sum(nV/Kw·p·deltaR), original necessary bounds and original RV certificates.
- manufactured.csv:30 same-graph scratch rows. selected_clocks.csv:10 unchanged original11-field rows with only a leading case alias. completion.json records the actual fixed counts and limitations.

Counts if genuinely successful:10 original force calls,30 complete Darcy calls including20 extra recomputes,20 DtVariable(false) calls,0 physical updates,0 material returns,0 new reader/VTK/solver invocations. No wall-clock speedup or solve-time estimate is inferred; this is bounded fixed-state work rather than600000 new updates.

The interpretation remains conditional: an attractive residual pair is possible even with global dissipative RV work; affine-null does not guarantee spacing or regularize all plastic localization. Full Darcy can change with RV Ace even though that stage's theta is fixed; later pressure may change total-AS spectra, but the probe does not advance that loop. Storage weighting is not fluid mass or complete coupled energy. A valid certificate, zero-change bit check, smaller deltaR or repulsive selected pair is not physical/paper acceptance or permission for3s/otherψ. Failures/partials and their first true error must be preserved, not bypassed by changing thresholds or forcing a neighboring pair.

## Commands for later root review, not executed

Build-only after all source/input artifacts are frozen and root selection exists:

D:/Anaconda3/python.exe -B tests/support/c08_h18_rv_onset_force_r1_build.py --execution-authorized

A separately reviewed single component invocation would use the newly built C08H18RvOnsetForceR1.exe, --check --selection tests/configs/c08_h18_rv_onset_force_r1.selection.csv, -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1, the actual original SHORT seed outputs/c08_h18_as03_n255_r1/c08_h18_as03_n255_r1 and fresh outputs/c08_h18_rv_onset_force_r1. Root must bind the passed build and current selection/native/seed/PRE stats before such a call. The builder does not run it, and this note does not create a run admission or notification mechanism. A later scientific review/plot script is a separate artifact if needed; none is authored here.
