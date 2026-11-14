# AV.2 narrow native reader — author only

New files are `support/c08_h18_av20_native_r1.cpp`, `_build.py` and this note. Authoring does not import/build/run a reader or solver. Root must read them, separately admit the utility build and inspect actual compiler/link receipts before any unique native invocation. Old AS255/Wendland tools, raw data, PRE and public source remain unchanged.

The existing `c08_h18_as255_native_r1` reader's **numerical receiver core already accepts positive explicit sample counts/end steps** through its genuine scalar plan. Two frames need no new dtype, field loop, budget or ledger logic. Its outer entry currently restricts window/formal and hardcodes GPU. That same entry also explicitly rejects all three AV metadata keys; an external wrapper cannot make the old tool accept AV.2 safely.

The new private entry is mechanically derived from the sealed AS255 generated entry. Exactly nine named transformations are recorded in `entry_profile.diff` and `core_derivation.json`, with a bytewise inverse that must recover every original entry byte:

1. Remove the outer `--source` CLI branch; source numerical functions remain untouched but are not exposed.
2. Replace CLI help and window/formal selection with two closed receiver profiles.
3. Require exact CPU/GPU completed-step schedules after the unchanged scalar-plan validator.
4. Restrict the actual unchanged17-key receiver CSV to original psi0/AS.3/exponent2.55.
5. Replace the combined five-key rejection with the same CompletedOnly two-key absence guard and mandatory typed AV policy checks.
6. Pass CPU for smoke and GPU for window into the original receiver core rather than mislabelling CPU as GPU.
7. Change only diagnostic metadata stage/name and append actual AV/profile annotations.

The list groups nine exact replacement anchors; no other original entry bytes change. All five other generated files, including complete source/receiver22-array numerical cores, remain byte-identical. The standalone utility builds one new entry plus the same six original Release BI4 utility objects with the original archived headers, MSVC14.36, `/fp:precise /O2 /MT /GL-` recipe. No JSph, CUDA or physical TU is linked/rebuilt. CPU/GPU labels describe admitted data-owner profiles, not the utility's compiler configuration or independently proved hardware.

## Exactly two profiles

The new utility is `outputs/c08_h18_av20_native_r1_build/C08H18Av20NativeR1_win64.exe`.

- CPU Debug-program smoke data: `--receiver smoke psi0 DATA PRE PLAN PROFILE_CSV FRESHOUT`. Exactly two frames, completed2000001 and2000400, final source-relative0.002s; both use original dt5us. Part0 is actual PRE+one update, not an inserted PRE state. The core receives backend argumentCPU.
- GPU Release-program bounded data: `--receiver window psi0 DATA PRE PLAN PROFILE_CSV FRESHOUT`. Exactly91 frames, completed2000001+2000*part for parts0–89 and genuine forced final2180000 at part90. This is the original0.90s plan, not a new schedule or half-step run. The core receives backend argumentGPU.

Both use the real five-column planned scalar clock after source2M. The validator replays scalar `+=dt`, preserving actual saved clocks/steps and signed interval diagnostics. It does not substitute n*dt or rewrite metadata. Formal301/source/other-psi/half/control profiles are not exposed.

Every **target** saved header must contain:

- `DynamicArtificialViscosityPolicy`: `DatText`, exactly `ReleaseOnly`.
- `DynamicArtificialViscosityOverrideActive`: `DatBool`, true.
- `DynamicArtificialViscosityCoef`: `DatFloat`, bit-equal `.2f`.

The original actual AS `ReleaseOnly`/active/float.3/2.55 checks remain. Both experimental ponding-policy keys must remain absent. These checks occur inside the original target header loop before the unchanged single field decode, not in an external post-check that bypasses the old rejection. The original schema2 same-material PRE is loaded once by its existing certified loader and is **not required** to contain AV override keys. Original XML Visco.1 or startup Configuration is not proof of release AV.2; typed per-frame metadata plus bound program/source/owner are required. No AV field is added to the original17-key material CSV.

All original22 typed arrays,6805 sorted active IDs (5000 soil/1805 fixed), bed-last retire255/keepfalse, P0 bit inheritance, J/n/V/rho/k/Ck2 ledger, original kappa-from-PRE guard, finite fields, active FS2/3 pressure sign, fixed-plane NoPen/geometry/ReactionClosed=false, nonempty signed intervals, natural step and genuine runtime Run.csv completion guards are retained unchanged. Source material law2/same-material plastic histories remain. The reader does not independently reconstruct the complete material contract or prove GPU hardware, and array checks cannot replace actual program/XML/owner binding.

Build-only command after root admission:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_av20_native_r1_build.py --execution-authorized`

Successful build authorizes no decode. The original core emits `typed22.bin`, layout/clocks/history/plane-gaps and its original `c08_h18_wend_native_r1.receiver` completion stage. New `bedkeep_metadata.json` carries theAV20 stage, exact profile/backend argument and AV typed-header count. Both completion and metadata must be reviewed together. Existing/partial output is refused; failures preserve the first error/partial files without automatic rebuild, solver replay, second decode or next window. Normal exit/native safety is not physical acceptance or evidence that viscosity repaired clumping.
