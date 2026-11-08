# C08 hdp sensitivity: preserved failure and matched-runtime short control

## Actual runs and scope

- hdp1.5 `upl_c08_hdp15_preload_GPU_r1`: real owner74956/direct solver47120; actual Popen/Win32 exit1 after1661.063s. Intended10s/4M source was not completed. Continuous nativeParts0000..0051; last saved actual time0.51000000000122425s, completed204000. First engine cause is `GPU material corrector return rejected the stage (status bits 4).` No source VTK or receiver ran.
- hdp1.2 `upl_c08_hdp12_preload_control_GPU_r1`: one fresh matched-runtime short control, owner75668/directsolver76220; actual Popen/Win32 exit0 after1387.704s, completed208000/53Parts through actual0.5200000000012898s. This is not a new10s qualified source.
- Both use frozen runtime_r6/law2 on local RTX3050, same material/dp.04/dt2.5us/damping.02/Shepard40/Model1-Ck2, fresh zero effective stress/hydrostaticP0. AS, NoPen and keepbed are OFF during the source phase. h1.5 versus old server law1 PRE was not an isolated h-only comparison; the new h1.2 short control removes that program/hardware confounding. It does not replace the original certified r2 GPU10s PRE.

## Independent saved-state inspection

Corrected narrow reader outputs are `outputs/upl_c08_hdp15_preload_partial_r3` and `outputs/upl_c08_hdp12_preload_partial_r3`; corresponding `.check.json` files are in logs. Both inspect all7060IDs=2060fixed+5000soil and all22typed arrays at every actual saved time, scalar+=dt clocks, original signed necessary-step guard, fixedP0/zero-kappa and J/n/V/rho/k ledger/cache/fixed-marker checks. Clock and ledger reference error were zero in both. h1.5 has260000soil ledger checks/367120 P0+kappa checks/51 signed intervals; h1.2 has265000/374180/52. No savedFS23 observation had positive pressure. h1.5 has5200 observations:100 negative and5100 zero; h1.2 has5300:2 negative and5298 zero. All negative observations occur at savedpart2 (~.02s), with soil minima-88.5858 and-16.9799Pa respectively. Positive-count zero must not be mistaken for all pressures zero. Sign is observational for this PRE diagnostic because save-time reclassification is not the exact earlier projection mask; no new savedFS sign gate or old release guard relaxation was made.

The reader's first utility link retained an unused AppInfo global and failed1120; r2 removed only that unused declaration/include and built. Its first read stopped at part1 because the offline reference mistakenly used base10 instead of the frozen program's natural exponential conductivity. Preserve those failed tool artifacts. r3 uses the exact CPU/GPU/loader `k=k0*exp((J-1)/((1-n0)*Ck))`, retains every original tolerance, and passed one independent read per profile. These were diagnostic-tool defects, not additional physical failures or changes to solver data.

## Matching actual time0.51000000000122425s

| Saved metric | hdp1.2 | hdp1.5 |
|---|---:|---:|
| Maximum saved DP yield f (Pa) | -4251.0243, ID6960 | -277.3663, ID7010 |
| Whole-soil velocity RMS (m/s) | 0.0001710279 | 0.0004287140 |
| Maximum speed (m/s) | 0.0002269273 | 0.0123060349 |
| Maximum pore pressure (Pa) | 33825.7148 | 33325.6992 |
| Same ID7010 effective yield f (Pa) | -4268.5575 | -277.3663 |
| Same ID7010 vertical velocity (m/s) | -0.00000453785 | +0.0039156475 |

Thus h1.5 saved maximum speed is about54.23times h1.2. Its approaching-yield growth is localized to the lower right wall corner, not a global pressure error or savedFS positive-pressure event. The last saved state still has negative f and kappa0: it does not identify the unsaved rejected trial's ID, yield value or exact failure time.

Frozen `FunSoilMaterial.h` defines Smooth=2; GPU sets `1u<<status` and rejects non-Elastic results when strict elastic_source is requested. Therefore bits4 means a successful smooth return rejected by the elastic-only source contract, NOT enumTensionRepair=4 (which would setbit16), nor proof of constitutive nonconvergence. No guard is bypassed.

## Coupled effects and remaining hypotheses

The same damping coefficient is not the same damping rate: cd=coefficient*sqrt(E/(rho_s*h^2)). The actual rate drops from about36.197685/s at h.048 to28.958149/s at h.060, a20percent reduction. Matching that rate would require coefficient.025 at h1.5, but this was not tested. h also changes neighbor support, eta2 and wall fits; no isolated damping attribution is made.

The original lower-left/lower-right wall role allocation is not mirrored: at h.048, the direct fixed support is8bedNoSlip+5sideFreeSlip versus6bed+7side; h.060 is10+6 versus8+8. Original right overlap nodes retain side normals during PRE; e.g.ID1800/1852 ghostpoints lie below the bed. DynamicPoreWall reflects each boundary point about its own face; it does not combine the second face constraint. This identifies a corner-consistency audit target, not an established cause. Existing KeepBed changes five node roles only after release and cannot explain/repair the fresh source failure by itself. Independent SPR0 does not omit the current dynamic wall's same-stage J-weighted mirrored derivative; standalone SPR1 remains incompatible with this Cubic/softening/AS configuration.

## Decision

Do not adopt this failed hdp1.5 source, launch its receiver, relax elastic eligibility, or start another10s preload/half chain. Preserve it and all previous sources/runs. Keep the accepted hdp1.2 source for the next bounded tensile-stability test. Under the user's existing instruction to test stronger artificial stress, prepare only epsilon.2/exponent4 with all other released physics unchanged, through0.90s. This covers known n3 pressure/J events around.80/.84s that a.66s window misses. Compare against retained n3 at actual times: near pairs/nearest-neighbor spacing, pressure transients, material histories, plastic/J state and early arrest. n4 increases relative short-range repulsion but reduces tails beyond dp; it is a hypothesis, not a demonstrated repair. Other psi remain locked until physical review; no formal/full acceptance or exact restart claim follows.

Offline comparison `upl_c08_hdp_preload_compare_r1` passed:52 exact common time/step records, h1.2 extra .52s retained. Root inspected both history and profiles_fields PNGs and matching four CSV tables. The plots show nearly matching bulk pressure but right-bottom localized velocity/yield growth for h1.5. Negative source FS pressures at .02s remain visible and unfiltered. No physical acceptance follows.
