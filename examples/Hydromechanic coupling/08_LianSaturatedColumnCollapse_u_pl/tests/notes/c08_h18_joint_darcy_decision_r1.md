# C08 joint pressure–acceleration consistency: completed diagnostic

The unique CPU zero-advance component completed with real Popen/Win32 exits 0, owner24824/child34472, UTC2026-11-14 22:20:32.655094–22:21:43.837838 (71.183 s). Its original baseline replay passed580000 external scalar-bit checks and the manufactured actual-rate branch passed30000 float-bit checks. All60000 manufactured rows,5700 active-wall records,12 summaries and original two saved clocks were independently reviewed. There was no physical integration, new solver, PRE, native decode, material update or filter. Source, public programs and formal inputs were unchanged; SHA scans0.

The fields H/N/X satisfy continuous `grad(p)+rho_w*Ace=0`. N has a1000Pa/m² normal curvature; X has a1000Pa/m³ cross coefficient. These are instantaneous spatial tests, not full mechanical/free-surface initial-boundary-value solutions. The real-wall branch genuinely refreshes current J-dependent wall state, C/FS and wall acceleration; the analytic branch changes only ghost p/Ace while sharing J/C/FS/quadrature. It never writes an oracle into the actual rate.

At original P30, tau=.3000049999886425s:

| Field/cohort | Real residual RMS [Pa/s] | Analytic-ghost RMS [Pa/s] | Same-ID real−analytic RMS [Pa/s] |
|---|---:|---:|---:|
| H, legal bed (225) |1.02605|1.02679|.103234|
| N, legal bed (225) |800.555|805.331|7.72936|
| N, no-wall interior (3994) |791.523|791.523|0|
| X, legal bed (225) |1388.67|1395.53|12.9782|
| X, no-wall interior (3994) |1732.61|1732.61|0|

The analytic extension does not improve the aggregate legal-bed N/X residuals; their paired differences are also small relative to the residuals. This is evidence against ghost p/Ace fitting being the dominant error in these specific fields/cohorts, not a proof that all wall coupling is correct. N paired Pearson is.68855, so equal scalar RMS must not be interpreted as identical spatial errors. Whole-domain X changes48575.2→6582.68Pa/s, but side/FS conditions of that global polynomial are not a compatible IBVP; this is not a physical wall-repair success.

N's characteristic single-curvature rate scale is `(Kw/n)*(k/gamma)*1000`, about58269.5Pa/s. The measured bed/interior residuals are1.374%/1.358% of that scale. **The continuous joint truth remains0.** The phrase “dimensionless reference rate” in the frozen author note is a wording error: the scale has units Pa/s; only RMS divided by it is dimensionless. No computed quantity or frozen file is changed by this clarification.

The polynomial audit predicts an Eta-dependent deficit for ideal complete isotropic support. General residuals also contain receiver/pair-C differences, first-gradient defects, non-symmetric higher moments and float storage. A1.36% signature alone does not establish Eta's actual contribution or justify a physical Eta0 trajectory. In particular, simply regularizing Da to force one quadratic cancellation would degrade the original affine acceleration divergence.

For two-dimensional isotropic pressure diffusion, the trace of the full Lian2023 Eq23 tensor is algebraically the existing receiver-C/bare scalar Taylor-defect form:

`trace(H23)=LP_Ci,bare−Gp·Lx_Ci,bare`.

It is not an additional P2/P3-reproducing matrix correction. A separate full-tensor component would repeat that scalar comparison. The next admitted work is pure offline attribution of the four existing Ci/Cavg × Eta/bare pressure weights on these same retained data, changing LP and Lx together while holding actual Gp/Da/chain/FS fixed. No force/API/solver repetition or new half chain is needed.

The original residuals and wall-error PNGs are readable. The original cancellation figure has crowded short tick labels; the separate display-only `c08_h18_joint_darcy_display_r2_cancellation.png` is the preferred cancellation view. It uses the unchanged60-row summary CSV; all original figures are retained. All outputs are test diagnostics, not formal three-psi publication or physical acceptance. The rejected radial RV and old full trajectories remain protected; clumping and late early arrest remain unresolved.
