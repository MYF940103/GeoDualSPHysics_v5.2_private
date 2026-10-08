from pathlib import Path
import xml.etree.ElementTree as ET


TESTS = Path(__file__).resolve().parents[1]
CASE_ROOT = TESTS.parent
BASE_XML = CASE_ROOT / "CaseTerzaghiConsolidation_q0_PR_full_k1em2_Def.xml"
CONFIGS = TESTS / "configs"


CASES = [
    {
        "tag": "s2p0138_k1em2",
        "case": "CaseTzq0_s2p0138_k1em2",
        "time_max": "0.364371428571429",
        "time_out": "0.00182185714285714",
        "dtfixed": "0.0000001",
        "damping": "0.02",
        "restart_part": 138,
        "restart_time": 0.069,
        "restart_source": "CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010",
    },
]


def set_attr(elem, value, comment=None):
    if elem is None:
        raise RuntimeError("Missing XML element")
    elem.set("value", value)
    if comment is not None:
        elem.set("comment", comment)


def set_param(root, key, value, comment=None):
    elem = root.find(f".//parameter[@key='{key}']")
    if elem is None:
        raise RuntimeError(f"Missing parameter {key}")
    elem.set("value", value)
    if comment is not None:
        elem.set("comment", comment)


def write_case(case_def):
    tree = ET.parse(BASE_XML)
    root = tree.getroot()
    hydro = root.find(".//hydromechanics")
    if hydro is None:
        raise RuntimeError("Missing hydromechanics block")

    set_attr(hydro.find("HydraulicConductivity"), "1e-2", "Stage 2: formal q0 dissipation from stabilized Stage1 restart")
    set_attr(hydro.find("PoreDtSafety"), "0.5", "Stage 2 q0 formal pore-pressure time-step safety")
    set_attr(hydro.find("PoreShepardRegularization"), "0", "Stage 2: disabled for formal dissipation comparison")
    set_attr(hydro.find("PoreShepardInterval"), "40", "Unused when Stage 2 regularization is disabled")
    set_attr(hydro.find("HydroMechInitMode"), "0", "Stage 2 restart inherits pore-pressure state from Stage1")
    set_attr(hydro.find("HydroMechTopLoadMode"), "TopVertical", "Stage 2: keep q0 vertical top load active")
    set_attr(hydro.find("HydroMechTopLoadRampTime"), "0", "Stage 2: q0 already applied in Stage1 restart")
    set_attr(hydro.find("HydroMechDrainage"), "1", "Stage 2: enable drained top free-surface pore pressure")
    set_attr(hydro.find("HydroMechDrainageStartTime"), "0", "Stage 2: dissipation time starts at restart")

    set_param(root, "DtIni", case_def["dtfixed"], "Stage 2 q0 fixed initial time step")
    set_param(root, "DtFixed", case_def["dtfixed"], "Stage 2 q0 fixed time step")
    set_param(root, "SoilDampingCoef", case_def["damping"], "Stage 2 q0 damping coefficient inherited from best Stage1 test")
    set_param(root, "TimeMax", case_def["time_max"], "Stage 2 duration from restart, reaching Tv=1 for k=1e-2")
    set_param(root, "TimeOut", case_def["time_out"], "Stage 2 output interval corresponding to Delta Tv=0.005")

    out = CONFIGS / f"{case_def['case']}_Def.xml"
    tree.write(out, encoding="UTF-8", xml_declaration=True)
    return out


def main():
    CONFIGS.mkdir(parents=True, exist_ok=True)
    for case_def in CASES:
        out = write_case(case_def)
        print(out)


if __name__ == "__main__":
    main()
