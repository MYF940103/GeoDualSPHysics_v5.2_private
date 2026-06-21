# Cryer theory and HydroMechLoadAce diagnostics, 2026-06-21

Scope:
- No new simulation was run.
- No C++ source was changed.
- Existing VTK/Run.out/XML outputs were postprocessed for two cases:
  - `refinement/sweep_corrected_20260621/r0000_d0_full_tout0250`
  - `refinement/sweep_corrected_20260621/k1e5_tv008_toutTv001`

Generated diagnostic outputs:
- `figures/cryer_theory_load_diagnostics_theory_parameters.csv`
- `figures/cryer_theory_load_diagnostics_load_summary.csv`
- `figures/cryer_theory_load_diagnostics.json`
- `figures/cryer_theory_load_diagnostics_radial_load_fraction.png`
- `figures/cryer_theory_load_diagnostics_*_radial_bins.csv`

Theory consistency:
- The paper equation was rechecked from the original PDF:
  - Eq. (46): center pressure uses denominator `eta*xi*cos(xi)/2 + (eta-1)*sin(xi)`.
  - Eq. (47): `(1 - eta*xi^2/2)*tan(xi) = xi`.
- The postprocessor has been aligned with these equations.
- Current material parameters give:
  - `E = 2.0e6`
  - `nu = 0.3`
  - `K = 1.6666667e6`
  - `G = 7.6923077e5`
  - `M = K + 4G/3 = 2.6923077e6`
  - `Kw = 2.0e8`
  - `n = 0.3`
  - `Kw/n = 6.6666667e8`
  - `M_eff = 1/(1/M + n/Kw) = 2.6814786e6`
- `M_eff/M = 0.99598`, so including finite water compressibility changes the time scale by only about 0.4%.
- Therefore the present peak underprediction is unlikely to be caused by using `M` instead of a storage-corrected modulus in the analytical time scale.

Time scale:
- For `k = 1e-4`, `Tv = 1` corresponds to `0.091092857 s` using `M`.
- For `k = 1e-5`, `Tv = 1` corresponds to `0.910928571 s` using `M`.

HydroMechLoadAce radial integration:
- At the saved early, peak-window, and final snapshots, all fluid particles have nonzero `HydroMechLoadAce`.
- The net resultant force is nearly zero:
  - order `1e-9` relative residual in both cases.
- The integrated inward equivalent pressure is not too small:
  - `k=1e-4`: signed inward equivalent pressure is about `1.1725-1.1743 q0`.
  - `k=1e-5`: signed inward equivalent pressure is about `1.1742-1.1753 q0`.
  - positive-only inward equivalent pressure is about `1.184-1.186 q0`.
- Radial distribution:
  - about `96.3%` of inward force lies in the boundary band `r >= R - KernelSize`.
  - about `93.9-94.0%` lies in the outer 10% radius.
  - about `3.6-3.7%` remains in the core region `r < R - KernelSize`.

Interpretation:
- The peak being too low is not explained by an under-applied total load; the integrated load is slightly larger than `q0`, not smaller.
- The time-scale mismatch from water compressibility is negligible for the current `Kw`.
- The more plausible sources are:
  1. spatial non-equivalence of the flexible confinement term to the analytical uniform surface traction;
  2. residual inward acceleration inside the nominally complete-support core;
  3. discrete drainage/free-surface representation near the outer shell;
  4. SPH consistency/resolution effects on the early Mandel-Cryer redistribution.

Recommended next checks:
- Use the radial bin CSV/plot to compare `HydroMechLoadAce` localization for any future loading variant.
- If changing the confinement implementation, preserve the near-zero net resultant and add a normalization diagnostic so the integrated pressure can be compared directly with `q0`.
- Do not prioritize further changes to the analytical `Tv` definition unless material parameters or governing storage terms are changed.
