"""Check that the real GenCase preserves the proposed HydroMechModel selector and Cryer geometry."""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

CASE = Path(__file__).resolve().parents[2]
BASE_COMMIT = "7965df7d7cabb1d1ba42f131c4873ea01a242f46"
SOURCE = CASE / "CaseCryer_TPI_P3_nu030_peak_r1_Def.xml"
SEED = CASE / "support/upl_seed_nu030_r1/CaseCryerProblem_u_pl_nu030_r1.xml"
PROGRAM = CASE.parents[2] / "bin/windows/GenCase_win64.exe"
STAGE = "cryer_model_gencase_r1"
OUT = CASE / "tests/outputs" / STAGE
CHECK = CASE / "tests/logs" / (STAGE + ".check.json")
HYDRO = "./execution/special/hydromechanics"
SELECTOR = "HydroMechModel"
OLD = {"HydroMechDynamicSeepage", "HydroMechPressureIntegrator"}


def tree(node):
    return node.tag, sorted(node.attrib.items()), (node.text or "").strip(), [tree(child) for child in node]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def fields(hydro):
    return [tree(child) for child in hydro if child.tag not in OLD | {SELECTOR}]


def check_model(model, source, seed):
    work = OUT / ("model" + str(model))
    work.mkdir()
    xml = ET.fromstring(source)
    hydro = xml.find(HYDRO)
    old = hydro.find("HydroMechDynamicSeepage")
    require(old is not None and old.get("value") == "1" and
            len(hydro.findall("HydroMechDynamicSeepage")) == 1 and
            hydro.find(SELECTOR) is None and hydro.find("HydroMechPressureIntegrator") is None,
            "Unexpected reference selector")
    old.tag = SELECTOR
    old.attrib.clear()
    old.set("value", str(model))
    definition = work / "Sphere_Def.xml"
    ET.ElementTree(xml).write(definition, encoding="utf-8", xml_declaration=True)
    require(tree(ET.parse(definition).find("casedef")) == tree(ET.fromstring(source).find("casedef")),
            "The particle-generation definition changed")
    command = [str(PROGRAM), "Sphere_Def", "Sphere"]
    with (work / "gencase.log").open("xb") as log:
        result = subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT)
    require(result.returncode == 0, "GenCase exit {}; see {}".format(result.returncode, work))
    generated = ET.parse(work / "Sphere.xml")
    require((work / "Sphere.bi4").stat().st_size > 0, "No particles generated")
    result_hydro = generated.find(HYDRO)
    require(len(result_hydro.findall(SELECTOR)) == 1 and result_hydro.find(SELECTOR).get("value") == str(model) and
            not any(result_hydro.findall(tag) for tag in OLD), "Selector transmission failed")
    require(fields(result_hydro) == fields(ET.fromstring(source).find(HYDRO)), "Other hydromechanics fields changed")
    particles = generated.find("execution/particles")
    require(tree(particles) == tree(seed.find("execution/particles")), "Geometry or material ID ranges differ from seed")
    require(tree(generated.find("execution/constants/dp")) == tree(seed.find("execution/constants/dp")), "dp changed")
    return dict(model=model, exit=result.returncode, command=command, runtime_xml=str((work/"Sphere.xml").relative_to(CASE)),
                fixed_ids=particles.find("_summary/fixed").get("id"), soil_ids=particles.find("_summary/fluid").get("id"),
                np=int(particles.get("np")), dp=float(generated.find("execution/constants/dp").get("value")),
                other_hydro_fields=len(fields(result_hydro)), geometry_input_and_generated_particle_summary_match=True)


def main():
    require(not CHECK.exists() and not OUT.exists(), "The stage already exists")
    repo = CASE.parents[2]
    def archived(path):
        return subprocess.check_output(["git", "show", BASE_COMMIT + ":" + path.relative_to(repo).as_posix()], cwd=repo)
    raw = archived(SOURCE)
    seed = ET.ElementTree(ET.fromstring(archived(SEED)))
    OUT.mkdir()
    results = [check_model(model, raw, seed) for model in (0, 1, 2)]
    with CHECK.open("x", encoding="utf-8") as writer:
        json.dump(dict(source=SOURCE.name, source_commit=BASE_COMMIT, program=str(PROGRAM), values=results, solver_launches=0), writer, indent=2)
        writer.write("\n")


if __name__ == "__main__":
    main()
