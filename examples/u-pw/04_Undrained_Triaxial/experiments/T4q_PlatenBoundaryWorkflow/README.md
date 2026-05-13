# T4q Platen Boundary Workflow

T4q tests an XML-only explicit platen boundary route for the reduced
undrained-triaxial workflow.

Cases:

- `CaseT4q_PlatenGeometry_NoLoad_Def.xml`: fixed bottom/top platen geometry,
  no loading.
- `CaseT4q_TopVelocity_NoConfinement_Def.xml`: fixed bottom platen and moving
  top platen, no lateral confinement.
- `CaseT4q_TopVelocity_LateralConfinement_Def.xml`: moving top platen plus
  lateral `FlexibleConfiningStress`.

Key grouping:

- specimen: `mkfluid=0`;
- top platen: moving `mkbound=1`;
- bottom platen: fixed `mkbound=2`;
- `CapConfiningStress=0`.

Run the BAT files with the CPU Release executable, then run:

```powershell
py -3 analyze_t4q_platen_workflow.py
```

The generated metrics and figures are committed. Heavy solver outputs are not
kept in git.
