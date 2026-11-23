"""Verify edited formal BAT inputs, historical-output guards and the FreshPR analysis input."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import hydro_frozen_entry_stage_r1 as stage
import hydro_frozen_entry_review_r1 as entry
from hydro_frozen_xml_review_r1 import parse, check


def source_case(cid):
    case, = stage.SUITE.glob(cid + "_*")
    return case


def review_mutable(cid, overlay, trial):
    case = source_case(cid)
    root = trial / cid
    entry.populate(case, root, overlay)
    path, = root.glob("*_Def.xml")
    model = stage.bridge.tree(path.read_bytes())
    special, water = stage.bridge.nodes(model)
    special.find("drainage").set("start", "0.0123456")
    span = model.find("execution/parameters/parameter[@key='TimeOut']")
    span.set("value", "0.000123456")
    if cid == "05":
        special.find("externalload").set("q0", "9876.5")
        special.find("externalload").set("ramptime", "0.25")
    path.write_bytes(stage.bridge.emit(model))
    bat, = root.glob("x*.bat")
    entry.call(bat.name, root, trial / (cid + "_edits.log"), 0)
    stem, _ = entry.parts_for(case, path.name, bat.name, root)
    generated = parse(stem.with_suffix(".xml").read_bytes())
    _, old = stage.bridge.nodes(generated)
    check(old.find(stage.bridge.DRAIN[1]).get("value") == "0.0123456", "Drain time did not reach the legacy run input")
    check(float(generated.find("execution/parameters/parameter[@key='TimeOut']").get("value")) == 0.000123456, "Lost cadence")
    if cid == "05":
        check(float(old.find(stage.bridge.LOAD[1]).get("value")) == 9876.5 and
              float(old.find(stage.bridge.LOAD[2]).get("value")) == .25, "Lost Lian load")
    else:
        # Use the original FreshPR analysis parser on the actual generated solver file and on its effective definition.
        post = case / "support/postprocess_selfweight_freshpr_r1.py"
        spec = importlib.util.spec_from_file_location("fresh", post)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(post.parent))
        spec.loader.exec_module(module)
        params = module.parameters(stem.with_suffix(".xml"))
        effective = module.parameters(stem.parent / (stem.name + "_Def.xml"))
        check(params == effective, "Generated solver file and consumed FreshPR postprocessing parameters differ")
    full_suffix = "_out" if cid == "01" else "_HGSPR_out"
    full = root / (stem.name + full_suffix)
    check(not full.exists(), "Preparation reserved the full output directory")
    full.mkdir()
    sentinel = full / "retained.txt"
    sentinel.write_bytes(b"immutable")
    user_arg = ["-solver-only"] if cid == "01" else ["--unattended"]
    text = entry.call(bat.name, root, trial / (cid + "_existing_full.log"), 1, args=user_arg)
    check("Output already exists" in text and list(full.iterdir()) == [sentinel] and sentinel.read_bytes() == b"immutable",
          "Existing full output not protected")
    return dict(case=cid, timeout=0.000123456, drainage_start=0.0123456,
                existing_full_preserved=True, configured_load=9876.5 if cid=="05" else None,
                actual_postprocessor_parameter_equality=cid=="01")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--tag", default="edits1")
    arg = parser.parse_args()
    check(arg.tag.isalnum(), "Simple fresh label required")
    trial = stage.STAGE / arg.tag
    trial.mkdir()
    mutable = [review_mutable(cid, arg.overlay, trial) for cid in ("01", "05")]
    case = source_case("04")
    root = trial / "04"
    entry.populate(case, root, arg.overlay)
    mapping = json.loads((root / "support" / stage.ARCHIVES).read_text())
    guards = []
    for name, spec in mapping.items():
        stem = name.removesuffix("_Def.xml")
        b = "x" + stem + "_win64_GPU.bat"
        suffix = "_GPU_out" if spec["mode"] in ("p3", "seed") else "_out"
        old = root / (stem + suffix)
        old.mkdir()
        sentinel = old / "retained.txt"
        sentinel.write_bytes(b"immutable")
        text = entry.call(b, root, trial / (stem + "_existing.log"), 1, args=["--unattended"])
        check("Existing result protected" in text and list(old.iterdir()) == [sentinel] and sentinel.read_bytes()==b"immutable",
              "Existing archive-root result was not protected: " + b)
        guards.append(b)
    # Physical edits on a fixed-seed package must fail even for prepare-only, and before extracting the archive.
    p3 = "CaseCryer_TPI_P3_nu030_peak_r1_Def.xml"
    src = root / p3
    original = stage.bridge.tree(src.read_bytes())
    stage.bridge.nodes(original)[1].find(stage.bridge.MODEL).set("value", "1")
    src.write_bytes(stage.bridge.emit(original))
    text = entry.call("x" + p3.removesuffix("_Def.xml") + "_win64_GPU.bat", root, trial / "p3_changed.log", 1)
    check("Frozen release" in text and not (root / mapping[p3]["workspace"]).exists(), "Changed fixed-seed P3 was accepted")
    result = dict(mutable_root_bat=mutable, protected_cryer_root_outputs=guards, p3_changed_model_rejected=True,
                  staging=str(trial), solver_launches=0)
    (trial / "edits_review.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()

