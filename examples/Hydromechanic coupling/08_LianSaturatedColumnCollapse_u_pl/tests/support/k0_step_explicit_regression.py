"""Replay the retained C08 plastic release window after changing the diffusion-step estimate."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

TESTS = Path(__file__).resolve().parents[1]
HYDRO = TESTS.parents[1]
CONTROL = HYDRO / "validation/force_stages_r1/c08"
sys.path.insert(0, str(CONTROL.parent))
from regression import unpack


def compare(control, output):
    baseline = sorted((control / "data").glob("Part_????.bi4"))
    actual = sorted((output / "data").glob("Part_????.bi4"))
    assert len(baseline) == 6 and [p.name for p in actual] == [p.name for p in baseline]
    records = []
    for old, new in zip(baseline, actual):
        prev = unpack(old)[5][0]
        curr = unpack(new)[5][0]
        meta, fields = curr[2], curr[4]
        assert meta["Nout"] == 0 and meta["Npok"] == 6805
        assert meta["dterror"] <= 1e-14 and prev[2]["dterror"] <= 1e-14
        for key in ("Cpart", "Step", "TimeStep", "SymplecticDtPre"):
            assert np.asarray(meta[key]).tobytes() == np.asarray(prev[2][key]).tobytes(), (new, key)
        assert fields.keys() == prev[4].keys() and len(fields) == 22
        for key, (layout, arr) in fields.items():
            oldlayout, oldarr = prev[4][key]
            assert layout == oldlayout and arr.tobytes() == oldarr.tobytes(), (new, key)
        soil = fields["Idp"][1] >= 2060
        assert np.unique(fields["Idp"][1]).size == 6805 and soil.sum() == 5000
        records.append(dict(step=int(meta["Step"])+1, time_s=float(meta["TimeStep"]),
                            changed_arrays=0, previous_dterror_s=float(prev[2]["dterror"]),
                            new_dterror_s=float(meta["dterror"]),
                            yielded=int(np.count_nonzero(fields["Kplastic"][1][soil] > 0))))
    assert records[-1]["step"] == 2002001 and records[-1]["yielded"] > 0
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=("cpu", "gpu"))
    parser.add_argument("tag")
    parser.add_argument("--review-only", action="store_true")
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run with Python assertions enabled to check every archived field.")
    if not args.tag.isidentifier():
        parser.error("Use a simple output tag.")
    backend = args.backend
    control = CONTROL / "runs" / f"plastic_{backend}_validated"
    output = TESTS / "outputs" / f"{args.tag}_{backend}"
    exe = HYDRO.parents[1] / "bin/windows" / (
        "DualSPHysics5.2CPU_win64.exe" if backend == "cpu" else "DualSPHysics5.2_GEO_win64.exe")
    seed = CONTROL / "seeds/plastic/c08_h18_as03_n255_r1"
    command = [str(exe), "-"+backend, "-stable"]
    if backend == "cpu":
        command.append("-ompthreads:1")
    command.extend(["-mdbc_freeslip:1", str(seed), str(output), "-dirdataout", "data",
                    "-svres", "-nsteps:2002001"])
    if not args.review_only:
        output.mkdir()
        with (output / "console.log").open("xb") as log:
            rc = subprocess.run(command, cwd=exe.parent, stdout=log, stderr=subprocess.STDOUT).returncode
        (output / "call.json").write_text(json.dumps(dict(command=command, exit=rc)), encoding="utf8")
        if rc:
            sys.exit(rc)
    call = json.loads((output / "call.json").read_text(encoding="utf8"))
    assert call["exit"] == 0 and call["command"] == command
    report = dict(backend=backend, control=str(control), new_updates=2001, records=compare(control, output))
    with (TESTS / "logs" / f"{args.tag}_{backend}.json").open("x", encoding="utf8") as f:
        json.dump(report, f, indent=2, allow_nan=False)
