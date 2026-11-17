# P3 B10us: root bounded-window decision

2026-11-17. The one genuine GPU Release solve completed199996 updates,1263 frames and actual scalar end2.00000577545594s. Original owner/handles/program/source/input/plan records passed; the native reader ran once. All1040 IDs/22 arrays,1262 signed nonempty intervals,1,263,000 ledger rows and11590 post-open true drained receivers passed. Three independent pressure rounds/five force phases passed3,789,000 saved pressure observations, actual q2=p1/q3=p2, finalp3 and original single J/history/HG update guards with no added tolerance.

The root inspected all six new PNGs and corresponding recorded CSV products. A display-sized preview was created under tests/outputs only; original PNGs/CSVs were not rewritten. An independent peer verified the small tables/targets/history/metrics.

| Legacy target | A pressure RMS(Pa) | P3 pressure RMS(Pa) | A top abs error(mm) | P2 top abs error(mm) | P3 top abs error(mm) | P3 minus A top(mm) | Original increment budget(mm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| .005 |114.6148671921|114.6411415197|.0199802355166|.0238117138678|.0225433264014|.00256309088483|.00371428571429|
| .05 |53.4390065578|52.5007636513|.0170165210099|.0197147342993|.0188180566340|.00180153562402|.00371428571429|

Both original pressure/top/bottom target budgets pass. Actual P3 saved target times are.1929944171906 and1.8316719226874576s, with requested-target gaps+.0008084740230497878 and-.0001854490515211804s. A is evaluated at its own actual saved times and finite-Kw reference; P3 uses the unchanged unfitted M0 companion. No interpolation/time/load/material fit or new tolerance was used. The references remain qualified quasi-static companions, not exact finite-ramp/band/inertial/current-J solutions.

All saved t>=.1-1e-7s original100Pa layer-total-stress/top-gap guards pass: maxima80.12241833447479Pa and8.344286992065463Pa. Alternating-X Uz full-window maximum is1.5518523653612615e-7mm, with no macroscopic growing mode seen within this2s window. This does not settle later-cycle modes. Original A105.3900807625Pa failure and P2 first-target top failure remain unchanged.

Top errors improve over P2, but pressure target RMS is slightly higher by.1505152335/.3128432965Pa. Startup oscillations are retained: P3-minus-P2 all-ID pressure RMS maximum3583.356715633631Pa is descriptive and is not a5Pa half error. Passing selected targets does not mean every field or startup transient improved. Final P3 pressure-profile RMS is50.833298151811235Pa and top signed error.01863920841539357mm.

Actual loop cost3810.424561s exceeds P2's3236.284912s and B10's2408.810059s; these are uncontrolled single-run observations, not a kernel speedup comparison. The larger step has not established the intended total-cost advantage. Preserve this completed P3/program as a qualified bounded reference; next development should target demonstrated redundant prototype cost without changing pressure/BC/Rgamma or removing necessary guards. No new half/reference/full solve is admitted by this record.

This is bounded-window acceptance only: not full2Tv, public TPI/XML release, second-order/literal-paper TPI, converged implicit pressure, restart or general-case acceptance. All formal cases, raw outputs and paused C08 dependencies remain protected.
