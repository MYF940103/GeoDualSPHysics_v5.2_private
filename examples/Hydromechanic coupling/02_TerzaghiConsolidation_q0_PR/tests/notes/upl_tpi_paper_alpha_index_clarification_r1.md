# Lian TPI alpha and pressure-update indices: independent clarification

2026-11-17. This new note records a direct rereading of the local original;
no existing frozen note/script, alpha, numerical implementation or active dependency is changed.
No solver, build, native reader, new reference, parameter scan or candidate is launched.

## Exact local sources and locations

- PDF: `D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/papers/PDF/Lian 2023 u-pl.pdf`.
  PDF1-based pages7,8,10 also carry printed page numbers7,8,10.
  Section3.3/Eq27 is page7; Eqs35–39 and their explanatory paragraphs are page8;
  Fig1 is page10. The figure was already visually available in the separately
  retained `tests/outputs/upl_tpi_paper_timing_r1/Lian2023_page10.png`; it was not regenerated.
- Text: `D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/papers/u-pw/Lian 2023 u-pl.md`.
  Lines373–381: half-level storage and Eq27. Lines435–447: the unknown linear system,
  Eq35 and source Eq36. Lines448–459: Eq37 and its approximation. Lines460–474:
  Eqs38–39, the meaning of alpha and its selected value. Lines515–519: Fig1 discussion
  stating that the pressure calculation changes while other variables retain LF.

## What the written pressure indices say

The following is mathematical transcription of indices, not a new numerical scheme:

```
Eq35: p_i^(t+1) = [B_ij + sum_j A_ij*p_j^(t+1)] / sum_j A_ij
Eq37: p_i^(t+1) = [B_ij + sum_j A_ij*p_j^t]     / sum_j A_ij
Eq38: p_i^(t+1) = [B_ij + sum_j A_ij*p_j^(t+alpha)] / sum_j A_ij
Eq39: p_j^(t+alpha) = p_j^t + alpha*(p_j^t-p_j^(t-1)).
```

The unknown output on the **left stays t+1** throughout35,37,38.
Only the unknown future neighbour pressure on the right is replaced, first by its
old value and then by an intermediate extrapolation from two known pressure levels.
The text at MD448–454 calls the right-hand quantities known at instant t and
explicitly describes calculating the output at t+1. MD463–474 defines the
intermediate pressure, permits alpha between0 and1, relates the limiting choices,
and says that the optimal coefficient also depends on timestep size. The reported
numerical investigation selects alpha=.5 for reasonably accurate/stable results.

Thus **alpha=.5 is the paper's timestep-dependent empirical neighbour-pressure
correction choice. It is not a compulsory factor because LF advances pressure
through only half a timestep.** The authors do not derive that value from Eq27.
Their statement about the alpha=1 limit also does not turn finite extrapolation
into a globally converged implicit solver in our implementation.

## LF storage does not mean a half-size pressure advance

Eq27 separately declares
`Upsilon_(t+dt/2)=Upsilon_(t-dt/2)+dt*rate_t`, with pressure included in Upsilon;
position advances from t to t+dt using the new half-level velocity.
The two pressure storage levels in this formula are separated by a **full dt**.
They are not an old full-level pressure and a new pressure only dt/2 later.

Section3.4 changes notation to t,t-1,t+1 without explicitly mapping each of those
indices onto Eq27's half-level physical times. One can consistently *choose* a
pressure-update index k with p^[k]=p_(n-1/2), p^[k-1]=p_(n-3/2), and unknown
p^[k+1]=p_(n+1/2); alpha=.5 then predicts the intervening physical time t_n.
That is an explanatory reindexing, **not an explicit mapping supplied by the paper**.
It must not be cited as proof that the paper forces alpha=.5 or directly specifies
our current full-grid pressure history. Fig1 contains processing order, not the
missing detailed superscripts or acceleration-source centring.

## Consequence for the current private P1 interpretation

P1 stores full-grid p_n,p_(n-1). The shared
`g=p_n+.5*(p_n-p_(n-1))` naturally forecasts its mechanical half pressure on a smooth
full-grid history; using the same g in the endpoint pressure row is an additional
selected Symplectic-compatible closure. Eqs38–39 support its neighbour-extrapolation
idea but do **not** instruct reuse of that field for both mechanical half and full
endpoint, nor specify P1's third endpoint force/full-R evaluation.

The paper alone still does not identify every Eq36 acceleration/source time or
the detailed centring of LF rates. Consequently this clarification neither orders
alpha to become1 at the endpoint nor proves that a new literal-LF implementation
would remove the present error. Any such algorithm needs an explicit source,
history, force, BC, material/J/HG and output-time contract plus independent evidence.
No automatic alpha change, LF replacement, local iteration or physical run follows.
