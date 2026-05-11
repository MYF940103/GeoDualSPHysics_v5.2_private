# Analytical Solution Notes for GPU G9/G9b Scenario 2 Comparison

Source:

- `src/papers/u-p/supporting_information_implementation_notes.md`, Section 3.
- Initial self-weight pore pressure from Eq. (4) in the local notes:
  `p0(z) = [(Kw/n) rho g (H-z)] / [K + 4G/3 + Kw/n]`.
- Dissipation basis from the Supporting Information Scenario 1 cosine series:
  `u(z,t) = sum A_n cos(lambda_n z) exp(-lambda_n^2 c_v t)`,
  with `lambda_n=(2n+1)pi/(2H)`.
- Scenario 2 keeps gravity on, so total pore pressure is reconstructed as
  `p_total(z,t)=p_hydro(z)+u(z,t)` and tends toward hydrostatic pressure.

No machine-readable Supporting Information curve data were found in the
repository. Curves here are reconstructed from the formulas above.

Parameters used:

- `E=2e+06 Pa`
- `nu=0.3`
- `K=1666666.66667 Pa`
- `G=769230.769231 Pa`
- `M=K+4G/3=2692307.69231 Pa`
- `Kw=2e+08 Pa`
- `n=0.3`
- `k=0.001 m/s`
- `rho_w=1000 kg/m3`
- `rho=2100 kg/m3`
- `g=9.81 m/s2`
- `zmin=0.0049999999 m`
- `zmax=0.995 m`
- `H=0.9900000001 m`
- `cv=k*M/(rho_w*g)=0.274445228574 m2/s`
- drainage clock starts at `t=0.002 s`
- analytical initial bottom excess `u(0,0)=20299.236034 Pa`

Important data limitation:

The G9/G9b raw `PartCsv_*.csv` profile data were intentionally cleaned after
the long runs. Time-series comparisons use retained frame-metrics CSV files.
Profile comparisons recover approximate profile curves from the retained SVG
figures; therefore profile error metrics are approximate and are marked as such
in `analytical_comparison_metrics.csv`.

Plot coordinate convention:

- Profile figures now follow the Supporting-Materials style more closely:
  horizontal axis is normalized pore pressure and vertical axis is normalized
  column elevation `z/H`.
- The profile figures use two side-by-side panels: `xi=0.10` on the left and
  `xi=0.05` on the right.  All target `Tv` profiles are overlaid in each panel.
- In profile figures, color identifies the profile time / `Tv`; solid lines are
  GPU results and dashed lines are the reconstructed analytical solution.
- `z/H=0` denotes the bottom no-flux side and `z/H=1` denotes the top drained
  side.
- Pressure and excess pressure are normalized by the reconstructed analytical
  initial bottom excess pressure `u(0,0)=20299.236034 Pa`.
- Time-history figures use normalized consolidation time
  `Tv=cv(t-0.002)/H^2` on the horizontal axis.
