"""One sealed 2s snapshot: unfitted reference conventions, no solver or acceptance gate."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
NAME, DATA = "upl_reference_snapshot_r1", "upl_bigstep_c625_r1_native_r1"
CHECK, CSV, PNG = T / "logs" / (NAME + ".check.json"), T / "figures" / (NAME + ".csv"), T / "figures" / (NAME + ".png")
PINS = {
    "logs/upl_bigstep_r1.native.json": (727018, "a8fa37ea11cacd5ed8488e8e3cc47c9fdce967d9ff0e2816d2751eecfb9235fe"),
    "logs/upl_bigstep_r1.inputs.json": (651239, "da17c2a094531df07b11e3bc9b2aeadb2a9e670836c4e5938a8a45f886888655"),
    "outputs/upl_spr_av_ReleaseCPU_r1_source/JSph.cpp": (191269, "9296c4db5bdfd929a20fdebda413fb09d8576781caca79b2721a5778dd53214d"),
    "outputs/upl_spr_av_ReleaseCPU_r1_source/JSphCpu.cpp": (267740, "6de7e04477e92ea141224b9df38e0860ae07efdc7b5d512ed30c318e7260236e"),
}
BOUND, META = {}, {}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def bind(e):
    path = Path(e["path"]).resolve(strict=True)
    if str(path) not in BOUND:
        with path.open("rb") as stream:
            got = hashlib.file_digest(stream, "sha256").hexdigest()
        s = path.stat()
        need((s.st_size, got) == (e["bytes"], e["sha256"]), "Sealed input changed: " + str(path))
        BOUND[str(path)], META[str(path)] = e, (s.st_size, s.st_mtime_ns)
    need(BOUND[str(path)] == e, "Conflicting sealed input claim")
    return path


def pinned(name):
    size, sha = PINS[name]
    return bind(dict(path=str(T / name), bytes=size, sha256=sha))


def read(e):
    return json.loads(bind(e).read_text(encoding="utf-8-sig"))


def frame(path, count, columns, part):
    record = 8 + count * columns * 8
    with path.open("rb") as stream:
        need(struct.unpack("<III", stream.read(12)) == (count, columns, 1292), "Typed sealed binary header differs")
        need(path.stat().st_size == 12 + 1292 * record, "Typed binary byte count differs")
        stream.seek(12 + part * record)
        data = stream.read(record)
    values = struct.unpack_from("<" + str(count * columns) + "d", data, 8)
    return struct.unpack_from("<d", data)[0], [values[i * columns:(i + 1) * columns] for i in range(count)]


def theory(zs, H, M, n0, g, k, water, Kw, q0, elapsed):
    B, Cv = 1 / (1 + n0 * M / Kw), k * M / (water * g)
    lam = [(i + .5) * math.pi for i in range(512)]
    decay = [math.exp(-B * Cv * l * l * elapsed / (H * H)) for l in lam]
    out = {}
    for z in set(zs):
        pressure = 2 * B * q0 * math.fsum(((-1) ** i) * math.cos(l * z / H) * decay[i] / l for i, l in enumerate(lam))
        integral = 2 * B * q0 * H * math.fsum(((-1) ** i) * math.sin(l * z / H) * decay[i] / (l * l) for i, l in enumerate(lam))
        out[z] = (pressure, 1000 * (q0 * z - integral) / M)
    return out, dict(B=B, Cv_finite_Kw=B * Cv, continuum_mean_P_Pa=2 * B * q0 * math.fsum(d / (l * l) for d, l in zip(decay, lam)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    need(args.execution_authorized and all(not p.exists() for p in (CHECK, CSV, PNG)), "Explicit fresh snapshot-only invocation required")
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    import psutil
    process = psutil.Process()
    process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    result = dict(stage=NAME, passed=False, physical_acceptance=False, failure=None, priority=process.nice(), no_solver_decoder_build_or_active_full_reads=True)
    try:
        native = json.loads(pinned("logs/upl_bigstep_r1.native.json").read_text(encoding="utf-8-sig"))
        m = json.loads(pinned("logs/upl_bigstep_r1.inputs.json").read_text(encoding="utf-8-sig"))
        need(native["passed"] is True and native["original_native_guards_passed"] is True and native["bindings_unchanged"] is True and
             native["independent_final_rehash_performed"] is True and native["physical_acceptance"] is False and m["passed"] is True, "Passed sealed native/input prerequisites required")
        item = native["datasets"]["candidate"]; done, run = read(item["completion"]), read(item["source_run"])
        need(done["passed"] is True and done["samples"] == 1292 and done["native_total_arrays"] == 22 and done["planned_completed_steps"] == 320000 and
             run["passed"] is True and run["job"] == m["jobs"][0] and run["program"]["sha256"] == "bee3e36348b2146b6532cc2d2edf2717c8f4ff657da75812c0bcd5bc2f6e931e", "Exact completed candidate association differs")
        leaves = {Path(e["path"]).name: e for e in item["files"]}
        physical = bind(leaves["physical.bin"]); t0, initial = frame(physical, 1000, 26, 0); time, q = frame(physical, 1000, 26, 1291)
        tj, jt = frame(bind(leaves["common_j_theta.bin"]), 1040, 2, 1291)
        with bind(leaves["native_ids.csv"]).open("r", encoding="utf-8", newline="") as stream:
            ids = list(csv.DictReader(stream))
        need(t0 == 0 and time == tj == 2.0000457763593587 and len(ids) == 1000 and all(int(r["id"]) == i + 40 and
             tuple(float(r[k]) for k in ("x0", "y0", "z0")) == initial[i][:3] and q[i][8:10] == jt[i + 40] and
             all(math.isfinite(v) for v in q[i]) and q[i][8] > .7 for i, r in enumerate(ids)), "Snapshot clocks/IDs/initial coordinates/native Jtheta differ")
        z = [v[2] for v in initial]; layers = [[i for i, zi in enumerate(z) if round(zi / .01 - .5) == level] for level in range(100)]
        need(all(len(v) == 10 for v in layers) and len(set(i for a in layers for i in a)) == 1000, "All100 original material layers required")
        xml = ET.parse(bind(m["jobs"][0]["runtime"])).getroot(); value = lambda name: float(next(xml.iter(name)).get("value"))
        E, nu, k, water, Kw, n0, q0, event = (value(name) for name in ("ModulusE", "PRvs", "HydraulicConductivity", "PoreWaterRho", "PoreWaterBulkModulus", "Porosity", "HydroMechTopLoadQ0", "HydroMechDrainageStartTime"))
        need((E, nu, k, water, Kw, n0, q0, event) == (2e6, .3, 1e-4, 1000., 2e8, .3, 10000., .010000228881835938), "Frozen XML constants differ")
        source, cpu = (pinned(name).read_text(encoding="utf-8-sig") for name in ("outputs/upl_spr_av_ReleaseCPU_r1_source/JSph.cpp", "outputs/upl_spr_av_ReleaseCPU_r1_source/JSphCpu.cpp"))
        need("SoilCte.Porosity=ReadHydroFloat" in source and "gamma=rhow*9.80665" in cpu and "1.-(1.-double(SoilCte.Porosity))/j" in cpu, "Archived float/J/gamma conventions differ")
        text = bind(run["run_out"]).read_text(encoding="utf-8-sig")
        bulk, shear = (float(re.search(label + r":\s*([0-9.]+)", text)[1]) for label in ("Bulk Modulus", "Shear Modulus"))
        need((bulk, shear) == (1666666.75, 769230.8125), "Actual printed binary-exact moduli differ")
        M, Mf, nf = E * (1 - nu) / ((1 + nu) * (1 - 2 * nu)), bulk + 4 * shear / 3, struct.unpack("<f", struct.pack("<f", n0))[0]
        mean = lambda a: math.fsum(a) / len(a)
        P, J, S = [v[6] for v in q], [v[8] for v in q], [-1000 * (v[2] - zi) for v, zi in zip(q, z)]
        weighted = lambda a: math.fsum(v * j for v, j in zip(a, J)) / math.fsum(J)
        summaries, rows = [], []
        for constants, modulus, porosity, g in (("XML_g9.81", M, n0, 9.81), ("XML_g9.80665", M, n0, 9.80665), ("float_Mn_g9.81", Mf, nf, 9.81), ("float_Mn_g9.80665", Mf, nf, 9.80665)):
            for H in (1., .995):
                ref, info = theory(z, H, modulus, porosity, g, k, water, Kw, q0, time - event)
                pr, sr = [ref[zi][0] for zi in z], [ref[zi][1] for zi in z]
                top, bottom = layers[99], layers[0]
                summaries.append(dict(constants=constants, H_m=H, M_Pa=modulus, n0=porosity, g=g, **info,
                    same_node_mean_P_Pa=mean(pr), same_node_J_weighted_mean_P_Pa=weighted(pr), P_profile_RMS_error_Pa=math.sqrt(mean([(a - b) ** 2 for a, b in zip(P, pr)])),
                    native_minus_same_node_mean_P_Pa=mean(P) - mean(pr), native_minus_same_node_J_weighted_mean_P_Pa=weighted(P) - weighted(pr),
                    settlement_profile_RMS_error_mm=math.sqrt(mean([(a - b) ** 2 for a, b in zip(S, sr)])),
                    top_reference_P_Pa=mean([pr[i] for i in top]), top_reference_settlement_mm=mean([sr[i] for i in top]),
                    top_settlement_error_mm=mean([S[i] - sr[i] for i in top]), top_settlement_relative_error_percent=100 * mean([S[i] - sr[i] for i in top]) / mean([sr[i] for i in top]),
                    bottom_reference_settlement_mm=mean([sr[i] for i in bottom]), bottom_settlement_error_mm=mean([S[i] - sr[i] for i in bottom])))
                for level, take in enumerate(layers):
                    rows.append(dict(constants=constants, H_m=H, layer=level, first_ID=min(take) + 40, last_ID=max(take) + 40, IDs=10, z0_m=mean([z[i] for i in take]),
                        native_P_mean_Pa=mean([P[i] for i in take]), reference_P_mean_Pa=mean([pr[i] for i in take]), native_settlement_mean_mm=mean([S[i] for i in take]),
                        reference_settlement_mean_mm=mean([sr[i] for i in take]), native_J_mean=mean([J[i] for i in take])))
        effects = []
        for row in summaries:
            base = next(r for r in summaries if r["constants"] == "XML_g9.81" and r["H_m"] == row["H_m"])
            effects.append(dict(constants=row["constants"], H_m=row["H_m"], continuum_mean_P_change_Pa=row["continuum_mean_P_Pa"] - base["continuum_mean_P_Pa"],
                same_node_mean_P_change_Pa=row["same_node_mean_P_Pa"] - base["same_node_mean_P_Pa"], top_reference_settlement_change_percent=100 * (row["top_reference_settlement_mm"] / base["top_reference_settlement_mm"] - 1)))
        with CSV.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(10, 5), constrained_layout=True)
        base = [r for r in rows if r["constants"] == "XML_g9.81"]
        for H in (1., .995):
            take = [r for r in base if r["H_m"] == H]
            for ax, field in zip(axes, ("P", "settlement")):
                ax.plot([r["reference_" + field + "_mean_" + ("Pa" if field == "P" else "mm")] for r in take], [r["z0_m"] for r in take], label="Unfitted H=" + str(H))
        for ax, field, unit in zip(axes, ("P", "settlement"), ("Pa", "mm")):
            take = base[:100]; ax.plot([r["native_" + field + "_mean_" + unit] for r in take], [r["z0_m"] for r in take], "k.", ms=2, label="Sealed native material means")
            ax.set(xlabel=field + " (" + unit + ")", ylabel="Initial material z0 (m)"); ax.grid(True); ax.legend(fontsize=8)
        fig.suptitle("One actual 2s snapshot; both pressure planes unfitted; no physical acceptance"); fig.savefig(PNG, dpi=160); plt.close(fig)
        result.update(passed=True, part=1291, actual_time_s=time, tau_since_original_drain_s=time - event, IDs=1000, layers=100, CSV_rows=len(rows),
            native_arithmetic_mean_P_Pa=mean(P), native_J_volume_weighted_mean_P_Pa=weighted(P), native_top_P_Pa=mean([P[i] for i in layers[99]]),
            native_top_settlement_mm=mean([S[i] for i in layers[99]]), native_bottom_settlement_mm=mean([S[i] for i in layers[0]]),
            current_volume_weights_are_J_proportional_from_previously_verified_native_ledger=True, constants_hold_XML_k_fixed=True, references=summaries, constant_effects_vs_XML_g9_81=effects,
            interpretation="Continuum means integrate0..H; same-node means use every original ID at its actual initial z0. H=.995 is the pre-existing unfitted pressure-plane convention, not a fitted replacement. Neither convention is an exact dynamic ramp/kernel-band/J-evolving solution or proof of the residual cause.")
    except Exception as error:
        result["failure"] = str(error)
    result["inputs"] = list(BOUND.values())
    result["author_files"] = [dict(path=str(p.resolve()), bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (Path(__file__), T / "notes" / (NAME + ".json"))]
    result["files"] = [dict(path=str(p), bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (CSV, PNG) if p.exists()]
    result["python_version"] = sys.version
    result["final_input_metadata_unchanged"] = all((Path(p).stat().st_size, Path(p).stat().st_mtime_ns) == v for p, v in META.items())
    result["passed"] = result["passed"] and result["final_input_metadata_unchanged"]
    result["hash_scope"] = "One cached full SHA per consumed input; physical initial/final and Jtheta final blocks only; no all-frame analysis or second full rehash."
    with CHECK.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], receipt=str(CHECK), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
