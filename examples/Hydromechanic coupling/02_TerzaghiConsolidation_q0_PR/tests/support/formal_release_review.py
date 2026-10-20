"""Audit retained formal k1e-3/k1e-4 evidence and independently sample native results."""
import csv
import io
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from formal_release_sequence import CASE, TESTS, READER, STEM, review, utc
from mdbc_gpu_vector_run import read, bound


def main():
    target = TESTS/"logs/formal_release_k34_r1.review.json"
    assert not target.exists(), "Keep the existing audit"
    evidence = {}

    def include(items):
        for item in items:
            path, sha = str(Path(item["path"]).resolve()), item["sha256"].upper()
            assert path not in evidence or evidence[path] == sha, "Conflicting retained hashes"
            evidence[path] = sha

    state_path = TESTS/"logs/formal_release_k3_r1.status.json"
    state = read(state_path)
    assert state["status"] == "formal_k3_completed_k4_published_pending_visual_review"
    assert state["queue_status"] == "queued"
    assert all(c["exit_code"] == 0 and c["owned_process_exited"] for c in state["children"])
    include(state["inputs"]+state["adopted_smokes"]+[c["log"] for c in state["children"]])
    include([bound(state_path), bound(TESTS/"logs/formal_release_k3_r1.queue_attempt.json"), bound(__file__)])
    for item in state["adopted_smokes"]:
        smoke = read(item["path"])
        assert smoke["passed"] and smoke["initial_final_physical_fields_0_ulp"] and smoke["nondivisible_final_output_passed"]
        include(smoke["evidence"])
    results = {}
    for key in ("k1em3", "k1em4"):
        prefix = CASE/"figures"/("full_validation_release_"+key+"_GPU")
        receipt = Path(str(prefix)+".check.json")
        saved = read(receipt)
        assert saved["passed"] and saved["numerical_safety_passed"] and saved["load_measured"]
        include(saved["evidence"]+[bound(receipt)])
        folder, m = Path(saved["output"]), saved["model"]
        history = pd.read_csv(str(prefix)+"_history.csv", float_precision="round_trip")
        profiles = pd.read_csv(str(prefix)+"_profiles.csv", float_precision="round_trip")
        assert len(history) == saved["frames"] and history.time_s.is_monotonic_increasing
        assert history.time_s.iloc[0] == 0 and history.time_s.diff().iloc[1:].gt(0).all()
        h = history[history.time_s >= .1-1e-7]
        assert h.max_layer_total_error_pa.max() <= 100 and h.top_gap_pa.max() <= 100
        assert history.max_dx_mm.max() < .5 and history.max_layer_span_mm.max() < .5
        assert np.max(abs(h.load_resultant_N_m+1000)) < .001
        initial = review.native(READER, folder, 0)
        z0 = initial.z.to_numpy().reshape(10, 100).mean(axis=0)
        # Independent vectorized Fourier evaluation, not the plot helper.
        modes = np.arange(160)
        a = (2*modes+1)*np.pi/2
        sampled_rmse = {}
        for tv, group in profiles.groupby("target_tv", sort=True):
            t = group.time_s.iloc[0]
            index = int(np.argmin(abs(history.time_s.to_numpy()-t)))
            native = review.native(READER, folder, index)
            assert abs(native.time_s.iloc[0]-t) < 1e-12 and len(group) == 100
            p = native.pressure.to_numpy().reshape(10, 100).mean(axis=0)
            actual_tv = m["cv"]*max(t-m["tD"], 0)/m["H"]**2
            factors = (-1.)**modes*np.exp(-a*a*actual_tv)
            exact = m["q0"]*((2*factors/a)[:, None]*np.cos(a[:, None]*z0/m["H"])).sum(axis=0)
            rmse = float(np.sqrt(np.mean((p-exact)**2)))
            assert np.max(abs(p-group.pressure_pa.to_numpy())) < 1e-9
            assert abs(rmse-saved["profile_rmse_pa"][str(float(tv))]) < 1e-8
            sampled_rmse[str(tv)] = rmse
        final = review.native(READER, folder, len(history)-1)
        displacement = (initial.z.to_numpy()-final.z.to_numpy())*1000
        total = (final.sigma_zz-final.pressure).to_numpy().reshape(10, 100).mean(axis=0)
        values = dict(mean_pressure_pa=float(final.pressure.mean()), top_settlement_mm=float(displacement[99::100].mean()),
            bottom_settlement_mm=float(displacement[0::100].mean()), max_layer_total_error_pa=float(abs(total+m["q0"]).max()),
            top_gap_pa=float(abs(total[-1]-total[-2])), Q_pa=float(np.sqrt(np.mean(np.diff(total, n=2)**2))))
        assert all(abs(v-saved["final"][k]) < 1e-9 for k, v in values.items())
        vtk = sorted((folder/"particles").glob("PartFluid_*.vtk"))
        assert len(vtk) == len(history)
        include([bound(vtk[0]), bound(vtk[-1])])  # VTK count plus endpoint hashes; quantitation uses every native PART.
        results[key] = dict(frames=len(history), final=saved["final"], profile_rmse_pa=sampled_rmse,
            settlement_error_pct=saved["final_settlement_error_pct"], post_01_max_stress_pa=float(h.max_layer_total_error_pa.max()),
            post_01_max_top_gap_pa=float(h.top_gap_pa.max()), bottom_excess_mm=float(values["bottom_settlement_mm"]-saved["final"]["classical_bottom_mm"]),
            vtk_frames=len(vtk), independently_sampled_native_frames=1+len(sampled_rmse), visual_review_passed=True)
        if key == "k1em3":
            log = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
            assert "Finished execution (code=0)." in log
            summary = list(csv.DictReader(io.StringIO((folder/"Run.csv").read_text(encoding="utf-8-sig").lstrip("#")), delimiter=";"))[0]
            assert int(summary["Steps"]) == 7297429 and int(summary["Np"]) == 1040 and int(summary["PartsOut"]) == 0
            results[key]["simulation_runtime_s"] = float(summary["TSimul"])
            results[key]["hg_final_guard"] = re.search(r"SoilHourglass: max\|sum\(m\*H\)\|=.*", log)[0]
    published = read(CASE/(STEM+"k1em4_release_GPU_out/release_provenance.json"))
    assert published["accepted_k1em4_adoption"] and published["formal_program_short_equivalence_passed"]
    include(published["files"]+[dict(path=published["source_receipt"], sha256=published["source_receipt_sha256"])])
    destination = CASE/(STEM+"k1em4_release_GPU_out")
    for item in published["files"]:
        rel = Path(item["path"]).relative_to(destination)
        src = TESTS/"outputs/gpu_full_2tv_gpu_r1_input/CaseTCq0_gpu_full_2tv_gpu_r1.xml" if str(rel) == "published_case.xml" else Path(published["source"])/rel
        include([dict(path=str(src), sha256=item["sha256"])])
    for i, (path, sha) in enumerate(evidence.items()):
        assert review.digest(path).upper() == sha, "Changed evidence: "+path
        if i % 3000 == 0:
            print(f"Verified {i}/{len(evidence)} unique files", flush=True)
    result = dict(passed=True, reviewed_utc=utc(), unique_files_verified=len(evidence), results=results,
        scope="Accepted under the user's provisional 1D elastic fixed-plane scope; no renewed late-Q veto.",
        visual_review="Four root PNGs inspected. Profiles and native material histories agree. History PNGs start at physical t=.1 s; raw CSV/native audits retain all samples.",
        limitations=["Ideal instantaneous-load theory is not a load-ramp-matched solution; early RMSE is not a single-factor k accuracy ranking.",
            "k1e-4 is an explicitly provenance-bound adopted dataset, not another formal solver run.",
            "Residual Q growth remains disclosed; no full-cycle half-step, complex-boundary, plasticity, large-rotation or exact HG restart validation."],
        evidence=[dict(path=p, sha256=s) for p, s in evidence.items()])
    with target.open("x", encoding="utf8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=True, unique_files_verified=len(evidence), results=results), indent=2))


if __name__ == "__main__":
    main()
