# C08 psi0 volume/stress consistency: bounded code and saved-state audit

Read-only audit of the frozen schema2 source used by the current Wendland AS
screen. Relevant current JSphGpu/JSphCpu, JSph.cpp, TypesDef.h and
FunSoilMaterial.h files match `outputs/c08_preload_schema2_source_r1/full_source.json`
byte lengths and exact recorded modification times. This is stat binding, not a
new content-hash proof. Only this note is added; no physical source/input change,
build, solver, native decoder, Git or hash operation is performed.

## The two rates share the intended same-stage operator

Actual C08 uses Kernel2/H1.8, PoreCompressionGradCorr=1,
SoilStressRateGradCorr=1, dynamic-wall derivative images,
SoilBoundaryDerivativeSPR=0, no symmetry/floating particles, DensityDT=0 and
Shifting=0. For a soil target i, write g_ij=grad_i W and
V_j=(massf/rho0)*J_j. In exact arithmetic its volume divergence is

`theta_J = sum_j V_j (v_j^deriv-v_i) dot (C_i g_ij)`.

`source/JSphGpu_ker.cu:1931-1966` selects the derivative velocity and computes
this sum. Its stress branch first accumulates the rows of
`Lraw = sum_j V_j (v_j^deriv-v_i) tensor g_ij`, then applies the same C_i
to each row (`2078-2081`, `2260-2267`; row convention at `800-804`). Thus
`trace(D)=trace(L)=theta_J` algebraically for this actual configuration. The
code does not intentionally use two different corrected divergence operators.

There is no bitwise identity gate between these results. Theta promotes the
float pair displacement/kernel factor to double, corrects each pair in double,
and accumulates in double (`1941-1966`). The stress gradient first rounds
V_j to float, forms float kernel-gradient products and float neighbor sums,
then applies the double matrix and converts back to float (`1798`, `2078-2081`,
`800-804`). Elastic moduli/rates are float; saved stress state is double.
These differences can create roundoff differences, especially for poorly
conditioned correction matrices. Their existence does not establish a cause
of AS.5 suction or early arrest.

## Wall and contact staging

Each predictor/corrector calls the force routine on that stage's state
(`JSphGpuSingle.cpp:813-827`). Dynamic wall state/derivative velocity is fitted
before the common correction matrix and forces (`JSphGpu.cpp:1329-1340`;
`JSphGpuSingle.cpp:631-670`). Independent legacy SPR returns immediately when
the dynamic wall owns the derivative state (`JSphGpu_mdbc.cpp:135-140`).
The wall writer supplies the same fitted J and derivative velocity to both
branches; actual wall `Velrhop` remains zero (`JSphGpu_mdbc_ker.cuh:152-175`).
Inactive J-wall pairs are skipped at `JSphGpu_ker.cu:1820-1823`.

NoPen projects trial displacement and incoming normal velocity after stress/J
advancement: predictor `JSphGpu.cpp:1775,1789-1791,1814-1815`; corrector
`1853-1855,1871,1881-1882`. The projection kernel changes displacement and
velocity only (`JSphGpuSimple_ker.cu:445-457`); it does not repair sigma, J or
pressure. The corrector sees the projected half-state, but there is no new
same-stage contact reaction in the already evaluated rates. Consequently the
shared rate does not guarantee J equals a determinant reconstructed from
projected particle positions, or close the contact/J/Darcy reaction balance.

## Trace identity and actual return-map exception

Elastic stiffness and Jaumann rotation give `trace(Rsigma)=3*K*trace(D)` in
exact arithmetic (`JSphGpu_ker.cu:586-622`): the rotational trace cancels.
For constant K and no volumetric return correction, the continuum expectation
is `I-I_PRE = 3*K*log(J/J_PRE)`, where I is trace of effective stress.

At psi0, DP_psi is zero (`FunSoilMaterial.h:52-68`). Ordinary smooth shear
return preserves trial I even with cohesion softening (`105-109`, `172-175`,
`198-205`). Increasing kappa alone therefore does not invalidate this identity.
However, the separate tension-face return sets I to `kc/alpha`
(`134-150`); at trial q=0 this can change I with zero kappa increment.
**Kappa=0 or unchanged kappa is not proof that every intervening step was
elastic.** An Apex label alone is also insufficient: the smooth endpoint can
preserve I. Actual trial-minus-returned trace is the relevant correction.

The implemented midpoint updates are
`Jh=Jn*(1+dt*theta_n/2)`, `Jnew=Jn+dt*Jh*theta_h`
(`JSphGpu_ker.cu:1398-1401`) and
`Inew=In+dt*trace(Rsigma_h)-Dret`, where
`Dret=Itrial-Ireturned` (`JSphGpuSimple_ker.cu:755-763`). Therefore

`deltaI-3K*log(Jnew/Jn) = 3K*dt*(theta_S-theta_h)`
`  +3K*[dt*theta_h-log(1+dt*(Jh/Jn)*theta_h)]-Dret`,

with `theta_S=trace(Rsigma_h)/(3K)`, plus arithmetic rounding. Even equal
rates do not preserve the logarithmic invariant exactly: constant theta gives
`Jnew/Jn=1+x+x*x/2`, not exp(x); its smooth local log defect is O(dt^3).

## Existing typed22 endpoint observation

A transient read-only NumPy calculation used the existing typed22 layouts,
all 5000 matched soil IDs and actual source Part1000 reference; no BI4 decoder
was run and no analysis output was written. It used double `SigmaState_kk`,
native double J and the actual float K=19607844 Pa from the formula at
`JSph.cpp:4228`, with `R=I-I_PRE-3*K*log(J/J_PRE)`.

| Exact shared save | AS | mean R [kPa] | RMS R [kPa] | minimum R [MPa] | IDs with abs(R)>10kPa |
|---|---:|---:|---:|---:|---:|
| tau .3000049999886425 | .3 | -1.09539 | 20.4594 | -1.08039 | 58 |
| same | .5 | -11.4260 | 56.3151 | -1.58672 | 352 |
| tau .6000049999772852 | .3 | -10.5689 | 58.4133 | -1.20219 | 356 |
| same | .5 | -60.9171 | 150.732 | -2.33503 | 1185 |
| tau .8900049999663064 | .3 | -25.5851 | 157.522 | -6.39156 | 602 |
| same | .5 | -88.9295 | 182.495 | -2.33503 | 1691 |

At the common last save, maximum positive R is only .489882/.309369 Pa.
The current-kappa-zero subsets have 1235/846 IDs and RMS R
.000405738/.000646951 Pa, respectively. First PRE+one-update R RMS is about
9.2e-9 Pa for both. These subsets are descriptive observations, not a logical
certificate excluding tension-face repair. AS.3 is still a failed run with a
qualified saved prefix; its missing final state is not supplied.

The negative residual pattern is compatible with accumulated trace-reducing
returns, but endpoints cannot establish that attribution. The .01s snapshots
omit about 2000 internal updates, material statuses and stage integrals;
`PoroThetaLastStage` contains only the last evaluated stage, not their sum.
Separating operator roundoff, integration and return correction requires
their actual stage accumulations. Saved n/volume/rho are derived from J and
are not independent volumetric-strain evidence. This audit neither proves
the cause of pore-pressure evolution nor supplies physical acceptance.
