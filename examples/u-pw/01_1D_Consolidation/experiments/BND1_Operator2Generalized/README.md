# BND1 Operator 2 Generalized Boundary Verification

CPU-first verification of `PorePressureBoundaryOperator=2` after generalizing it from a top/bottom prototype to a solid-wall hydraulic boundary-particle route.

Cases:

- `Case1DConsolidation_PR_BND1_L3c_Mode1`: feedback-off, operator 1 reference.
- `Case1DConsolidation_PR_BND1_L3c_Mode2`: feedback-off, generalized operator 2.
- `Case1DConsolidation_PR_BND1_L5_Mode1`: feedback-on, operator 1 reference.
- `Case1DConsolidation_PR_BND1_L5_Mode2`: feedback-on, generalized operator 2.

All cases keep the L3c/L5 initial-pressure route: no AccInput, no MechanicalTopLoad, no long run, no GPU simulation.
