"""Offline review of the actual consumer/MLS fixtures; never launches a solver."""
from pathlib import Path
import csv
import hashlib
import json
import math
from datetime import datetime, timezone

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def rows(name):
    path = TESTS / "outputs" / name / "pairs.csv"
    data = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    # Explicit alias; no inner join is allowed to silently drop six trials.
    def key(r):
        trial = r["trial"].replace("aux_normal_negative_shear", "aux_normal_shear_negative")
        return int(r["dimension"]), int(r["slip"]), trial
    table = {key(r): r for r in data}
    assert len(data) == len(table) == 72
    assert set(k[:2] for k in table) == {(d, s) for d in (2, 3) for s in (1, 2, 3)}
    return table, path

def main():
    check_path = TESTS / "logs/bv_review_r1.check.json"
    assert not check_path.exists(), "Refusing to overwrite sealed review"
    names = dict(before="bv_pair_cpu_before_r1", debug="bv_pair_cpu_after_r1",
                 release="bv_pair_cpu_release_r1", gpu="bv_pair_gpu_debug_run_r2")
    data, artifacts = {}, []
    def bind(p):
        p = Path(p)
        artifacts.append(dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size))
    for label, name in names.items():
        data[label], path = rows(name)
        bind(path)
        completion = path.with_name("completion.json")
        done = read(completion)
        assert done["diagnostic_completed"] and done["kernel_calls"] == 72
        assert done["passed"] is (label != "before")
        bind(completion)
    keys = set(data["debug"])
    assert all(set(table) == keys for table in data.values())
    failed = [k for k in keys if data["before"][k]["passed"] != "1"]
    assert len(failed) == 12 and all(k[2] in ("aux_shear", "aux_shear_negative") for k in failed)
    fields = ["soil_ar", "soil_pore_rate", "soil_viscdt", "ace_x", "ace_y", "ace_z",
              "rsigma_xx", "rsigma_yy", "rsigma_zz", "rsigma_xy", "rsigma_yz", "rsigma_xz"]
    cross, debug_release, patch = {}, {}, {}
    for field in fields:
        cross[field] = max(abs(float(data["debug"][k][field])-float(data["gpu"][k][field])) for k in keys)
        debug_release[field] = max(abs(float(data["debug"][k][field])-float(data["release"][k][field])) for k in keys)
        changed = [k for k in keys if float(data["debug"][k][field]) != float(data["before"][k][field])]
        patch[field] = len(changed)
        assert not changed if field != "rsigma_xz" else set(changed) == set(failed)
        for k in keys:
            a, b = float(data["debug"][k][field]), float(data["gpu"][k][field])
            assert math.isfinite(a) and math.isfinite(b)
            # Same original field-specific comparison floors, not a physical error tolerance.
            floor = 20 if field.startswith("rsigma") else 2000 if field == "soil_pore_rate" else .02
            assert abs(a-b) <= floor + 2e-5*abs(b)
        assert debug_release[field] == 0
    mem = TESTS / "logs/bv_pair_gpu_debug_run_r2.memcheck.log"
    assert "ERROR SUMMARY: 0 errors" in mem.read_text(encoding="utf-8-sig")
    bind(mem)
    mls = []
    for dim in (2, 3):
        results = []
        for suffix in ("after_r1", "release_r1"):
            folder = TESTS / "outputs" / f"bv_mls_{dim}d_{suffix}"
            p = folder / "bv_mls_complete.json"
            result = read(p)
            assert result["passed"] and result["dimension"] == dim
            assert result["native_count"] == (208 if dim == 2 else 3328)
            assert result["physical_fields_unchanged_by_spr_and_ct"] and not result["time_integrated"]
            bind(p)
            for filename in ("aux_rows.csv", "consumer_rows.csv", "stage_rows.csv"):
                bind(folder / filename)
            results.append(result)
        assert results[0] == results[1]
        mls.append(results[0])
    builds = ["bv_bv_pair_cpu_r1_before_r3", "bv_bv_pair_cpu_r1_after_r1",
              "bv_bv_pair_cpu_r1_r1", "bv_bv_mls_cpu_r1_after_r1", "bv_bv_mls_cpu_r1_r1", "bv_pair_gpu_Debug_r1"]
    for name in builds:
        p = TESTS / "logs" / (name + ".build.json")
        b = read(p)
        exe = Path(b.get("executable", "")) if "executable" in b else Path(b["runtime"][0]["path"])
        if exe.suffix.lower() != ".exe":
            exe = next(Path(x["path"]) for x in b["runtime"] if Path(x["path"]).suffix.lower() == ".exe")
        assert sha(exe) == b["exe_sha256" if "exe_sha256" in b else "executable_sha256"].lower()
        bind(p)
    for p in (REPO / "src/source/JSphCpu.cpp", TESTS / "outputs/bv_before_r1/JSphCpu.cpp", Path(__file__)):
        bind(p)
    result = dict(passed=True, utc=datetime.now(timezone.utc).isoformat(),
        scope="Implementation/route contract only; no integration or physical acceptance",
        failed_before_patch=12, passed_after_cpu_debug=72, passed_after_cpu_release=72,
        passed_gpu_debug_memcheck=72, gpu_memcheck_errors=0,
        cpu_patch_changed_rows_by_field=patch, cpu_debug_release_max_abs=debug_release,
        cpu_gpu_soil_max_abs=cross, cpu_gpu_wall_receiver_compared=False,
        shear_after_pa_s={str(d): float(data["debug"][(d, 1, "aux_shear")]["rsigma_xz"]) for d in (2, 3)},
        mls_and_stage_observers=mls, production_patch="Only CPU six stress-rate accumulations moved outside rho/force/viscosity guard; DDT merge remains inside",
        guards_relaxed=False, new_parameters=False, gpu_kernel_changed=False,
        before_mls_initialization_failure="Incremental-object initialization failed the unchanged SPR guard; a full CPU Debug Rebuild and fresh companions passed. No prior failed result was admitted; exact stale-object cause not independently proven.",
        limitations=["Single-pair consumer injects auxiliary data and is not an MLS/physical-wall case", "MLS fixtures are static horizontal FreeSlip, zero prestress; not general Jaumann objectivity",
                     "Stage observer changes fields/InterStep, not actual integration time", "MDBCCorrector=0 retains tn viscous ghost while refreshing derivative auxiliary",
                     "Density retains raw gradients; equal velocities do not imply discrete S/P/rho consistency", "DDT sentinel split CPU/GPU difference remains unaudited by these DensityDT=0 fixtures",
                     "Old physical/full-cycle case data are not retroactively validation of this CPU-only patch"],
        physical_acceptance=False, artifacts=artifacts)
    check_path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("passed", "failed_before_patch", "cpu_gpu_soil_max_abs", "shear_after_pa_s")}, indent=2))

if __name__ == "__main__":
    main()
