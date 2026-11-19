"""Exercise public case generators and plotting inputs, including returned server XML."""
from importlib import import_module
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from drainage_case_matrix import BASE, options, parse, require


def check_missing_release(case, work):
    results = {}
    for stage in ("Stage1", "Scenario2"):
        src = case / f"xCaseSelfWeightConsolidation_{stage}_win64_GPU.bat"
        folder = work / "empty_distribution/examples/hydro" / stage
        folder.mkdir(parents=True)
        script = folder / src.name
        shutil.copyfile(src, script)
        require(not (folder / "../../../bin/windows").resolve().exists(), "Expected no solver for this test")
        if stage == "Scenario2":
            prereq = folder / "CaseSelfWeightConsolidation_Stage1_out/data"
            prereq.mkdir(parents=True)
            for prefix in ("Part_", "PartExtra_"):
                (prereq / (prefix+"0060.bi4")).touch()
        output = folder / f"CaseSelfWeightConsolidation_{stage}_out"
        output.mkdir()
        sentinel = output / "retained.txt"
        sentinel.write_bytes(b"retained")
        run = subprocess.run(["cmd.exe","/d","/c",script.name,"-force"], cwd=folder, capture_output=True)
        require(run.returncode == 1 and b"Required public GPU Release" in run.stdout and
                sentinel.read_bytes() == b"retained", f"Unsafe missing-program handling for {script.name}")
        results[src.name] = "exit 1 before modifying prior output"
    return results


def main(tag):
    column, cryer, slope = (next(BASE.glob(n + "_*")) for n in ("02","04","07"))
    tests = cryer / "tests"
    matrix = tests / "outputs/drainage_public_roots_r1"
    work = tests / "outputs" / tag
    work.mkdir(parents=True, exist_ok=False)
    for case in (column, cryer, slope):
        sys.path.insert(0, str(case / "support"))
    from compare_precision_q0 import special_settings, drainage_start
    from release_case import model
    from plot_cryer_formal_four_nu_r1 import GROUPS, parameters
    from prepare_case import make_xml

    bats = check_missing_release(next(BASE.glob("01_*")),work)

    columns = {}
    for p in sorted((matrix / "02").iterdir()):
        old, new = [p / label / "Case.xml" for label in ("previous","current")]
        require(model(old) == model(new), f"C02 release postprocessor changed for {p.name}")
        require(special_settings(ET.parse(old)) == special_settings(ET.parse(new)), p.name)
        columns[p.name] = drainage_start(ET.parse(new))
    # Detect genuine fixed-step vs time-clock changes despite equivalent XML spellings being allowed.
    old = ET.parse(matrix / "02/CaseTerzaghiConsolidation_q0_PR_full_k1em4_Def/previous/Case.xml")
    new = ET.parse(matrix / "02/CaseTerzaghiConsolidation_q0_PR_full_k1em4_Def/current/Case.xml")
    new.find("execution/special/drainage").set("clock", "time")
    require(special_settings(old) != special_settings(new), "C02 clock difference hidden")
    retained = {}
    for run in ("CaseTerzaghiConsolidation_q0_PR_full_k1em3_release_GPU_out",
                "CaseTerzaghiConsolidation_q0_PR_full_k1em4_release_GPU_out",
                "CaseTerzaghiConsolidation_q0_PR_full_k5em5_release_CPU_uniform_out"):
        xml, = (column/run).glob("*.xml")
        values = model(xml)
        require(values["tD"] == .01 and values["q0"] == 10000, xml)
        retained[run] = dict(xml=xml.name, drainage_start=values["tD"], q0=values["q0"])

    groups = {}
    for _group, nu, stem, _steps in GROUPS:
        folder = cryer / (stem+"_out")
        archived = parameters(folder, stem, nu)
        # Current-schema mirror of the saved XML, restricted to the options consumed by this plot.
        root = ET.parse(folder / (stem+".xml"))
        special = root.find("execution/special")
        hydro = special.find("hydromechanics")
        load = ET.SubElement(special, "externalload")
        for oldname, attr in (("Mode","mode"),("Q0","q0"),("RampTime","ramptime")):
            el = hydro.find("HydroMechTopLoad"+oldname)
            load.set(attr, el.attrib["value"])
            hydro.remove(el)
        start = hydro.find("HydroMechDrainageStartTime").attrib["value"]
        for key in ("HydroMechDrainage","HydroMechDrainageStartTime","HydroMechDrainageFixedGrid"):
            hydro.remove(hydro.find(key))
        ET.SubElement(special,"drainage",mode="drained",start=start,clock="fixedStep")
        root.write(work / (stem+".xml"), encoding="utf-8")
        mirrored = parameters(work, stem, nu)
        require({k:v for k,v in archived.items() if k != "runtime"} ==
                {k:v for k,v in mirrored.items() if k != "runtime"}, stem)
        groups[stem] = dict(nu=nu, drainage_start=float(start), clock="fixedStep")

    fieldplot = import_module("plot_cryer_poisson_sweep_dp002_rampclosed")
    sweeps = {}
    for p in sorted((matrix / "04").glob("*_dp002_rampclosed_*")):
        pars = []
        for label in ("previous","current"):
            fieldplot.ROOT = p / label
            pars.append(fieldplot.parse_xml("Case"))
        require(pars[0] == pars[1], "Cryer rampclosed plot clock changed")
        sweeps[p.name] = pars[1]["drainage_start"]

    cfg = dict(dp=.002, damping=.02, time_max=.01, tout=.001, drainage_start=.0025, ramp=.0025,
               drain_start=.0025, drainage_mode="FreeSurface", init_mode=0, load_ramp=.0025,
               pore_dt=.1, shepard=0, shepard_interval=30, shift_tfs=2.75, visco=.1, dt=1e-6,
               stage1_time=.02, drain_duration=.1, e=2e6, khyd=1e-5, nu=.3, q0=10000, radius=.05)
    jobs = [
        ("run_damping_sweep_20260622","write_xml", (), 0),
        ("run_k1e5_convergence_20260622","write_xml", (), 0),
        ("run_ramp_drain_closed_sweep_20260624","write_xml", (), cfg["drainage_start"]),
        ("run_cryer_refinement","write_variant_xml", (), cfg["drain_start"]),
        ("run_cryer_undrained_then_drained","write_stage_xml", (1,), cfg["stage1_time"]+cfg["drain_duration"]),
        ("run_cryer_undrained_then_drained","write_stage_xml", (2,), cfg["stage1_time"])]
    variants = {}
    for mod, fun, args, expected in jobs:
        label = mod + ("_stage"+str(args[0]) if args else "")
        output = work / (label+".xml")
        getattr(import_module(mod),fun)(output,cfg,*args)
        root = parse(output.read_bytes())
        require(options(root) == ["drained",expected,"time"], label)
        variants[label] = expected
    for stage in ("prestress","failure"):
        xml = make_xml(stage)
        require(options(parse(xml.encode())) == ["drained",0,"time"], stage)
        require(parse(xml.encode()).find("execution/special/drainage") is not None, stage)
        cfgpath = slope / f"CaseSelborne3D_u_pw_{stage}_Def.xml"
        require(xml.splitlines() == cfgpath.read_text(encoding="utf-8-sig").splitlines(), "Regeneration differs: "+stage)
    receipt = dict(column_model_and_signature=columns, retained_column_outputs=retained,
                   missing_release_bats=bats, server_xml_and_public_copies=groups,
                   cryer_ramp_profiles=sweeps, generated_variants=variants,
                   selborne_regenerated=["prestress","failure"], intentionally_changed_clock_detected=True,
                   solver_launches=0)
    with (tests / "logs" / (tag+".check.json")).open("x",encoding="utf-8") as f:
        json.dump(receipt,f,indent=2)
        f.write("\n")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--tag", required=True)
    tag = cli.parse_args().tag
    require(re.fullmatch(r"[A-Za-z0-9_]+", tag), "Invalid tag")
    main(tag)
