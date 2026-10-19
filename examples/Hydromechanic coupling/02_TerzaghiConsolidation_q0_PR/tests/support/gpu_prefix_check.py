"""Compare a completed GPU run's saved soil/HG prefix without rerunning it."""
import argparse
import hashlib
import json
from pathlib import Path
from mdbc_gpu_vector_run import TESTS, bound, read, verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--tag", required=True)
    args = p.parse_args()
    path = TESTS / "logs" / (args.tag + ".check.json")
    assert not path.exists()
    manifests = [TESTS / "logs" / (n + ".run.json") for n in (args.candidate, args.reference)]
    a, b = map(read, manifests)
    assert a["passed"] and b["passed"] and a["exit_code"] == b["exit_code"] == 0
    assert a["argv"][0] == b["argv"][0]
    assert {k: v for k, v in a["settings"].items() if k not in ("label", "duration_s", "duration_text", "steps")} == {
            k: v for k, v in b["settings"].items() if k not in ("label", "duration_s", "duration_text", "steps")}
    files, evidence = {}, [bound(f) for f in manifests] + [bound(__file__)]
    for name in ("state.csv", "hourglass.csv"):
        reference = TESTS / "outputs" / args.reference / name
        candidate = TESTS / "outputs" / args.candidate / name
        entry = next(e for e in b["outputs"] if Path(e["path"]).resolve() == reference.resolve())
        verify([entry]);evidence.append(entry)
        digest, count = hashlib.sha256(), 0
        with candidate.open("rb") as c, reference.open("rb") as r:
            while chunk := r.read(1024 * 1024):
                other = c.read(len(chunk))
                if other != chunk:
                    raise RuntimeError("Same-GPU saved prefix differs: " + name)
                digest.update(chunk);count += len(chunk)
        files[name] = dict(bytes=count, sha256=digest.hexdigest(), byte_identical=True)
    with path.open("x", encoding="utf8") as stream:
        json.dump(dict(passed=True, candidate=args.candidate, reference=args.reference, files=files,
                       soil_frames=b["completion"]["sampled_frames"], evidence=evidence,
                       scope="Saved 1000-native-soil state and sampled HG statistics prefix only; not every intermediate wall/HG native state.",
                       physical_acceptance=False), stream, indent=2)
    print("PASS identical saved GPU state/HG prefix: " + args.reference)


if __name__ == "__main__":
    main()
