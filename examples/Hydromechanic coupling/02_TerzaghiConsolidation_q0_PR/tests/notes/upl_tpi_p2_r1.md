# Private P2 source preparation

Author-only. This stage adds the three private pressure/timestep authors to fresh
complete copies of the original M0-r2 source snapshots. Nothing here builds,
launches or accepts a physical job. Original source, runtimes and results remain.

CPU retains267 files; GPU retains270. Only the two backend host translation units,
the existing private pressure header and the existing private M0 timestep header
are replaced. No public class header, CUDA source/cuh, physical spatial operator,
material/J/HG update or input parameter is changed. The GPU header has one explicitly
excluded host-only API declaration block; removing it must leave the original
implementation-prefix bytes exactly identical. The copied CUDA objects can be
considered only after that proof and actual original-link closure review.

The Single loop now evaluates two complete endpoint defects at the already
committed full geometry. Each has a real force/bound/Prepare/Pos/Write/BC lifecycle.
The first validates/copies p1 without history rotation; the second reads that actual
float and commits history once. CPU SecondEndpoint already captures HG internally;
its first endpoint retains the original outer CaptureHG. No additional material,
J, position, HG history, global TimeStep or Nstep update is introduced. Each force
uses the original source clock and loading. H3 and staged-load authors are excluded.

The backend DtVariable passes the pressure helper's actual EndpointPhase2/3 to the
independent four-phase writer. Original signed necessary bounds and all guards
remain. Only phase3 finishes the dt audit; final pressure validation and commit
must still succeed. Actual uncommitted failure state is not a restart/rollback.

Every backend preparation requires a separate root fully read prepare-only
admission with stage `upl_tpi_p2_r1.prepare_admission`, passed/prepare_only=true,
backend CPU/GPU and actual consumed stat inputs. The entry takes `--backend`,
`--admission` and `--execution-authorized`. Source trees, receipts and diffs use
`outputs/upl_tpi_p2_{CPU,GPU}_r1_source` and `logs/upl_tpi_p2_{CPU,GPU}_r1.*`.
Existing or partial paths reject instead of overwriting. No SHA scan occurs.

The preparation receipt is source qualification only. Default-A, both pressure
rows, four signed phases and all original22/native/ledger/drain/HG checks still
need real independently admitted implementation tests before any bounded science
job. No half/reference/full-cycle or production XML follows automatically.
