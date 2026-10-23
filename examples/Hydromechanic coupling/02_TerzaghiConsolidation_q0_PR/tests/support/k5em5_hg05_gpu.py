"""Fresh GPU .3-s pair, same XML physics as the verified CPU HG .05 pair."""
import argparse
import json
from formal_release_sequence import TESTS
from mdbc_gpu_vector_run import read, verify
import k5em5_uniform as runner

runner.TAG = "k5em5_hg05_gpu_r1"


def prepare():
    patch = "*** Begin Patch\n"
    for v in ("c", "h"):
        old, label = "k5em5_hg05_r1_"+v, runner.TAG+"_"+v
        xml = (TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
        bat = (TESTS/"configs"/("x"+old+"_win64_CPU.bat")).read_text(encoding="utf8")
        bat = bat.replace(old, label).replace("DualSPHysics5.2CPU_win64.exe", "DualSPHysics5.2_GEO_win64.exe")
        bat = bat.replace("-cpu -ompthreads:8", "-gpu:0 -ompthreads:1")
        for path, text in ((TESTS/"configs"/(label+"_Def.xml"), xml),
                           (TESTS/"configs"/("x"+label+"_win64_GPU.bat"), bat)):
            assert not path.exists()
            patch += "*** Add File: "+str(path)+"\n"+"\n".join("+"+s for s in text.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        prior = read(TESTS/"logs/k5em5_hg05_review_r1.check.json")
        assert prior["both_safety_passed"] and prior["half_passed"] and not prior["full_admitted"]
        verify(prior["evidence"])
        runner.run()
