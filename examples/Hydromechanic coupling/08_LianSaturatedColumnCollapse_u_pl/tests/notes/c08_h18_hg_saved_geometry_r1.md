# Actual saved C08 geometry: offline HG necessary-condition screen

Author-only new files: support/c08_h18_hg_saved_geometry_r1.py and this note. No analysis/import/build/solver/reader/VTK/GPU/Git/SHA execution was performed by the author. The root must independently admit a future one-shot offline run. No physical input, source, program, PRE, existing native export or retained result is modified.

## Closed data and output

Only the already decoded AS03 full301 native bundle is used, at Parts0,38,60,83,87,300. Every selected frame retains all5000 original soil IDs2060..7059, its true time, completed/saved steps,5us and signed dterror. Part0 is the genuine first post-update save near tau5us, not PRE/t0. Part300 is the real completed2600000 state; no n*dt reconstruction, time interpolation or signed-clock rewrite occurs.

The script binds logs/c08_h18_as03n255_full3_review_r1.check.json and logs/c08_h18_as03n255_full3_native_r1.check.json, the latter's completion/metadata/actual-call/reader-build entries, and the original review's unique sealed typed22.bin/layout/clocks, XML, Run.out and source archive stats. It validates the original12-byte6805/22/301 header and212-byte-per-particle layout, then read-only memmaps the existing payload and touches only six frames. It does not decode again, scan PRE1001, rerun the broad analysis or call old load_bundle/analyze helpers.

A future admitted command is:

    python support/c08_h18_hg_saved_geometry_r1.py --execution-authorized

Fresh outputs only: outputs/c08_h18_hg_saved_geometry_r1/receivers.csv(30000 rows), summary.csv(6 rows), figures/c08_h18_hg_saved_geometry_r1.png(2x2 panels), and logs/c08_h18_hg_saved_geometry_r1.check.json. Existing complete/partial paths are refused. Native arrays remain unchanged. A completed analysis may have passed=true while a necessary geometry/dt gate is false; the separate gate fields carry that scientific result. Input failure preserves partial derived outputs and the true first error, without retry.

## Actual source constants and algebra

The actual current src/source/JSphHourglassCpu.cpp is read before computation. Its exact numerical anchors are also checked in the original schema2 full_source.zip, together with the relevant config/kernel/type/modulus anchors in JSphCpuSingle.cpp, FunSphKernel.h, JSph.cpp, JSph.h and DualSphDef.h. Current source stats are first captured for this offline calculation; that is not invented historical program provenance. The original archive/XML/Run.out binding remains the historical reference.

JSphCpuSingle.cpp145–148 passes CSP.kernelh, KernelSize, CSP.kwend.bwen, SoilCte.ModulusG, MassFluid, RhopZero and water rho into HG. JSphHourglassCpu.cpp36–39,78,111–159 supplies:

    support = 2H; d = xi-xj; rr = dx*dx+dz*dz
    s = max(0,1-sqrt(rr)/(2H)); w = (-Bwen/H)*s*s*s
    V_i = (MassFluid/RhopZero)*J_i
    m_i = (MassFluid/RhopZero)*(RhopZero-rhow+rhow*J_i)
    beta_ij = xi*G*V_i*V_j*w
    LS weights at receiver i = V_j*w

H is the original float H promoted to double, native value0.071999996900558472m. FunSphKernel.h191–195 computes Bwen=float(-2.7852/(H*H*H)); support comes from float2*H. The physical XML and Run.out both declare2D Wendland, so the HG and physical kernel families/H/support agree. HG's double polynomial weight does not imply bit equality with the physical GPU kernel's floating gradient evaluation.

Xi=.1 is a fixed hypothetical candidate, stored as double just as SoilHourglassXi is in JSph.h/JSph.cpp. The actual run's XML still has HGoff; nothing changes it. G follows the real float path E/[2.f*(1.f+nu)] from JSph.cpp4229 and the float declarations in DualSphDef.h. E20e6Pa and nu=.33 from the bound actual XML produce the existing Run.out shear modulus7518796.5Pa, not the rounded7.5MPa toy scale. MassFluid/RhopZero use execution/constants, while rhow comes from execution/special/hydromechanics/PoreWaterRho; their actual generated XML float values are promoted to double. Native V and rho are compared to their source forms under the existing original5e-13 ledger budget; m uses ParticleMass's exact algebraic order rather than silently substituting nativeV*nativeRho. Their small descriptive difference is reported. Vel.w/native_Rhop is not used as mixture inertia.

## Graph and original rank gate

Only bounded soil-soil neighbors enter this2D HG graph: no fixed ghosts, walls, periodic images or hydraulic receiver change. SciPy cKDTree broadens its candidate radius by an explicit floating search envelope, then the original strict rr<support^2 filter determines the graph. Candidates are sorted into a deterministic offline order. Near-boundary candidates are counted. This is source-form algebra, not a reproduction of CPU linked-cell traversal/reduction order or GPU intermediate force bits.

All support pairs and receiver IDs are retained. Coincident rr=0 is reported as an original geometry failure, never deleted to hide it. Zero computed w is also counted without discarding the pair. It is NOT mislabeled as an original rank failure: the old BuildPairs only guards rr>0. Positive w is an additional active-energy-model sqrt(D) domain flag and is reported separately.

For each receiver the script reproduces the original2x2 moment/normal equations, det, hi=.5*(tr+hypot(Mxx-Mzz,2Mxz)), lo=det/hi and condition=hi/lo. The original condition is unchanged: finite det, lo>0 and condition<1e8. There is no ridge, pinv, singular-value clipping or softened condition threshold. Failed rows stay in receivers.csv with their actual determinant/condition and false rank flag; undefined L/Pv values are empty, not fabricated zeros. Any such failure makes that state's original geometry/rank/dt gate false. Sorting-induced last-bit differences are not an original CPU bit proof; near-threshold cases require scrutiny, never an automatic tolerance change.

## Frozen stiffness scale and descriptive velocity residual

For worst gamma1 the reported old formula is

    lambda_i = 2*sum_j(beta_ij)/m_i
    lambda_formula = max_i lambda_i; old_scale = .2/sqrt(lambda_formula).

With shared positive G/xi, positive V/m/w, full-rank original LS and the full adjoint, the exact mathematical Gamma<=1 operator obeys lambda_max(M^-1/2 K M^-1/2)<=lambda_formula. The script evaluates this formula in double source-form arithmetic, not a rigorous interval eigenvalue computation or a literal old CPU reduction. The margin against5us is reported. A failure means the retained conservative HG scale rule does not admit5us; it is not proof that the true coupled mode must be unstable. Passing is only one necessary candidate screen.

receivers.csv contains actual coordinates/velocity/J/V/rho/m, neighbor counts/minimum distance, full LS moment/rank/gradient, beta degree, receiver lambda/scale, and Pv norm statistics. summary.csv retains pair count, minimum positive r, zero/coincident counts, all-rank result, global scale/maximum-ID, residual RMS/max and source/native ledger gaps. All5000 receivers in all six states are present. Pv uses float native velocities promoted to double and full LS; it is a descriptive saved-state nonaffine velocity residual, not a historical Pre/Cor force or a diagnosis of the unique cause of clumping. Instantaneous skew is not an accumulated-spin estimate.

The original elastic implementation rejects nonzero kappa and has plastic/restart/spin/config restrictions. Nonzero-kappa counts are context only, and no gamma is inferred from kappa. The script neither invokes nor relaxes those guards: old_implementation_admitted, plastic_producer_qualified, spin_history_qualified, actual_Symplectic_qualified, Darcy_qualified and physical_acceptance remain false. New energy-model positive-weight eligibility is separate from original rank/dt eligibility. This bounded state screen cannot authorize plastic HG, a new solver, another psi group or any physical accuracy claim.
