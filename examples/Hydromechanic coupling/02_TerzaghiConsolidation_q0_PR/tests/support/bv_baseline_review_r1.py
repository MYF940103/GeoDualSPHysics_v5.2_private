"""Check freshly recompiled original CPU implementation; no solver launch."""
import csv
import hashlib
import json
from pathlib import Path

tests = Path(__file__).resolve().parents[1]
output = tests / "logs/bv_baseline_rebuild_r1.check.json"
assert not output.exists(), "Refusing overwrite"
paths = [tests / "outputs" / name / "pairs.csv" for name in (
    "bv_pair_cpu_sealed_before_r1", "bv_pair_cpu_before_r1", "bv_pair_cpu_after_r1")]
tables = [list(csv.DictReader(p.open(encoding="utf-8-sig", newline=""))) for p in paths]
assert all(len(t) == 72 for t in tables)
assert tables[0] == tables[1], "Fresh original-source baseline differs from initial diagnostic"
assert sum(r["passed"] == "0" for r in tables[0]) == 12
assert all(r["passed"] == "1" for r in tables[2])
source = tests / "outputs/bv_before_r1/JSphCpu.cpp"
build = tests / "logs/bv_baseline_bv_pair_cpu_r1_r2.build.json"
record = json.loads(build.read_text(encoding="utf-8-sig"))
assert Path(record["private_original_cpu_source"]) == source
assert any(Path(p).name == "JSphCpu_before.obj" for p in record["link"])
assert not any(Path(p).name == "JSphCpu.obj" for p in record["link"])
exe = tests / "outputs/bv_baseline_bv_pair_cpu_r1_r2/bv_pair_cpu_r1.exe"
def bind(p):
    return dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
assert bind(exe)["sha256"] == record["exe_sha256"].lower()
assert next(p["sha256"] for p in record["inputs"] if Path(p["path"]) == source).lower() == bind(source)["sha256"]
result = dict(passed=True, causal_reproduction_with_fresh_original_source=True,
    baseline="Private original CPU source, same current headers and all other authoritative full-Rebuild objects; canonical source/object not replaced",
    rows=72, original_failed_pure_shear_rows=12, initial_vs_recompiled_original_csv_values_identical=True,
    physical_acceptance=False, artifacts=[bind(p) for p in paths+[source,build,exe,Path(__file__)]])
output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
print("PASS: privately recompiled original CPU reproduces exactly the same 12/72 shear failures")
