# Stage1 ON/OFF equilibrium diagnostic

Both sealed 61-frame runs and all four prerequisite jobs passed their existing execution/safety gates. This review adds no physical acceptance gate.

Reference: M=K+4G/3, Mf=Kw/n, B=Mf/(M+Mf); ph=rho_w*g*(H-z), q=B*(rho-rho_w)*g*(H-z), sigma_zz=-(1-B)*(rho-rho_w)*g*(H-z). R=q_native+Mf*trace(sigma)/(3K). H1 and HD curves use separate explicitly labelled reference planes.

| Job | Actual final t [s] | Bottom p / native q [kPa] | Bottom effective zz [Pa] | Bottom total zz [kPa] | Top / bottom s [mm] | Max speed [m/s] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| on | 0.300000999999 | 20.1473451 / 10.4354447 | -462.310144 | -20.6096553 | 0.0187861401 / 0.00695586221 | 1.30057645e-05 |
| off | 0.300000999999 | 20.8744682 / 11.1625678 | -44.8709434 | -20.9193391 | 0.0104194753 / 0.00290247338 | 4.29937831e-05 |

on: final actual time 0.30000099999889152 s; HD=0.99499999999999988 m. Last-window 0.25000000000022932..0.30000099999889152 s, 11 samples; max speed 7.86218007e-05 m/s; maximum layer pressure endpoint drift 19.6675781 Pa; final layer-mean R RMS / max 15865.5251 / 104041.356 Pa. Initial/final changes and both ideal-reference RMS/max errors are diagnostic JSON metrics, without pass thresholds.

off: final actual time 0.30000099999889152 s; HD=0.99499999999999988 m. Last-window 0.25000000000022932..0.30000099999889152 s, 11 samples; max speed 9.65150393e-05 m/s; maximum layer pressure endpoint drift 50.9224609 Pa; final layer-mean R RMS / max 4363.00147 / 43628.9894 Pa. Initial/final changes and both ideal-reference RMS/max errors are diagnostic JSON metrics, without pass thresholds.

- Diagnostic small-strain, linear constrained-column references only; no new theory-error threshold or physical acceptance.
- H=1 is the physical geometry; HD is the initial drained material-node plane. Neither is fitted or used to shift saved data.
- The ideal undrained reference excludes Shepard. Enabled Shepard changes local excess pressure without changing effective stress.
- k=0 eliminates Darcy, including symC; this is not a symC accuracy test. The ten drained top nodes still have finite particle volume.
- p0 is a fixed material reference; native float excess and double(p)-double(p0) are reported separately.
- Current hydro uses the mean actual drained top-material plane, not a fitted boundary or a recomputed per-particle p0.
- Layer curves use fixed initial material IDs. All 61x100 layer means are retained; no smoothing, clipping or interpolation.
- Independent native redecoding covers first/final frames. Full 61-frame native safety/ID coverage comes from verified sealed receipts.
- Sealed owned-exit evidence is checked; this offline analysis does not launch a solver or perform a new process inventory.
- The original 5-Pa/.005-mm limit belongs to the short matched-time half comparison, not ON/OFF or ideal-theory differences.
- Completion is not equilibrium, restart interoperability, long-cycle or general constitutive acceptance.

Next decision remains a physical review of late drift, stress/weight balance and the chosen handoff state; only then a separate Scenario2 interoperability test. No automatic solver, restart or formal run is launched.
