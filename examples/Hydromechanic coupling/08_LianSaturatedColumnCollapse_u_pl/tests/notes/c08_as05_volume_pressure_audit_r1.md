# Original AS.5 volume and pressure: read-only audit

This note records the completed read-only calculation; no new calculation/helper invocation accompanies its authoring. Inputs were the existing22-array maps, layouts, clocks and completions in `tests/outputs/c08_h18_wend_psi0_a05_w09_r1/native_r1` (6805IDs/91records) and `tests/outputs/c08_h18_wend_psi0_pre_r2/native_r1` (7060IDs/1001records). All sums use the same5000 material IDs2060..7059; source record1000 is actual PRE at9.9999999997060076s. Maps were opened read-only and their size/mtime pairs matched before/after. Exact stat Entries were not exported by that transient calculation and are not invented here. No BI4 decode, solver, build, SHA scan, active-window access or existing-file change occurred.

## Actual saved totals

Kw=float(1e9)=1e9Pa, n0=double(float(.35)), s=1−n0. Native V is the J-derived current volume per unit depth; its sum is not an independent geometric reconstruction of the deformed column. PRE sum V=7.997137179229603m². Define the signed diagnostic `S=sum(n_i*V_i/Kw*p_i)`, in m² per unit depth, using absolute native pressure.

| Actual tau [s] | All-soil mean J | (sum V/sum V_PRE−1) [ppm] | Mean p [kPa] | S [m²] | Negative soil /5000 | FS2/3 negative / zero |
|---|---:|---:|---:|---:|---:|---:|
| PRE,0 | .999642152004 | 0 | 9.825912 | +2.747506459e−5 | 0 | 0 /100 |
| .000005 | .999642152320 | +.000316 | 9.717974 | +2.717324994e−5 | 2 | 2 /147 |
| .100005 | .999641957837 | −.194236 | 6.621810 | +1.851211626e−5 | 1203 | 147 /2 |
| .300005 | .999641104183 | −1.048196 | 1.772377 | +4.930147644e−6 | 1834 | 147 /0 |
| .600005 | .999642818118 | +.666353 | −18.237494 | −5.113113718e−5 | 3175 | 148 /0 |
| .900000 | .999642406418 | +.254505 | −27.602138 | −7.734687483e−5 | 4074 | 148 /0 |

There were no positive saved FS pressures in these rows. Receiver times are nearest actual saves: .100004999996214/.300004999988643/.600004999977285/.899999999965928s since PRE; the first receiver state is genuine PRE+1, not PRE relabelled as t0. Saved FS masks are recomputed at save and need not equal an earlier RHS mask.

At.9s, sum V=7.997139214544994m², ratio=1.0000002545054993 and change=+2.035315391e−6m². S changes by−1.048219394e−4m², or−13.107433ppm of PRE total volume. The storage-weighted pressure mean changes9.822566→−27.652137kPa; the arithmetic mean changes9.825912→−27.602138kPa. Thus the suction is broad, not solely one negative outlier. All148 saved FS particles at.9s are negative, with minimum/mean approximately−67.2824/−53.5197kPa.

## Which pressure/volume relation is justified

The original frozen schema2 archive gives n=1−s/J and V=V0*J (`src/source/JSphCpu.cpp:3139-3141`; GPU pressure n at `JSphGpu_ker.cu:1534`). Its same-stage compression source is p_dot_comp=−Kw*theta/n (`JSphGpu_ker.cu:1588`; CPU3254). Volume uses explicit midpoint: Jh=Jn+(dt/2)*Jn*theta_n and Jnew=Jn+dt*Jh*theta_h (`JSphCpu.cpp:3303,3318`; GPU `JSphGpu_ker.cu:1398-1401`, host1999). Pressure is also midpoint-rate accumulation rounded to float (`JSphCpu.cpp:3357,3375`). Admitted plastic volume follows this divergence update; psi0 does not force theta or elastic volumetric changes to zero.

For the **compression-only continuous equations**, J_dot=J*theta gives

`dp_comp/dJ=−Kw/(J−s)`, hence `Delta p_comp=−Kw*ln[(J−s)/(J_PRE−s)]`.

This is a conditional continuum reference, not an exact identity of the implemented discrete trajectory. In one corrector the compression-only increment is `−Kw*Delta J/(Jh−s)`; it is a midpoint quadrature for the logarithm, not its exact finite integral. The actual update additionally contains Darcy/acceleration/variable-k terms and completed-state pressure projection. Saved10ms endpoints do not retain all intervening Jh/theta/rates, so their difference from the log reference cannot isolate any one source term or precision effect.

Kw/n is about2.86GPa (final local range2.682–2.885GPa). Dimensionally a uniform dilation of only about13ppm could generate a37.4kPa pressure drop. However, actual net native dilation at.9s is only.255ppm: applying a uniform-mean-J comparator gives approximately−.73kPa, far below observed mean Delta p=−37.42805kPa. At.1/.3s the native total volume even decreases slightly while mean pressure decreases. The observed bulk offset is therefore not explained by the measured global dilation alone.

Heterogeneity also matters: averaging the per-ID compression-only log reference at.9s gives **+27.10115kPa**, opposite in sign to actual mean Delta p; the PRE-volume-weighted reference is+26.85279kPa. It cannot be replaced by the logarithm of mean J. This comparison identifies an unresolved contribution of the complete coupled update/boundary/integration history; it is not new evidence that a specific Darcy term, contact stage or rounding operation is the root cause.

## Boundary and storage limitations

The actual completed-step FreeSeepage cap writes only finite positive FS pressure to zero (`JSphGpu.cpp:1428-1434`, `JSphGpu_ker.cu:1108-1109`). Negative pressure is retained; it is not a p=0 Dirichlet boundary. The original raw FS RHS continues to evaluate LP+rho*(Ace.Lx+Da), with the variable-k chain, rather than setting rate or an observed pair flux to zero (`JSphGpu_ker.cu:1585-1600`). Calling the negative branch “no-flow” describes its intended unilateral policy; these formulas do not certify exact discrete zero normal flux or conservative global transport. At fixed geometry/J/prescribed Ace, a constant pressure offset leaves the pressure-difference terms unchanged, while negative values have no zero-pressure clamp restoring that offset.

S is a **conditional linear pressure-storage proxy with changing n and V**. Its value/change is not actual water mass, saturation, cavitation, measured boundary flow, or a proven global conservation residual/invariant. The current operator is not documented as a conservative pair flux; the cap, evolving masks, body/contact coupling and time integration must be distinguished. Native J/V themselves need not equal a geometric determinant reconstructed after NoPen projections. These totals explain pressure sensitivity and constrain simple explanations; they neither establish physical admissibility of the suction nor prove its cause. No numerical/physical gate or equation is changed.
