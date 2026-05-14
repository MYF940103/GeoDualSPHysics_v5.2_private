# ExternalLoad L4 GPU Long-Run

L4 extends the L3c consistent initial-state Terzaghi gate as a GPU long-run
Level-1 validation.

## Scope

- `PorePressureInit=3`
- `PorePressureExcessAmp=10000 Pa`
- `InitialStressMode=0`
- `PorePressureFeedback=0`
- no `AccInput`
- no `MechanicalTopLoad`
- GPU Release is the main route

This validates PR diffusion and hydraulic boundaries, not mechanical top-load
generation.

## Time Window

The XML uses:

- `TimeMax=0.08 s`
- `TimeOut=0.004 s`

With the current Terzaghi parameters this reaches approximately
`Tv=2.23e-2`, extending L3c by four times while retaining a compact set of
saved frames.

## Commands

Run GPU:

```powershell
py -3 run_l4_gpu_long.py
```

Run analysis:

```powershell
py -3 analyze_l4_1d_consolidation_long.py
```

The CPU BAT is provided for parity, but the matching CPU long run is optional
because L3c CPU already took several minutes for one quarter of this duration.
