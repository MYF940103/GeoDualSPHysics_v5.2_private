"""One bounded HG-strength causal test, original Darcy and same dp; no source edit."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import k5em5_lapcorr_run as runner
from formal_release_sequence import save, utc
from mdbc_gpu_vector_run import read, bound, verify

runner.TAG = "k5em5_hg05_r1"
runner.BUILD = runner.TESTS/"logs/k5em5_hg05_r1.adopted_cpu.json"


def prepare():
    control = runner.TESTS/"logs/k5em5_rhocorr_r1.status.json"
    prior = read(control)
    assert prior["status"] == "completed_pending_causal_review"
    exe = runner.REPO/"bin/windows/DualSPHysics5.2CPU_win64.exe"
    proof = [r for r in prior["inputs"] if Path(r["path"]) == exe]
    assert len(proof) == 1
    verify(proof)
    assert not runner.BUILD.exists()
    # Existing verified Release program, not a claimed new compilation.
    save(runner.BUILD, dict(built=True, adopted_existing_production_cpu=True, utc=utc(),
                           production_modified=False, executable=str(exe), executable_sha256=proof[0]["sha256"],
                           inputs=proof+[bound(control), bound(Path(__file__))],
                           changed_operator="none; XML HG strength .1 to .05 sensitivity only"))
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        runner.prepare()
    patch = json.loads(stream.getvalue())["patch"]
    patch = patch.replace('tests/outputs/k5em5_lapcorr_r1_bin/DualSPHysicsCpuProbe.exe',
                          '%dirbin%/DualSPHysics5.2CPU_win64.exe')
    assert patch.count('key="SoilHourglassXi" value="0.1"') == 2
    patch = patch.replace('key="SoilHourglassXi" value="0.1"', 'key="SoilHourglassXi" value="0.05"')
    patch = patch.replace("rem Isolated .3-s Darcy-moment diagnostic only; no full-cycle admission.",
                          "rem .3-s HG-strength diagnostic; original Darcy, no full-cycle admission.")
    print(json.dumps(dict(patch=patch)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--variant", choices=("c", "h"))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        assert args.variant
        runner.run(args.variant)
