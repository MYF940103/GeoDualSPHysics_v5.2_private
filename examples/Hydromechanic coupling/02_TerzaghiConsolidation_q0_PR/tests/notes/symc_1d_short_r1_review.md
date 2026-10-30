# symC: 1D default compatibility and optional-ON startup review

Reviewed 2026-10-30. Implementation checkpoint `7c0006e`; pre-test HEAD `be006f1`. No production source, formal input or accepted result changed.

## Decision

The CPU/GPU switch is already in source and defaults to OFF. Keep accepted case02 inputs OFF. This stage passes default-OFF implementation compatibility and bounded ON startup/backend safety, not ON physical accuracy, half-step or full2Tv acceptance. Do not enable symC globally from these results. Case01 should first establish a current OFF baseline; its k=0 initialization needs no duplicate symC group.

## Experiment and coverage

- Six fresh actual Release jobs: CPU1/GPU, each archived pre-switch / current default-OFF / current ON. Original k=1e-4, dp=.01, width=.1, 1000 soil IDs40..1039, band/SPR/gradient/HGxi=.1/eta=.04/fixed drainage/dt1e-5 unchanged. Only TimeMax=.15,TimeOut=.001; ON alone adds the switch.
- Each completed15000steps and151native saves, final actual t=.15000000000000924s, only legacyTv=.0038422.
- Both old/OFF pairs passed all151 states x35 columns bitwise, including native time/step/IDs/flags/dterror/signed zero, with no field exclusion or interpolation.
- Independent audit re-decoded Parts0,10,11,100,150 on each backend: ten old/OFF pairs,350000 compared column values all exact. Additional selected ON native states and all151 history/backend comparisons were checked. Independent native coverage is sampled, not a second full-series decode.
- Independent audit verified69 prepared bindings plus final run/six receipts:76bindings,336328349bytes,zero SHA/size mismatches. All six immutable completions show normal exits and no owned survivors.
- Original geometry, active drainage, native1000N/m load within.001, post-.1s100Pa stress/top-gap, finite/elastic/no-exclusion/natural/pore-step and HG call/cache/dt/spin guards passed. No guard was relaxed.

## ON changes the solution, not merely the implementation

CPU final results (GPU gives the same conclusion):

| Quantity at actual t=.15s | OFF | ON |
| --- | ---: | ---: |
| Mean pore pressure, Pa | 9277.789689 | 9233.626574 |
| Top material settlement, mm | .262475493 | .278089260 |
| Max layer total-stress residual, Pa | 66.744962 | 48.809420 |
| Top adjacent-layer gap, Pa | 69.138393 | 31.586918 |
| Layer second-difference RMS Q, Pa | 10.560051 | 4.638766 |

Across startup, max ON/OFF pressure RMS difference149.162625Pa(CPU)/149.162880Pa(GPU); final top settlement increases.015613767mm(CPU). These are intentional option differences, not half-step/backend errors. Lower stress variation alone is not pressure/settlement accuracy acceptance. A classical post-ramp curve is not an exact dynamic-startup reference.

All151 CPU/GPU ON pairs pass original5Pa/.005mm delivery bounds: max pressure RMS.008855933Pa, top material settlement difference4.253066e-8mm. This is not time-step convergence.

Part10 actually saves at.01000999999999976s, not exactly the.01 event. Compare native times/steps. Signed dterror is a mechanical-step margin, not clock accumulation error. Timings are not an isolated benchmark: comparison jobs read additional native reference states.

## Reproduce and limits

`../logs/symc_1d_short_r1.inputs.json` binds programs, runtime, archived compiler sources, helpers and all XML/BAT. See `../logs/symc_1d_short_r1.check.json`, `.run.json`, six immutable job `.completion.json`/`.receipt.json`, matching `../figures/*_history.csv` and `../figures/symc_1d_short_r1_comparisons.csv`. Raw output remains under `../outputs/<job>`.

No formal figure/data was overwritten. No ON independent half,15s/full2Tv/general-boundary/plasticity/restart acceptance or automatic long-run admission follows. Cryer server work is untouched. Preserve prior accepted case02 results; source integration does not require a default change.
