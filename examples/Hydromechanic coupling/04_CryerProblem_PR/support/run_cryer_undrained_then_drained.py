from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import run_cryer_refinement as rr


ROOT = Path(__file__).resolve().parent.parent
CASE = "CaseCryerProblem_PR"
WORKROOT = ROOT / "refinement" / "ud2"


def set_value(root, xpath, value):
    node = root.find(xpath)
    if node is None:
        raise RuntimeError(f"XML node not found: {xpath}")
    node.set("value", str(value))


def set_comment(root, xpath, text):
    node = root.find(xpath)
    if node is None:
        raise RuntimeError(f"XML node not found: {xpath}")
    node.set("comment", text)


def ensure_soil_value(root, name, value, comment=None):
    soils = root.find(".//soils")
    if soils is None:
        raise RuntimeError("XML soils node not found")
    node = soils.find(name)
    if node is None:
        node = ET.SubElement(soils, name)
    node.set("value", str(value))
    if comment is not None:
        node.set("comment", comment)


def ensure_soil_double3(root, name, xyz, comment=None):
    soils = root.find(".//soils")
    if soils is None:
        raise RuntimeError("XML soils node not found")
    node = soils.find(name)
    if node is None:
        node = ET.SubElement(soils, name)
    node.set("x", str(xyz[0]))
    node.set("y", str(xyz[1]))
    node.set("z", str(xyz[2]))
    if comment is not None:
        node.set("comment", comment)


def remove_soil_value(root, name):
    soils = root.find(".//soils")
    if soils is None:
        raise RuntimeError("XML soils node not found")
    node = soils.find(name)
    if node is not None:
        soils.remove(node)


def set_newvar(root, name, value):
    for node in root.findall(".//newvarcte"):
        if node.get("name") == name:
            node.set("value", str(value))
            return
        if name in node.attrib:
            node.set(name, str(value))
            return
    raise RuntimeError(f"newvarcte not found: {name}")


def write_stage_xml(dst, cfg, stage):
    tree = ET.parse(rr.BASE_XML)
    root = tree.getroot()

    set_newvar(root, "Dp", cfg["dp"])
    set_newvar(root, "radius", cfg["radius"])

    ensure_soil_value(
        root,
        "HydroMechInitMode",
        0,
        "HydroMechInitMode values: 0=None, 1=FreeSurface, 2=ConstantZ, 3=AnalyticalSelfWeight1D; Cryer two-stage verification uses 0=None",
    )
    ensure_soil_double3(root, "HydroMechSphereCenter", (0, 0, 0), "Shared sphere center for radial load and spherical drainage")
    ensure_soil_value(root, "HydroMechTopLoad", 1, "Apply sustained spherical normal pressure p0")
    ensure_soil_value(root, "HydroMechTopLoadMode", 3, "HydroMechTopLoadMode values: 0=None, 1=TopVertical, 2=SphereNormal, 3=FlexibleConfinement; Cryer uses 3=FlexibleConfinement")
    ensure_soil_value(root, "HydroMechTopLoadQ0", cfg["q0"], "Compressive spherical surface pressure p0")
    set_value(root, ".//HydroMechTopLoadRampTime", cfg["load_ramp"])
    set_comment(root, ".//HydroMechTopLoadRampTime", "Ramp duration for the undrained loading stage")
    ensure_soil_value(root, "HydroMechDrainageMode", "FreeSurface", "Drain tracked free-surface particles on Cryer's exterior")
    remove_soil_value(root, "HydroMechDrainageRadius")
    remove_soil_value(root, "HydroMechDrainageThickness")
    set_value(root, ".//PoreDtSafety", cfg["pore_dt"])
    set_value(root, ".//PoreShepardRegularization", cfg["shepard"])
    set_value(root, ".//PoreShepardInterval", cfg["shepard_interval"])
    set_value(root, ".//PRvs", cfg["nu"])
    set_value(root, ".//ModulusE", cfg["e"])
    set_value(root, ".//parameter[@key='SoilDampingCoef']", cfg["damping"])
    set_value(root, ".//parameter[@key='Visco']", cfg["visco"])
    set_value(root, ".//parameter[@key='ShiftTFS']", cfg["shift_tfs"])
    set_value(root, ".//parameter[@key='DtIni']", cfg["dt"])
    set_value(root, ".//parameter[@key='DtFixed']", cfg["dt"])
    set_value(root, ".//parameter[@key='DtMin']", min(1e-8, cfg["dt"] / 100.0))
    set_value(root, ".//parameter[@key='TimeOut']", cfg["tout"])

    if stage == 1:
        ensure_soil_value(root, "HydraulicConductivity", 0.0, "Stage 1 is undrained: no pore-water diffusion before drainage opens")
        ensure_soil_value(root, "HydroMechDrainage", 1, "Stage 1 keeps the spherical surface undrained by delaying the drainage start time")
        set_value(root, ".//HydroMechDrainageStartTime", cfg["stage1_time"] + cfg["drain_duration"])
        set_value(root, ".//parameter[@key='TimeMax']", cfg["stage1_time"])
    elif stage == 2:
        ensure_soil_value(root, "HydraulicConductivity", cfg["khyd"], "Stage 2 restores hydraulic conductivity for Cryer drainage")
        ensure_soil_value(root, "HydroMechDrainage", 1, "Stage 2 opens the spherical drained boundary")
        set_value(root, ".//HydroMechDrainageStartTime", cfg["stage1_time"])
        set_comment(root, ".//HydroMechDrainageStartTime", "Drainage starts at the restart time; this is the analytical time origin")
        set_value(root, ".//parameter[@key='TimeMax']", cfg["stage1_time"] + cfg["drain_duration"])
    else:
        raise RuntimeError(f"Unknown stage: {stage}")

    tree.write(dst, encoding="UTF-8", xml_declaration=True)


def run_postprocess(particles, figdir, tag, cfg, summary_json):
    env = os.environ.copy()
    env.update({
        "CRYER_PARTICLES": str(particles),
        "CRYER_FIGDIR": str(figdir),
        "CRYER_OUTTAG": tag,
        "CRYER_SUMMARY_JSON": str(summary_json),
        "CRYER_RADIUS": str(cfg["radius"]),
        "CRYER_DP": str(cfg["dp"]),
        "CRYER_Q0": str(cfg["q0"]),
        "CRYER_TL": str(cfg["stage1_time"]),
        "CRYER_LOAD_RAMP": str(cfg["load_ramp"]),
        "CRYER_E": str(cfg["e"]),
        "CRYER_NU": str(cfg["nu"]),
        "CRYER_K_HYD": str(cfg["khyd"]),
        "CRYER_TOUT": str(cfg["tout"]),
        "CRYER_TIME_MAX": str(cfg["stage1_time"] + cfg["drain_duration"]),
    })
    with (figdir / f"{tag}_postprocess_stdout.log").open("w") as out, (figdir / f"{tag}_postprocess_stderr.log").open("w") as err:
        code = subprocess.call([sys.executable, str(ROOT / "support" / "postprocess_cryer.py")], cwd=str(ROOT), env=env, stdout=out, stderr=err)
    if code != 0:
        raise RuntimeError(f"Postprocess failed for {tag}")


def run_solver(stage_dir, solver, device_arg, tmax, tout, support_dir, partbegin=None):
    outdir = stage_dir / f"{CASE}_out"
    data = outdir / "data"
    runout = outdir / "Run.out"
    args = [
        solver,
        device_arg,
        f"{CASE}_out/{CASE}",
        f"{CASE}_out",
        "-dirdataout",
        "data",
        "-svres",
        "-svextraparts:1",
        f"-tmax:{tmax}",
        f"-tout:{tout}",
    ]
    if partbegin is not None:
        begin, begin_dir = partbegin
        args.extend([f"-partbegin:{begin}", str(begin_dir)])
    rr.run_process(args, stage_dir, support_dir / "solver_stdout.log", support_dir / "solver_stderr.log", runout)
    return outdir, data


def run_stage(stage_dir, cfg, stage, solver, device_arg, partbegin=None):
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)
    support = stage_dir / "support"
    support.mkdir()
    write_stage_xml(stage_dir / f"{CASE}_Def.xml", cfg, stage)
    rr.run_process([rr.GENCASE, f"{CASE}_Def", f"{CASE}_out/{CASE}", "-save:all"], stage_dir, support / "gencase_stdout.log", support / "gencase_stderr.log")
    tmax = cfg["stage1_time"] if stage == 1 else cfg["stage1_time"] + cfg["drain_duration"]
    outdir, data = run_solver(stage_dir, solver, device_arg, tmax, cfg["tout"], support, partbegin)
    particles = outdir / "particles"
    rr.run_process([rr.PARTVTK, "-dirin", data, "-savevtk", particles / "PartFluid", "-onlytype:-bound", f"-vars:{rr.VARS}"],
                   stage_dir, support / "partvtk_stdout.log", support / "partvtk_stderr.log")
    return outdir, data, particles


def latest_part_index(data_dir):
    parts = sorted(data_dir.glob("Part_*.bi4"))
    if not parts:
        raise RuntimeError(f"No PART files in {data_dir}")
    return int(parts[-1].stem.split("_")[-1])


def main():
    cfg = {
        "name": "dp0100_t040",
        "radius": 0.05,
        "dp": 0.01,
        "q0": 10000.0,
        "e": 2.0e6,
        "nu": 0.3,
        "khyd": 1.0e-3,
        "pore_dt": 0.1,
        "shepard": 0,
        "shepard_interval": 30,
        "load_ramp": 0.005,
        "stage1_time": 0.04,
        "drain_duration": 0.005,
        "tout": 0.0001,
        "dt": 0.000001,
        "damping": 0.2,
        "visco": 0.1,
        "shift_tfs": 2.75,
        "use_gpu": False,
    }

    work = WORKROOT / cfg["name"]
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    solver = rr.DUAL_RELEASE if rr.DUAL_RELEASE.exists() else rr.DUAL_DEBUG
    device_arg = "-cpu"

    stage1 = work / "s1"
    stage2 = work / "s2"
    figdir = work / "figures"
    figdir.mkdir()

    print(f"Running Stage 1 undrained loading in {stage1}", flush=True)
    stage1_out, stage1_data, stage1_particles = run_stage(stage1, cfg, 1, solver, device_arg)
    partbegin = latest_part_index(stage1_data)

    run_postprocess(stage1_particles, figdir, f"{cfg['name']}_stage1", cfg, figdir / "stage1_summary.json")
    stage1_summary = json.loads((figdir / "stage1_summary.json").read_text())
    print(
        "Stage 1 restart candidate: "
        f"Part_{partbegin:04d}, p_center/p0={stage1_summary['load_end_num']:.6g}, "
        f"max_speed={stage1_summary['max_speed']:.6g}",
        flush=True,
    )

    print(f"Running Stage 2 drained restart in {stage2}", flush=True)
    stage2_out, stage2_data, stage2_particles = run_stage(stage2, cfg, 2, solver, device_arg, (partbegin, stage1_data))
    run_postprocess(stage2_particles, figdir, cfg["name"], cfg, figdir / "summary.json")
    summary = json.loads((figdir / "summary.json").read_text())
    summary.update({
        "stage1_partbegin": partbegin,
        "stage1_out": str(stage1_out),
        "stage2_out": str(stage2_out),
        "history_csv": str(figdir / f"{cfg['name']}.csv"),
        "history_png": str(figdir / f"{cfg['name']}.png"),
        "stage1_history_csv": str(figdir / f"{cfg['name']}_stage1.csv"),
        "stage1_history_png": str(figdir / f"{cfg['name']}_stage1.png"),
        "config": cfg,
    })
    (figdir / "two_stage_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Stage 2 load-start p_center/p0={summary['load_end_num']:.6g}")
    print(f"Stage 2 peak SPH={summary['peak_num']:.6g} at Tv={summary['peak_num_tv']:.6g}")
    print(f"Cryer theory peak={summary['peak_theory']:.6g} at Tv={summary['peak_theory_tv']:.6g}")
    print(f"Final SPH={summary['final_num']:.6g}, theory={summary['final_theory']:.6g}")
    print(f"Saved {figdir / (cfg['name'] + '.png')}")


if __name__ == "__main__":
    main()
