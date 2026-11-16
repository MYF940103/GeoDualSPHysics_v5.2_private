# P1: TPI/PPE-t time layers and fixed-mode consistency (author preparation)

2026-11-17. Only new assets are `support/upl_tpi_time_layers_r1.py` and this note under case02/tests. Author does not execute the component, any old component, a force, physical solver, reader, build, Git or hash. Root must read and separately admit one algebra-only execution. This reuses the **definition** in old C08 `c08_tpi_coupled_r1.py`; it does not rerun its 24-case entry or alter its results. Original A data and paused C08 owner/GPU remain untouched.

## Selected B/C time schedule

For this clear full-pressure-prediction comparison define endpoint-neighbor extrapolation alpha and mechanical-half forecast kappa separately in the algebra, then freeze:

- B: alpha=.5 and kappa=.5, matching retained X0 beta0.
- C: alpha=0 and kappa=0; no previous pressure is used by either half or endpoint guess.

Thus B/C differ in the **complete pressure prediction rule**, including the pressure used by mechanical half force, not only the endpoint neighbor row. Do not call it a perfectly isolated endpoint-alpha experiment. An alternative alpha0/kappa.5 would isolate neighbor extrapolation but still use previous pressure in mechanics; it is not the selected no-history C, and no extra physical run is proposed here.

At old state y=(sigma,v), pressure pn and previous pm, using iq=i*q:

1. an=iq*(sigma−pn)/rho; yh=y+.5*h*(As*y+b*pn).
2. ph=pn+kappa*(pn−pm); ynew=y+h*(As*yh+b*ph).
3. guess=pn+alpha*(pn−pm); a_endpoint=iq*(sigma_new−guess)/rho.
4. S=k*q²/(1−mu), B=−gamma*iq*vnew+rhow*k*iq*a_endpoint; pnew=(B+S*mu*guess)/S.
5. previous becomes actual pn exactly once after full success in a real implementation.

No beta is present. This is the current original-space/Symplectic endpoint extension, not literal Lian LF or a converged pressure Poisson solve.

## Independent M0 reference and shifted fast block

Let r=rhow/rho, dr=rho−rhow>0. Eliminating pressure from the continuous fixed-mode equations gives

    p = P y,
    P = [−r/(1−r), −gamma*iq/(k*q²*(1−r))],
    y_dot = L y,
    L = [[0,H*iq],[iq/dr,−gamma/(k*dr)]].

For the retained S split, define m=r+(1−r)*mu. The actual endpoint update is exactly

    pnew=(1−m)*P*ynew + m*[(1+alpha)*pn−alpha*pm].

This identity, including density-feedback shift mu→m, is new coverage distinct from the old standalone scalar row. At h=0 the physical state is frozen; the pressure-history fast block has characteristic

    z²−m*(1+alpha)*z+m*alpha=0.

For real m and 0≤alpha≤1, strict Jury conditions are 1−m>0, 1+m*(1+2alpha)>0, and 1−m*alpha>0; equivalently −1/(1+2alpha)<m<1. The selected mu=.2/.8 and retained rho/rhow lie in that domain. This does not prove an actual irregular SPH operator has real modes or lies in it. At m=1 the pressure gauge branch is neutral; alpha=1 makes a double unit root and can drift. No alpha1 physical option is selected.

## Consistency and order: no second-order claim

On a smooth, stable slow manifold write p=Py+h*z1*y+O(h²). The endpoint identity yields

    z1 = −[m*(1−alpha)/(1−m)]*P*L.

So beta0 alpha=.5 and alpha0 both approach the same M0 constraint as h→0 **when the fast block is stable and the limit is regular**, but the endpoint pressure has a generic O(h) lag. Alpha=.5 halves this leading lag relative to alpha0; it does not remove it. Existing X0 must not be called second-order merely because the solid integrator is Symplectic or the pressure uses three points.

With mechanical pressure coupling b=[0,−iq/rho]^T, comparison of the one-step solid map with exp(hL) gives modified generator

    L_eff=L+h*L1+O(h²),
    L1=[kappa−.5−m*(1−alpha)/(1−m)]*b*(P*L).

For selected B the coefficient is −m/[2(1−m)], and for selected C it is −.5−m/(1−m). Generally both are first order as combined endpoint extensions, though error coefficients differ. Mode-specific cancellation or spatial error can hide this order; it cannot be asserted from one physical curve. Setting kappa=.5 alone does not remove pressure slow-manifold lag. Choosing kappa to cancel it would depend on m/spatial modes, so is not a universal fix.

The root may accept a first-order method only if measured benchmark accuracy meets the frozen requirement; if a second-order claim/design is required, the time schedule must be redesigned and tested, not rescued by beta/HG/damping.

M0 retains a mechanical-Darcy relaxation scale tau=k*(rho−rhow)/gamma independent of Kw. For retained k=.0002, tau≈2.187e−5s; k=.00001 would give≈1.094e−6s. Removing the explicit finite-Kw diffusion bound does not remove all coupled stiffness. These continuous scales are **not** a universal 2*tau timestep limit for actual SPH; the full discrete map, AV, boundaries and spatial modes matter.

## Proposed new tiny component, not executed

The script uses the old fixed Fourier **example** material values (H=29632906Pa,rho2072.5,rhow1000,k=.0002,gamma9806.65), not case02's real k=1e−4 A input. It directly checks the independent M0 constraint and h0 endpoint identity, 4 shifted fast blocks, and 32 new 4×4 matrices/128 modes for B/C at q=pi/2,pi/.04,mu=.2/.8 and algebraic h=1e−8..8e−8. These tiny h only expose the Taylor limit in milliseconds of algebra; they are not proposed particle time steps or a new long run.

The matrix uses the actual selected half forecast. It verifies linear-map/eigensystem arithmetic, preserves all four physical/history modes, reports principal-log generator errors, the analytic first modified-generator coefficient and observed fast-mode error order. Two physical mode matches minimize exact amplification error over all4! assignments; this is a diagnostic association, not proof of a full invariant subspace in real SPH. Near h→0 the selected physical roots are well separated from stable history roots, but roundoff and branches are retained.

`passed` means the declared algebra/counts and arithmetic completed, **not** that TPI is second-order, stable for real SPH, physically accurate, or selected for release. Order/coefficient results are reported rather than silently thresholded into success. Beta and pressure clipping are absent. No native/SPH state is opened, advanced or rewritten. Four CSVs are new under `outputs/upl_tpi_time_layers_r1`; summary receipt is `logs/upl_tpi_time_layers_r1.check.json`. Existing/partial outputs refuse overwrite.

After root full read only: `D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_time_layers_r1.py --execution-authorized` from case02 root. No solver/build/native/GPU or next stage follows automatically.
