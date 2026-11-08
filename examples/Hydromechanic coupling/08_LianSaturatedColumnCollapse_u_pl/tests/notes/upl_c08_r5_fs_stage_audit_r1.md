# r5 GPU FS/pressure/Ace stage audit

Read-only current-source audit; new note name checked absent and untracked before writing. No production edits, build, solver, decoder or VTK. This does not diagnose the recorded pressure peak solely from its magnitude. The r5 native safety pass and the separately disclosed `ReactionClosed=false` policy remain unchanged.

## Actual order and pressure projection

- `JSphGpuSingle.cpp:807–830`: force at n -> predictor -> half-geometry `RunCellDivide` -> force at half -> corrector. Main-loop completed-geometry divide is at 1234, before advancing TimeStep; save refresh is at 1275.
- Each force call (`Single:631–687`) allocates/resets scratch; dynamic wall state -> FS/C -> wall C via `JSphGpu.cpp:1151–1162`; applies legacy drainage; computes current-J AS; runs main mechanical kernel (including AV), optional damping/load/HG/DEM, zeroes 2D y; then computes dynamic Darcy. No FS recomputation occurs between that force call's main force and Darcy.
- `JSphGpu_mdbc.cpp:135–140` returns early for dynamic walls: the state fit, not an earlier legacy derivative-velocity pass, supplies the wall derivative velocity. Same-stage wall Ace is reconstructed only after all force contributions (`JSphGpu.cpp:1832–1840`).
- `RunCellDivide -> ApplyPorePressureBoundaries` (`Single:580–588`, `Gpu:1246–1255`) recomputes FS/C. FreeSeepage ponding runs only when `!PorePressPreg`: **completed geometry**, not half geometry. The predictor buffers exist through the half divide and are freed at `Gpu:1665–1670`.
- In this no-legacy-drain r5, the force-path `ApplyFreeSurfacePorePressure()` is not the positive-only ponding call. The latter kernel (`Gpu_ker.cu:1063–1072`) changes only normal native fluid FS2/3 with finite p>0 to zero. It preserves p<=0, NaN/Inf, rate, P0, effective sigma, J, theta and kappa. Half-stage FS2/3 may therefore retain positive as well as negative p; saved completed-stage FS2/3 obey finite p<=0. FS2 negative p is the selected policy, not a missing negative-pressure clamp.
- Explicit p updates (`Gpu:1581–1583,1658–1660`; `ker:1315–1340`) use p_n+h*rate_n and p_n+dt*rate_half. J advances separately (`Gpu:1752–1767`, `ker:1352–1358`); material sigma advances in Pre/Cor before completed ponding. Ponding does not recompute an elastic/J/rate response. At frozen n/Kw, its delta-p corresponds to a storage increment (n/Kw)*delta-p; algebraic J/n/rho/k ledger checks alone do not establish pressure mass balance.

## FS switching is a real operator change

FS uses Vj=V0*Jj and the packed-float pair gradient: moment M_i=−sum(Vj*d_ij tensor g_ij), C_i=M_i^-1, position divergence −sum(Vj*d_ij dot g_ij) (`ker:807–870`). In 2D the candidate thresholds are 1.7 and 1.1 plus the stated neighbor test; the umbrella scan may turn FS2 back into FS0 (`885–947`). Near-FS marking is disabled (`Gpu:1154`). There is no temporal hysteresis. Within a force stage the same classification is shared; n/half/completed classifications need not be equal.

For Darcy set g_i=C_i*g, gp=sum(Vj*(pj−pi)*g_i), w=Vj*d dot ((Ci+Cj)*g)/(r^2+eta^2), L=sum(w*(pi−pj)), lx=sum(w*d), and da=sum(Vj*(Aj−Ai) dot g_i) (`ker:1505–1523`). Then (`1528–1548`):

- inner: lap=L−gp dot lx+rho_w*da;
- FreeSeepage FS2/3: lap=L+rho_w*(Ai dot lx+da);
- change on inner -> FS is **(gp+rho_w*Ai) dot lx**. It vanishes for an exactly balanced hydraulic vector, not for arbitrary p/Ace or incomplete support. In r5 legacy drainage/closedfs are false, so the variable-k chain still uses gp+rho_w*Ai on both classifications; switching changes lap, not directly that chain expression.

This is an explicit branch with no blend/hysteresis, so FS transitions can change the rate even with otherwise frozen fields. It is not evidence that the implemented branch is contrary to its selected formulation, nor proof that it caused the actual .63/.64 s peak.

## Mechanical pressure, AS/AV, and the continuum comparison

Momentum uses **raw** packed-float gradient gR (`ker:1712–1723`), Vj=V0*Jj and receiver mixture inertia rho_i=rho_w+(rho0−rho_w)/Ji. Its pressure part is a_i^p=−sum(Vj*(pi+pj)*gR_ij)/rho_i (`1770–1779`); effective-stress sums use the same raw gradient. Neither Ci nor the pair Ci+Cj is applied to this momentum term. Corrected C for velocity/stress-rate gradients (`2184–2194`) does not correct momentum pressure.

In a complete, consistent stencil with frozen rho/k, continuum a^p=−grad(p)/rho reduces grad(p)+rho_w*a^p to (1−rho_w/rho)*grad(p), initially about0.51749*grad(p). The actual raw symmetric-sum momentum gradient and corrected difference/divergence in Darcy are not one matched adjoint pair; near incomplete support the raw sum also contains the constant-pressure partition defect. The continuum reduction is therefore a reference identity, not a demonstrated discrete cancellation/stability bound.

AS is formed after wall state/FS at `Single:639`: raw-Pa R=−epsilon*(positive spectral part of sigma_eff−p*I), double subtraction then float spectrum (`ker:645–691`). It is zero during PRE and active after release (`Gpu:1471–1476`). Its pair force uses Vj/rho_i*(W/Wdp)^exponent*(Ri+Rj)*gR (`1814–1824`). AV is added inside the same main kernel before Ace storage (`1997–2024,2225`), using current mixture neighbor inertia and the wall tangent velocity for its velocity difference (`1843–1850`). Thus both AS and AV enter the actual Ace consumed by wall-Ace reconstruction and Darcy; AS itself depends nonlinearly on p through the positive-stress spectrum. No body g is added to fluid Ace there; g enters the integrator separately. Wall stage2 reflects Q*(Ace+g_n)−g_n (`mdbc_ker.cuh:49–52,183–188`), with head removal/restoration in stage0 (`37–41,153–156`); this is not an exact enforced discrete q_normal=0 proof.

## What saved22 can establish

Saved22 contains native IDs, completed double positions, float velocity/p/P0, double effective sigma, J/derived n/rho/k, kappa, completed FSType/FSNormal/PosDiv, and theta from the last force stage. It can locate pressure/FS neighborhoods and reconstruct a clearly labeled frozen-geometry C/pressure-only operator proxy, retaining full boundary stencil if required. It does **not** contain actual CorrMat, total Ace or its AS/AV/stress decomposition, pressure rate, Rsigma, predictor p/J/sigma/velocity/positions, pre-ponding p, packed PosCell bits/cell ordering, or contact impulse. Saved theta is half-force-stage data at the time of the completed save, not a completed-geometry divergence replay. Save refreshes state/C/FS, not the complete earlier force/Ace/rate.

Consequently the HG pure-pressure -> raw mechanical Ace -> corrected Darcy Jacobian is a useful isolated diagnostic but excludes the pressure-dependent AS spectrum, AV/velocity feedback, effective-stress evolution, compression theta, wall stage2 errors and contact reaction. It must not be named a full actual-rate replay or a proven cause of the recorded pulse. This audit found no definite unintended call-order/negative-clamp bug; it identified the existing full-only split, FS branch jump, and unmatched discrete pressure-gradient composition as specific quantities to inspect using already saved data. No cap, new public parameter or new solve is proposed here.
