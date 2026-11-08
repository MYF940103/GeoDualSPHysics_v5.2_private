# Release Shepard40 rejected for C08

The actual GPU/tool exits are both1, with matching owner49996/target11012, frozen source/program/input/PRE and no ownership error. Original90-frame/.90s plan is unchanged. Only72 frames completed, ending at actual10.720000000602795 s (tau0.7200000002285378), completed4288000/saved4287999. Engine reports the necessary pore-step bound2.4984880987us below fixed2.5us at step4289868, with speed118.7379m/s. This is an actual numerical failure, not a postprocessing or notification failure. Its unsaved failure field/time is not reconstructed.

Unique partial native read passed all original22-array/6805-ID, P0, J/n/V/rho/k/cache, nondecreasing plastic history, drainage, plane, scalar-clock and signed-dterror guards for all72 saved frames. This validates the saved data only. Baseline retained total-AS/n3 has its original90-frame header and real byte-prefix proof against root r6; comparison uses its first72 actual same-time states without rewriting either header or the launch plan.

At the final shared save tau0.72:

| Quantity | Retained n3, Shepard OFF | Release Shepard40 |
| --- | ---: | ---: |
| Pressure min/max (kPa) | -51.328 /15.935 | -271.776 /159.432 |
| Pressure RMS (kPa) |14.281 |24.376 |
| PRE material mean settlement (mm) |97.366 |98.069 |
| Front particle-center x (m) |4.604954 |4.647374 |
| Maximum speed (m/s) |0.85234 |0.96019 |
| Minimum nonself distance/dp |0.42033 |0.26185 |
| Pairs closer than0.7dp |42 |56 |

These are same-time algorithm differences, not theory errors or half-step errors. Shepard has not removed clustering and cannot be selected merely because some individual filter calls reduce pressure extrema.

There are7246 real metered calls, not the planned9000. The final46 calls occur after the last native save. They independently observe filter-global pressure envelopes, not saved particle coordinates or peak material IDs. Their filter-derived last completed clock is10.724600000604255s, not an inferred solver failure time. Whole-window pre-filter pressure extrema reach-242.450592/+299.812640MPa, and maximum single-call pressure change is50.487120MPa. An earlier burst near tau0.53 also grows and decays between10ms native saves; native plots alone under-sample these excursions.

The cumulative filter storage change is-4.79127053e-5 in the producer's2D unit-thickness model-volume units; sum of absolute net changes is1.45688830e-4 and sum of particle-weighted absolute changes3.53455010e-3. Relative to the first actual filter-before S0, these are-1.83190,5.57028 and135.14019. S=sum(nV/Kw*p), with wrapper free-surface projection included, is not true fluid mass and S0 is not the PRE initial state. These figures expose substantial numerical intervention, not a fluid-mass-balance measurement.

Root inspected all three `figures/upl_c08_shepard_compare_r1_{history,meter,final}.png` and matching CSVs. Signed pressure ranges are retained; final spatial plots share color ranges and preserve all soil points. Full-bed context makes local features small, so these are diagnostic figures rather than final paper-comparison graphics. Retain all original outputs and this failed private build; do not install the release-Shepard intervention, repeat it with a smaller dt, or start the other psi groups from this outcome.

Next bounded work is a no-time-advance CPU force observation of the previously untested velocity -> AV acceleration -> dynamic Darcy pressure-rate block at the actual0.50/0.72 saved states. Literature supports using the same numerical acceleration rather than blindly deleting AV/AS. This observation must report its frozen-direction/float/branch limitations and cannot itself prove full coupled stability. Production code and formal configuration remain unchanged.
