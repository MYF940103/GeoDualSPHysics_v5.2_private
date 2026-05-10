# CPU PorePress Restart Plan

This note defines the CPU-side restart work needed for staged u-pw PR cases, especially Supporting Information self-weight Scenario 1. It is a design document only; no source changes are made here.

## 1. Current Restart Chain

Current restart starts from `-partbegin` and flows through:

1. `JSphCfgRun.cpp`
   - Parses `-partbegin:<part>:<first>` and sets `PartBegin`, `PartBeginFirst`, and `PartBeginDir`.
2. `JSph::LoadCaseParticles()`
   - Calls `PartsLoaded->LoadParticles(DirCase, CaseName, PartBegin, PartBeginDir)`.
3. `JPartsLoad4::LoadParticles()`
   - Loads `Part_XXXX.bi4` when `PartBegin > 0`.
   - Reads the core arrays:
     - `Idp`
     - `Pos` or `Posd`
     - `Vel`
     - `Rhop`
   - Reads restart metadata:
     - `PartBeginTimeStep`
     - `SymplecticDtPre`
     - `DemDtForce` if present.
   - Detects and reads GeoDualSPHysics soil-state arrays only when all are present:
     - `Sigma_kk`
     - `Sigma_ij`
     - `Kplastic`
4. `JSphCpuSingle::ConfigDomain()`
   - Allocates CPU particle arrays.
   - Copies `Posc`, `Idpc`, and `Velrhopc` from `PartsLoaded`.
   - Restores `Sigmac` and `Kplasticc` using an `Idp` mapping when restart soil fields are present.
   - Preserves `Velrhopc.w` for restart, avoiding the old `RhopZero` reset.
   - Allocates and initializes hydromechanical arrays, including `PorePressc`.

The current restart is therefore stress/rhop/velocity/position consistent, but it is not yet pore-pressure consistent.

## 2. How PorePress Is Currently Saved

`JSphCpuSingle::SaveData()` reserves a double buffer when pore-pressure output is enabled:

```cpp
if(SavePorePressure && PorePressc)
  porepress = ArraysCpu->ReserveDouble();
```

It then gathers particle data with `GetParticlesData(...)` and adds the field:

```cpp
if(SavePorePressure && porepress)
  arrays.AddArray("PorePress", npsave, porepress);
```

`JDataArrays::AddArray()` records a `double*` field as `TypeDouble`.

`JSph::SavePartData()` writes all arrays except the core `Pos`, `Idp`, `Vel`, and `Rhop` arrays as extra BI4 arrays:

```cpp
DataBi4->AddPartData(arr.keyname, npok, arr.ptr, arr.type);
```

`JPartDataBi4::AddPartData(..., TypeDouble, ...)` maps this to `JBinaryDataDef::DatDouble`.

Therefore the current output field is:

| Field | BI4 name | Type | Written when |
|---|---|---|---|
| pore pressure | `PorePress` | `DatDouble` | `SavePorePressure=1` and `PorePressc != NULL` |

`ExcessPorePress` is also written as a derived diagnostic, but it should not be restored. It is recomputed from `PorePress` and the hydrostatic baseline for the active XML settings.

## 3. Why PorePress Is Not Restored Yet

`JPartsLoad4` currently has restart members only for:

```cpp
bool RestartSoilFields;
tfloat3 *SigmaKk;
tfloat3 *SigmaIj;
float *Kplastic;
```

It detects only:

```cpp
pd.ArrayExists("Sigma_kk")
pd.ArrayExists("Sigma_ij")
pd.ArrayExists("Kplastic")
```

There is no `RestartPorePress` flag, no `double *PorePress` buffer, and no `GetPorePress()` accessor.

In `JSphCpuSingle::ConfigDomain()`, after hydromechanical arrays are allocated, the code always initializes `PorePressc`:

```cpp
memset(PorePressc, 0, sizeof(double)*Np);
```

Then, if `HydromechCoupling && (PorePressureInit==1 || PorePressureInit==3)`, it overwrites `PorePressc` from the XML initialization logic.

Thus even when `Part_XXXX.bi4` contains a valid `PorePress` field, restart currently discards it.

## 4. Files That Need Changes

### `source/JPartsLoad4.h`

Add members:

```cpp
bool RestartPorePress;
double *PorePress;
```

Add accessors:

```cpp
bool GetRestartPorePress() const;
const double* GetPorePress() const;
```

Update allocation accounting in `GetAllocMemory()`.

### `source/JPartsLoad4.cpp`

Update:

- constructor / `Reset()` / `AllocMemory()`
- field detection in `LoadParticles()`
- all-piece consistency checks
- per-piece data loading
- temporary auxiliary buffers if needed

Detection should be independent from the stress-field detection:

```cpp
const bool loadporepress = PartBegin && pd.ArrayExists("PorePress");
```

Type should be checked as:

```cpp
pd.GetArray("PorePress", JBinaryDataDef::DatDouble);
```

When loading each piece:

```cpp
pd.GetArray("PorePress", JBinaryDataDef::DatDouble)->GetDataCopy(npok, PorePress+ntot);
```

If `RestartPorePress` is true, all pieces must contain `PorePress`. If any piece is missing the field, throw an exception because mixed restart pieces would be unsafe.

### `source/JSphCpuSingle.cpp`

`ConfigDomain()` should restore `PorePressc` after:

- CPU arrays have been allocated;
- `Posc`, `Idpc`, and `Velrhopc` have been copied;
- `LoadCodeParticles()` has been called or before it if only `Idp` mapping is required.

Current stress restore happens before `LoadCodeParticles()` and uses `Idp` only, so pore-pressure restore can follow the same mapping pattern. However, `CODE_IsFluid(Codec[p])` is only available after `LoadCodeParticles()`. Two options are possible:

1. Restore for all particles by `Idp`, then let boundary particles remain whatever was saved.
2. Move pore-pressure restore after `LoadCodeParticles()` and restore only material/fluid particles, setting boundary pore pressure to zero.

Recommended first implementation: restore all particles by `Idp`, because the saved `PorePress` field already contains zeros for boundary particles from `GetParticlesData()`. This keeps the implementation close to the existing stress restore.

### `source/JPartDataBi4.*` and `source/JDataArrays.*`

No new interface should be necessary.

Existing support already covers:

- `JDataArrays::AddArray(..., const double*)`
- `JPartDataBi4::AddPartData(..., TypeDouble, ...)`
- `JBinaryDataArray::GetDataCopy()` for `DatDouble`

The loader only needs to call the existing generic array API.

## 5. Restart Priority Rules

Recommended priority for `PartBegin > 0`:

1. If `PorePress` exists in the restart PART:
   - restore `PorePressc` from `PorePress`;
   - skip XML pore-pressure initialization (`PorePressureInit=1/3`) for `PorePressc`;
   - still initialize diagnostics to zero:
     - `PorePressRatec`
     - `DivVelc`
     - `LapPorePressc`
     - `LapZc`
     - `PorePressureAcec`
     - `PorePressureAceDiffc`
   - then apply hydraulic boundary corrections according to current XML and current restart time:
     - top drained if active at `PartBeginTimeStep`;
     - bottom no-flux if enabled.

2. If `PorePress` is missing and `HydromechCoupling=1`:
   - recommended behavior for R1/R2: warning, not fatal, to preserve backward compatibility with old restart files;
   - warning text should be explicit:

```text
Restart PorePress field not found; PorePressc will be initialized from XML PorePressureInit.
This restart is not pore-pressure-consistent for staged u-pw simulations.
```

3. If `PorePress` is missing and `PorePressureInit=0`:
   - `PorePressc=0` remains valid as a compatibility path.

4. If `PorePress` exists but the XML also requests `PorePressureInit=1/3`:
   - restart field wins;
   - print:

```text
Restart PorePress field restored from PART; XML PorePressureInit is skipped.
```

This avoids silently overwriting the staged pore pressure.

Longer term, an optional stricter parameter could be added, but R1/R2 should avoid adding more user-facing switches.

## 6. Idp Mapping

Use the same `Idp` mapping strategy as the stress restore:

1. Build `idmap` from restart `ridp`:

```cpp
idmap[ridp[p]] = p;
```

2. For each current particle `p`, find matching restart index:

```cpp
pr = idmap[Idpc[p]];
```

3. Restore:

```cpp
PorePressc[p] = restart_porepress[pr];
```

4. Count restored and missing particles.

5. Log:

```text
Restart pore-pressure state restored from PART_XXXX: PorePress restored for N/N particles using Idp mapping.
```

Using `Idp` mapping is safer than relying on array order, especially after previous restart work showed that stress/rhop continuity is sensitive to exact particle-state matching.

## 7. Missing Field Policy

Recommended behavior:

| Condition | Behavior |
|---|---|
| `PartBegin=0` | normal XML initialization |
| `PartBegin>0`, `PorePress` present | restore from PART and skip XML init |
| `PartBegin>0`, `PorePress` missing, `HydromechCoupling=1` | warning, then XML init/zero fallback |
| `PartBegin>0`, `PorePress` present in first piece but missing in later piece | hard error |
| `PorePress` type is not `DatDouble` | hard error |

Rationale:

- Old restart files without `PorePress` should still run, but should clearly warn that staged u-pw restart is not pore-pressure-consistent.
- Partial multi-piece data is unsafe and should fail immediately.
- `PorePressc` is a double array, so the restart field should be `DatDouble`.

## 8. Minimum Implementation Stages

### R1: Load PorePress in `JPartsLoad4`

Scope:

- Add `RestartPorePress`.
- Add `double *PorePress`.
- Detect `PorePress` in `Part_XXXX.bi4`.
- Load `DatDouble` values for all pieces.
- Add accessors.

Smoke:

- Run a saved PART inspection or a short restart and verify log reports `PorePress` availability.

### R2: Restore `PorePressc` in `JSphCpuSingle::ConfigDomain()`

Scope:

- Restore `PorePressc` using `Idp` mapping.
- Skip XML `PorePressureInit` when restart pore pressure is restored.
- Keep all diagnostic arrays initialized to zero.
- Keep top drained / bottom no-flux correction after restore.

Smoke:

- Restart same case for one output interval.
- Compare source `Part_XXXX` and restart `Part_0000`:
  - `PorePress` max difference close to 0;
  - `ExcessPorePress` consistent with hydrostatic baseline;
  - `Vel`, `Rhop`, `Sigma_kk`, `Sigma_ij`, `Kplastic` still continuous.

### R3: Scenario 1 Restart Continuity Smoke

Scope:

- Run short self-weight undrained stage to `T_undrained=0.002`.
- Save `PorePress`.
- Restart with:
  - body gravity off, or later with `BodyGravityStopTime` disabled because restart XML uses `Gravity=0`;
  - `HydraulicGravity=(0,0,-9.81)`;
  - top drained active;
  - bottom no-flux active;
  - feedback mode excess and operator difference-gradient.

Smoke criteria:

- `code=0`;
- `excluded=0`;
- no NaN;
- restart `Part_0000` pore pressure equals source final pore pressure;
- top drained layer is corrected only if active at restart time;
- early post-restart velocity does not show a restart impulse.

## 9. Smoke Test Details

### Same-Gravity Restart Test

Purpose: isolate restart continuity.

1. Stage A:
   - self-weight short run to `T=0.002`;
   - `SavePorePressure=1`;
   - write `Part_XXXX.bi4`.
2. Stage B:
   - restart from `Part_XXXX`;
   - same gravity, same hydraulic settings;
   - run to `T=0.0025` or one output frame.
3. Check:
   - restart `Part_0000` equals Stage A final frame for:
     - `PorePress`;
     - `Vel/Rhop`;
     - `Sigma_kk/Sigma_ij/Kplastic`;
   - no sudden `DivVel` or `PorePressRate` spike.

### Gravity-Off Restart Test

Purpose: staged Scenario 1 path.

1. Stage A:
   - self-weight undrained generation.
2. Stage B:
   - body `Gravity=(0,0,0)`;
   - explicit `HydraulicGravity=(0,0,-9.81)`;
   - restored `PorePress`;
   - top drained active.
3. Check:
   - `dt_pore` remains finite and unchanged by body gravity off;
   - `PorePress` is not reinitialized to hydrostatic/zero;
   - top drained layer excess is zero after correction;
   - pore pressure starts dissipating from the restored field.

## 10. GPU Restart Implications

Pore-pressure restart affects GPU planning in two ways:

1. `PorePress` must become a first-class restartable particle state, not only an output diagnostic.
2. GPU parity tests should include restart continuity once GPU has:
   - `PorePress` device array;
   - GPU output of `PorePress`;
   - GPU-side initialization or host-to-device restore path.

For the current CPU-first milestone, GPU changes should not be made. The future GPU plan should treat restart as a separate milestone after passive `PorePress` GPU output and PR pressure update parity are working.

Suggested GPU sequence impact:

- G1/G2 can proceed with passive arrays and diagnostics.
- G3/G4 pressure-only parity can run without restart.
- PorePress restart should be planned before long staged Scenario 1 GPU runs.

## 11. Recommended Next Step

Implement R1 and R2 together as one small CPU patch:

- add `PorePress` loading to `JPartsLoad4`;
- restore `PorePressc` by `Idp` mapping in `JSphCpuSingle::ConfigDomain()`;
- skip XML pore-pressure initialization when restart pore pressure is restored;
- warn clearly when restart pore pressure is missing.

Do not add new XML parameters for this first patch. The restart field should be used automatically when available.

