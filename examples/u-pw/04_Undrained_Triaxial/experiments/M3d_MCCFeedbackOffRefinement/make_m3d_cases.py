#!/usr/bin/env python3
"""Generate M3d feedback-off MCC platen refinement XML/BAT cases."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
T5B = ROOT.parent / "T5b_DPFeedbackOffRefinement" / "CaseT5b_DPMildYield_ReactionRefinement_Def.xml"

CASES = {
    "CaseM3d_MCCHighPc_Extended": {
        "description": "M3d MCC high-pc elastic-like extended feedback-off platen response",
        "pc0": "100000",
    },
    "CaseM3d_MCCMildYield_Extended": {
        "description": "M3d MCC mild-yield extended feedback-off platen response",
        "pc0": "120",
    },
}

MCC_PARAMS = {
    "SoilConstitutiveModel": ("3", "Modified Cam Clay CPU stress update"),
    "MccLambda": ("0.20", "MCC compression index"),
    "MccKappa": ("0.04", "MCC swelling index"),
    "MccM": ("1.20", "MCC critical-state stress ratio"),
    "MccInitialVoidRatio": ("0.80", "Initial void ratio"),
    "MccTensionCutoff": ("1e-5", "MCC p' tension cutoff"),
    "MccReturnTolerance": ("1e-8", "MCC local return tolerance"),
    "MccReturnMaxIter": ("45", "MCC local Newton maximum iterations"),
    "SaveMccState": ("1", "Output MCC state fields"),
    "MccStressUpdateEnabled": ("1", "Enable MCC CPU stress update"),
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


def find_soils(root: ET.Element) -> ET.Element:
    node = root.find("./execution/special/soils")
    if node is None:
        raise RuntimeError("Missing execution/special/soils")
    return node


def set_soil_param(soils: ET.Element, name: str, value: str, comment: str = "") -> None:
    node = soils.find(name)
    if node is None:
        node = ET.SubElement(soils, name)
    node.set("value", value)
    if comment:
        node.set("comment", comment)


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


def update_motion(root: ET.Element, timemax: str) -> None:
    begin = root.find("./casedef/motion/objreal/begin")
    mvrect = root.find("./casedef/motion/objreal/mvrect")
    if begin is not None:
        begin.set("finish", timemax)
    if mvrect is not None:
        mvrect.set("duration", timemax)


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
        f"echo M3d CPU Release completed for {case_name}.\n"
        "exit /b 0\n",
        encoding="utf-8",
    )


def main() -> None:
    for case_name, cfg in CASES.items():
        tree = ET.parse(T5B)
        root = tree.getroot()
        root.set("date", cfg["description"])
        soils = find_soils(root)
        for key, (value, comment) in MCC_PARAMS.items():
            set_soil_param(soils, key, value, comment)
        set_soil_param(soils, "MccInitialPreconsolidationPressure", cfg["pc0"], "Initial preconsolidation pressure [Pa]")
        params = find_parameters(root)
        set_parameter(params, "TimeMax", "0.018")
        set_parameter(params, "TimeOut", "0.0005")
        set_parameter(params, "InitialStressMode", "1")
        set_parameter(params, "InitialEffectiveStressIso", "50")
        set_parameter(params, "InitialEffectiveStressTargetMk", "-1")
        set_parameter(params, "PorePressureFeedback", "0")
        set_parameter(params, "SavePorePressureFeedbackDiagnostics", "0")
        update_motion(root, "0.018")
        indent(root)
        out = ROOT / f"{case_name}_Def.xml"
        tree.write(out, encoding="utf-8", xml_declaration=True)
        write_bat(case_name)


if __name__ == "__main__":
    main()
