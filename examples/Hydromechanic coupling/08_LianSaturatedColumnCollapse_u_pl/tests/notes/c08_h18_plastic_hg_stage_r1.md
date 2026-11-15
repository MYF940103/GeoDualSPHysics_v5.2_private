# Private plastic-HG actual CPU-stage feasibility

AUTHOR ONLY, four new files: support/c08_h18_plastic_hg_stage_r1.hpp, .cpp, _build.py, and this note. No build, program/help, native read, analysis, solver, GPU, Git or SHA action was executed by the authors. Root must separately review and admit a build, and later the one bounded component. No public source/ABI, formal input, frozen program, original result or PRE is modified. No long window, other psi, half/reference chain or automatic next job follows.

## Closed actual state and eight-update scope

Only the existing AS03 full301 decoded native Parts38/76 (completed2076001/2152001) are admitted. The unchanged original small seed/normal triple and original schema2 Wendland psi0 PRE are reused by the existing real class initialization/handoff; the10s preload is NOT recalculated. Original sigma/kappa/J/p/P0 are restored from the selected actual saved states, including all nonzero plastic history. The candidate e is newly cold-zero at each late snapshot. This is neither recovery of missing HG history nor full-state restart.

Each source performs exactly: one unmodified ComputeStep_Sym full update, one manually spelled original OFF full update, and two successive candidate-ON updates. Thus2 source reads,6 branch restores,2 original-method calls,6 manual updates and8 actual in-memory updates total. The ON two-step legs do not Restore between their updates. No solver loop, native writer, BI4/VTK/particle series or formal physical trajectory is produced.

The source physical settings stay HGoff in the original program, AS.3/n2.55, AV.1, Wendland H1.8,5us, original fixed-plane NoPen/bedroles/keepfalse, current-J density/conductivity and CompletedOnly positive-FS projection. The private candidate uses xi=.1 internally. There is no change of AS, AV, Darcy operator, material parameters, wall policy or boundary pressure clipping. Existing open contact/Darcy reaction limitations remain.

## Source reuse, ABI and OFF control

The build retains exactly86 original DebugCPU physical objects and160 archived headers, replacing only the old diagnostic entry with one new entry (87 objects total). It adopts the actual passed as03_step CL/link recipe and7 companion files. No physical TU is recompiled. The two generated includes are reversible derivatives of the sealed AS03 RHS loader and original StepState/StepProbe capture/material helper prefix: protected diagnostic access and AppInfo label only, plus closing the extracted helper class. No friend or public class layout change occurs.

The entry calls original ComputeStep_Sym for the reference. Manual OFF follows original predictor force/DtVariable/Pre/cleanup/divide/corrector force/DtVariable/Corr/cleanup/SymplecticDtPre order, then the same outer completed divide and one scalar TimeStep+=dt, LastDt assignment and Nstep++. OFF never builds/evaluates a candidate graph and never adds an arithmetic zero to Ace. The extra pure material evaluation is validated not to alter its final result by the OFF control.

Each branch has an independent new constant JDsFixedDt(5us) object. Both the saved original and fresh object must have empty GetFile and exactly5us. RAII restores the original pointer and destroys only the new object; caches/tables are not copied. Restore also explicitly restores TimeStep/Nstep, LastDt and SymplecticDtPre. Signed dt error must be finite, nonempty (not -DBL_MAX) and <=the original1e-14 gate. It is never replaced by abs(error) or zero.

Original and manual OFF completed states are compared by native ID over the CPU map corresponding to all22 export fields, including FS/FSnormal, P0, J/n/V/rho/k/theta, actual double sigma, float legacy stress views and actual outer time/step/LastDt/SymDt/dterror. This gives220000 grouped field checks across2x5000, not a new native-file byte proof. The legacy float/excess views are explicitly derived from the identical internal fields; no native exporter was called. The first mismatch identifies source part, native ID and field and aborts. Force scratch is not claimed to be native22. All original active soil primaries are checked unchanged across each force; fixed ghost fields may legitimately be rebuilt.

An immutable P0 map is captured from each actual source snapshot by ID. It is checked before/after every retained Capture and in the completed CPU map. No tautological or reconstructed-zero P0 comparison is used. Native source P0/PRE inheritance was already independently qualified; this component does not reread1001 PRE frames.

## Actual material-return gamma and unchanged commits

At the actual n force, a duplicate EvaluateMaterial uses exactly Sigma_n + (dt/2)R_sigma and old kappa. At actual h force it uses SigmaPrec_n + dt R_sigma_h and the still-old kappa. The named six source assignments, StSoilCte/DPCtes/StrainSoftening and PartBegin&&StrainSoftening trigger follow FunSoilMaterial/ComputeSymplectic. Result policy is explicit:

- Elastic: gamma=1, including zero trial q.
- Smooth: returned_q/trial_q, requiring finite trial_q>0 and gamma in[0,1].
- Apex or TensionRepair: gamma=0 by this new DP/HG hypothesis.
- Invalid/nonadmissible status, nonfinite values or gamma outside[0,1]: reject, never clip.

Per-row g_ij=(gamma_i+gamma_j)/2 is used in the new HG drive only, as suggested by Zhang2025 Eq32–34; DP/apex/tension handling and the full adjoint/normalized memory are NOT the paper's literal validated J2 implementation. Kappa is never used as a proxy for current plastic activity.

The duplicate result is retained until the unmodified original Pre/Corr call runs. All six actual double stress components must match it bitwise. Predictor kappa must equal old kappa; full kappa must equal the returned original policy value. These420000 scalar checks cover60k duplicate evaluations. stage_nodes calls this same_input_shadow_status: the original unmodified method's local Status is not directly instrumented. The matching result/output establishes same-input correspondence, not a hidden production cache. Original internal material calls are80000 from the closed5000-soil source loops; duplicate overhead is60000 and is disclosed.

## Candidate operator, history and rotation

The private header uses the actual current stage5000 native soil positions/float velocities, single-J volume and original mixture inertia. Its bounded head/next cell graph follows the original nonperiodic HG traversal; it is not a49-point O(N^2) enlargement. H/support/Bwen/G come directly from CSP/current original constants; positive current volumes/inertia, strict support and noncoincidence, full-rank original LS condition<1e8 and full5us<=.2/sqrt(lambda bound) are required. No eigen/pinv/ridge or relaxed rank threshold is introduced. The complete P^T includes all LS backpropagation.

The independent active directed-ID energy variable is e, D=xi*G*Vi*Vj*w/2 and u=sqrt(D)Pv. Existing e is not multiplied by the newest gamma. Every stage starts from the same committed e_n: predictor half trial does not commit, and h full trial is not based on e_pred. New rows get exact zero e; dead-row .5|e|^2 is recorded. Only the validated full trial commits after original full update, completed divide, clock/safety checks. Its same-generation predictor trial is required by Commit. The committed edge set is the accepted h-stage graph; a later stage resolves its own births/deaths by ID.

For each receiver Omega=.5(L-L^T) from the HG LS. In xz coordinates the scalar rotation rate is (L_zx-L_xz)/2. Each trial applies a half exact rotation, the already passed fixed-u/g unloading contract, then another half rotation. The force uses the UNROTATED middle Ie/T through current P^T/sqrt(D), as specified. Taylor cos/sin with explicit remainder and outward arithmetic bounds certify the small rotations; no assumed libm ULP accuracy is substituted. The retained cumulative small-rotation limit is<.01rad, using max of n/h stage omega bounds. This is explicitly NOT the legacy n+1 endpoint spin measurement, finite-rotation ODE qualification or permission to remove the production guard. A long collapse would need separate objective-transport evidence.

The exact-zero drive exception is narrow: every actual donor's two stored velocity components must be bit-identical to the receiver. Its computed LS four entries and u must first satisfy the zero arithmetic certificates. Only then is ExactStep supplied the analytically known constant-patch zero. P/PT/moments and any old e are retained. Small residual, general affine, computed-value zero, mixed signed zero or an uncertain positive Z do NOT get clipped. Uncertifiable nonconstant domains remain a true implementation-domain failure, not a fabricated rank/physical failure.

## Complete hydraulic feedback, arithmetic and real work

Original Interaction_Forces has already computed a no-HG Darcy rate. ON then adds HG force/current mixture mass to actual float Ace, verifies its float cast/force-commit arithmetic bound, calls the COMPLETE original ComputeDynamicPorePressureRateCpu again, and recomputes AceMax with the original ComputeAceMax(Np-Npb,Acec+Npb,Codec+Npb). The wrapper itself recomputes dynamic wall acceleration before all Darcy pressure/acceleration/variable-k terms. No gravity is added by this component, no pressure-only term is patched and no stale acceleration limit is used. Only then does original DtVariable run. Thus16 original Darcy calls include8 ON rates that are deliberately discarded, and8 additional full calls overwrite them; this is24 calls, not production-efficiency evidence.

The original force literal/final-float pressure checks, source-order J/p predictor/corrector bit checks, completed positive-only FS cap, pressure/J arithmetic balance, finite/saturated ledger, kappa nondecrease, P0 inheritance and geometry gates remain. Failures preserve actual logs/partials and stop; no rerun, threshold change or unsaved-time reconstruction follows.

The B error mechanism requires IEEE binary64, round-to-nearest in both fegetround and MXCSR bits13/14, and gradual underflow (FTZ/DAZ off). The entry only reads/rejects, never changes real floating environment. Actual MXCSR before/after each Evaluate is saved. The float-commit envelope uses the actual measured float cast error, the header's force bound and an explicit12-operation roundoff envelope covering division/addition/subtraction/multiplication and their absolute-scale sum; it is a numerical envelope, not a physical tolerance. No new physical residual gate is introduced.

HG stage energy/work/rotation/deletion/adjoint/net-force/torque certificates remain hard arithmetic checks. They refer to the fixed actual stage drive. actual_work separately measures dt*F_HG dot(v_n+v_full)/2, the corresponding pre-contact velocity expression, actual float committed force increment, and the changing source-form mixture-mass energy term. Differences from the h-stage toy drive work, contact work and float commit are retained with sign. The observed full discrete defect is NOT forced to zero/passive, fitted or hidden behind a tolerance. Predictor/full trial energies must not be added as two committed histories. Actual nonsmooth DP/NoPen and pressure coupling are not thereby second-order or coupled-energy qualified.

## Bounded output and future execution

Saved files: stage_nodes.csv60000 rows (manualOFF plusON force stages), on_completed_soil.csv20000 rows (ON only), manual_off.csv2 rows, hg_stages.csv8 rows, actual_work.csv4 rows, and bounded hg_focus.csv rows touching material6817/6866. Old full Capture continues all in-memory checks but its formatted stream is directed to Windows NUL; it does NOT create another210000-row stages series. Root Run.out/first actual exception and the meaningful node/body tables preserve diagnostics. Header edge history remains entirely in memory; no full edge-by-stage CSV is written.

The2 original-method baseline steps have4 force calls determined by the actual calls and the immutable closed method, not new callbacks. The6 manual steps have12 directly counted forces. Completion distinguishes both, the6 restores,8 HG trials and8 extra full Darcy calls. No native22 output series, GPU bit equivalence, physical repair, source merge, formal release, long window or other-psi approval is claimed.

A future root-owned component command after a separately passed build is:

    C08H18PlasticHgStageR1.exe --check --native ORIGINAL_FULL301_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_AS03_SEED FRESH_FIXED_OUT

The build only compiles/links/copies the original companion files and never runs this command. Existing complete/partial paths are protected. Authors must not execute it automatically.
