# C08 private GPU plastic-HG implementation boundary

AUTHOR ONLY, c08_h18_hg_gpu_r1. Four new support/note assets: POD/API .hpp, independent CUDA .cu, reversible overlay+build.py, and this note. No prepare/build/program/help/solver/native/VTK/Git/SHA was run by these authors. Original source archives, public classes, XML/BAT/PRE, typed22 and retained trajectories are unchanged. Root separately admits source preparation, each build, and later each implementation job. No long window or other psi case follows automatically.

## Model and scope

This implements the new energy-normalized active-directed-row memory model, not literal GNOG or an existing paper time integrator. Each row holds e, E=.5 sum|e|², current D=xi G Vi Vj w/2, drive u=sqrt(D) P(v), and force=-P^T sqrt(D) e_average. xi is fixed .1. The original positive LS weights aij=Vj*w and the full adjoint are retained; gamma does not enter the LS fit. gamma_ij=.5 gamma_i+.5 gamma_j acts on the loading drive, not by scaling away old memory. Frozen-input loading/unloading uses the already tested exact piecewise integral. New rows begin at zero; dead rows lose their actual .5|e|² energy and are counted, never slept/reawakened. Physical sigma/kappa/J/p histories are not reset.

Local receiver omega is the xz skew of its actual LS gradient. Each trial uses two exact 2D half-rotations with the fixed-input update between them. The middle integrated drive supplies the force. Each local half angle must remain <=.005; the new objective e transport permits finite accumulated angle. This deliberately differs from legacy raw-history HG. The public legacy .01 spin guard, its objects and its policy remain untouched. The numeric component qualified only shared-value refactoring and pure-spin helper range, not coupled large-rotation accuracy or passivity.

Runtime ON is exact C08_HG_H18=1; absent env takes the original path with no State construction, graph allocation, kernel launch, sidecar, or addition of zero to Ace. Other env values fail. The closed ON scope is schema2 same-material psi0, original certified Wendland H=.072f/dp.04/5us source, normal bedroles retirement255/keepfalse, native6805=1805fixed+5000soil IDs2060..7059, nonperiodic 2D, original AS.3/n2.55/AV.1/CompletedOnly/NoPen/current Darcy and all source/material flags. It does not support a native restart of e or other psi groups.

## Genuine stages, material and acceptance

The host overlay is generated from the original full_source.zip Single source, never the RV-modified Single. It adds nine unique insertion anchors and reverses them byte-for-byte before preparation can pass:

1. Include the private API and namespace nonowning pointer/Run-local scope after the original Single include.
2. Create that scope after original Run AppName/Log/CfgRun assignment.
3. Add the HG stage after the original mechanical/AS/AV/load/2D reset and immediately before the sole original ComputeDynamicPorePressureRateGpu call.
4–5. Immediately after each original DtVariable return, require actual ddt_p/ddt_c=5us.
6–7. Immediately after the unchanged real ComputeSymplecticPre/Corr returns, compare six sigma components and kappa against the same-input material shadow, keyed by native ID.
8. Only after the original completed RunCellDivide and actual TimeStep+=stepdt/LastDt assignment, accept the full trial once.
9. Write HG sidecar records only after the original JSph::SaveData returns.

Before the n trial the original FixedDt must be constant5us with empty file and current SymplecticDtPre=5us. This is an explicit fixed-step contract before DtVariable, followed by an actual selected-dt check; no previous dterror or n*dt inference is used. The first predictor checks exact certified source TimeStep9.9999999997060076 at global2000000; a nominal time>=10 would incorrectly reject it. Both force stages retain original source TimeStep/Nstep. n/h trials always start from the same committed e_n; predictor e is never committed or used as the full base. A failure after an actual solver update is a real partial failure, not permission to reconstruct unsaved state or retry.

The n material input uses the actual Sigma_n+(dt/2)Rsigma_n; h uses the still-live SigmaPreg_n+dt Rsigma_h, old kappa unchanged. The Simpleker tensor layout is (xx,xy)/(xz,yy)/(yz,zz). The private CUDA translation unit receives StSoilCte/fit/soft/trigger/require-elastic explicitly: it never links to another TU's SOILSCTE or timestep constant symbols. Gamma is Elastic1, Smooth returned_q/trial_q, Apex/TensionRepair0. Invalid status, zero invalid Smooth trial q, nonfinite or outside[0,1] rejects without clipping. Predictor actual six stresses and old kappa, then corrector actual six stresses and returned kappa, must match bitwise. h expected values survive the original SigmaPreg free inside ComputeSymplecticCorr. No new physical material commit is performed.

The original dynamic Darcy, variable-k chain, wall acceleration update and AceMax run exactly once in their original order, after HG has changed Ace. The original material, pressure, position, porosity and contact kernels are not modified. Necessary fixed5us, rank, positive current volume/inertia, active-ID and finite gates remain. Sidecar mechanical work/ledger discrepancies and floatcommit budgets are diagnostic quantities, not a claim that the original Symplectic/contact/Darcy integration inherits the frozen toy energy contract.

## GPU graph and lifetime

The original cell-linked-list Initsp/ParticleRange(cellfluid) enumerates candidate donors. Per receiver the bounded128-entry table is sorted by original native ID; actual overflow, duplicate ID, missing reverse membership, coincident pair, nonpositive active weight, failed LS rank or condition>=1e8 is rejected. Capacity128 is an explicit implementation limit; the retained six-state geometry review observed max degree44, which is not a guarantee for a future trajectory. No5000² search, per-force allocation, graph/history host download or unordered floating atomic sum is used.

The complete adjoint needs Fit M/L, row memory/integral and Zi/Ti, then outgoing/incoming q gather. It is not the old RV average residual operator; old RV has a tau viscosity weight and cannot supply this HG D. beta multiplication uses one canonical native-ID order so both directed D agree. Current m=V0(rho0-rhow+rhow J) is used for Ace. Actual float Ace writeback and its force discrepancy are recorded. Each receiver thread first sums only its <=128 current/old rows into a local summary; the final diagnostic reduction visits5000 compact receiver summaries, never serially scans the full directed-row graph. Only compact error/summary records return to the host each stage; their synchronization is real overhead, not benchmarked speed. The CSV objective_accumulated_angle is the accepted-step sum of twice the maximum local half-angle across that step’s two stages: it is an accumulated envelope, not any particle’s net signed rotation.

Debug only additionally captures the first genuine n-stage5000-node input (ID/x/z/vx/vz/V/m/gamma) and uncast HG force once, before h can overwrite that graph. The first actual Save writes that node CSV and its Config h/Bwen/G/width/e0 policy; it downloads no row/history. This is a one-time Debug implementation crosscheck input, not live graph telemetry. Release has no snapshot buffer/kernel/D2H/file. Root may independently evaluate the already qualified CPU value core on those exact inputs; no GPU correctness is presumed from memcheck or self-reported adjoint ledger alone.

State owns persistent CUDA buffers through its Impl. The Run-local unique owner releases them on normal/exception exit, before Single/base destruction and cudaDeviceReset. The namespace pointer never owns CUDA memory; there is no static destructor cudaFree after reset. The bounded buffers allocate only on the first genuinely ON stage.

## Build closure and remaining implementation evidence

The builder first requires actual passed CPU stage and numeric receipts/calls/completions:220000 OFF fields,420000 material sigma/kappa comparisons,20000 old force bits, both unloading cases and quarter/full spin checks. These are prerequisite implementation evidence, not GPU equivalence. Preparation emits only a fresh source capture, Single overlay, private .cu/.hpp and exact diff/anchor proof. Each chosen Debug/Release build is separate and uses one original host CL recipe, one original CUDA11.7/MSVC14.36 sm86 recipe and one link invocation. No program is launched by the builder.

The authoritative113-object schema2 inventory loses only JSphGpuSingle.obj;112 original objects (including original main, physical interaction CUDA, Simpleker material CUDA and legacy HG) plus new Single and HG CUDA objects give114. All frozen original headers are copied from the same schema2 archive. Original9 runtime files are protected/copied with bytes+mtime and byte identity; public programs/runtime_r5/runtime_r6/original PRE are stat protected. No historical object seal is invented: the new object inventory is matched to the genuine original link receipt and its recorded build interval.

Original -use_fast_math/FMA numerical flags remain, especially for the material shadow versus original Simpleker. Only the new CU Debug appends -DC08_HG_DEBUG_SNAPSHOT to compile its one-time node observation; Release forbids that macro. This does not change the original112 objects or select a second numerical algorithm. HG value operations explicitly select their RN arithmetic. Shared source/header and compiler flags still cannot statically promise material bit equality; the actual Pre/Corr comparison is the necessary implementation test. No RV --fmad=false flag is silently inherited for the whole new CU. Debug/Release outputs and source preparation are exclusive fresh tags and preserve any failure/partial.

Future root-owned operations, not executed here:

    python support/c08_h18_hg_gpu_r1_build.py --prepare --execution-authorized
    python support/c08_h18_hg_gpu_r1_build.py --configuration Debug --execution-authorized
    python support/c08_h18_hg_gpu_r1_build.py --configuration Release --execution-authorized

Subsequent OFF Release1-update/native byte regression and ON Debug2-update/memcheck/material/native review require separate root admission. There is no new owner/reader/queue/long-window asset in this package. A successful build or short implementation test is not physical repair, formal collapse acceptance, full energy stability, restart support or admission of the other psi cases.
