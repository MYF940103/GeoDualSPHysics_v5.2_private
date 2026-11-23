"""Rebuild the reviewed 59 small files from Git history and portable provenance, without binary packages."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import hydro_frozen_entry_stage_r1 as stage

HERE = Path(__file__).resolve().parent
SOURCE = HERE/"hydro_frozen_clean_inputs_r2.json"
REVIEW = HERE/"hydro_frozen_entry_release_r2.json"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def bytes_id(raw):
    return {"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}


def original_bytes(raw, required, name):
    # Git tracked some original XML/BAT as text. Only the exact registered byte sequence is admissible.
    if bytes_id(raw) == required:
        return raw, "raw_blob"
    lf = raw.replace(b"\r\n",b"\n")
    for cmd, data in (("LF",lf),("CRLF",lf.replace(b"\n",b"\r\n"))):
        if bytes_id(data) == required:
            return data, cmd
    raise ValueError("Pinned Git input cannot recreate its registered original: "+name)


def rebuild(repo, out):
    data = json.loads(SOURCE.read_text());expected = json.loads(REVIEW.read_text())
    ref = data["git_baseline"]
    prefix = "examples/Hydromechanic coupling/"
    expected_files = {r["path"]:r for r in expected["entries"]}
    with tempfile.TemporaryDirectory(prefix="hydro_xml_src_") as folder:
        cases = Path(folder)
        conversions = {}
        for rel, row in expected_files.items():
            if row["previous"] is None:
                continue
            old, label = original_bytes(git(repo,"cat-file","blob",ref+":"+prefix+rel),row["previous"],rel)
            target = cases / rel
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(old)
            conversions[rel] = label
        # The unchanged C08 public BATs select the revision and backend. They are not deployment replacements.
        c08,=cases.glob("08_*")
        wrappers={r["launcher"] for r in expected["staged_normal_entry"]["rows"] if r["case"]=="08"}
        for name in sorted(wrappers):
            (c08/name).write_bytes(git(repo,"cat-file","blob",ref+":"+prefix+c08.name+"/"+name))
        stage.assemble(cases,out,data["archives"])
    actual={p.relative_to(out).as_posix():p for p in out.rglob("*") if p.is_file()}
    if set(actual) != set(expected_files):
        raise ValueError("Reconstructed deployment path set does not match the reviewed 59 files")
    for rel,p in actual.items():
        if bytes_id(p.read_bytes()) != expected_files[rel]["proposed"]:
            raise ValueError("Reconstructed file differs from the reviewed proposal: "+rel)
    return dict(git_baseline=ref,old_inputs=conversions,unchanged_c08_launchers=len(wrappers),
                generated_files=len(actual),generated_bytes=sum(p.stat().st_size for p in actual.values()))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=stage.STAGE/"winrelease")
    a=parser.parse_args()
    output=a.out.resolve()
    if not output.is_relative_to((stage.SUITE/"04_CryerProblem_PR/tests/outputs").resolve()):
        raise ValueError("Only a new/restored C04 test-staging path is permitted")
    report=rebuild(HERE,output)
    print("Verified",report["generated_files"],"files,",report["generated_bytes"],"bytes, at",output)

