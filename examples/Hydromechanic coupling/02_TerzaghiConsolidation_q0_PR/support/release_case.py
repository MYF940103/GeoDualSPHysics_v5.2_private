"""Formal case-02 native-PART review; actual times and fixed material IDs only."""
import argparse
import csv
from decimal import Decimal, ROUND_CEILING
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from compare_precision_q0 import pressure_theory, xml_value

CASE = Path(__file__).resolve().parents[1]
REPO = CASE.parents[2]
TARGETS = (.1, .2, .4, .5, .7, 1., 1.5, 2.)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def model(xml):
    tree = ET.parse(xml)
    h = "./execution/special/hydromechanics/"
    m = {k: xml_value(tree, p) for k, p in dict(E="./execution/special/soils/ModulusE",
        nu="./execution/special/soils/PRvs", H="./execution/uservars/varnum[@name='sizefz']",
        q0=h+"HydroMechTopLoadQ0", tD=h+"HydroMechDrainageStartTime", k=h+"HydraulicConductivity",
        n=h+"Porosity", Kw=h+"PoreWaterBulkModulus", rho_w=h+"PoreWaterRho",
        dt="./execution/parameters/parameter[@key='DtFixed']",
        tmax="./execution/parameters/parameter[@key='TimeMax']").items()}
    m["dp"] = xml_value(tree, "./execution/constants/dp")
    m["width"] = xml_value(tree, "./execution/uservars/varnum[@name='sizefx']")
    m["nx"], m["nz"] = round(m["width"]/m["dp"]), round(m["H"]/m["dp"])
    m["M"] = m["E"]*(1-m["nu"])/((1+m["nu"])*(1-2*m["nu"]))
    m["cv"] = m["k"]*m["M"]/(m["rho_w"]*9.81)
    return m


def native(reader, folder, part, nx=10, nz=100):
    run = subprocess.run([str(reader), str(Path(folder)/"data"), str(part)], capture_output=True)
    if run.returncode:
        raise RuntimeError(run.stderr.decode(errors="replace"))
    a = pd.read_csv(io.BytesIO(run.stdout), float_precision="round_trip")
    assert len(a) == nx*nz and np.array_equal(a.id, np.arange(4*nx, 4*nx+nx*nz))
    assert np.isfinite(a.select_dtypes(include="number").to_numpy()).all()
    assert a.rho.gt(0).all() and a.kplastic.eq(0).all()
    return a


def settlement(z, t, m):
    if t == 0:
        return 0.
    a = (2*np.arange(240)+1)*np.pi/2
    tv = m["cv"]*max(t-m["tD"], 0)/m["H"]**2
    integral = np.sum(2*m["q0"]*m["H"]*(-1.)**np.arange(240)/a**2*np.exp(-a*a*tv)*np.sin(a*z/m["H"]))
    return float((m["q0"]*z-integral)/m["M"]*1000)


def inspect(a, initial, m):
    nx, nz = m["nx"], m["nz"]
    t = float(a.time_s.iloc[0])
    z, z0 = a.z.to_numpy(), initial.z.to_numpy()
    displacement = (z0-z)*1000
    total = (a.sigma_zz-a.pressure).to_numpy().reshape(nx, nz).mean(axis=0)
    dx = (a.x.to_numpy()-initial.x.to_numpy()+m["width"]/2) % m["width"]-m["width"]/2
    r = dict(time_s=t, tv=m["cv"]*max(t-m["tD"], 0)/m["H"]**2,
        mean_pressure_pa=float(a.pressure.mean()), top_settlement_mm=float(displacement[nz-1::nz].mean()),
        bottom_settlement_mm=float(displacement[0::nz].mean()),
        classical_top_mm=settlement(z0[nz-1], t, m), classical_bottom_mm=settlement(z0[0], t, m),
        max_layer_total_error_pa=float(np.max(abs(total+m["q0"]))),
        top_gap_pa=float(abs(total[-1]-total[-2])), Q_pa=float(np.sqrt(np.mean(np.diff(total, n=2)**2))),
        max_dx_mm=float(np.max(abs(dx))*1000), max_layer_span_mm=float(np.max(np.ptp(z.reshape(nx, nz), axis=0))*1000),
        load_available=bool(a.load_available.eq(1).all()))
    assert (z>0).all() and r["max_dx_mm"] < .5 and r["max_layer_span_mm"] < .5
    if t >= .1-1e-7:
        assert r["max_layer_total_error_pa"] <= 100 and r["top_gap_pa"] <= 100, f"Stress guard failed at {t}"
        assert set(a.id[a.drained.eq(1)]) == set(initial.id.iloc[nz-1::nz]) and a.pressure.iloc[nz-1::nz].eq(0).all()
        if r["load_available"]:
            r["load_resultant_N_m"] = float(2100*m["dp"]**2*a.load_az.sum())
            r["equivalent_full_width_resultant_N_m"] = r["load_resultant_N_m"]*.1/m["width"]
            assert abs(r["equivalent_full_width_resultant_N_m"]+1000) < .001, f"Load guard failed at {t}"
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--reader", default=str(REPO/"bin/windows/ReadHydroMechPart_win64.exe"))
    args = p.parse_args()
    assert args.label.replace("_", "").isalnum()
    folder = Path(args.output).resolve()
    prefix = CASE/"figures"/args.label
    check = Path(str(prefix)+".check.json")
    if check.exists():
        old = json.loads(check.read_text(encoding="utf8"))
        assert old["passed"] and all(digest(e["path"]) == e["sha256"] for e in old["evidence"])
        print("Existing verified figures preserved: " + str(check))
        return
    xmls = [x for x in folder.glob("*.xml") if ET.parse(x).find("execution/particles") is not None]
    assert len(xmls) == 1
    m = model(xmls[0])
    provenance = folder/"release_provenance.json"
    if provenance.exists():
        adopted = json.loads(provenance.read_text(encoding="utf8"))
        assert adopted["accepted_k1em4_adoption"] and adopted["formal_program_short_equivalence_passed"]
        assert digest(adopted["source_receipt"]) == adopted["source_receipt_sha256"]
    else:
        log = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
        assert "Finished execution (code=0)" in log
        with (folder/"Run.csv").open(encoding="utf-8-sig") as stream:
            records = list(csv.DictReader(io.StringIO(stream.read().lstrip("#")), delimiter=";"))
        assert len(records) == 1 and int(records[0]["Np"]) == m["nx"]*(m["nz"]+4) and int(records[0]["PartsOut"]) == 0
        tree = ET.parse(xmls[0])
        value = lambda k: tree.find("./execution/parameters/parameter[@key='"+k+"']").get("value")
        expected = int((Decimal(value("TimeMax"))/Decimal(value("DtFixed"))).to_integral_value(rounding=ROUND_CEILING))
        assert int(records[0]["Steps"]) == expected
        counts = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", log)
        assert counts and list(map(int, counts.groups())) == [2*expected, expected, expected, 2*expected]
        limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", log)
        assert limits and float(limits[1]) <= .2 and float(limits[2]) < .01
    parts = sorted((folder/"data").glob("Part_*.bi4"))
    assert parts and [int(x.stem.split("_")[-1]) for x in parts] == list(range(len(parts)))
    initial, rows, selected = None, [], {}
    evidence_paths = [xmls[0], Path(args.reader), Path(__file__), Path(__file__).with_name("compare_precision_q0.py"), folder/"Run.out"]
    evidence_paths.append(provenance if provenance.exists() else folder/"Run.csv")
    for i, path in enumerate(parts):
        a = native(args.reader, folder, i, m["nx"], m["nz"])
        if initial is None:
            initial = a.copy()
        r = inspect(a, initial, m)
        assert not rows or r["time_s"] > rows[-1]["time_s"]
        rows.append(r)
        for target in TARGETS:
            if target not in selected or abs(r["tv"]-target) < selected[target][0]:
                selected[target] = (abs(r["tv"]-target), a.copy(), r)
        evidence_paths.append(path)
        if i % 1000 == 0:
            print(f"Reviewed {i}/{len(parts)} PART frames", flush=True)
    assert rows[-1]["tv"] >= 2-1e-6 and abs(rows[-1]["time_s"]-m["tmax"]) < m["dt"]+1e-7
    rows = pd.DataFrame(rows)
    profile, errors = [], {}
    z0 = initial.z.to_numpy().reshape(m["nx"], m["nz"]).mean(axis=0)
    for target, (_, a, r) in selected.items():
        pressure = a.pressure.to_numpy().reshape(m["nx"], m["nz"]).mean(axis=0)
        theory = pressure_theory(z0, r["tv"], m)
        errors[str(target)] = float(np.sqrt(np.mean((pressure-theory)**2)))
        for j in range(m["nz"]):
            profile.append(dict(target_tv=target, actual_tv=r["tv"], time_s=r["time_s"], z0_H=z0[j]/m["H"], pressure_pa=pressure[j], classical_pa=theory[j]))
    profiles = pd.DataFrame(profile)
    paths = [Path(str(prefix)+suffix) for suffix in ("_history.csv", "_profiles.csv", "_profiles.png", "_history.png")]
    assert not any(x.exists() for x in paths)
    rows.to_csv(paths[0], index=False, mode="x"); profiles.to_csv(paths[1], index=False, mode="x")
    fig, ax = plt.subplots(figsize=(7, 6))
    for color, target in zip(plt.cm.viridis(np.linspace(.05, .95, len(TARGETS))), TARGETS):
        a = profiles[profiles.target_tv.eq(target)]
        ax.plot(a.pressure_pa/m["q0"], a.z0_H, color=color, label=f"Tv~{target:g}")
        ax.plot(a.classical_pa/m["q0"], a.z0_H, color=color, ls="--", lw=.8)
    ax.set(title=f"k={m['k']:g} m/s: numerical solid / classical dashed", xlabel="Pore pressure / q0", ylabel="Initial material z0/H", ylim=(0, 1))
    ax.grid(alpha=.25); ax.legend(fontsize=8); fig.tight_layout()
    with paths[2].open("xb") as stream:
        fig.savefig(stream, dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    h = rows[rows.time_s >= .1-1e-7]
    for ax, key, title in zip(axes.flat, ("mean_pressure_pa", "top_settlement_mm", "bottom_settlement_mm", "max_layer_total_error_pa", "top_gap_pa", "Q_pa"),
        ("Mean pressure (Pa)", "Top material settlement (mm)", "Bottom material settlement (mm)", "Layer total-stress residual (Pa)", "Top adjacent-layer gap (Pa)", "Layer second-difference RMS Q (Pa)")):
        ax.plot(h.tv, h[key], color="#2168a6"); ax.set(title=title, xlabel="Tv from actual time"); ax.grid(alpha=.25)
    axes[0, 1].plot(h.tv, h.classical_top_mm, "k--", label="Classical material top"); axes[0, 1].legend(fontsize=8)
    axes[0, 2].plot(h.tv, h.classical_bottom_mm, "k--")
    fig.suptitle(f"k={m['k']:g}: elastic fixed-plane u-pw PR / band / HG / SPR")
    fig.tight_layout()
    with paths[3].open("xb") as stream:
        fig.savefig(stream, dpi=170)
    plt.close(fig)
    evidence_paths += paths
    evidence = [dict(path=str(x), sha256=digest(x)) for x in evidence_paths]
    report = dict(passed=True, numerical_safety_passed=True, physical_acceptance_pending_review=True,
        output=str(folder), model=m, frames=len(rows), final=rows.iloc[-1].to_dict(), profile_rmse_pa=errors,
        final_settlement_error_pct=float(100*(rows.iloc[-1].top_settlement_mm/rows.iloc[-1].classical_top_mm-1)),
        load_measured=bool(rows.load_available.all()), evidence=evidence, visual_review_pending=True,
        limitations=["Native fixed material points, actual times; ideal theory omits the dynamic load ramp.",
                     "Load checks require native HydroMechLoadAce; old missing-array placeholders are not measured force.",
                     "Native PART has no exact HG restart history; runtime HG guards and logs are separate evidence."])
    with check.open("x", encoding="utf8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(dict(passed=True, frames=len(rows), final=report["final"], profile_rmse_pa=errors), indent=2))


if __name__ == "__main__":
    main()
