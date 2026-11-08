# CPU one-step pressure-map result

Offline review only: sealed run/check and three CSVs, no new force/solver/native decode/raw-state read. Actual component call closed Popen/Win32 0 with clean ownership. All10 independent one-step maps/20 original force calls and40000 ID rows are retained. Source is Shepard part71, t=10.720000000602795, completed4288000; only interior ID5205 (p=-271776.375 Pa) is perturbed.

| h [us] | norm gain (+/-100,+/-50 Pa) | Qp share | Qv share | 100-vs-50 relative difference | max abs delta J |
|---:|---:|---:|---:|---:|---:|
| 2.50 | 0.808872-0.809504 | 99.86099-99.86372% | 0.13627-0.13901% | 0.11956% | 3.482e-11 |
| 1.25 | 0.894436-0.895077 | 99.96969-99.97026% | 0.02974-0.03031% | 0.10842% | 8.699e-12 |

Each h has its own baseline (clones1/6), zero self-difference and blank undefined gain. Float input deltas are exactly +100/-100/+50/-50 Pa. All5000 IDs per perturbation, same-h baseline p/FS/theta/T, pressure and T differences, map J/kappa/position maxima, Q sums/ratios and central-norm parallelogram identity agree. Qsigma is at most 3.12e-08 of output Q. All three Q terms consistently omit1/2; initial V/rho/n weights and full3D effective-stress compliance are frozen. CSV checks use only1e-12 relative double-arithmetic tolerance, not a physical acceptance threshold.

Perturbation delta kappa is bit-zero; FS matches the same-h baseline and endpoint plane-membership changes are zero. P0 checks pass. Maximum position differences are 7.382e-13/1.907e-13 m. These are perturbation differences, not evidence of no plastic evolution, no FS change from the saved input, or no contact projection.

T = tr(sigma_eff,end)-tr(sigma_eff,input)-3*K*h*theta_mid is observational. Baseline max abs T is 210.962/106.556 Pa for2.5/1.25us; max perturbation-induced abs delta T is 0.000847418/0.000209543 Pa. Nonzero T can reflect volumetric return plus gradient/integration effects; return statuses were not recorded. It cannot identify a tension/apex hit or pulse cause.

All eight perturbations contract in this declared norm. The shorter step contracts less over its shorter interval; this does not support a halve-dt fix. This is one local direction at one saved state, not the largest singular gain, a full-state energy theorem, full spectrum, long-time proof or GPU restart. No additional step-size chain is recommended; physical acceptance remains false.
