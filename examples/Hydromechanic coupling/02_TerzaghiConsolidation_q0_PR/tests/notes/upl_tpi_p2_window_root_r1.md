# P2 B10us two-second outcome

The actual RTX3050 solve completed 199996 updates and 1263 frames at scalar time 2.00000577545594 s. Original owner/tool/solver handle exits are all zero. Unique native decoding and full two-round/four-phase implementation review passed: 1040 IDs, 22 typed arrays, 1263000 soil ledgers, 11590 true drained receiver checks, 2526000 pressure rows, actual q2=p1, one J/history advance and every original signed interval. No solver or native read was repeated.

Root inspected all six fresh PNGs and matching CSV/metrics products. Theory is unchanged and unfitted; A keeps its finite-Kw companion and own actual times, while B10/P1-staged/P2 use M0. Different-method differences are not a half-step or 5Pa equivalence test.

|Requested legacy Tv|A pressure RMS Pa|P2 pressure RMS Pa|A top abs error mm|Original B10 top error mm|P2 top error mm|P2 original target budgets|
|---|---:|---:|---:|---:|---:|---|
|.005|114.614867192|114.490626286|.019980235517|.027607493173|.023811713868|FAIL top only|
|.05|53.439006558|52.187920355|.017016521010|.022399051511|.019714734299|PASS|

At the first actual selected time .1929944171906 s, top-error increment versus A is .0038314783512216066 mm, above the unchanged .003714285714285715 mm budget by .00011719263693589152 mm (0.11719 micrometre). The failure is retained despite its small magnitude. At the second selected time 1.8316719226874576 s the increment .002698213289381024 mm passes. Top errors improve about13.75%/11.98% from original B10. Pressure and bottom budgets pass both targets.

All post-.1s100Pa guards pass: max layer error79.60076682914223 Pa, top-pair gap7.054460383758851 Pa. Alternating-X Uz peaks9.030554394551249e-8 mm in the observed window; the1.5-2s panel does not show a macroscopic growing mode. This does not settle behavior after2s. Startup oscillations, original A failures and all raw records remain visible.

Single-run TSimul: original B10 2408.810059 s; staged P1 2677.168213 s; P2 3236.284912 s. P2 costs34.35% more than original B10 under these instrumented, uncontrolled runs; this is not pure kernel timing or a full-run speedup certificate. Saved R/S correction RMS drops15.1880561850 to9.7520231456 Pa between rounds, which is an iteration diagnostic, not theory accuracy.

The reused reader's generic final_frame_forced_by_step_stop=true label is retained as historical tool output. Actual solver termination crossed TimeMax=2 at199996 before nsteps uppercap200000; no clock, step or native state was rewritten to match that label.

P2 has not passed every original physical comparison budget. No full2Tv, further timestep, half/reference chain or other case is admitted here. Continue only the already authorized offline error-source and numerical/cost review before selecting another bounded candidate. Public source/formal results stay unchanged and C08 remains paused.
