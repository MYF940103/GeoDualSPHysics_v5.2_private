"""Prepare small fixed-plane GenCase inputs; never launch a physical solver.

Default/--dry-run validates every XML in memory and prints the plan only.
--prepare writes fresh configurations, runs GenCase, and records hashes.
The candidate vector/slip combinations are not assumed to be supported.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
TEMPLATE = TESTS / "configs/CaseMdbcPlane_Def.xml"
GENCASE = REPO / "bin/windows/GenCase_win64.exe"
GEOMETRIES = {
    "2d_h": (2, 0., (0., 1., 0.)),
    "2d_v": (2, 90., (0., 1., 0.)),
    "2d_t": (2, 30., (0., 1., 0.)),
    "3d_h": (3, 0., (0., 1., 0.)),
    "3d_t": (3, 30., (0., 1., 0.)),
    "3d_o": (3, 30., (1., 1., 0.)),
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def hashed(path):
    path = Path(path)
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def number(value):
    return format(0. if abs(value) < 1e-15 else value, ".17g")


def rotate_matrix(axis, angle):
    norm = math.sqrt(sum(v*v for v in axis))
    x, y, z = (v/norm for v in axis)
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    d = 1.-c
    return [[c+x*x*d, x*y*d-z*s, x*z*d+y*s],
            [y*x*d+z*s, c+y*y*d, y*z*d-x*s],
            [z*x*d-y*s, z*y*d+x*s, c+z*z*d]]


def render(geometry, slip):
    dimension, angle, axis = GEOMETRIES[geometry]
    root = ET.fromstring(TEMPLATE.read_text(encoding="utf-8"),
                         parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    definition = root.find("casedef/geometry/definition")
    definition.find("pointmin").set("y", "-0.295" if dimension == 3 else "0")
    definition.find("pointmax").set("y", "0.295" if dimension == 3 else "0")
    for box in root.findall("casedef/geometry/commands/mainlist/drawbox"):
        box.find("point").set("y", "-0.075" if dimension == 3 else "0")
        box.find("size").set("y", "0.15" if dimension == 3 else "0")
    for item in root.findall("casedef/initials/rotateaxis"):
        # GenCase rotateaxis uses the opposite sign to the right-handed
        # Rodrigues matrix recorded below (verified with the 90-degree patch).
        item.set("angle", number(-angle))
        for k, value in zip("xyz", axis):
            item.find("axisp2").set(k, number(value))
    rotation = rotate_matrix(axis, angle)
    normal = [float(number(row[2])) for row in rotation]
    plane = root.find("execution/special/initialize/boundnormal_plane")
    for k, value in zip("xyz", normal):
        plane.find("normal").set(k, number(value))
    parameters = {p.get("key"): p for p in root.findall("execution/parameters/parameter")}
    parameters["SlipMode"].set("value", str(slip))
    parameters["DPCtes"].set("value", "1" if dimension == 3 else "3")
    required = {"Boundary": "2", "StepAlgorithm": "2", "Kernel": "2", "NoPenetration": "0",
                "SoilHourglassXi": "0", "SoilDamping": "0", "Shifting": "0", "DensityDT": "0",
                "SoilStressRateGradCorr": "1", "SoilBoundaryDerivativeSPR": "1"}
    if any(parameters[k].get("value") != value for k, value in required.items()):
        raise ValueError("Template changed the declared manufactured-field controls")
    if any("Periodic" in key for key in parameters):
        raise ValueError("Fixed-plane fixtures must not enable periodicity")
    hydro = root.find("execution/special/hydromechanics")
    for key, value in {"HydroMechTopLoadMode": "0", "HydroMechTopLoadQ0": "0", "HydroMechDrainage": "0",
                       "PoreCompressionSourceMode": "PairDivergence", "PoreCompressionGradCorr": "1"}.items():
        if hydro.find(key).get("value") != value:
            raise ValueError("Template changed hydro control: " + key)
    # Verify declared GenCase bounds enclose the rotated patch plus >=2h.
    corners = product((-.075, .075), ((-.075, .075) if dimension == 3 else (0.,)), (-.025, .095))
    rotated = [[sum(row[j]*point[j] for j in range(3)) for row in rotation] for point in corners]
    margins = []
    for j, k in enumerate("xyz"):
        low, high = float(definition.find("pointmin").get(k)), float(definition.find("pointmax").get(k))
        if dimension == 2 and k == "y":
            if any(abs(p[j]) > 1e-14 for p in rotated):
                raise ValueError("2D rotation leaves the x-z plane")
        else:
            margins.append(min(min(p[j] for p in rotated)-low, high-max(p[j] for p in rotated)))
    if min(margins) <= .036:
        raise ValueError("GenCase definition does not include 2h rotation margin")
    ET.indent(root, space="  ")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
    ET.fromstring(xml)  # All variant documents are checked before any file write.
    walls, soil = (48, 160) if dimension == 2 else (768, 2560)
    info = dict(geometry=geometry, dimension=dimension, angle_deg=angle, axis=list(axis),
                normal=normal, rotation=rotation, slip_mode=slip, native_count=walls+soil,
                wall_count=walls, soil_count=soil, wall_roi_count=(24 if dimension == 2 else 192),
                roi_local_tangent_abs_max_m=.035, nearest_side_clearance_m=.04,
                dp_m=.01, h_m=.018, support_m=.036, definition_margin_min_m=min(margins))
    return xml, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="mdbc_plane_r1")
    parser.add_argument("--geometry", nargs="+", choices=GEOMETRIES, default=list(GEOMETRIES))
    parser.add_argument("--slip", nargs="+", type=int, choices=(1, 2, 3), default=[1, 2, 3])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"mdbc_plane[A-Za-z0-9_-]*", args.tag):
        raise ValueError("Tag must start with mdbc_plane and contain only safe label characters")
    if len(set(args.geometry)) != len(args.geometry) or len(set(args.slip)) != len(args.slip):
        raise ValueError("Duplicate variants are not admitted")
    variants = []
    for geometry, slip in product(args.geometry, args.slip):
        xml, info = render(geometry, slip)
        label = f"{args.tag}_{geometry}_s{slip}"
        name = "CaseMdbcPlane_" + label
        definition = TESTS / "configs" / (name + "_Def.xml")
        output = TESTS / "outputs" / (label + "_input")
        prefix = output / name
        log = TESTS / "logs" / (label + ".gencase.log")
        info.update(label=label, definition=str(definition), output=str(output), prefix=str(prefix), log=str(log))
        variants.append((xml, info))
    receipt = TESTS / "logs" / (args.tag + ".prepare.json")
    plan = dict(status="dry_run_inputs_only", tag=args.tag, created_utc=stamp(),
                template=hashed(TEMPLATE), script=hashed(Path(__file__).resolve()),
                variants=[v for _, v in variants], xml_documents_validated=len(variants),
                normals="production boundnormal_plane initializer; no handwritten NBI4",
                solver_started=False, physical_accuracy_accepted=False,
                limitations="Candidate vector modes require separate production support and manufactured-field validation")
    if not args.prepare:
        brief = {key: plan[key] for key in ("status", "tag", "xml_documents_validated", "solver_started", "physical_accuracy_accepted")}
        brief["variants"] = [{key: item[key] for key in ("geometry", "slip_mode", "native_count", "wall_count",
                                                        "soil_count", "wall_roi_count", "normal", "definition_margin_min_m")}
                             for _, item in variants]
        print(json.dumps(brief, indent=2))
        return
    targets = [receipt]
    for _, item in variants:
        targets.extend(Path(item[key]) for key in ("definition", "output", "log"))
    for path in targets:
        if path.exists():
            raise FileExistsError("Refusing overwrite: " + str(path))
    plan.update(status="preparing_gencase_only", gencase=hashed(GENCASE), runs=[])
    try:
        for xml, item in variants:
            definition, output, prefix, log = (Path(item[k]) for k in ("definition", "output", "prefix", "log"))
            with definition.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(xml)
            output.mkdir()
            command = [str(GENCASE), str(definition.with_suffix("")), str(prefix), "-save:all"]
            run = dict(label=item["label"], command=command, started_utc=stamp(), definition=hashed(definition))
            plan["runs"].append(run)
            with log.open("x", encoding="utf-8") as stream:
                result = subprocess.run(command, cwd=TESTS / "configs", stdout=stream, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
            run.update(exit_code=result.returncode, finished_utc=stamp(), log=hashed(log),
                       outputs=[hashed(p) for p in sorted(output.rglob("*")) if p.is_file()])
            if result.returncode:
                raise RuntimeError(f"GenCase failed for {item['label']}; see {log}")
            for extension in (".xml", ".bi4"):
                if not prefix.with_suffix(extension).is_file():
                    raise RuntimeError("Missing required GenCase output: " + str(prefix.with_suffix(extension)))
            particles = ET.parse(prefix.with_suffix(".xml")).getroot().find("execution/particles")
            if particles is None or int(particles.get("np")) != item["native_count"] or int(particles.get("nb")) != item["wall_count"]:
                raise RuntimeError("GenCase native particle counts differ from the declared grid")
        plan["status"] = "gencase_prepared_not_solver_validated"
    except Exception as error:
        plan.update(status="preparation_failed", failure=str(error))
        raise
    finally:
        plan["finished_utc"] = stamp()
        with receipt.open("x", encoding="utf-8") as stream:
            json.dump(plan, stream, indent=2)
            stream.write("\n")
    print(json.dumps(dict(status=plan["status"], variants=len(variants), manifest=str(receipt)), indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
