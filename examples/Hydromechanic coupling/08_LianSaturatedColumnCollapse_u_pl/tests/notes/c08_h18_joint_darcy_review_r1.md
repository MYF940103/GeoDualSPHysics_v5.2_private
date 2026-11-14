# C08 joint-Darcy paired scientific review r1

Author-only `support/c08_h18_joint_darcy_review_r1.py`; root must fully read and separately admit one offline execution. No component, solver, reader, native decode, source/header change, build, Git, SHA scan, PRE or time integration is invoked. The already passed source component and all six raw CSVs remain unchanged.

## Actual source contract

Require `logs/c08_h18_joint_darcy_probe_r1.check.json` passed with bound completion, actualPopen/Win32 exits0 and build. Require its **check.files** seals for all six CSVs plus completion, before reading and again at the end; there is no fresh-stat fallback or invented exit-time seal. Reuse only this completed component's evidence rather than reopening old native frames/object inventories.

Exact source coverage:manufactured88×60000,summary16×12,walls38×5700 (count taken from completion),baseline11×2,route8×14 and full signed clock12×2. All5000 material IDs are present in every2parts×3fields×2oracles group. Actual-proof and analytic-generated roles each cover30000 rows. Require original2bare forces/8productionDarcy API calls,6actual-field reconciliations,6analytic oracle groups,580000external baseline bits and original budget ratios. No analytic row is reclassified as an actual API result.

Read source tables once. Group-order/ID/time/tau joins use actual saved clocks and signed dterror<=1e−14; no interpolation, retiming or normalized-time substitution. Same-ID real/analytic pairs must have identical J/C/FS, cohort flags, geometry and unchanged soil p/Ace data. Same-wall identity/J/C/normal fields are also matched. Only ghost p/Ace is allowed to account for the conditional difference. All real/analytic vectors remain distinguishable.

The seven per-row source contributions are independently re-summed in original order and checked against exported sum/remainder. Source literal-to-float conversion and original logged arithmetic budgets are checked without a new physical tolerance. Whole/legal-bed/interior source RMS summaries are reproduced in original row order. Undefined plane-C conditioning remains blank with defined=false and is counted; no singular value/condition is clipped to make it usable.

## Scientific quantities / limitations

Three soil cohorts are all5000, the producer's predeclared **legal_flat_bed**, and **interior_no_wall**. Empty cohorts retain count0 and N/A metrics. No outliers, negative pressures, FS or side/corner points are removed from the full retained source table. Ordinary per-material RMS is used; this is not a fluid-mass/flux conservation estimate.

For every cohort retain rate signedmean/RMS/absmax, all7channel signedmeans/RMS, pressure(LP+Taylor), acceleration(Da+FSreceiverAce) and k-chain RMS, numerical/storage error scales, actual drive/J-gradient and conditioning descriptors. NetRMS/(pressureRMS+accelerationRMS+chainRMS) is only an amplitude/cancellation descriptor, not a mass fraction or stability gate.

On the **real** summary row additionally retain same-ID real−analytic rate mean/RMS/absmax, full-vector Pearson correlation and same/opposite-nonzero-sign fractions, with both-zero/one-zero counts. Each of the7channels has its own matched mean/RMS difference. Zero-variance correlation and empty denominators stay N/A; correlations are not clamped. Similar scalar RMS alone therefore cannot be interpreted as evidence that the ghost closure is irrelevant; different signed spatial errors can cancel.

For N only, define the dimensionless reference rate

`Rref=(Kw/n)*(k/gamma_ref)*B`, Kw=1GPa, B=1000Pa/m², gamma_ref=1000*9.80665, using actual constant n/k from each manufactured cohort. This is the characteristic magnitude of a single normal-curvature contribution, **not a nonzero expected joint-Darcy truth: the continuous joint rate is0**. It is about5.83e4Pa/s; a measuredRMS near791–805Pa/s is about1.36–1.38% of that reference. The value is a spatial residual normalization, not a pressure error after integration or a physical acceptance threshold. Water reference density1000, not mixture density, enters gamma.

Independent source math identifies a compatible Eta signature only: on ideal isotropic Ci=Cj=cI with complete common quadrature, writing alpha_zj=−Vj*c*Fac*dz², an N joint residual contains −B*sum(alpha_zj*Eta²/(r²+Eta²)) plus gradient-defect terms. Current Eta=(.1h)², h=.072; anisotropy, pair-C variation, disordered support and float storage can contribute too. This review does **not** attribute the observed1.36% to Eta or select a new operator; any separate exact shadow remains a separate task.

All-domain X rows involve side/free-surface boundary conditions not generally compatible with this manufactured IBVP. Smaller all-domain analytic-oracle RMS is therefore not evidence of a physically improved wall model. Legal flat-bed and interior results are reported separately, including their actual matched error vectors. The operator/Q/k flags are unchanged. Continuous gradp+rho_w Ace is declared zero, while the observed discrete rates quantify truncation, ghost reconstruction and float storage on two fixed clouds—not coupled dynamics, a mechanical equilibrium, a new TPI trajectory or clump repair.

## Compact output

One `figures/c08_h18_joint_darcy_review_r1_summary.csv` has36soil-region plus24wall-region rows with explicitfamily/region/units. N/A fields remain blank. Paired-difference/correlation metrics occur on the real row only; analytic rows are not duplicate experiments. Wall rows describe allactive or geometricflatbed(x[.5,3.5],+Znormal,NoSlip) sets, which are **not** silently equated to the receiver legal-bed cohort.

Three static PNGs use that same compact table:

1. residuals:2parts×H/N/X, paired actual/oracle RMS for all/legalbed/interior, common Pa/s scale, symlog linear range1Pa/s preserving zero;
2. cancellation:legal-bed signedmean LP/Taylor/Da/FS-Ace/k-chain/net, common signedPa/s scale. Means can cancel spatially; RMS and matched-vector deltas remain in CSV;
3. wall_errors:paired p/Ace RMS errors for allactive/geometricbed, common yscale within each unit row. Analytic curves retain float storage error; zeros are not deleted. The plot is about extension error, not a closed physical wall force/work law.

The new check lists exact counts, definitions, consumed seals and products; physical_acceptance remains false, and visualQA remains pending root inspection. All outputs use exclusive new paths and retain partials on failure. No follow-on is launched.

After independent root review only:

`D:/anaconda3/python.exe -B tests/support/c08_h18_joint_darcy_review_r1.py --execution-authorized`

Author read the genuine passed receipt/summary and small headers, then wrote only this script/note. No analysis script/import/build/component/solver/reader/Git was executed.
