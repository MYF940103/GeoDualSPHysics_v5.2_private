# C08 radial RV window: physical decision r1

The one fresh .90s GPU solve completed safely with180000 new updates/91 saves, actual end10.899999999671936s and actual release-relative end.899999999965928s. Original Pre/Cor calls/commits180000 each, MFG5 and fixtures8 passed. The unique original22 native read and three-trajectory analysis passed; all four PNGs were inspected. This is implementation/native completion, not physical repair acceptance.

| Actual trajectory | Final p RMS kPa | Final pairs r<.5dp | Final min NN/dp | Worst saved NN/dp | Worst saved p kPa | Front advance m | Top settlement mm | .6-.9s motion RMS mm |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Retained original AS03 | 12.9522 | 7 | 0.351468 | 0.270834 | -58.414 | 1.01932 | 264.755 | 150.294 |
| Vector RV alpha0.1 | 7.30818 | 66 | 0.211515 | 0.211515 | -58.3275 | 1.08818 | 304.543 | 203.66 |
| Radial RV alpha0.1 | 10.724 | 8 | 0.241752 | 0.092459 | -61.2758 | 0.991432 | 266.508 | 154.51 |

Relative to the retained AS03 diagnostic, final p RMS changes by-17.203%, but the final close-pair count is8 versus7 and the worst saved spacing falls to.092459dp versus.270834dp. Worst saved pressure becomes-61.276kPa versus-58.414kPa. Final front and top settlement remain close to the original response, with little evidence of repaired early arrest. The new loop is5908.236816s versus1887.332764s: 3.130469 times the observed trajectory cost, not an isolated benchmark.

Decision: do not select either vector or radial RV for formal three-psi delivery. Do not install these test operators into production or start another physical trajectory from normal exit alone. Pressure smoothing and descriptive NN thresholds are not standalone accuracy/stability gates. Preserve all true native clocks and all physical fields; there is no5Pa cross-operator equivalence or half/full convergence claim.

Continue authorized diagnosis using retained states: localize the worst near pair, distinguish anisotropic/shear deformation from nonphysical point crowding, compare material-neighborhood deformation with the independently evolved J field and actual stress/FS/pressure response. Check existing HG eligibility before any attempted reuse: a plastic C08 activation cannot be inferred from the passed elastic column. Reconcile earlier H1.8 AS parameter evidence before choosing another intervention; no blind parameter scan, new PRE, other psi or half chain is admitted by this decision. Raw solver and native outputs remain intact.
