# C08 frozen CPU pressure matrix and controls r1

Status: author-only, no build or execution. New entry is `tests/support/c08_fs_matrix_cpu_r1.cpp`; public/retained source and active GPU dependencies are untouched. This is the actual frozen pressure RHS, not a coupled tangent, solver run, eigenvalue analysis or physical acceptance.

Use one identical entry source linked separately to the reviewed original CPU object closure and the reviewed minimal candidate CPU closure. Both execute real HydroMechFreeSeepage=ON for basis probes. `--expect raw|normal` selects only the independent all-particle reference; it never selects or emulates the production closure. Wrong executable/reference pairing must fail the actual-rate comparison. FreeSeepageOFF is only an explicit control, not the old FreeSeepageON baseline.

## Predeclared geometry/material profiles

- 81 fluids, Wendland only, dp=.04 m, actual H=.072f, support2H; mass=float(2072.5*dp^2), rho0=2072.5, water rho=1000, Kw=1e9f, n0=.35f, k0=.0002f, Ck=2. Gravity=(0,0,-9.81f); gamma=1000*9.80665 independently of body gravity.
- Native ID=(iz+4)*9+(ix+4), ix,iz=-4..4. x=1+ix*dp+(iz<4?dp/8:0), y=0, z=1+iz*dp. This is the same fixed subsurface tangential offset topology; top plane z=1.16 is unshifted. ID76 is the predeclared central top FS canary. No perturbation search, walls, periodicity, AS, compression, force call or integrator.
- Profile0 J=1. Profile1 J=1+(ix+2*iz)/512. Both use actual conductivity k(J)=k0*exp((J-1)/((1-n0)*2)); profile0 has exactly zero gradJ. J is prescribed once per profile, not integrated. Real ledger n,V,rho is obtained from GetPorosityFeedbackStateCpu; rho cache is its binary32 conversion, and FS uses the real J volumes.
- For each profile, PreInteraction_Forces supplies scratch arrays, then production ComputeFreeSurfaceTracking generates C, FS and normals exactly once. These arrays are held and checked bitwise throughout. No desired label/C/normal is injected. Actual inner and FS coverage plus actual FS ID76 are required. Node CSV includes native coordinates, actual labels/normals/C, J/n/V/rho/k and storage weight W=V*n/Kw.

## Controls before the matrix

Every field uses the actual production rate with FreeSeepageOFF then ON; the independent reference follows that flag and the expected raw/normal formula. OFF/ON inner rates must be bit-identical; exported actual_bits also permits independent old/candidate OFF bit comparison. Actual rates and all-particle references must agree under the predeclared arithmetic budgets.

1. Negative hydraulic F0 hydrostatic null: p_ideal=-4096+rho_water*g_z*(z-1), Ace=-Gravity, v=theta=0. This is stationary a_s=0, not freefall. Stored p is its binary32 conversion; all remain negative. F=grad(p_ideal)+rho*Ace=0. Pressure input quantization is explicitly propagated below, not hidden by changing an accuracy tolerance.
2. Nonconstant Ace: exact negative p=-16+ix/8+iz/16, Ace=(ix/128+iz/256,0,ix/256-iz/128), all exact binary32. This is a prescribed instantaneous field; only the complete LP/Lx/gp/da/chain reference is asserted, not a coupled mechanical solution or continuum-null claim.
3. Nonzero variable-k chain: exact negative p=-16+ix/4+iz/8, Ace=0. Profile1 must have at least one actual FS row whose independent chain contribution exceeds its unchanged whole-rate arithmetic budget. This prevents a vacuous variable-k comparison; no new physical threshold is used. Profile0 retains the constant-k control.

Pressure projection is not called here because it would regenerate FS/C. Strictly negative pressures bypass its cap; the unchanged previous486-row fixture already checked actual negative-pressure projection preservation. The new component checks positions, velocity/density, pressure/P0, J/theta, stress, kappa and supplied Ace unchanged by every rate call. TimeStep/Nstep remain0 and predictor pointers remainnull.

## Independent reference and budgets, fixed before execution

Use the actual production C/J/k/Ace and original Wendland functions, with an independent all-particle search. d=xi-xj, gi=Ci*gradW, gj=Cj*gradW, Vj=(MassFluid/rho0)*Jj, w=Vj*d.(gi+gj)/(r2+Eta2). Assemble LP=sum(w*dp), Lx=sum(w*d), gp=-sum(Vj*gi*dp), da=sum(Vj*(Aj-Ai).gi), gradJ=sum(Vj*gi*(Jj-Ji)). Let s=Kw/(n*gamma), k'=ki/((1-n0)*Ck).

OFF and inner: c=gp, lap=LP-c.Lx+rho*da. Raw ON FS: c=gp, lap=LP+rho*(Ai.Lx+da). Normal ON FS: c=gp-nhat*(nhat.(gp+rho*Ai))/|nhat|2, lap=LP-c.Lx+rho*da. In all cases chain=k'*gradJ.(c+rho*Ai), rate=s*(ki*lap+chain). Thus the candidate normal target also changes the actual variable-k chain. No analytic normal replaces the production estimated normal.

The retained sourcefloat factor is B=32*FLT_EPSILON+4096*DBL_EPSILON. Define LPabs=sum|w*dp| and DAabs=sum(Vj*sum_components|deltaA_component*gi_component|). Rate arithmetic budget is B*max(1,s*(ki*LAPabs+k'*sum_components|gradJ_component*(c+rho*Ai)_component|)), where LAPabs=LPabs+rho*DAabs plus rho*sum|Ai_component*Lx_component| for raw FS, otherwise sum|c_component*Lx_component|. This is a sourcefloat/direct-sum budget, not physical accuracy or stability acceptance.

For hydro only epsilon_i=|p_float_i-p_ideal_i|, QL=sum|w|*(epsilon_i+epsilon_j), QG=sum(Vj*abs(gi)*(epsilon_i+epsilon_j)). Let T be the tangent projector only for normal ON FS, identity otherwise; QLx=0 for raw ON FS, otherwise T*Lx. Additional input budget is Q=s*(ki*(QL+abs(QLx).QG)+k'*abs(T*gradJ).QG). Require actual hydro |rate|<=2*arithmetic_budget+Q: one budget covers production/reference and one covers ideal cancellation. No budget is fitted after execution.

## Actual basis matrix output

After controls, set p*=-16 Pa, Ace=theta=0, same J/geometry/C/FS/normals. Baseline actual/reference rates must be exactly zero. For each native ID j=0..80 set p=p*+.25*e_j; all values are strictnegative exact binary32. The actual operator column is Aij=(actual_rate_i-baseline_rate_i)/.25. Export all81x81 entries per profile with the independent reference column and propagated entry budget (rate_budget_i+baseline_budget_i)/.25. This is a finite exact pressure-basis response, not a physical increment in time. Completion requires972 control rows,162 null-baseline checks and13122 matrix entries over both profiles, plus nonempty inner/variable-k coverage.

`matrix.csv` stores actual/reference A and entry budgets; `controls.csv` stores972 control rows plus162 explicitly labelled field3 baseline rows, with actual rates/bits, references, budgets and LP/Lx/gp/da/gradJ/c/lap/chain; `nodes.csv` stores both complete native profiles and storage weights. `completion.json` states formula_reference_matched and physical_acceptance=false only after all declared checks. A missing completion/nonzero exit leaves an incomplete diagnostic; no eigenspectrum or automatic winner is produced.

## Root integration and later offline analysis

After full read, compile this one entry with the reviewed DebugCPU ABI/includes/defines. Link twice against the exact reviewed CPU object receipts, each excluding its main object; swap only the authorized actual JSphCpu object closure and matching canonical headers. Do not separately compile/link the included retained Feedback source entry. No new public build is needed or authorized by this note. Prospective calls: original executable `--expect raw --out FRESH_OLD_DIR`; candidate executable `--expect normal --out FRESH_NORMAL_DIR`. Each rejects an existing output directory.

Later offline analysis must pair identical node profiles and distinguish constant/right-null preservation, storage-weighted left defect, row gains, eigenvalues and nonnormal amplification. The actual frozen pressure Symplectic update has R(dt*A)=I+dt*A+dt^2*A^2/2 (`source/JSphCpu.cpp:3346–3375`). The current Dmax and grad-k bounds (`3738–3782`) are necessary scales, not proof of an M-matrix or stability of either FS closure. Analyze actual dt5us at these C08 scales, reporting propagated matrix uncertainty; no half-chain/new physical threshold follows. The81-point manufactured geometry has no C08 mDBC wall, moving support or pressure-to-acceleration feedback, so passing controls or a favorable spectrum cannot certify the .9s coupled run, conservation or C08 suction causation.
