# Fixed-geometry plastic-HG adjoint algebra: author scope

Status: three new author-only assets. No prepare, compilation, component, solver, native read, physical stage, Git or SHA operation has been performed by this author. A future build and a future one-shot component call each require the root's independent admission. This note makes no C08 physical or plastic-HG implementation acceptance.

## Assets and execution boundary

- support/c08_h18_plastic_hg_adjoint_r1.cpp: standalone C++17, fixed 49-point algebra; no JSph class, material producer, source-state reader or solver callback.
- support/c08_h18_plastic_hg_adjoint_r1_build.py: build-only DebugCPU one-entry/CRT recipe. It adopts the actual passed c08_h18_material_tangent_r1 compiler/linker calls, retains /Od /MTd /RTC1 /fp:precise and the MSVC14.36 ABI, and removes only the unused project include path. It compiles one new entry and links that one object with default CRT libraries; zero retained/recompiled physical objects and zero project libraries. The original project, executables and all canonical results remain untouched.
- notes/c08_h18_plastic_hg_adjoint_r1.md: this scope and interpretation.

Future commands, not executed here:

    python support/c08_h18_plastic_hg_adjoint_r1_build.py --execution-authorized
    outputs/c08_h18_plastic_hg_adjoint_r1_build/C08H18PlasticHgAdjointR1.exe FRESHOUT

The component accepts one fresh output directory and refuses an existing directory. It writes graphs.csv (3 rows), certificates.csv (65 groups), completion.json, or a preserved failure.json on an actual failure. No automatic component follows the build, and neither asset launches a solver/reader/GPU/queue/next job. No physical input, PRE, old CSV or public source file is opened by the component.

## Frozen source and paper reference

The builder reads, without extracting or modifying, only JSphHourglassCpu.cpp/.h from outputs/c08_preload_schema2_source_r1/full_source.zip, bound through the existing build's source_archive/source_capture stats. Exact original anchors are checked. In the archived CPP, BuildPairs lines111–115 define the radial pair weight; Rate127–159 defines the matched LS, force-rate and one-sided quadratic; Gather76 rejects plastic states, EvaluateRate196/211 retains the time-scale and .01rad spin restrictions. These restrictions are neither changed nor exercised as if a C08 stage were qualified here.

The complete primary paper is src/papers/u-pw/non-hourglass.md, local lines334–364 and378–389 (Zhang et al., CMAME440(2025)117948, Eq26–34). Eq26–28 uses a velocity residual integrated in time; Eq32–34 puts a return scale inside that integral. Its J2 return, plastic xi=.2, elastic xi=4 and h/dp1.3 do not calibrate current saturated DP/H1.8. The present full-adjoint formulation is a mathematical extension, not a literal or validated implementation of that paper. No q_return/q_trial producer is used. Apex, tension-face, q_trial=0 and the same-stage half/full policies remain future interfaces; accumulated kappa is not a substitute.

## Operator definitions and actual implementation

The original LS is unchanged with respect to gamma; it is still volume/kernel-weighted, not literally an unweighted fit. For every directed soil row i->j:

    d_ij = x_i-x_j; a_ij = V_j w_ij
    M_i = sum_j a_ij d_ij d_ij^T
    L_i(v) = [sum_j a_ij (v_i-v_j) d_ij^T] M_i^-1
    (Pv)_ij = v_i-v_j-L_i(v)d_ij
    beta_ij = xi G V_i V_j w_ij; D_ij = beta_ij I/2
    gamma_ij = (gamma_i+gamma_j)/2; K_gamma = P^T D Gamma P

Each undirected pair supplies TWO directed, one-sided residuals. Replacing these by only their pair average before forming P^TDP would change the quadratic and is not done. Prescribed gamma fields are exactly one, zero, and a deterministic nonuniform node field containing both zero and one. Its averaged edge gamma has the same value in both directions. Gamma never enters M_i, so a zero gamma region cannot manufacture a new LS rank failure.

ApplyP is the direct original-style LS/residual evaluation. The ACTUAL ApplyPT is matrix-free and includes the LS backpropagation. For an arbitrary edge-vector input y it computes:

    Z_i = sum_j y_ij d_ij^T; T_i = Z_i M_i^-1
    t_ij = y_ij-a_ij T_i d_ij
    (P^T y)_i += t_ij; (P^T y)_j -= t_ij

The independent reference builds P's 98 columns by applying ApplyP to coordinate basis vectors, then directly contracts that stored basis with y. ApplyPT cannot read the basis. This small reference is not a production matrix, CSR assembly or spectral solver.

The force-rate/stiffness check is Fdot=-P^T D Gamma Pv. Its quadratic identity is

    sum_i v_i dot Fdot_i = -sum_directed (beta_ij/2) gamma_ij |(Pv)_ij|^2 <= 0.

For gamma=1, sum_j a_ij (Pv)_ij d_ij^T=0 eliminates the LS adjoint correction, yielding exactly the original mathematical pair expression -beta*(r_i+r_j)/2. The code compares these independently evaluated mathematical quantities within arithmetic bounds, NEVER asserts their bit equality.

D has units Pa for this 2D unit-depth convention. Pv has m/s, Fdot has N/(m s), and acceleration-rate M^-1 Fdot has m/s^3. Thus v dot Fdot is a force-rate quadratic, not an instantaneous viscous-force mechanical power. Only the history force F=-P^TDh has N/m and v dot F has W/m. The small scalar counterexample uses that latter interpretation.

## Fixed manufactured scope and certificates

There are three fixed point clouds: a 7x7 structured grid, deterministic mild perturbation, and its rigid rotation. H=double(float(.072)), dp=.04 and the original HG Wendland pair expression are used. Xi=.2 and G=7.5e6Pa are merely fixed manufactured scales, not fitted production coefficients. Positive prescribed J-like numbers vary V and mixture-like mass only to verify the final inertial conversion; this is NOT a native/current-J/solid-fluid ledger or continuum mass proof.

The component checks translation, full affine, rigid rotation, compression, shear and a deterministic nonaffine velocity field in each cloud/gamma combination (54 groups). It checks matrix-free versus basis transpose; symmetric bilinear K with a second distinct nonaffine comparison field; PSD/quadratic work; full affine null; net force-rate and torque-rate; gamma1 versus original simplified law; and sum m_i v_i dot(M_i^-1 Fdot_i). Gamma0 computed force-rate values must be numerical zero, rather than using an undefined relative zero denominator.

Nine additional groups test arbitrary nonzero directed h with F=-P^TDh and force/torque balance. Gamma is intentionally not reapplied to this memory force. One rotation group tests the same edge identities, recomputed radial weights, P equivariance under v'=R v+Omega_super R x+b, nonzero-history h'=Rh and F'=RF. The local skew(L) covariance Omega'=R Omega R^T+Omega_super is also checked. R is the exact3/5,4/5 rotation enclosed by its actual floating evaluation. This is algebraic objectivity only: no finite-rotation history ODE, time integrator, neighbour-history remap, Darcy feedback or material commit is run.

## Roundoff budget, without a new physical tolerance

A small local B(value,error) type follows the actual ordered double additions/subtractions, products, divisions and square roots. Declared double inputs have zero initial uncertainty; exact3/5 and4/5 and all derived coordinates/weights acquire propagated bounds. Each round-to-nearest elementary operation adds u/(1-u)*abs(computed_value) plus a subnormal allowance. Nonnegative error-bound additions/products/divisions themselves use nextafter toward +infinity. Division uses a downward-rounded lower bound abs(divisor)-error; sqrt uses downward-rounded positive endpoint/root bounds. If a denominator/root or determinant cannot be certified, the fixture rejects it; nothing is clipped or regularized. The component explicitly requires round-to-nearest and MXCSR FTZ/DAZ both off (gradual underflow). This uses IEEE binary64 basic operations and the MSVC sqrt behavior under the retained precise Debug recipe, not an arbitrary residual tolerance.

Original lo>0 and condition<1e8 rank tests remain, followed by the stricter arithmetic requirement det-error>0 needed to make a finite inverse enclosure. All positivity/support endpoints are rounded outward; support intervals must not overlap. No physical dt or lambda is inferred.

All identities compare the actual computed difference with its propagated absolute error. certificates.csv retains scalar-check count, maximum actual absolute discrepancy, its own associated bound, and maximum discrepancy/bound (which may belong to a different scalar). completion.json records actual operation counts and the maximum ratio. This permits the root to reject an excessively weak budget; a true statement here requires both a small observed discrepancy and a meaningful finite bound, not merely a boolean. No 5Pa criterion or physical acceptance threshold is introduced.

## History limitation is an explicit result

For the possible internal-history extension

    F=-P_current^TDh; hdot=Gamma Pv+Omega h,

with frozen scalar D and skew Omega, E=.5 h^TDh gives

    Edot + v dot F = h^TD(Gamma-I)Pv.

Its sign is indefinite. The included unloading example h=1, Pv=-1, D=1, gamma=.5 gives mechanical power+1, memory-energy rate-.5 and a positive total+.5. It MUST be observed, and completion always states history_passive=false. Gamma0 stops new driving but does not remove pre-existing h or its force. A fixed positive gamma could instead motivate a D/Gamma energy, but it becomes singular at zero and does not provide a switching-plasticity energy proof.

With independent h, changing P does not itself require writing h=P_current*u; that equality is NOT claimed. Changing D/gamma, edge birth/death/reorientation and remapping create additional parameter work or energy jumps. A loading-only gamma rule with gamma1 on HG unloading is a possible new model, not this fixture or a statement of the paper. No scheme for it is selected. Consequently passed algebra would authorize only further design scrutiny, not removal of any old rank/spin guard, physical CPU/GPU HG use, restart support or another C08 trajectory.
