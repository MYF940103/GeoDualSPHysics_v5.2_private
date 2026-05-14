#!/usr/bin/env python3
"""Generate M3h MCC admissible return XML/BAT cases."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BASE_XML = ROOT.parent / "M3f_MCCReturnStagingRefinement" / "CaseM3f_MCCMildBaseline_Def.xml"

CASES: dict[str, dict[str, Any]] = {
    "CaseM3h_MCCMildBaseline": {
        "description": "M3h original-rate mild MCC baseline, old line-search",
        "time_max": "0.018",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "substepping": "0",
        "max_substeps": "1",
        "min_substeps": "1",
        "mode": "0",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "0",
        "line": "0",
    },
    "CaseM3h_MCCMildAdmissibleLine": {
        "description": "M3h original-rate mild MCC with admissible line-search",
        "time_max": "0.018",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "substepping": "0",
        "max_substeps": "1",
        "min_substeps": "1",
        "mode": "0",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "1",
        "line": "1",
    },
    "CaseM3h_MCCMildAdaptiveLine": {
        "description": "M3h original-rate mild MCC with adaptive substepping and admissible line-search",
        "time_max": "0.018",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "substepping": "1",
        "max_substeps": "16",
        "min_substeps": "1",
        "mode": "1",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "1",
        "line": "1",
    },
    "CaseM3h_MCCMildHalfSpeedAdaptiveLine": {
        "description": "M3h half-speed mild MCC with adaptive substepping and admissible line-search",
        "time_max": "0.036",
        "time_out": "0.001",
        "velocity_z": "-0.0025",
        "substepping": "1",
        "max_substeps": "16",
        "min_substeps": "1",
        "mode": "1",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "1",
        "line": "1",
    },
    "CaseM3h_MCCMildQuarterSpeedLine": {
        "description": "M3h quarter-speed mild MCC with admissible line-search diagnostic",
        "time_max": "0.072",
        "time_out": "0.002",
        "velocity_z": "-0.00125",
        "substepping": "1",
        "max_substeps": "16",
        "min_substeps": "1",
        "mode": "1",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "1",
        "line": "1",
    },
}


def indent(elem: ET.Element, level: int = 0) -> None:
    pad = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = pad + "  "
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = pad
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = pad


def find_required(root: ET.Element, path: str) -> ET.Element:
    node = root.find(path)
    if node is None:
        raise RuntimeError(f"Missing XML node: {path}")
    return node


def set_parameter(params: ET.Element, key: str, value: str) -> None:
    for node in params.findall("parameter"):
        if node.get("key") == key:
            node.set("value", value)
            return
    node = ET.SubElement(params, "parameter")
    node.set("key", key)
    node.set("value", value)


def set_soil_param(soils: ET.Element, name: str, value: str) -> None:
    node = soils.find(name)
    if node is None:
        node = ET.SubElement(soils, name)
    node.set("value", value)


def update_motion(root: ET.Element, cfg: dict[str, Any]) -> None:
    obj = find_required(root, "./casedef/motion/objreal")
    for child in list(obj):
        obj.remove(child)
    begin = ET.SubElement(obj, "begin")
    begin.set("mov", "1")
    begin.set("start", "0")
    begin.set("finish", str(cfg["time_max"]))
    mvrect = ET.SubElement(obj, "mvrect")
    mvrect.set("id", "1")
    mvrect.set("duration", str(cfg["time_max"]))
    vel = ET.SubElement(mvrect, "vel")
    vel.set("x", "0")
    vel.set("y", "0")
    vel.set("z", str(cfg["velocity_z"]))
    vel.set("units_comment", "m/s")


def write_bat(case_name: str) -> None:
    bat = ROOT / f"xRun_{case_name}_win64_CPU_release.bat"
    bat.write_text(
        "@echo off\n"
        "setlocal\n"
        "set dirbin=..\\..\\..\\..\\..\\bin\\windows\n"
        "set gencase=\"%dirbin%\\GenCase_win64.exe\"\n"
        "set dualsphysicscpu=\"%dirbin%\\DualSPHysics5.2CPU_win64.exe\"\n"
        f"set name={case_name}\n"
        "set dirout=%name%_out\n"
        "if exist %dirout% rd /s /q %dirout%\n"
        "%gencase% %name%_Def %dirout%\\%name% -save:all\n"
        "if not \"%ERRORLEVEL%\" == \"0\" exit /b 1\n"
        "%dualsphysicscpu% -cpu %dirout%\\%name% %dirout% -dirdataout data -sv:csv,binx -svres\n"
        "if not \"%ERRORLEVEL%\" == \"0\" exit /b 1\n"
        f"echo M3h CPU Release completed for {case_name}.\n"
        "exit /b 0\n",
        encoding="utf-8",
    )


def main() -> None:
    for case_name, cfg in CASES.items():
        tree = ET.parse(BASE_XML)
        root = tree.getroot()
        root.set("date", str(cfg["description"]))
        params = find_required(root, "./execution/parameters")
        set_parameter(params, "TimeMax", str(cfg["time_max"]))
        set_parameter(params, "TimeOut", str(cfg["time_out"]))
        soils = find_required(root, "./execution/special/soils")
        set_soil_param(soils, "MccReturnTolerance", "1e-8")
        set_soil_param(soils, "MccReturnMaxIter", "45")
        set_soil_param(soils, "MccSubstepping", str(cfg["substepping"]))
        set_soil_param(soils, "MccMaxSubsteps", str(cfg["max_substeps"]))
        set_soil_param(soils, "MccMinSubsteps", str(cfg["min_substeps"]))
        set_soil_param(soils, "MccSubstepMode", str(cfg["mode"]))
        set_soil_param(soils, "MccSubstepStrainThreshold", str(cfg["strain_threshold"]))
        set_soil_param(soils, "MccSubstepYieldDistanceThreshold", str(cfg["yield_threshold"]))
        set_soil_param(soils, "MccAdmissibilityGuard", str(cfg["guard"]))
        set_soil_param(soils, "MccFailureFallback", "0")
        set_soil_param(soils, "MccAdmissibleLineSearch", str(cfg["line"]))
        set_soil_param(soils, "MccLineSearchMaxBacktrack", "32")
        set_soil_param(soils, "MccLineSearchMinStep", "1e-12")
        set_soil_param(soils, "MccLineSearchResidualReduction", "0")
        set_soil_param(soils, "MccEnforcePositivePlasticMultiplier", "1")
        set_soil_param(soils, "MccAdmissibleProjection", "1")
        update_motion(root, cfg)
        indent(root)
        tree.write(ROOT / f"{case_name}_Def.xml", encoding="utf-8", xml_declaration=True)
        write_bat(case_name)

    (ROOT / "README.md").write_text(
        "# M3h MCC Admissible Return\n\n"
        "CPU-only feedback-off MCC cases for admissible Newton / line-search diagnostics. "
        "Fallback remains disabled in validation candidates.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
