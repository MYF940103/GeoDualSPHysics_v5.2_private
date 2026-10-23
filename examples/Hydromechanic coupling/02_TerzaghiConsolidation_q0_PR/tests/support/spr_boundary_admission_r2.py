"""Finish admission checks after correcting the curved fixture's outer normals.

The r1 plane/corner/edge results are retained, not rerun. GenCase's discretized
sphere shell straddles the ideal radius; initialize both sides explicitly.
"""
import copy
import json
import spr_boundary_admission as base

original = base.variant


def variant(key):
    root = original(key)
    if key.startswith(("curve", "sphere")):
        initialize = root.find("execution/special/initialize")
        outside = copy.deepcopy(initialize.find("boundnormal_sphere"))
        outside.find("inside").set("v", "false")
        outside.find("clear").set("v", "false")
        initialize.append(outside)
    return root


if __name__ == "__main__":
    base.TAG = "spr_boundary_admission_r2"
    base.CASES = ("curve2", "sphere3", "translate2", "rotate3", "nopen2", "nopen3")
    base.variant = variant
    base.main()
    receipt = base.TESTS/"logs"/(base.TAG+".check.json")
    result = json.loads(receipt.read_text(encoding="utf8"))
    result["inputs"].append(base.bound(__file__))
    receipt.write_text(json.dumps(result,indent=2),encoding="utf8")
