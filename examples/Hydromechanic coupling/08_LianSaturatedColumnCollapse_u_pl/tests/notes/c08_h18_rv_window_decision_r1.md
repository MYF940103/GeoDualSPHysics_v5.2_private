# C08 H1.8 RV 0.90 s review decision

The single R2 solver and its unique native/analysis reviews completed safely. Actual end is 10.899999999671936 s, drainage/release-relative tau is 0.89999999996592805 s; 91 native states, all 5000 original soil IDs and 6805 active IDs were retained. Solver exit zero alone was not used as physical acceptance. All four history/spatial PNGs were visually inspected and matching CSVs retained.

## Measured outcome

| Final metric | Retained AS03 | RV alpha .1 |
|---|---:|---:|
| Native pressure RMS (kPa) | 12.952182 | 7.308176 |
| Minimum pressure (kPa) | -41.433926 | -16.281699 |
| Front advance from PRE (m) | 1.019316182 | 1.088181261 |
| Fixed top-material settlement from PRE (mm) | 264.755326 | 304.543039 |
| Minimum nonself NN / dp | 0.351468232 | 0.211514726 |
| Unique pairs below .5 dp | 7 | 66 |

The final pressure RMS falls 43.576%, and fixed material motion continues more strongly. However, full-window worst suction remains approximately -58.4 kPa in both trajectories. At P38, RV improves NN min .3607 to .5737 dp; the close-pair count reverses around P43 and late slip-band stripes become denser. This is a mixed result, not a tensile/clumping repair. Thresholds .7/.5/.3 dp are descriptive spacing measures, not newly imposed physical acceptance criteria.

Observed loop times are 1887.332764 versus 4041.640137 s for the same 180000 new updates, ratio 2.141456035. This is not an isolated benchmark: trajectories and neighbor costs differ.

## Decision and continuation

Do not select RV for formal 3 s or unlock the other psi groups from this result. Preserve every completed/failed tag and certified PRE. Continue a narrow offline diagnosis of new material pairs through .40-.45 s and late slip-band evolution. Distinguish tensile attraction from compressive/shear localization using actual stress signs, pair relative velocity and material histories. No exact RV force history is reconstructed from saved native states. Audit shifting transport compatibility before considering it; current u-pl rejects the old position-only shifting path.

Mechanical RV certificates constrain only the added operator, not the entire coupled energy balance or wall reaction. Fixed-plane NoPen remains ReactionClosed=false; native p-P0 uses fixed initial P0 and is not paper plastic excess. The first receiver save follows a real update. No new half chain, solver, PRE, native decode, VTK or production source/formal-input change was made by this decision. No SHA scan was used.

Evidence: `logs/c08_h18_rv_window_GPU_r2.run.json`, unique `native_r1.check.json`, `c08_h18_rv_window_review_r1.check.json`, independent visual check and decision JSON. The original successful analysis check is immutable, including its original visual_QA_pending field; subsequent visual completion is recorded separately.
