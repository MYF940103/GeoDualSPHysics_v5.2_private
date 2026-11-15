# C08 cached-HG scheduling optimization r1

AUTHOR ONLY. Four new assets: support/c08_h18_hg_opt_r1.hpp, .cu, _build.py and this note. They mechanically derive the completed frozen cached package; no old file, generated source, executable, receipt, result or dependency is edited. No preparation/build/import/help, device/program/solver/native/VTK/profiler, queue or Git is executed by the author. Future preparation, each configuration build and any short or physical run require independent root admission.

## Exact numerical boundary

Namespace/API remain c08cached because each program is separate. ON is exclusively C08_HG_OPT_H18=1; absent env retains original already compiled cusphs Pre/Cor calls, no graph/state allocation, private launch or sidecar. The cached env does not enable this family. Outputs are fresh c08_h18_hg_opt_r1_source, c08_h18_hg_opt_{Debug,Release}_r1, C08OptPlasticHG.csv, C08OptPlasticHGPolicy.json and Debug-only C08OptPlasticHGDebugFirstN.*. Policy schema2, main60 columns and all numerical meanings remain; only its family identity is PrivateC08SingleProducerOptPlasticHG.

The complete NodeKernel source is byte-identical to frozen cached, including its per-thread atomic error read, material trial/Result, FMA context policy, original root/status/finite gates and Gamma. No HG value expression, LS weight, graph/support/capacity/rank, native-ID sorting, full adjoint, history, rotation, current inertia, necessary5us gate, cast arithmetic, cache identity/once/commit check or copied integration expression changes. Physical scope remains original psi0/2D/nonperiodic/Wendland H1.8/5us/AS.3 n2.55/AV.1, same source PRE/NoPen/material/loader; no new parameter is selected.

## Only two scheduling edits

(a) Nine kernels (CheckConsumed, Neighbor, Fit, Row, AdjointFit, AdjointRow, Force, AceUnchanged and CheckCommit) replace per-thread atomicAdd(error,0) with one thread0 atomic snapshot into shared memory, then unconditional __syncthreads(), then the original index/error return. The barrier is before every out-of-range or error return, including the120 extra lanes in a5000/128 launch. Every launched thread participates. Node is deliberately unchanged; LocalSummary's ordinary prior-kernel failure read is unchanged.

Normal-path source RMW count/full update changes from 2*10*5000=100000 to 2*(5000+9*ceil(5000/128))=10720. There are nine block-barrier kernel sites per phase. These are source operation counts, not measured timings or a speedup claim. Kernel count/configuration remains33/full update including two consumers replacing original integrators, not33 additional physical kernels.

(b) AceUnchanged runs immediately after Force and before LocalSummary/Summary. The summary's existing error/id/slot is downloaded. A nonzero summary error immediately calls unchanged ErrorNow() to fetch full first-ID/detail/value and throw, before any generic summary gate. Normal completion does not redundantly download the same Failure there; the former post-summary Ace/ErrorNow site disappears. CommitAce remains after summary download, all host coverage/finite/domain checks and every Ace check. Normal-path small D2H count changes from 11 to 7/full update; consumer, writeback and Accept ErrorNow checks stay at their original boundaries/cadence. All launch/error return-code checks remain.

No intervening original kernel or host check writes Ace between its new location and Commit: LocalSummary/Summary only read Node/Row/history and write observations. Moving this guard neither alters normal numerical input nor postpones rejection past force commit. No summaries, telemetry cadence, runtime gate or fault report is dropped.

## Failure semantics and proof limits

A block snapshots error once rather than independently per lane. If a failure appears during a kernel, some lanes may perform more scratch work than previously; already-running old lanes could also continue. Existing atomic Fail bit accumulation/claimed-first-report remains. Do not demand the same union of secondary bits or the same race winner among simultaneous invalid inputs. Ordered kernel boundaries expose preceding failures, and Summary/conditional ErrorNow rejects before CommitAce. CUDA asynchronous/launch failures still use the existing Cuda exception path. A later consumer/writeback failure can leave the same partial original-stage arrays as cached but cannot Accept or save a completed history; no stronger rollback promise is invented.

On error the new summary may contain fewer nonessential normal observations than the former late Ace failure. Full actual first cause is still fetched and thrown; no unsaved history/arrays/time is reconstructed. Failure/partial assets remain preserved, never retried by this builder.

Future prepare count-checks cached-to-opt derivation of both sources, reverses all permitted CUDA edits to full cached bytes, verifies exact Node function and no added kernel/launch, and embeds the edit list in source_proof.json. Header reverse covers only guard/env labels. Author source must equal that derivation exactly. It binds actual cached Debug/Release builds, completed cached91 run and passed182-row phase review. These establish provenance/implementation scope, not physical acceptance.

## Build closure and future evidence

Unchanged authoritative schema2 ZIP/headers and actual MSVC14.36/CUDA11.7 sm86/fast-math recipes remain. Original113 objects lose only Single/Gpu host objects:111 originals plus new Single/Gpu/CU equal114. Original interaction/material/Simpleker/Darcy/legacyHG objects are not compiled again. Two hosts, one CU and link are the only build tools; no runtime follows. Raw material failure, CPU stage/numeric safeguards and original builder protection gates remain.

Preserving Node text does not prove its new binary/PTX context identical. An actual build must separately examine new machine/body or the existing exact first-n input/reference as root chooses; cached force/trajectory proofs cannot be relabelled as new executable evidence. Observer placement/polling equivalence is not a physical energy certificate. Root plans a same-dt bounded prefix comparison, not a half-step chain; this note admits neither that run nor a full3/window. No speed, physical benefit, coupled passivity or long-trajectory equivalence is claimed.

Future independent commands, for review only:
D:/anaconda3/python.exe -X utf8 -B support/c08_h18_hg_opt_r1_build.py --prepare --execution-authorized
D:/anaconda3/python.exe -X utf8 -B support/c08_h18_hg_opt_r1_build.py --configuration Debug --execution-authorized
D:/anaconda3/python.exe -X utf8 -B support/c08_h18_hg_opt_r1_build.py --configuration Release --execution-authorized
