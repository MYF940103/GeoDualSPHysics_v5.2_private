# Completed new basic granular collapse visualization

This is the .1 s startup, not the full1 s result. Run: `basic_material_short_new_CPU_r1`. All 11 actual saved frames and2500soil points per frame were exported by official PartVTK v5.0.206; `PartFluid_*.vtk` is the ParaView series. Original BI4/native exports remain unchanged.

Coordinates are the original saved float32 positions. `Vel`, `Rhop`, `Kplastic`, and legacy `Sigma_kk/ij` retain their declared display types. `SigmaState_kk/ij` is included from native double stress; inspect the field declarations below for actual VTK storage. Offdiagonal order is xy,yz,xz. `Press` is the dry WCSPH EOS pressure derived by PartVTK, NOT pore-water pressure. This dry case has no pore equation.

```text
SigmaState_kk 3 2500 double
SigmaState_ij 3 2500 double
Sigma_kk 3 2500 float
Sigma_ij 3 2500 float
Kplastic 1 2500 float
Vel 3 2500 float
Rhop 1 2500 float
Press 1 2500 float
```

No interpolation, smoothing, new solver, equilibrium claim or physical acceptance threshold is introduced.
