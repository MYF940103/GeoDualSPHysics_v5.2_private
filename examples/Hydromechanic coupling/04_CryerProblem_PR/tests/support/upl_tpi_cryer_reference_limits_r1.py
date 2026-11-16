"""Offline finite-storage/M0 companion comparison; no native reader or solver."""
import ast
import csv
import json
from pathlib import Path

T = Path(__file__).resolve().parents[1]
SOURCE = T.parent / "support/plot_cryer_formal_four_nu_r1.py"
NOTE = T / "notes/upl_tpi_cryer_reference_limits_r1.md"
OUT = T / "figures/upl_tpi_cryer_reference_limits_r1.csv"
CHECK = T / "logs/upl_tpi_cryer_reference_limits_r1.check.json"


def stat(p):
    s = p.stat()
    return dict(path=str(p.resolve()), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def main():
    import numpy as np
    from scipy.optimize import brentq, minimize_scalar
    assert not OUT.exists() and not CHECK.exists(), "Preserve existing/partial outputs"
    before = [stat(p) for p in (Path(__file__), SOURCE, NOTE)]
    # Read only the reviewed mathematical class. Do not import or call the
    # original module's extraction/hash/program orchestration functions.
    tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
    classes = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "Reference"]
    assert len(classes) == 1
    ns = dict(np=np, brentq=brentq, R=.05, Q=10000.)
    exec(compile(ast.Module(body=classes, type_ignores=[]), str(SOURCE), "exec"), ns)
    Reference = ns["Reference"]
    rows = []
    for nu in (.1, .2, .3, .45):
        models = {}
        for label, finite in (("finite_Kw", True), ("M0", False)):
            r = Reference(nu, finite=finite)
            # Both models use the same physical gamma. The original finite=False
            # branch deliberately used paper legacy g=9.81 for its time scale.
            # Keep legacy_cv for labels, but use H*kappa for the M0 pressure PDE.
            if not finite:
                r.cv = r.H*r.kappa
                r.decay = r.xi*r.xi*r.cv/.05**2
            lo, hi = .005*.05**2/r.legacy_cv, .5*.05**2/r.legacy_cv
            peak = minimize_scalar(lambda t: -r.pressure(t, radius=.0025)[0],
                                   bounds=(lo, hi), method="bounded", options={"xatol": 1e-14})
            assert peak.success and lo < peak.x < hi
            fine = Reference(nu, modes=720, finite=finite)
            if not finite:
                fine.cv = fine.H*fine.kappa
                fine.decay = fine.xi*fine.xi*fine.cv/.05**2
            sample = np.geomspace(lo, hi, 129)
            convergence = float(np.max(abs(r.pressure(sample)-fine.pressure(sample))))
            assert convergence < 1e-7
            models[label] = dict(peak=float(-peak.fun), time=float(peak.x))
            rows.append(dict(nu=nu, model=label, Kw_Pa=2e8 if finite else "M0",
                initial_undrained_amplitude_B=r.B, storage_factor_A=r.A,
                gamma_physical_N_m3=1000*9.80665, Cv_physical_m2_s=r.cv,
                legacy_Cv_for_Tv_m2_s=r.legacy_cv, fixed_r0_m=.0025, nominal_a_m=.05,
                continuous_peak_Pa=float(-peak.fun), continuous_peak_tau_s=float(peak.x),
                continuous_peak_legacy_Tv=float(peak.x*r.legacy_cv/.05**2),
                modes360_720_max_P_difference_Pa=convergence, physical_acceptance=False))
        a, b = models["finite_Kw"], models["M0"]
        for row in rows[-2:]:
            row.update(M0_minus_finite_peak_Pa=b["peak"]-a["peak"],
                       M0_minus_finite_peak_percent=100*(b["peak"]/a["peak"]-1),
                       M0_relative_peak_phase_percent=100*(b["time"]/a["time"]-1))
    assert before == [stat(p) for p in (Path(__file__), SOURCE, NOTE)]
    with OUT.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with CHECK.open("x", encoding="utf-8") as f:
        json.dump(dict(stage="upl_tpi_cryer_reference_limits_r1", passed=True,
            inputs=before, table=stat(OUT), rows=len(rows), solver_invocations=0,
            native_invocations=0, hash_scans=0, original_reference_modified=False,
            physical_acceptance=False, models_have_different_storage=True), f, indent=2)
    print(CHECK)


if __name__ == "__main__":
    main()
