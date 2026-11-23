"""Review the small-file overlay against current formal inputs, without modifying a formal case."""
import hashlib
import json
from pathlib import Path

import hydro_frozen_entry_stage_r1 as stage

V = stage.bridge.HERE
OVERLAY = stage.STAGE / "winrelease"


def binding(path):
    return dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    checked = json.loads((stage.STAGE/"winbat3/entry_review.json").read_text())
    edits = json.loads((stage.STAGE/"winedit2/edits_review.json").read_text())
    if checked["launches"] != 28 or checked["real_preparation_entries"] != 20 or len(edits["protected_cryer_root_outputs"]) != 8:
        raise ValueError("Missing successful staged entry evidence")
    changed = []
    for file in sorted(OVERLAY.rglob("*")):
        if not file.is_file():
            continue
        rel = file.relative_to(OVERLAY)
        root = stage.SUITE / rel
        if len(rel.parts)>1 and (rel.parts[1] in {"tests","figures"} or rel.parts[1].endswith("_out")):
            raise ValueError("Staged output outside the formal source/configuration set")
        changed.append(dict(path=rel.as_posix(), previous=binding(root) if root.exists() else None, proposed=binding(file)))
    defaults = []
    for name, item in stage.bridge.records().items():
        case, = stage.SUITE.glob(item["case"] + "_*")
        source = (case / name).read_bytes()
        modern = (OVERLAY / case.name / name).read_bytes()
        # A Git checkout may change public XML's line endings or UTF-8 BOM.
        for raw in (modern,b"\xef\xbb\xbf"+modern.replace(b"\n",b"\r\n")):
            if stage.bridge.restore(name, source, raw) != source:
                raise ValueError("Public lexical representation changed the frozen input: "+name)
        defaults.append(name)
    report=dict(overlay=str(OVERLAY),entries=changed,public_line_ending_and_bom_roundtrips=defaults,
                staged_normal_entry=checked,staged_edits=edits,installed=False)
    (V/"hydro_frozen_entry_release_r2.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print("Guarded overlay files:",len(changed),"old:",sum(r["previous"] is not None for r in changed),
          "new:",sum(r["previous"] is None for r in changed), "bytes:", sum(r["proposed"]["bytes"] for r in changed))


if __name__ == "__main__":
    main()

