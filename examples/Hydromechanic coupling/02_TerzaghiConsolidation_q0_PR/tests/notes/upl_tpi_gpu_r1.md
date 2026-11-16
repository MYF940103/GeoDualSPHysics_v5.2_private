# Private GPU P1 author preparation

Status: authored candidate only; no preparation, compilation, help, solver,
native read, VTK, hash sweep or Git action has been executed by this work.
This is the current Symplectic scheme with TPI neighbour-pressure prediction
and one leading-LP M0/beta0 correction. It is not the paper's literal LF
integrator, an implicit pressure solution or a claimed second-order method.

Use only the retained GPU stabilizers source family:
`logs/upl_gpu_stabilizers_r1.source.json` contains 265 code and two document
snapshots. Its Debug/Release builds each have 111 matching objects. Do not
mix current public code, the older CPU snapshot's GPU HG headers, or C08
schema2 code. The original finite-Kw GPU control remains the retained
150-frame run through completed 1632, actual 0.010200233459472378 s, with
the same SPR1/AV.1/HG.1/eta.04/FreeSlip/constant-k/wall operator.

The prepare author copies the 267 archived files and two new private helper
files into `outputs/upl_tpi_gpu_r1_source` (269 entries; source_diff is separate).
Three translation-unit bodies change: `JSphGpu.cpp`, `JSphGpuSingle.cpp`,
`JSphGpu_ker.cu`. The fourth source change is `JSphHourglassGpu.h`, adding
only nonvirtual const bulk device pointer accessors. No member, class layout,
vtable or old external kernel signature changes. Recompile the unchanged-body
`JSphHourglassGpu.cpp` too, so all complete definitions of the extended class
match strictly: four replacement objects plus 107 retained configuration-
matching objects. Canonical code/project/programs are not modified.

Default/explicit `UPL_TPI_GPU_R1=A` retains the original pressure integration.
The default branch does not allocate pressure history, publish a device
descriptor or run another force pass. The single spatial pressure kernel is
templated on CaptureRows; ordinary n/h and default A use false, compiling
capture logic out. Only the extra B/C endpoint selects true through the
unchanged old public wrapper. This design is not proof of unchanged A bits:
the new real GPU A path still needs independent native byte comparison to
the actual retained GPU control, including clock/signed fields and original
declaration headers. Previous master-OFF tests do not replace that gate.

B uses alpha=.5, C alpha=0; both beta=0 and M0. Histories belong to the
1040 real native IDs, with only the 1000 soil owners participating. Periodic
copies read their native owner's prediction and never rotate history. ID
slots are refreshed at sorted stages; no stale physical array index is
kept across cell division. Both normal and periodic copies must have the
owner's actual fixed/fluid role in both directions. Eight source-level host
boolean fixtures exercise the shared host/device predicate; they are not
presented as executed GPU negative fixtures or memcheck evidence. The mechanical half uses the same pressure guess
as the endpoint, as in the already exercised CPU prototype. Actual half
pressure/J/theta is captured at corrector entry before mechanics or Jfull;
the original J corrector is applied once, then Jfull is captured. The guess
replaces pressure only after the original full-position update. All outer
scratch release and original necessary timestep checks remain in place.

After the genuine final cell divide and before the original scalar time
increment, B/C perform one force/rate evaluation at original source-clock n.
Every original mechanics/material/J update remains single. The private row
hook uses the current real Idpg through its private descriptor; the old
external pressure-rate function gains no parameters. Drained rows are
captured before the genuine early return. Other rows capture
`S=-k sum(w)` and the complete double `R=-gamma theta+k lap` before float
rate storage. The original lap includes `rho_w Da`, the Taylor term and
the original same-stage force/drainage closures; it is not reconstructed
from the quantized old scaled rate. PorePressRate remains that legacy
scaled residual diagnostic, not the actual M0 pressure time derivative.

All rows, positive unconstrained diagonals, committed core fields and HG
observations must validate before pressure is written. The final original
boundary policy is then applied and all owners validate before rotating
previous=pn. Constrained pressure remains positive-zero. There is no epsilon
diagonal repair, omitted particle, pressure clamp or smoothing filter. A
rejected endpoint does not rotate history or create an invented native state.

Read-only HG injection occurs at the original HG location after normalized
band loading and before the complete Darcy rate. It reuses existing
`cuhg::MapNative`/`AddHistory` with private slots/errors/reduction buffers and
the genuine committed H=Q/M0. Original current-mi scaling and explicit
`__dadd_rn`/`__dmul_rn` arithmetic are retained. It does not invoke the HG
phase methods or mutate their cache/statistics. Both double2 histories/rates
are compared by device bits after D2D snapshots, with mismatch reporting;
all 24 Stats and 15 RateInfo fields are compared by host bits. No per-ID
device-to-host HG getters are used. Seven categories of committed soil
fields are checked by bits; native theta intentionally records endpoint
divergence and is not reinterpreted as the J integration theta.
The unchanged raw Map/AddHistory wrappers and every original slot's missing/
duplicate/ID error checks cover all 1000 injections; StReduce has no count
field and no invented net-force tolerance is added. Each raw wrapper launch
has an immediate getLastError check, followed by its genuine synchronized
reduction copy and the complete zero error-bit requirement.

All Init/Begin/Corr/Saved/Finish/Free calls use the same JSphGpu base-owner
pointer. FreeOwner is explicit, noexcept and idempotent in the original GPU
destructor before cudaDeviceReset. It releases only private buffers and
clears the private descriptor, without dereferencing a potentially destroyed
derived HG object. Partial initialization is owner-bound before allocation.
The static State destructor performs host stream/vector cleanup only and
never attempts CUDA cleanup after context destruction.

No current phase grants solver admission. After root source review the
planned qualification is an independently admitted GPU Debug two-update/
two-frame memcheck smoke, then the real Release A short control, then B/C
at the already declared .15-s scalar schedule, each with independent native
and pressure-sidecar review. Preserve all 22 arrays, 1040 IDs, actual clock,
signed dterror, ledger, load/drainage and HG guards. Same-scheme CPU/GPU
checks are distinct from cross-model A/B/C accuracy comparisons; no new
half or full-cycle chain is implied. The old A stress-accuracy limitation,
finite-Kw/M0 distinction, FSNormal backend differences and force-stage versus
saved-proxy limitations remain explicit.

Prepare only after separate root admission:

```text
python -B tests/support/upl_tpi_gpu_r1_prepare.py
  --execution-authorized --admission ROOT_PREPARE_ADMISSION.json
```

The admission has `stage="upl_tpi_gpu_r1.prepare_admission"`, `passed=true`,
`prepare_only=true`, and `inputs=[{path,bytes,mtime_ns}, ...]` pinning the
three authors, this note, source manifest, both old GPU builds/programs and
all 267 actual archived files. Existing outputs/receipts are never overwritten.
The prepared receipt records 269 source/header entries, three changed TU
stat records, one changed-header record, all four recompile-source records,
and the exact source diff. No old SHA scan is performed and preparation
does not claim implementation, numerical or physical acceptance.
