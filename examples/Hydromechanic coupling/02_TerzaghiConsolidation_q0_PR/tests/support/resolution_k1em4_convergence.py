from pathlib import Path
import argparse
import csv
import importlib.util
import math
import re
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
CASE_ROOT = ROOT.parent
FIGDIR = ROOT / "figures"
POSTPROCESS = CASE_ROOT / "support" / "postprocess_terzaghi_q0.py"

spec = importlib.util.spec_from_file_location("terzaghi_q0", POSTPROCESS)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

BASE_TAG = "k1em4"
BASE_CASE = f"CaseTerzaghiConsolidation_q0_PR_full_{BASE_TAG}"
BASE_XML = CASE_ROOT / f"{BASE_CASE}_Def.xml"
TARGET_TV = [0.05, 0.1, 0.25, 1.0]
L2_PLOT_TV = [0.05, 0.1]
CASES = [
    {"tag": "k1em4_dp003", "case": "CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp003", "dp": 0.03, "k": "1e-4"},
    {"tag": "k1em4_dp002", "case": "CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp002", "dp": 0.02, "k": "1e-4"},
    {"tag": "k1em4", "case": BASE_CASE, "dp": 0.01, "k": "1e-4"},
    {
        "tag": "k1em4_dp0005_dt2em6",
        "case": "CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0005_dt2em6",
        "output_case": "CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0005_dt2em6",
        "xml_case": "CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0005_dt3em6",
        "dp": 0.005,
        "k": "1e-4",
        "dt_fixed": 0.000002,
    },
]


def cv_for_k(k_text):
    return float(k_text) * pp.M_CONSTRAINED / (pp.RHO_W * pp.G_REF)


def tv_from_time(time, cv, tl):
    return cv * max(0.0, time - tl) / (pp.H * pp.H)


def time_from_tv(tv, cv, tl):
    return tl + tv * pp.H * pp.H / cv


def read_xml_value(xml_path, tag, default):
    tree = ET.parse(xml_path)
    elem = tree.find(f".//{tag}")
    if elem is None:
        return default
    return float(elem.attrib["value"])


def read_parameter(xml_path, key, default):
    tree = ET.parse(xml_path)
    for param in tree.findall(".//parameter"):
        if param.attrib.get("key") == key:
            return float(param.attrib["value"])
    return default


def read_dp(xml_path):
    tree = ET.parse(xml_path)
    elem = tree.find(".//newvarcte[@Dp]")
    if elem is None:
        return pp.DP
    return float(elem.attrib["Dp"])


def xml_path_for(meta):
    if "xml_path" in meta:
        return Path(meta["xml_path"])
    xml_case = meta.get("xml_case", meta["case"])
    direct = CASE_ROOT / f"{xml_case}_Def.xml"
    if direct.exists():
        return direct
    tests_direct = ROOT / "configs" / "resolution" / f"{xml_case}_Def.xml"
    if tests_direct.exists():
        return tests_direct
    output_case = meta.get("output_case", meta["case"])
    generated = CASE_ROOT / f"{output_case}_out" / f"{xml_case}.xml"
    if generated.exists():
        return generated
    tests_generated = ROOT / "outputs" / "resolution" / f"{output_case}_out" / f"{xml_case}.xml"
    if tests_generated.exists():
        return tests_generated
    return generated


def particles_folder_for(meta):
    if "particles" in meta:
        return Path(meta["particles"])
    output_case = meta.get("output_case", meta["case"])
    direct = CASE_ROOT / f"{output_case}_out" / "particles"
    if direct.exists():
        return direct
    tests_direct = ROOT / "outputs" / "resolution" / f"{output_case}_out" / "particles"
    return tests_direct


def layer_average(rows, value_key, dp):
    bins = {}
    for row in rows:
        if value_key not in row:
            continue
        key = int(math.floor(row["z"] / dp + 0.5 + 1e-6))
        bins.setdefault(key, []).append(row)
    prof = []
    for _, items in sorted(bins.items()):
        z = sum(row["z"] for row in items) / len(items)
        value = sum(row[value_key] for row in items) / len(items)
        prof.append((z, value))
    return prof


def top_rows(rows, dp):
    zmax = max(row["z"] for row in rows)
    return [row for row in rows if row["z"] >= zmax - 0.55 * dp]


def mean(rows, key):
    vals = [row[key] for row in rows if key in row]
    return sum(vals) / len(vals) if vals else 0.0


def max_value(rows, key):
    vals = [row[key] for row in rows if key in row]
    return max(vals) if vals else 0.0


def terzaghi_excess(z, tv, nterms=300):
    value = 0.0
    for n in range(nterms):
        lam = (2 * n + 1) * math.pi / (2.0 * pp.H)
        an = 2.0 * pp.Q0 * math.sin(lam * pp.H) / (pp.H * lam)
        value += an * math.cos(lam * z) * math.exp(-lam * lam * pp.H * pp.H * tv / (pp.H * pp.H))
    return value


def exact_excess(z, tv, nterms=300):
    value = 0.0
    for n in range(nterms):
        m = (2 * n + 1) * math.pi / 2.0
        lam = m / pp.H
        an = 2.0 * pp.Q0 * math.sin(lam * pp.H) / (pp.H * lam)
        value += an * math.cos(lam * z) * math.exp(-m * m * tv)
    return value


def normalized_l2(profile, tv):
    num = 0.0
    den = 0.0
    for z, sph in profile:
        ref = exact_excess(z, tv)
        num += (sph - ref) ** 2
        den += ref ** 2
    return math.sqrt(num / den) if den > 0.0 else math.nan


def profile_rms_kpa(profile, tv):
    if not profile:
        return math.nan
    return math.sqrt(sum((p - exact_excess(z, tv)) ** 2 for z, p in profile) / len(profile)) / 1000.0


def degree_num(rows):
    return 1.0 - mean(rows, "excess") / pp.Q0


def load_series(folder):
    data = []
    for path in sorted(folder.glob("PartFluid_*.vtk")):
        idx = pp.part_index(path)
        data.append({"name": path.name, "index": idx, "rows": pp.read_part_vtk(path)})
    if not data:
        raise RuntimeError(f"No PartFluid VTK files found in {folder}")
    return data


def prepare_cases():
    if not BASE_XML.exists():
        raise FileNotFoundError(BASE_XML)
    base_text = BASE_XML.read_text(encoding="utf-8")
    made = []
    for meta in CASES:
        if meta["tag"] == BASE_TAG:
            continue
        xml_path = CASE_ROOT / f"{meta['case']}_Def.xml"
        text = re.sub(r'<newvarcte Dp="[^"]+"', f'<newvarcte Dp="{meta["dp"]:g}"', base_text, count=1)
        text = text.replace("Particle spacing", f"Particle spacing for dp={meta['dp']:g} m resolution check", 1)
        text = text.replace(
            '<parameter key="TimeMax" value="72.8842857142858" comment="Formal final time, reaching Tv=2 after tL" units_comment="seconds" />',
            '<parameter key="TimeMax" value="36.4471428571429" comment="Resolution check final time, reaching Tv=1 after tL" units_comment="seconds" />',
        )
        if "dt_fixed" in meta:
            text = re.sub(
                r'<parameter key="DtFixed" value="[^"]+"[^/]*/>',
                f'<parameter key="DtFixed" value="{meta["dt_fixed"]:.9g}" comment="Stable fixed time step for dp={meta["dp"]:g} resolution check" units_comment="seconds" />',
                text,
                count=1,
            )
        xml_path.write_text(text, encoding="utf-8")
        bat_path = CASE_ROOT / f"x{meta['case']}_win64_CPU.bat"
        bat_path.write_text(cpu_bat_text(meta["case"]), encoding="ascii")
        made.append((xml_path, bat_path))
    for xml_path, bat_path in made:
        print(xml_path)
        print(bat_path)


def cpu_bat_text(case_name):
    return f"""@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case={case_name}
set dirout=%case%_out
set diroutdata=%dirout%\\data

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress

if exist "%dirout%" (
  if /i "%~1"=="-force" (
    rd /s /q "%dirout%"
  ) else (
    echo Output directory "%dirout%" already exists.
    choice /c YN /m "Delete it and rerun {case_name}"
    if errorlevel 2 goto abort
    rd /s /q "%dirout%"
  )
  if exist "%dirout%" goto fail
)

%gencase% %case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -ompthreads:20 -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo {case_name} done.
popd
exit /b 0

:abort
echo {case_name} aborted by user.
popd
exit /b 0

:fail
echo {case_name} failed.
popd
exit /b 1
"""


def summarize_cases(prefix, figdir):
    figdir.mkdir(parents=True, exist_ok=True)
    summaries = []
    targets = []
    profiles = []
    for meta in CASES:
        xml_path = xml_path_for(meta)
        folder = particles_folder_for(meta)
        if not folder.exists():
            raise RuntimeError(f"Missing particles folder: {folder}")
        if not xml_path.exists():
            raise RuntimeError(f"Missing XML file: {xml_path}")
        dp = read_dp(xml_path)
        dt_fixed = read_parameter(xml_path, "DtFixed", math.nan)
        cv = cv_for_k(meta["k"])
        tl = read_xml_value(xml_path, "HydroMechTopLoadRampTime", pp.TL)
        tout = read_parameter(xml_path, "TimeOut", 0.0)
        series = load_series(folder)
        for item in series:
            item["time"] = item["index"] * tout
            item["tv"] = tv_from_time(item["time"], cv, tl)
        final = series[-1]
        summaries.append({
            "tag": meta["tag"],
            "case": meta["case"],
            "dp": dp,
            "snapshots": len(series),
            "fluid_particles": len(series[0]["rows"]),
            "dt_fixed": dt_fixed,
            "final_tv": final["tv"],
            "final_u_num": degree_num(final["rows"]),
            "final_u_theory": pp.degree_theory(final["tv"]),
            "max_speed": max(max_value(item["rows"], "speed") for item in series),
        })
        for tv in TARGET_TV:
            target_time = time_from_tv(tv, cv, tl)
            item = min(series, key=lambda row: abs(row["time"] - target_time))
            profile = layer_average(item["rows"], "excess", dp)
            l2 = normalized_l2(profile, tv)
            targets.append({
                "tag": meta["tag"],
                "case": meta["case"],
                "dp": dp,
                "dt_fixed": dt_fixed,
                "target_tv": tv,
                "actual_tv": item["tv"],
                "snapshot": item["name"],
                "time_s": item["time"],
                "normalized_l2_error": l2,
                "profile_rms_kpa": profile_rms_kpa(profile, tv),
                "u_num": degree_num(item["rows"]),
                "u_theory": pp.degree_theory(item["tv"]),
                "top_excess_kpa": mean(top_rows(item["rows"], dp), "excess") / 1000.0,
                "max_speed": max_value(item["rows"], "speed"),
            })
            for z, sph in profile:
                ref = exact_excess(z, tv)
                profiles.append({
                    "tag": meta["tag"],
                    "dp": dp,
                    "target_tv": tv,
                    "actual_tv": item["tv"],
                    "snapshot": item["name"],
                    "z_m": z,
                    "z_over_h": z / pp.H,
                    "pore_sph_pa": sph,
                    "pore_sph_norm": sph / pp.Q0,
                    "pore_theory_pa": ref,
                    "pore_theory_norm": ref / pp.Q0,
                })
    write_csv(figdir / f"{prefix}_summary.csv", summaries)
    write_csv(figdir / f"{prefix}_targets.csv", targets)
    write_csv(figdir / f"{prefix}_profiles_data.csv", profiles)
    plot_profiles(figdir / f"{prefix}_profiles.png", profiles)
    plot_l2(figdir / f"{prefix}_l2_error.png", targets)
    print(figdir / f"{prefix}_targets.csv")
    print(figdir / f"{prefix}_l2_error.png")


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_profiles(path, rows):
    colors = {0.03: "#984ea3", 0.02: "#377eb8", 0.01: "#4daf4a", 0.005: "#e41a1c"}
    fig, axes = plt.subplots(1, len(TARGET_TV), figsize=(13.2, 4.4), sharey=True)
    for ax, tv in zip(axes, TARGET_TV):
        subset_tv = [row for row in rows if abs(row["target_tv"] - tv) < 1e-12]
        for dp in sorted({row["dp"] for row in subset_tv}, reverse=True):
            subset = sorted([row for row in subset_tv if abs(row["dp"] - dp) < 1e-12], key=lambda row: row["z_m"])
            ax.plot([row["pore_sph_norm"] for row in subset], [row["z_over_h"] for row in subset],
                    marker="o", ms=2.8, lw=1.1, color=colors.get(dp), label=f"dp={dp:g}")
        theory = sorted([row for row in subset_tv if abs(row["dp"] - min(r["dp"] for r in subset_tv)) < 1e-12], key=lambda row: row["z_m"])
        ax.plot([row["pore_theory_norm"] for row in theory], [row["z_over_h"] for row in theory],
                "k--", lw=1.2, label="Terzaghi")
        ax.set_title(f"Tv={tv:g}")
        ax.set_xlabel("excess pore pressure / q0")
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("z/H")
    axes[-1].legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_l2(path, rows):
    fig, ax = plt.subplots(figsize=(5.4, 4.3))
    markers = ["o", "x", "s", "^", "D"]
    all_dps = []
    for idx, tv in enumerate(L2_PLOT_TV):
        subset = sorted([row for row in rows if abs(row["target_tv"] - tv) < 1e-12], key=lambda row: row["dp"])
        if not subset:
            continue
        dps = [row["dp"] / pp.H for row in subset]
        errs = [row["normalized_l2_error"] for row in subset]
        all_dps.extend(dps)
        ax.loglog(
            dps,
            errs,
            marker=markers[idx % len(markers)],
            ls="-",
            color="black",
            mfc="white",
            mew=1.4,
            label=f"Calculated Tv={tv:g}",
        )
    if len(all_dps) >= 2:
        # These are absolute order thresholds on the normalized grid
        # spacing, not arbitrarily shifted visual slope guides.
        xs = [min(all_dps), max(all_dps)]
        ax.loglog(xs, xs, "k--", lw=1.1, label="First order: error=dp/H")
        ax.loglog(xs, [x * x for x in xs], "k-", lw=1.1, label="Second order: error=(dp/H)^2")
    ax.set_title("Normalized L2 error")
    ax.set_xlabel("dp/H")
    ax.set_ylabel("Normalized L2 norm error")
    ax.set_ylim(bottom=1e-4, top=0.1)
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "summarize"])
    parser.add_argument("--prefix", default="resolution_k1em4")
    parser.add_argument("--figdir", default=str(FIGDIR))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare_cases()
    else:
        summarize_cases(args.prefix, Path(args.figdir))


if __name__ == "__main__":
    main()
