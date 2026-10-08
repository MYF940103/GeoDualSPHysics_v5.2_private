from pathlib import Path
import xml.etree.ElementTree as ET


TESTS = Path(__file__).resolve().parents[1]
CASE_ROOT = TESTS.parent
BASE_XML = CASE_ROOT / "CaseTerzaghiConsolidation_q0_PR_full_k1em2_Def.xml"
CONFIGS = TESTS / "configs"


CASES = [
    ("dt1em6", "0.000001", "0.01", "0.02"),
    ("dt1em7", "0.0000001", "0.01", "0.02"),
    ("dt1em7_t006", "0.0000001", "0.06", "0.02"),
    ("dt1em7_t010", "0.0000001", "0.10", "0.02"),
    ("dt1em7_t015", "0.0000001", "0.05", "0.02"),
    ("d04t010", "0.0000001", "0.10", "0.4"),
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


def write_case(tag, dtfixed, time_max, damping):
    tree = ET.parse(BASE_XML)
    root = tree.getroot()
    hydro = root.find(".//hydromechanics")
    if hydro is None:
        raise RuntimeError("Missing hydromechanics block")

    set_attr(hydro.find("HydraulicConductivity"), "0", "Stage 1: undrained loading/stabilization before q0 dissipation restart")
    set_attr(hydro.find("PoreDtSafety"), "0.5", "Stage 1 q0 test pore-pressure safety setting")
    set_attr(hydro.find("PoreShepardRegularization"), "1", "Stage 1: enabled to suppress pore-pressure oscillation during stabilization")
    set_attr(hydro.find("PoreShepardInterval"), "40", "Stage 1: apply Shepard pore-pressure regularization every 40 steps")
    set_attr(hydro.find("HydroMechInitMode"), "0", "Stage 1 q0 loading starts from zero excess pore pressure")
    set_attr(hydro.find("HydroMechTopLoadMode"), "TopVertical", "Stage 1: instantaneous q0 vertical top load")
    set_attr(hydro.find("HydroMechTopLoadRampTime"), "0", "Stage 1: instantaneous q0 loading")
    set_attr(hydro.find("HydroMechDrainage"), "1", "Stage 1: keep free-surface drained boundary enforcement enabled")
    set_attr(hydro.find("HydroMechDrainageStartTime"), "0", "Stage 1: drained free-surface enforcement from the start")

    set_param(root, "DtIni", dtfixed, "Stage 1 q0 fixed initial time step")
    set_param(root, "DtFixed", dtfixed, "Stage 1 q0 fixed time step")
    set_param(root, "SoilDampingCoef", damping, "Stage 1 q0 damping coefficient")
    set_param(root, "TimeMax", time_max, "Stage 1 q0 stabilization duration")
    set_param(root, "TimeOut", "0.0005", "Stage 1 q0 output interval for stability/profile checks")

    case = f"CaseTerzaghiConsolidation_q0_PR_stage1_{tag}"
    out = CONFIGS / f"{case}_Def.xml"
    tree.write(out, encoding="UTF-8", xml_declaration=True)
    return out


def main():
    CONFIGS.mkdir(parents=True, exist_ok=True)
    for tag, dtfixed, time_max, damping in CASES:
        out = write_case(tag, dtfixed, time_max, damping)
        print(out)


if __name__ == "__main__":
    main()
