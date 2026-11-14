# X0: small coupled Fourier compatibility component

2026-11-14, author-only. New support/c08_tpi_coupled_r1.py and this note. No author execution/import, force, solver, native, build, Git or SHA action. Root must review and separately admit one algebra-only execution; outputs/c08_tpi_coupled_r1/{cases,modes}.csv and logs/c08_tpi_coupled_r1.check.json are exclusive. Existing failures and physical data stay unchanged.

This is not an SPH transfer spectrum or physical case. Take g=0, constant k, elastic Fourier q>0, stress sigma in Pa and velocity v in m/s. The reviewed equations are sigma_dot=H iq v, a=iq(sigma-p)/rho, and M p_dot=-gamma iq v-k q²p+rhow k iq a, with M in 1/m. Fixed SI inputs are H=29632906Pa, rho=2072.5kg/m³, rhow=1000kg/m³, k=.0002m/s, gamma=9806.65Pa/m and alpha=.5. No coefficient is fitted.

For M=0 the independent reference state (sigma,v) has generator [[0,H iq],[iq/(rho-rhow),-gamma/(k(rho-rhow))]]. For M>0 the reference state (sigma,v,p) has generator

```
[0,                         H iq,         0]
[iq/rho,                    0,            -iq/rho]
[-rhow k q²/(rho M),         -gamma iq/M,  -k q²(1-rhow/rho)/M]
```

Its characteristic polynomial, multiplied by M rho, is M rho lambda³+k(rho-rhow)q²lambda²+(MH+gamma)q²lambda+kHq⁴. With these positive constants the strict continuous decay condition is (rho-rhow)gamma > M rhow H. The beta0 reference uses the incompressible two modes; a fixed negative branch beta>0 uses M_eff=beta(1-alpha) from the dt->0 pressure-row expansion. This latter reference is an **elastic perturbation about a fixed negative background with beta forced active and no branch switching**, a compatibility counterexample to indiscriminately applying beta at all locally elastic points in a plastic material. It is not a disproof of Lian's qualified plastic/dilatant procedure. Actual return/dilation eligibility remains undefined; cumulative kappa or materialTypePlastic alone is not established as sufficient.

X0 is an unselected Symplectic extension, not the paper's LF scheme. It follows exactly the root-declared n-force, half velocity/stress, extrapolated half pressure, half-force full velocity/stress, then an additional endpoint acceleration with p_guess=pn+alpha(pn-pPrevious). Its row uses S=kq²/(1-mu), B=-gamma iq vnew+rhow k iq a_endpoint and pnew=(B+S mu p_guess+(beta/dt)p_guess)/(S+beta/dt); previous pressure then becomes pn. The script constructs the full4x4 amplification from four basis vectors and counterchecks a fixed independent complex vector. It does not assemble real Ai/B/E, boundaries, free surfaces, AV, material returns, J, porosity or particle histories.

The grid is fixed: q=pi/2 and pi/.04 [1/m], mu=.2/.8, dt=5/10/20us, beta=0/.04 m^-1, yielding24 cases and all96 discrete modes. References never depend on mu. Eigenvalues use fixed physical-unit similarity scales (H,sqrt(H/rho),H,H), truncated to the reference dimension; this is not parameter fitting. Reference characteristic polynomials and small-matrix eigensystem residuals have separate arithmetic-only checks.

All4! discrete-mode permutations are considered only to minimize squared amplification error against exp(lambda_ref dt). Unmatched history modes remain in modes.csv; matching does not prove a true invariant-subspace identification. Generator error means principal log(z)/dt minus the assigned reference lambda; zero z is explicitly undefined. Branch/alias limitations and all positive growth are retained. There is no physical error pass gate: passed means the declared algebra, counts and arithmetic checks completed, not that X0 is acceptable. Growth in the elastic fixed-beta reference must be reported, not hidden, tuned away or presented as automatic failure of the paper's plastic model.

Root-only command after review: python -B tests/support/c08_tpi_coupled_r1.py --execution-authorized. No physical job follows automatically. Original physical guards do not apply to this paper component and are not relaxed or replaced by it.
