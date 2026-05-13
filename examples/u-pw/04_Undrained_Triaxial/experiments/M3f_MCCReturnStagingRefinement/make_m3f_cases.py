#!/usr/bin/env python3
"""Generate M3f MCC return/staging robustness XML/BAT cases."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BASE_XML = ROOT.parent / "M3d3_MCCSubstepping" / "CaseM3d3_MCCMildBaseline_Def.xml"

CASES = {
    "CaseM3f_MCCMildBaseline": {
        "description": "M3f original-rate mild MCC baseline, no substepping",
        "time_max": "0.018",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "ramp": False,
        "substepping": "0",
        "max_substeps": "1",
        "min_substeps": "1",
        "mode": "0",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "0",
        "fallback": "0",
    },
    "CaseM3f_MCCMildRampCurrentAdaptive": {
        "description": "M3f smoother platen ramp with current adaptive-on-failure MCC substepping",
        "time_max": "0.020",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "ramp": True,
        "ramp_duration": "0.004",
        "constant_duration": "0.016",
        "substepping": "1",
        "max_substeps": "16",
        "min_substeps": "1",
        "mode": "1",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "1",
        "fallback": "0",
    },
    "CaseM3f_MCCMildImprovedAdaptive": {
        "description": "M3f original-rate mild MCC with strain/yield-distance proactive adaptive substepping",
        "time_max": "0.018",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "ramp": False,
        "substepping": "1",
        "max_substeps": "32",
        "min_substeps": "4",
        "mode": "2",
        "strain_threshold": "5e-7",
        "yield_threshold": "0.02",
        "guard": "1",
        "fallback": "0",
    },
    "CaseM3f_MCCMildRampImprovedAdaptive": {
        "description": "M3f smoother platen ramp with proactive adaptive MCC substepping",
        "time_max": "0.020",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "ramp": True,
        "ramp_duration": "0.004",
        "constant_duration": "0.016",
        "substepping": "1",
        "max_substeps": "32",
        "min_substeps": "4",
        "mode": "2",
        "strain_threshold": "5e-7",
        "yield_threshold": "0.02",
        "guard": "1",
        "fallback": "0",
    },
    "CaseM3f_MCCMildHalfSpeedAdaptiveRef": {
        "description": "M3f half-speed adaptive-on-failure reference",
        "time_max": "0.036",
        "time_out": "0.001",
        "velocity_z": "-0.0025",
        "ramp": False,
        "substepping": "1",
        "max_substeps": "16",
        "min_substeps": "1",
        "mode": "1",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "1",
        "fallback": "0",
    },
    "CaseM3f_MCCMildHalfSpeedRampAdaptive": {
        "description": "M3f half-speed smooth-ramp adaptive-on-failure clean-candidate check",
        "time_max": "0.039",
        "time_out": "0.001",
        "velocity_z": "-0.0025",
        "ramp": True,
        "ramp_duration": "0.006",
        "constant_duration": "0.033",
        "substepping": "1",
        "max_substeps": "16",
        "min_substeps": "1",
        "mode": "1",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "1",
        "fallback": "0",
    },
    "CaseM3f_MCCMildQuarterSpeedAdaptiveRef": {
        "description": "M3f quarter-speed adaptive-on-failure strain-increment diagnostic",
        "time_max": "0.072",
        "time_out": "0.002",
        "velocity_z": "-0.00125",
        "ramp": False,
        "substepping": "1",
        "max_substeps": "16",
        "min_substeps": "1",
        "mode": "1",
        "strain_threshold": "0",
        "yield_threshold": "0",
        "guard": "1",
        "fallback": "0",
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
    if cfg["ramp"]:
        ramp_duration = float(str(cfg["ramp_duration"]))
        velocity = float(str(cfg["velocity_z"]))
        ace = velocity / ramp_duration
        mvace = ET.SubElement(obj, "mvrectace")
        mvace.set("id", "1")
        mvace.set("duration", str(cfg["ramp_duration"]))
        mvace.set("next", "2")
        velini = ET.SubElement(mvace, "velini")
        velini.set("x", "0")
        velini.set("y", "0")
        velini.set("z", "0")
        ace_node = ET.SubElement(mvace, "ace")
        ace_node.set("x", "0")
        ace_node.set("y", "0")
        ace_node.set("z", f"{ace:.12g}")
        mvrect = ET.SubElement(obj, "mvrect")
        mvrect.set("id", "2")
        mvrect.set("duration", str(cfg["constant_duration"]))
    else:
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
        f"echo M3f CPU Release completed for {case_name}.\n"
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
        set_soil_param(soils, "MccFailureFallback", str(cfg["fallback"]))
        update_motion(root, cfg)
        indent(root)
        tree.write(ROOT / f"{case_name}_Def.xml", encoding="utf-8", xml_declaration=True)
        write_bat(case_name)

    (ROOT / "README.md").write_text(
        "# M3f MCC Return/Staging Refinement\n\n"
        "Generated cases compare original-rate mild MCC, smoother platen ramping, and "
        "proactive adaptive MCC substepping. All cases keep PorePressureFeedback=0 and "
        "do not use fallback as a clean validation route.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
