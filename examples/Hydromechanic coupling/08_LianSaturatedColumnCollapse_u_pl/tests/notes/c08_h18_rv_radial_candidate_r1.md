# H1.8 compression-only radial residual candidate r1

Author-only. New assets are support/c08_h18_rv_radial_candidate_r1.cpp, its build.py and this note. No prepare/build/component/solver/reader/VTK/Git/SHA/queue was executed by the author. The root must full-read and separately admit a build, then independently decide a single component invocation. No GPU candidate, new trajectory,3s, otherψ, half, PRE or alpha sweep is implied.

## Operator and exact scope

This is the independent candidate described in notes/c08_h18_rv_radial_limiter_scope_r1.md, not a Lian/Rosswog paper formula. Alpha remains.1. The original unregularized LS reconstruction L and its slope are unchanged. For canonical native-ID edge i<j:

d=x_i−x_j; n=d/|d|; dv=v_i−v_j;
s=dv·n; q=[dv−.5(L_i+L_j)d]·n;
a=min(max(−s,0),max(−q,0)); c=fl(fl(alpha*beta)*a);
F_i=c*n; F_j=−F_i.

The finite-input limiter explicitly returns positive0 when s<0 and q<0 is not simultaneously true; otherwise it returns min(−s,−q). This only canonicalizes the inactive FORCE-scalar zero, avoiding a signed-zero fixture mismatch. Evaluate checks finite s/q before limiting, and the helper also rejects nonfinite inputs; NaN is not silently treated as inactive. Native signed clocks/dterror and all saved fields are never normalized or modified. No budget or physical formula changes.

Thus a real closing pair with q>0 does not receive the old inward residual component. A truly affine field has q=0 up to the independently bounded LS/field arithmetic error. Pure affine compression remains a null mode; this is not a minimum-spacing potential or a remedy for every plastic-localization mode. Even when each active DIRECT pair force is outward, ALL-neighbor relative acceleration of a chosen pair may still be inward; both are measured.

The same closed input contract as the successful onset component is retained: original/RV aliases, original AS03 SHORT91 and RV windowR2/native_r1, Parts40/42/43/76/90, steps2080001/2084001/2086001/2152001/2180000 and actual11-column clock rows. Read all22 exact typed fields from only those ten existing records; no reader or decoding. Native σij isxy,yz,xz; all6805IDs, original material/ledger/P0/κ/FS and5us necessary checks remain. Fresh CPU recomputed force is not the previous GPU half-stage or GPU bit truth.

The unchanged root selection is configs/c08_h18_rv_onset_force_r1.selection.csv:80 rows, eight actual representatives×two target cases×five parts. Source provenance remains sourcealias:rule from the passed localization representative table. The new candidate does not generate/alter this selection, discard non-neighbor pairs or add arbitrary-state CLI. direct_neighbor=false retains directF0 and all-neighbor/curvature results.

## Source, baseline and lifecycle reuse

One new DebugCPU entry links the same86 immutable physical objects with160 archived headers and7 runtime files. No public source, class ABI, physical CUDA/CPU TU or canonical executable changes. Builder reuses the actual successful onset CL/link recipes and copies its six immutable generated fragments into fresh outputs/c08_h18_rv_radial_candidate_r1_build. Only shared91.inc AppInfo is renamed; closed loader,setup,CellGraph method, RHS literal, original Graph/Fit and diagnostic float eigen helper remain unchanged. Old vector Evaluate is present in the copied math include but NEVER CALLED; the new CPP declares independent RadialStats/EvaluateRadial and certificates. It never claims work+2form or contraction as a radial identity.

Per state: restore the existing saved material fields by ID and actual CPU cells; call one original force/Darcy; compare its bare rate and Acex/Acez against the actual sealed outputs/c08_h18_rv_onset_force_r1/soil.csv, all50000 CPU control rows with matching IDs/steps/times (AceY=0). Then evaluate/commit the new radial force once and call complete original Darcy, including real wall acceleration, once. The original literal/final-float/seven-channel budgets are enforced for BOTH rates, with the independent eighth numeric residual. Candidate force/wave/pore/k-gradient5us necessary limits use the genuinely recomputed candidate Ace/rate/speed, never the baseline speed.

Totals:10 original force calls,20 complete Darcy calls (10 extra),20 DtVariable(false),50000 bare CPU control bit rows,100000 literal-rate rows,0 physical steps/constitutive returns/filter calls. The successful old zero-change chain is reused as provenance, not rerun or relabelled as GPU truth. All soil primaries and established wall/active-scratch checks retain their scope; ignored wall modes are not read. No time, velocity, position,J,p,κ or material update is integrated. Rate changes are frozen-state responses, not a new trajectory.

## Independent arithmetic model and actual counts

Let u=DBL_EPSILON/2 and Γ(k)=ku/(1−ku). N=5000, E=actual unique-edge count, d_i=actual neighbor count and d_max=max d_i. All counts are from the actual CPU-cell graph with duplicate/reverse-membership checks. Basic arithmetic follows the existing MSVC DebugCPU /Od /fp:precise recipe. Computed positive beta, shared c and computed n are INPUTS to the pair/node power identity; their geometric/LS/normalization quality is checked separately. No inherited global64(N+E) gamma is reused.

- Normalization:Γ16 covers the double norm dot (5),sqrt(1),three divisions(3),check dot(5),difference(1) and one conservative source-operation slot. abs(n·n−1) must be within this bound. The real normalized-vector upper bound also enters the degree estimate; no assumption ||n||²=1 exactly.
- Net force: the exact same computed F is scattered with± signs. Local force accumulation and global reduction have a longest path d_max+N, so budget Γ(d_max+N)*2Σedges||F||_1. The computed positive scale is raised by1/(1−Γ(4E)) to account for its own component/edge accumulation.
- Power: D=Σedges c(−s)>=0 is independent of node P=Σnodes v_i·F_i. abs(P+D)<=B_P and P<=B_P.Γ(19E+6N) accounts for3velocity subtractions+5dot operations+3force-component products+2D product/accumulation+6±scatter operations per edge, then6dot/reduction operations per node. Its cancellation-safe scale is Σedges c Σcomponents(|v_i|+|v_j|)|n| +Σnodes Σcomponents|v_i F_i|, raised by1/(1−Γ) for positive-scale accumulation. Because c is shared, its two products do not create a second independently rounded c in D. No pair/nonzero scalar is divided by s to implement the limiter.
- Torque: first sum computed pair torque d_z F_x−d_x F_z, and check its central-force error againstΓ16Σc(|d_z n_x|+|d_x n_z|), with positive summation correction. Separately compare node torque to pair torque usingΓ(13E+4N) and pre-cancellation coordinate/force scales. Per edge this includes3position differences,6force scatters and4cross/reduction operations; nodes add4torque/reduction operations. The budget includes that computed d differs from the exact difference of stored coordinates. Full node |torque| must be within central+reduction budgets; it is not set to0.

All work/net/torque/Euler and affine qb/fb/lb budgets and corresponding checked measurements must be finite before acceptance/commit; Inf cannot make an inequality pass. Γ arguments must remain finite and below1; uncertifiable conditions reject, never clamp. These are arithmetic certificates of this bounded component, not extra physical tolerances or proof of a general GPU implementation.

## LS and affine-null forward evidence

The original Graph/Fit/rank gate is immutable. New CertifyLS independently rebuilds the identical weighted N and absolute M/N contribution sums. With computed M/N treated as matrix inputs, each scaled2×2 solve residual L M−N must fitΓ20 times the sum of absolute PRE-CANCELLATION products |L|·|M|+|N|. This covers the three scaling divisions, determinant/denominator and numerator/division operations plus the checked product/residual. The actual inverse upper norm uses scaled det and the strictly positive denominator1−Γ12(1+condition); undefined/nonfinite/nonpositive inverse qualifications reject without a ridge.

Manufacture is genuinely evaluated at all actual nodes, on the current nonuniform V/mass/graph: translation,full affine,isotropic compression,pure shear and rigid rotation (five fields per state=50 rows). The double synthetic v=A*x+b is not assumed exact.Γ4 bounds its two products/two additions; position and velocity differences have separate u(|input_i|+|input_j|) bounds. The weighted target residual plusΓ(3*d_i)M/N product/accumulation bounds and actual backward-solve budget are multiplied by the qualified inverse norm to bound L−A. The q bound then uses PRE-CANCELLATION |L|·|d| product sums andΓ12 for the Mul/average/residual/dot path (rather than cancellation-small Ld), and the force bound includes c/n/norm and node accumulation. Measured q and force must remain below these independently declared forward bounds; manufacture residuals are never forcibly zeroed. wLS/d/dv are actual Graph inputs for M/N accumulation; their analytic field-formation errors are included separately rather than omitted.

The inherited Graph computes an old gamma cache while preparing the same moment matrices. That cache is not a radial certificate and is not read by the new proofs. Original rank/finite gates remain.

Eight scalar limiter fixtures cover four s/q sign combinations, amplitude cap, tiny negative s or q, and zeros; they are pure mathematical calls, not force-stage counts or a new physical state. Canonical unique-edge±scatter supplies exact exchange symmetry of the force used in the node accumulation; a separately optimized CUDA implementation would still require its own actual path qualification.

## New frozen Euler and float-commit certificates

For this ONE frozen graph/mass/force, gamma_ij=alpha*beta*a/(−s) lies in[0,alpha*beta] when active; it need not be divided out in the force implementation. An upper bound is

lambda_upper=2*alpha*max_i(Σbeta_ij/m_i) * positive-sum/multiply/normalization corrections.

Code uses the actual beta/mass weighted g.dmax (not neighbor count),Γ(d_max)positive-degree correction,Γ2 for c's products andΓ16 for n. dt*lambda_upper/2 must be<=1. Independently measure the stable algebraic kinetic increment

ΔE_Euler=dt*P +.5dt²Σ|F_i|²/m_i,

with its explicitΓ(7N+8)dot/division/reduction budget and power budget; positive energy beyond arithmetic allowance rejects. This is not a full coupled pre/cor energy theorem: geometry,J,mass,limiter active sets,original forces,plasticity and Darcy evolve in a trajectory.

Float Ace is updated once as before. The actual added committed force is Fc_i=m_i*(Ace_new−Ace_old), not the ideal F. For

b_i=2*FLT_EPSILON*m_i*(||Ace_old||+||F_i/m_i||),

require ||Fc_i−F_i||<=b_i, then extend net/power/torque budgets respectively byΣb_i,Σ||v_i||b_i,Σ||x_i||b_i. The committed frozen-Euler error extends by

dtΣ||v_i||b_i +.5dt²Σ[2||F_i||b_i+b_i²]/m_i

and its own reduction arithmetic. Actual committed power/net/torque/Euler values are measured. A float update is not claimed exactly central; it must pass its explicit budget. No numerical dissipation is silently added to pore energy or called fluid mass.

## Output/decision limits

Fresh outputs/c08_h18_rv_radial_candidate_r1 contains soil/pairs/focus/metrics,50 manufacture rows,8 scalar fixtures,10 original selected-clock rows and completion. Soil preserves the seven complete-RHS channels and independent numeric remainder; pair rows add actual SOURCE-ORDERED s/q/a (dv−.5(pi+pj), exactly the evaluator order),active flag,new direct force and a labelled old-vector direct shadow (not another force call). The retained rbar_n diagnostic and old-vector shadow use the old .5(ri+rj) expression; they are not asserted bitwise equal to the new radial_q expression. All-neighbor relative acceleration and actual curvature are the decisive local measurements. The same current dynamic AS caller passes unit density, so the actual AS tensor projection remainsPa; no erroneous rho² rescaling/relabel is introduced.

A change from inward to outward conditional response at rv/Part90 pair6918/6967 would motivate further review, not physical admission. If new all-neighbor response is still inward, or if RHS/numerical certificates fail, preserve the result and do not tune alpha or alter the original gates to manufacture success. Direct deactivation for s<0,q>0 alone does not prove repair. RawFS,NoPen ReactionClosed=false,finiteKw,material localization and full coupled-energy limitations remain. No new3s or otherψ is automatic.

Later root-only build command, not executed by author:

D:/Anaconda3/python.exe -B tests/support/c08_h18_rv_radial_candidate_r1_build.py --execution-authorized

A separate reviewed component command uses the new C08H18RvRadialCandidateR1.exe with the unchanged --check --selection root onset CSV, original SHORT91 seed,CPU1 and a fresh new candidate output. The builder never invokes it. No additional analysis/plot script is authored in this step.
