#!/usr/bin/env python3
"""Generate M3d2 MCC return-robustness diagnostic XML/BAT cases."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BASE_XML = ROOT.parent / "M3d_MCCFeedbackOffRefinement" / "CaseM3d_MCCMildYield_Extended_Def.xml"

CASES = {
    "CaseM3d2_MCCMildBaseline": {
        "description": "M3d2 mild MCC baseline rerun",
        "time_max": "0.018",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "tol": "1e-8",
        "max_iter": "45",
    },
    "CaseM3d2_MCCMildSlowerHalfVelocity": {
        "description": "M3d2 mild MCC half platen velocity same displacement",
        "time_max": "0.036",
        "time_out": "0.001",
        "velocity_z": "-0.0025",
        "tol": "1e-8",
        "max_iter": "45",
    },
    "CaseM3d2_MCCMildEarlyStop": {
        "description": "M3d2 mild MCC early stop before extended failures",
        "time_max": "0.006",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "tol": "1e-8",
        "max_iter": "45",
    },
    "CaseM3d2_MCCMildTightReturn": {
        "description": "M3d2 mild MCC tighter tolerance and higher max iterations",
        "time_max": "0.018",
        "time_out": "0.0005",
        "velocity_z": "-0.005",
        "tol": "1e-10",
        "max_iter": "80",
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


def find_parameters(root: ET.Element) -> ET.Element:
    node = root.find("./execution/parameters")
    if node is None:
        raise RuntimeError("Missing execution/parameters")
    return node


def set_parameter(params: ET.Element, key: str, value: str) -> None:
    for node in params.findall("parameter"):
        if node.get("key") == key:
            node.set("value", value)
            return
    node = ET.SubElement(params, "parameter")
    node.set("key", key)
    node.set("value", value)


def find_soils(root: ET.Element) -> ET.Element:
    node = root.find("./execution/special/soils")
    if node is None:
        raise RuntimeError("Missing execution/special/soils")
    return node


def set_soil_param(soils: ET.Element, name: str, value: str) -> None:
    node = soils.find(name)
    if node is None:
        node = ET.SubElement(soils, name)
    node.set("value", value)


def update_motion(root: ET.Element, time_max: str, velocity_z: str) -> None:
    begin = root.find("./casedef/motion/objreal/begin")
    mvrect = root.find("./casedef/motion/objreal/mvrect")
    vel = root.find("./casedef/motion/objreal/mvrect/vel")
    if begin is not None:
        begin.set("finish", time_max)
    if mvrect is not None:
        mvrect.set("duration", time_max)
    if vel is not None:
        vel.set("z", velocity_z)


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
        f"echo M3d2 CPU Release completed for {case_name}.\n"
        "exit /b 0\n",
        encoding="utf-8",
    )


def main() -> None:
    for case_name, cfg in CASES.items():
        tree = ET.parse(BASE_XML)
        root = tree.getroot()
        root.set("date", cfg["description"])
        params = find_parameters(root)
        set_parameter(params, "TimeMax", cfg["time_max"])
        set_parameter(params, "TimeOut", cfg["time_out"])
        soils = find_soils(root)
        set_soil_param(soils, "MccReturnTolerance", cfg["tol"])
        set_soil_param(soils, "MccReturnMaxIter", cfg["max_iter"])
        update_motion(root, cfg["time_max"], cfg["velocity_z"])
        indent(root)
        tree.write(ROOT / f"{case_name}_Def.xml", encoding="utf-8", xml_declaration=True)
        write_bat(case_name)


if __name__ == "__main__":
    main()
