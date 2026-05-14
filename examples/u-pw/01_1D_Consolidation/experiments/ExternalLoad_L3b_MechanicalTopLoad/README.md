# ExternalLoad L3b Mechanical Top-Load

This experiment tests the first CPU-only mechanical top-load prototype for the
paper-aligned 1D consolidation case.

Files:

- `Case1DConsolidation_PR_MechanicalTopLoad_L3b_Def.xml`
- `xCase1DConsolidation_PR_MechanicalTopLoad_L3b_win64_CPU_release.bat`
- `analyze_l3b_mechanical_top_load.py`

Route:

- no `AccInput`;
- `MechanicalTopLoad=1`;
- `MechanicalTopLoadQ0=-10000 Pa`;
- `MechanicalTopLoadArea=0.1 m2`;
- ramp `0 -> 0.005 s`;
- top drainage starts after the ramp;
- `PorePressureFeedback=0`;
- CPU Release only for this prototype.

Outcome:

- CPU run: `code=0`, `excluded=0`, `DtMin=0`;
- applied force scale: `|Fz|=1000 N`;
- peak excess pressure remains about `5.9e5 Pa`;
- this is not a strict Terzaghi validation route.

Interpretation:

The prototype is useful as a loading-route audit. It shows that directly
forcing the top material surface still produces a dynamic response. L3a remains
the better analytical PR diffusion gate; a strict mechanical route needs a
consistent initial stress/pore-pressure state or a true force-controlled
loading plate.
