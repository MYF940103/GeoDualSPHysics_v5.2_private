# q0 k=1e-2 cleanup conclusion

Date: 2026-07-06

The temporary Stage1/Stage2 outputs for the `k=1e-2` q0 Terzaghi tests were cleaned after recording the main conclusion.

## Conclusion

The best tested workflow used a two-stage restart:

- Stage1: `DtFixed=1e-7 s`, `SoilDampingCoef=0.02`, undrained loading/stabilization.
- Restart candidate: `CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010`, `Part_0138`, `t=0.069 s`.
- Stage2: `HydraulicConductivity=1e-2 m/s`, top drainage active from restart, run to `Tv=1`.

This workflow produced good mid-to-late dissipation behavior. In the formal Stage2 run, `Tv>=0.05` tracked the Terzaghi theory reasonably well, and the final `Tv=1` result was:

- `U_num=0.920759`
- `U_theory=0.931260`
- final profile RMS `0.113547 kPa`
- excluded particles `0`

However, the large-permeability early response remains unresolved. At the first formal Stage2 output, `Tv=0.005`, the numerical response still showed strong transient over-dissipation/oscillation:

- `U_num=0.660803`
- `U_theory=0.079788`
- profile RMS `6.03781 kPa`

Increasing Stage1 damping to `0.4` did not solve this without degrading the pressure-state selection, and extending Stage1 beyond the selected restart window made the pressure profile drift low. Therefore, for now, the `k=1e-2` case should be treated as unresolved for the very early `Tv=0.005` point, even though the same two-stage setup is useful from about `Tv=0.05` onward.

The retained durable records are the markdown notes and support/config scripts under `tests/`; bulky run outputs, figures, VTK/CSV products, and logs were removed.
