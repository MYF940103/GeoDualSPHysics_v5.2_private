# T5d DP Feedback-Off Validation Package Report

## Objective

T5d does not add a new simulation. It consolidates the reduced DP feedback-off explicit-platen triaxial route into one validation package, using retained outputs from T4s, T4t, T5, T5b, and T5c.

## Scope

The package covers:

- explicit top/bottom platen workflow;
- selected lateral `FlexibleConfiningStress`;
- pairwise platen reaction diagnostic where available;
- specimen-only stress, p'-q, pore-pressure, and plasticity proxies;
- Drucker-Prager high-strength and mild-yield skeleton response;
- `PorePressureFeedback=0`;
- CPU-only reduced diagnostics.

It does not cover MCC, full pore-pressure feedback, GPU validation, true actuator reaction, or strict paper triaxial reproduction.

## Consolidated Cases

The package inventory includes:

| Case id | Source | Role |
| --- | --- | --- |
| `T4s_elastic_platen_lateral` | T4s | elastic feedback-off platen baseline |
| `T4t_elastic_reaction` | T4t | elastic pairwise reaction diagnostic |
| `T5_dp_high_strength` | T5 | DP high-strength baseline |
| `T5_dp_mild_yield` | T5 | DP mild-yield baseline |
| `T5b_dp_high_strength` | T5b | DP high-strength reaction refinement |
| `T5b_dp_mild_yield` | T5b | DP mild-yield reaction refinement |
| `T5c_dp_high_strength_extended` | T5c | DP high-strength extended response |
| `T5c_dp_mild_yield_extended` | T5c | DP mild-yield extended response |

All retained package cases have `code=0`, `excluded=0`, and `DtMin adjustments=0`.

## Key Metrics

| Case | Time [s] | Pairwise reaction [N] | Fz_proxy [N] | Ratio | p' [Pa] | q [Pa] | Kplastic max | Plastic count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T4s elastic lateral | 0.006032 | n/a | 1.03854 | n/a | 145.66 | 332.47 | 0 | 0/407 |
| T4t elastic reaction | 0.006032 | 0.956997 | 1.03854 | 0.921 | 145.66 | 332.47 | 0 | 0/407 |
| T5 high strength | 0.006032 | n/a | 1.03854 | n/a | 145.66 | 332.47 | 0 | 0/407 |
| T5 mild yield | 0.006032 | n/a | 0.48374 | n/a | 86.58 | 126.76 | 4.38e-4 | 341/407 |
| T5b high strength | 0.006032 | 0.956997 | 1.03854 | 0.921 | 145.66 | 332.47 | 0 | 0/407 |
| T5b mild yield | 0.006032 | 0.492775 | 0.48374 | 1.019 | 86.58 | 126.76 | 4.38e-4 | 341/407 |
| T5c high strength | 0.018097 | 3.27401 | 3.11480 | 1.051 | 385.80 | 1073.74 | 0 | 0/407 |
| T5c mild yield | 0.018097 | 0.43352 | 0.40311 | 1.075 | 62.23 | 120.51 | 1.462e-3 | 407/407 |

## What Is Validated

This package validates the reduced workflow pieces needed before any more ambitious constitutive work:

- explicit top moving platen and bottom fixed platen remain separated from the specimen and measurement regions;
- selected lateral `FlexibleConfiningStress` coexists with the platen workflow with active target count `112` and cap leakage `0`;
- pairwise platen reaction diagnostics are usable where enabled, with pairwise/Fz_proxy ratios from about `0.921` to `1.075`;
- high-strength DP matches the elastic reference over the short window with `Kplastic=0`;
- mild-yield DP activates plasticity and reduces `q`, reaction force, and pore-pressure response relative to high-strength DP;
- PR pore-pressure update remains bounded with `PorePressureFeedback=0`;
- T5c extends the mild-yield response without excluded particles, DtMin bursts, or velocity blow-up.

## What Is Not Validated

The package does not validate:

- full u-pw pore-pressure feedback in the momentum equation;
- MCC;
- true actuator reaction or prescribed-motion constraint force;
- strict experimental or paper triaxial reproduction;
- GPU execution;
- final undrained pore-pressure sign correctness.

The T5c mild-yield case finishes with negative mean pore pressure (`-3.525e4 Pa`). This is acceptable for a reduced feedback-off diagnostic but not for a strict undrained validation claim.

## Figure Recommendations

Main figures:

1. `main_reaction_axial_stress_vs_axial_strain`: reaction-based axial stress vs axial strain for elastic, high-strength DP, and mild DP.
2. `main_pq_path`: p'-q path for the same reduced family.
3. `main_kplastic_evolution`: Kplastic evolution, showing high-strength DP inactive and mild-yield DP active.
4. `main_pore_pressure_vs_axial_strain`: pore-pressure response vs axial strain.
5. `main_pairwise_reaction_vs_fz_proxy_ratio`: pairwise reaction vs Fz_proxy comparison.

Supplementary figures:

1. `supp_top_platen_displacement`;
2. `supp_lateral_active_targets`;
3. `supp_cap_leakage_final`;
4. `supp_force_balance_error_final`;
5. `supp_porepressrate_maxabs`;
6. `supp_divvel_maxabs`;
7. `supp_velocity_max`;
8. `supp_kplastic_fraction`.

Recommended tables:

- `t5d_case_inventory.csv`;
- `t5d_summary_metrics.csv`;
- `t5d_reaction_comparison.csv`;
- `t5d_plasticity_summary.csv`;
- `t5d_pore_pressure_summary.csv`.

## Next Step

T5d is sufficient to close the reduced DP feedback-off validation package. A T5e longer reduced route is optional, but not required unless the DP curves need more post-peak evidence.

MCC can now move into planning-only work. Immediate MCC implementation is still premature because full feedback, strict reaction interpretation, and MCC return mapping design have not been settled.

Full feedback and GPU remain deferred.
