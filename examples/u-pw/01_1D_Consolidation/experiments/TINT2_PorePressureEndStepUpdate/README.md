# TINT2 Pore-Pressure End-Step Update

CPU-only verification of the opt-in `PorePressureTimeIntegrationMode=1`
end-step pressure commit.

The cases are generated from the BND1 1D consolidation templates:

- L3c feedback-off, operator 1, mode 0/1.
- L5 feedback-on, operator 1, mode 0/1.
- BND1 generalized operator 2 feedback-off, mode 0/1.
- BND1 generalized operator 2 feedback-on, mode 0/1.
- Verlet L3c operator 1 smoke, mode 0/1.

No GPU simulation is part of TINT2. GPU XML loading must hard-error for
`PorePressureTimeIntegrationMode!=0`.

Summary after the CPU matrix:

- all cases finished with solver `code=0`;
- L3c/L5 operator `1` mode `1` is stable but numerically unchanged from mode
  `0`;
- BND1 operator `2` feedback-off is unchanged;
- BND1 operator `2` feedback-on remains unstable in both modes
  (`excluded=973`, `DtMin=10252`);
- mode `1` should stay active-experimental only until the TINT2-clean
  decision.
