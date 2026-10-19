"""Verify the formal read-only PART reader against retained native CSV fields."""
import io
import json
import subprocess
import numpy as np
import pandas as pd
from mdbc_gpu_vector_run import TESTS, bound, read, verify


def main():
    build_path = TESTS / "logs/read_hm_part_r2.build.json"
    build = read(build_path)
    assert build["built"]
    evidence = [bound(build_path), dict(path=build["executable"], sha256=build["executable_sha256"])] + build["inputs"]
    verify(evidence)
    checks = []
    fields = ["x", "y", "z", "vx", "vy", "vz", "rho", "pressure", "sigma_xx", "sigma_yy", "sigma_zz", "sigma_xy", "sigma_yz", "sigma_xz", "kplastic"]
    for backend in ("gpu", "cpu"):
        folder = TESTS / "outputs" / ("gpu_full_save_" + backend + "_r1")
        saved = pd.read_csv(folder / "state.csv", float_precision="round_trip")
        evidence.append(bound(folder / "state.csv"))
        for part in (0, 1, 15):
            process = subprocess.run([build["executable"], str(folder / "data"), str(part)], capture_output=True)
            assert process.returncode == 0, process.stderr.decode(errors="replace")
            a = pd.read_csv(io.BytesIO(process.stdout), float_precision="round_trip")
            b = saved.iloc[part * 1000:(part + 1) * 1000]
            assert np.array_equal(a.id, b.id) and a.id.eq(np.arange(40, 1040)).all()
            assert a[fields].to_numpy(dtype="<f8").tobytes() == b[fields].to_numpy(dtype="<f8").tobytes()
            assert np.array_equal(a.time_s, b.time_s) and np.array_equal(a.step, b.step)
            assert a.load_available.eq(backend == "gpu").all()
            if backend == "gpu":
                assert a.load_az.to_numpy().tobytes() == b.load_az.to_numpy().tobytes()
            checks.append(dict(backend=backend, part=part, native_soil=1000, physical_fields_0_ulp=True,
                               load_saved=backend == "gpu"))
            evidence.append(bound(folder / "data" / (f"Part_{part:04d}.bi4")))
    evidence.append(bound(__file__))
    verify(evidence)
    with (TESTS / "logs/release_reader_r1.check.json").open("x", encoding="utf8") as stream:
        json.dump(dict(passed=True, checks=checks, evidence=evidence,
                       scope="Read-only native double stress/positions and float pressure; no solver or new physics"), stream, indent=2)
    print(json.dumps(dict(passed=True, checks=checks), indent=2))


if __name__ == "__main__":
    main()
