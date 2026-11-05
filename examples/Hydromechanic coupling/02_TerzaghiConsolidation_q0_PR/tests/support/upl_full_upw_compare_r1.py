"""Qualified CSV-only full u-pl/u-pw overlay at each source's actual saved times."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
CASE, NAME = T.parent, "upl_full_upw_compare_r1"
TV = (.005, .05, .1, .25, .4, .5, .7, 1., 1.5, 2.)
PINS = {
    "tests/support/upl_bigstep_full_review_r1.py": (38206, "8e1ce9083390a63b446d6a50e842d6ed6727971e72778bfec04a9875629e35c2"),
    "tests/notes/upl_bigstep_full_review_r1.json": (8730, "269430b1c2354355fd8141e386abcf342f5892fbde3e300524fe12969be55527"),
    "figures/full_validation_release_k1em4_GPU.check.json": (2279233, "4f5301f44c2f870120217a0fc41064a5281be1b8b86350168ca5e8a06b2f4b49"),
    "figures/full_validation_release_k1em4_GPU_history.csv": (1892064, "78da4b0b43efcb4f69135d9082763ca1e7d951b94a6681ef1727687e883749fd"),
    "figures/full_validation_latest.check.json": (24315, "b6f8923dc5f6f7d75252307ea359ae4d13358152c1aca26105d35e6f47f977a3"),
    "figures/full_validation_latest_profiles_data.csv": (229067, "f8c37d20223d824c11e5b61854c80f146844e0a50e8295859c10a891e7c60698"),
    "figures/full_validation_latest_targets.csv": (1638, "a92e335135683670d4382558ff55cd266cacba17aceeb1e9d0b1b6287931fa86"),
}
BOUND = {}


def entry(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha)


def bind(expected):
    got = entry(expected["path"])
    assert got["sha256"] == expected["sha256"] and got["bytes"] == expected.get("bytes", got["bytes"]), got["path"]
    key = str(Path(got["path"])).casefold()
    assert key not in BOUND or BOUND[key] == got, "Conflicting consumed input"
    BOUND[key] = got
    return Path(got["path"])


def read(expected):
    return json.loads(bind(expected).read_text(encoding="utf-8-sig"))


def rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, data):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    assert parser.parse_args().execution_authorized, "Explicit fresh offline invocation required"
    products = {name: T / "figures" / (NAME + "." + name) for name in ("history.csv", "profiles.csv", "profile_times.csv", "history.png", "profiles.png")}
    record = T / "logs" / (NAME + ".check.json")
    assert not any(path.exists() for path in [record, *products.values()]), "Retained outputs protected"
    pins = {name: dict(path=str(CASE / name), bytes=size, sha256=sha) for name, (size, sha) in PINS.items()}
    for value in pins.values(): bind(value)
    bind(entry(__file__)); bind(entry(T / "notes" / (NAME + ".json")))
    review_e = entry(T / "logs/upl_bigstep_full_r1.review.json"); review = read(review_e)
    assert review["stage"] == "upl_bigstep_full_review_r1.review" and review["passed"] is True and review["failure"] is None
    assert review["physical_acceptance"] is False and review["bindings_unchanged"] and review["independent_final_rehash_performed"] and review["all100_material_layers_exported"]
    native = read(review["source_native"])
    assert native["stage"] == "upl_bigstep_full_review_r1.native" and native["passed"] and native["reader_attempts"] == 1 and native["original_native_guards_passed"]
    assert native["measured_common1291_prefix_bitwise_identity"] and native["physical_acceptance"] is False and native["bindings_unchanged"] and native["independent_final_rehash_performed"]
    run = read(native["source_run"]); call = read(run["call"])
    assert run["passed"] and run["window"] == "candidate_full2Tv" and run["job"]["SlipMode"] == 3 and run["threads"] == 1 and run["backend"] == "CPU"
    assert call["typed_returncode_captured_immediately"] and call["owned_call_exited"] and type(call["exit_code"]) is int and call["exit_code"] == 0
    full = {Path(e["path"]).name.removeprefix("upl_bigstep_full_r1."): bind(e) for e in review["files"] if Path(e["path"]).suffix == ".csv"}
    assert set(full) == {"history.csv", "layers.csv", "theory.csv", "profiles.csv", "profile_times.csv"}
    release = read(pins["figures/full_validation_release_k1em4_GPU.check.json"]); publication = read(pins["figures/full_validation_latest.check.json"])
    assert release["passed"] and release["numerical_safety_passed"] and release["frames"] == 7290
    assert publication["publication_verified"] and publication["sources_verified_by_hash"] and publication["solver_rerun"] is False
    old_history = pins["figures/full_validation_release_k1em4_GPU_history.csv"]
    assert any(e["sha256"] == old_history["sha256"] and Path(e["path"]).resolve() == Path(old_history["path"]).resolve() for e in release["evidence"])
    for name in ("profiles_data.csv", "targets.csv"):
        e = pins["figures/full_validation_latest_" + name]
        assert any(x["sha256"] == e["sha256"] and Path(x["path"]).resolve() == Path(e["path"]).resolve() for x in publication["outputs"])
    old_xml = next(e for e in release["evidence"] if Path(e["path"]).name == "published_case.xml")
    xml = ET.parse(bind(old_xml)).getroot()
    assert next(n for n in xml.iter("parameter") if n.get("key") == "SlipMode").get("value") == "1"
    old_log = next(e for e in release["evidence"] if Path(e["path"]).name == "Run.out")
    assert 'RunMode="Stable - Pos-Cell - Single-GPU"' in bind(old_log).read_text(encoding="utf-8-sig")
    h, oh = rows(full["history.csv"]), rows(bind(old_history))
    assert len(h) == 1682 and len(oh) == 7290 and [int(r["part"]) for r in h] == list(range(1682))
    stress = {}
    with full["layers.csv"].open(encoding="utf-8", newline="") as stream:
        for r in csv.DictReader(stream):
            part = int(r["part"]); values = stress.setdefault(part, [])
            assert int(r["initial_layer"]) == len(values) and float(r["time_s"]) == float(h[part]["time_s"])
            values.append(float(r["total_sigma_zz_mean_Pa"]))
    assert set(stress) == set(range(1682)) and all(len(v) == 100 for v in stress.values())
    history = []
    for i, r in enumerate(h):
        s = stress[i]; q = review["theory_constants"]["q0"]
        history.append(dict(series="current_upl_CPU1_FreeSlip3", part=i, time_s=float(r["time_s"]), actual_Tv=float(r["legacy_Tv_since_drain"]), mean_pressure_pa=float(r["pressure_mean_Pa"]),
            top_settlement_mm=float(r["top_settlement_mm"]), bottom_settlement_mm=float(r["bottom_settlement_mm"]), Q_pa=math.sqrt(sum((s[j+2]-2*s[j+1]+s[j])**2 for j in range(98))/98),
            max_layer_total_error_pa=max(abs(v+q) for v in s), top_gap_pa=abs(s[-1]-s[-2])))
    for i, r in enumerate(oh):
        history.append(dict(series="retained_upw_GPU_Vel0_1", part=i, **{key: float(r[key]) for key in ("time_s", "mean_pressure_pa", "top_settlement_mm", "bottom_settlement_mm", "Q_pa", "max_layer_total_error_pa", "top_gap_pa")}, actual_Tv=float(r["tv"])))
    assert all(math.isfinite(v) for r in history for v in r.values() if isinstance(v, float))
    new_profiles, nt = rows(full["profiles.csv"]), rows(full["profile_times.csv"])
    old_profiles = [r for r in rows(bind(pins["figures/full_validation_latest_profiles_data.csv"])) if r["case"] == "k1em4"]
    ot = [r for r in rows(bind(pins["figures/full_validation_latest_targets.csv"])) if r["case"] == "k1em4"]
    assert len(new_profiles) == len(old_profiles) == 1000 and len(nt) == len(ot) == 10
    profiles, timing = [], []
    for tv in TV:
        a = sorted([r for r in new_profiles if float(r["requested_Tv"]) == tv], key=lambda r: int(r["initial_layer"]))
        b = sorted([r for r in old_profiles if float(r["target_tv"]) == tv], key=lambda r: int(r["layer"]))
        n = next(r for r in nt if float(r["requested_Tv"]) == tv); o = next(r for r in ot if float(r["target_tv"]) == tv)
        assert len(a) == len(b) == 100 and [int(r["initial_layer"]) for r in a] == [int(r["layer"]) for r in b] == list(range(100))
        meta = dict(target_Tv=tv, new_part=int(n["actual_part"]), old_part=int(o["native_part"]), new_actual_time_s=float(n["actual_time_s"]), old_actual_time_s=float(o["time_s"]),
            new_actual_Tv=float(n["actual_Tv"]), old_actual_Tv=float(o["actual_tv"]), signed_new_minus_old_time_gap_s=float(n["actual_time_s"])-float(o["time_s"]),
            new_signed_target_gap_s=float(n["signed_time_gap_s"]), old_signed_target_gap_s=float(o["time_s"])-(release["model"]["tD"]+tv*release["model"]["H"]**2/release["model"]["cv"]))
        assert float(h[meta["new_part"]]["time_s"]) == meta["new_actual_time_s"] and float(oh[meta["old_part"]]["time_s"]) == meta["old_actual_time_s"]
        timing.append(meta)
        for j, (x, y) in enumerate(zip(a, b)):
            assert float(x["actual_time_s"]) == meta["new_actual_time_s"] and float(y["time_s"]) == meta["old_actual_time_s"] and int(y["native_part"]) == meta["old_part"]
            profiles.append(dict(**meta, initial_layer=j, new_z0_m=float(x["z0_m"]), old_z0_m=float(y["z0_H"])*release["model"]["H"], new_pressure_Pa=float(x["actual_P_mean_Pa"]), old_pressure_Pa=float(y["pressure_pa"]),
                new_H1_classical_Pa=float(x["H1_classical_P_at_actual_time_Pa"]), new_H1_finite_Kw_Pa=float(x["H1_finite_Kw_P_at_actual_time_Pa"]), new_H995_finite_Kw_Pa=float(x["H995_finite_Kw_P_at_actual_time_Pa"]), old_classical_at_own_time_Pa=float(y["classical_pa"])))
    assert all(math.isfinite(v) for r in profiles+timing for v in r.values() if isinstance(v, float))
    for name, data in (("history.csv", history), ("profiles.csv", profiles), ("profile_times.csv", timing)): write(products[name], data)
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"): os.environ[key] = "1"
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), constrained_layout=True)
    for ax, key in zip(axes.flat, ("mean_pressure_pa", "top_settlement_mm", "bottom_settlement_mm", "Q_pa", "max_layer_total_error_pa", "top_gap_pa")):
        for series in ("current_upl_CPU1_FreeSlip3", "retained_upw_GPU_Vel0_1"):
            rr = [r for r in history if r["series"] == series]; ax.plot([r["time_s"] for r in rr], [r[key] for r in rr], label=series)
        ax.set(xlabel="Each source's actual saved time (s)", ylabel=key); ax.grid(True)
    axes[0, 0].legend(fontsize=7); fig.suptitle("Qualified u-pl/u-pw histories: different wall/formulation/backend/step; no interpolation or accuracy gate")
    fig.savefig(products["history.png"], dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 5, figsize=(16, 10), constrained_layout=True)
    curves = (("new_pressure_Pa", "new_z0_m", "-", "current u-pl", "C0", "o", 8), ("old_pressure_Pa", "old_z0_m", "-", "retained u-pw", "C1", "x", 10),
        ("new_H1_classical_Pa", "new_z0_m", "--", "H1 classical/new time", ".25", None, 1), ("new_H1_finite_Kw_Pa", "new_z0_m", ":", "H1 finite Kw/new time", "C2", None, 1),
        ("new_H995_finite_Kw_Pa", "new_z0_m", "-.", "H.995 sensitivity/new time", "C4", None, 1), ("old_classical_at_own_time_Pa", "old_z0_m", (0, (1, 3)), "classical/old time", ".6", None, 1))
    for ax, tv in zip(axes.flat, TV):
        rr = [r for r in profiles if r["target_Tv"] == tv]; m = next(r for r in timing if r["target_Tv"] == tv)
        for field, z, style, label, color, marker, spacing in curves:
            ax.plot([r[field] for r in rr], [r[z] for r in rr], linestyle=style, color=color, lw=.7, marker=marker, markevery=spacing, markersize=3., markerfacecolor="none", markeredgewidth=.8, label=label)
        ax.set(title="Tv=%g; tnew=%.6g, told=%.6g\ngap=%+.4g s" % (tv, m["new_actual_time_s"], m["old_actual_time_s"], m["signed_new_minus_old_time_gap_s"]), xlabel="Pressure (Pa), linear scale", ylabel="Original material z0 (m)"); ax.grid(True)
    axes.flat[0].legend(fontsize=6); fig.suptitle("u-pl CPU1/FreeSlip3/current-J versus retained u-pw GPU/Vel0; own actual times and unfitted companions")
    fig.savefig(products["profiles.png"], dpi=160); plt.close(fig)
    for e in BOUND.values(): assert entry(e["path"]) == e, "Consumed CSV/receipt changed"
    result = dict(stage=NAME, passed=True, physical_acceptance=False, source_full_review=review_e, inputs=list(BOUND.values()), files=[entry(p) for p in products.values()],
        rows=dict(history=len(history), profiles=len(profiles), profile_times=len(timing)), new_Q_definition="RMS of98 second differences of100 original material-layer mean total sigma_zz; total=sigma_effective_zz-p", Q_is_not_X_alternating_mode=True,
        qualifiers="Current u-pl: CPU1,FreeSlip3,current-J quadrature/storage/inertia,dt6.2501430511474609e-6,tD.010000228881835938. Retained u-pw: GPU,Vel0/Slip1,legacy density/inertia,dt1e-5,tD.01. Both eta.04/Visco.1/HG.1; this is a descriptive formulation/wall/backend/step/event comparison, not isolated causality or matched truth.",
        clock_qualifier="Every series keeps original actual time and own Tv; current signed pre-drain Tv differs from retained max(t-tD,0) convention. Profile targets use primary H1; time gaps are explicit. H.995 is unfitted sensitivity at new actual time; continuum means are never substituted for native arithmetic means.",
        interpolation_or_clock_rewrite=False, solver_decoder_build_or_program_invoked=False, new_5Pa_or_0p005mm_gate=False, full_physical_acceptance_claimed=False, independent_final_rehash_performed=True)
    with record.open("x", encoding="utf-8", newline="\n") as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps(dict(passed=True, receipt=str(record), rows=result["rows"])))


if __name__ == "__main__":
    main()
