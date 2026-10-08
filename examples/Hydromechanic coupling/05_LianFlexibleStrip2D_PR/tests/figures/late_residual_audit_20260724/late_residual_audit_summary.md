# Late residual audit summary, 2026-07-24

Generated from existing saved comparison CSVs only; no solver output was overwritten.

| case | window | metric | SPH start | SPH end | reference start | reference end | slope ratio | end/ref | end error | note |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SelfWeight Scenario2 | Tv=1->1.5 | bottom_excess_kPa | 0.821320 | 0.524191 | 0.738771 | 0.215140 | 0.567 | 2.437 | 0.309052 | root_zero_order_Tv2 |
| SelfWeight Scenario2 | Tv=1.5->2 | bottom_excess_kPa | 0.524191 | 0.511759 | 0.215140 | 0.062651 | 0.082 | 8.168 | 0.449108 | root_zero_order_Tv2 |
| q0 Terzaghi 1e-3 | Tv~1->1.5 | mean_excess_kPa | 0.722815 | 0.330418 | 0.683588 | 0.199070 | 0.810 | 1.660 | 0.131348 | actual Tv 1.002->1.502, U 0.928->0.967 |
| q0 Terzaghi 1e-3 | Tv~1.5->2 | mean_excess_kPa | 0.330418 | 0.323824 | 0.199070 | 0.058691 | 0.047 | 5.517 | 0.265133 | actual Tv 1.502->1.997, U 0.967->0.968 |
| q0 Terzaghi 1e-4 | Tv~1->1.5 | mean_excess_kPa | 0.700338 | 0.546161 | 0.687869 | 0.200316 | 0.316 | 2.726 | 0.345845 | actual Tv 1.000->1.500, U 0.930->0.945 |
| q0 Terzaghi 1e-4 | Tv~1.5->2 | mean_excess_kPa | 0.546161 | 0.536976 | 0.200316 | 0.058335 | 0.065 | 9.205 | 0.478641 | actual Tv 1.500->2.000, U 0.945->0.946 |
| Lian FlexibleStrip2D | t=3->49.95s | max_excess_kPa | 2.117932 | 0.269150 | 1.750000 | 0.060000 | 1.094 | 4.486 | 0.209150 | mean 0.626->0.108 kPa; p95 1.940->0.244 kPa |

Interpretation: slope_ratio is computed from signed changes; values well below 1 mean the numerical residual dissipates more slowly than the reference over that late window. end/ref highlights residual level at the final point.
