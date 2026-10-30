# G0/G1 Stage1 diagnostic, both ShepardOFF

All 61 actual matched frames per variant passed their existing sealed execution/safety checks. Four native first/final states were independently decoded. No new physical gate is introduced.

| Variant | Bottom p / q [kPa] | Top / bottom s [mm] | All-layer R RMS [Pa] | Native non-top R RMS [Pa] |
| --- | ---: | ---: | ---: | ---: |
| G0_ShepardOFF | 20.8744682 / 11.1625678 | 0.0104194753 / 0.00290247338 | 4363.00147 | 30.0627686 |
| G1_ShepardOFF | 20.8727605 / 11.1608602 | 0.00981260204 / 0.00293493025 | 4516.65207 | 0.311173925 |

H1/HD errors and multiple material endpoint pairs are diagnostics, not tuned references or 5-Pa theory gates. All-layer R RMS uses 100 layer means; non-top R RMS is the sealed direct 990-particle metric. The excluded top layer is still plotted and retained in CSV. Complete 6100-row source profiles remain linked in JSON, not duplicated. No smoothing, clipping or interpolation is used.

- Diagnostic small-strain, linear constrained-column references only; no new theory-error threshold or physical acceptance.
- H=1 is the physical geometry; HD is the initial drained material-node plane. Neither is fitted or used to shift saved data.
- k=0 eliminates Darcy, including symC; this is not a symC accuracy test. The ten drained top nodes still have finite particle volume.
- p0 is a fixed material reference; native float excess and double(p)-double(p0) are reported separately.
- Current hydro uses the mean actual drained top-material plane, not a fitted boundary or a recomputed per-particle p0.
- Independent native redecoding covers first/final frames. Full 61-frame native safety/ID coverage comes from verified sealed receipts.
- Sealed owned-exit evidence is checked; this offline analysis does not launch a solver or perform a new process inventory.
- The original 5-Pa/.005-mm limit belongs to the short matched-time half comparison, not gradient-option or ideal-theory differences.
- Completion is not equilibrium, restart interoperability, long-cycle or general constitutive acceptance.

Both runs disable Shepard; this option comparison changes only stress-rate gradient correction. No solver, restart, automatic full-consolidation or formal acceptance is admitted. The two PNGs still require visual inspection.
