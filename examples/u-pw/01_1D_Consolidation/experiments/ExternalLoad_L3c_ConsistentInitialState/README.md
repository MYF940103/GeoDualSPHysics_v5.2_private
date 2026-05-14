# ExternalLoad L3c Consistent Initial State

L3c formalizes the Terzaghi initial-state route after L3b showed that direct
mechanical forcing of top material particles still produces a dynamic pressure
peak.

## Route

- `PorePressureInit=3`
- `PorePressureExcessAmp=10000 Pa`
- `PorePressureAnalyticalProfile=3` uniform initial excess pressure
- `InitialStressMode=0`
- `MechanicalTopLoad=0`
- no native `AccInput`
- `PorePressureFeedback=0`
- top drained from initialization
- bottom no-flux correction enabled

The effective stress increment is deliberately zero. This matches the
instantaneous-undrained Terzaghi analytical initial condition, where the
surcharge initially appears as excess pore pressure.

## Runs

- CPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- GPU Release: `code=0`, `excluded=0`, `DtMin=0`.

Postprocessing:

```powershell
py -3 analyze_l3c_consistent_initial_state.py
```

Generated CSV files and figures are retained. Heavy solver outputs are cleaned
before commit.
