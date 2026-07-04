# Cleanup before combined legacy-path isolation

Context: the direct `HydroMechInitMode=3` CPU control with only the old standalone pore-pressure-rate scheduling was completed and compared against the old CPU baseline.

Recorded conclusion before deleting temporary run artifacts:

- The standalone pore-pressure-rate path improved early and mid-time behavior but did not reproduce the old CPU baseline.
- Initial bottom excess pore pressure was identical to the old CPU baseline.
- At `Tv=1.0`, the standalone-rate run remained slower than the old CPU baseline: about `1.0348 kPa` versus `0.7947 kPa`.
- Maximum bottom-curve absolute difference from the old CPU baseline was about `0.3376 kPa`; target-point bottom difference reached about `0.2401 kPa`.
- The old XML compatibility short check showed the legacy `<soils>` hydromechanics options are still parsed to the same runtime values, so XML migration/default compatibility is not the apparent source.
- The free-surface drainage set matched the old upward-normal criterion in this 1D case: `10` drained top particles at all checked target times, with no extra current-drained particles.

Next isolation: restore both old CPU paths together, namely separate mDBC pore-pressure extrapolation plus standalone pore-pressure-rate evaluation, while keeping all case parameters unchanged.
