"""Prepare the refined C08 receiver and characterize its independent preload before release."""
import argparse
import copy
import csv
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np

from c08_dp03125_pre import DP, GEN, LOG, PRELOAD_TAG, SEED, TESTS, load, read, verified_seed
from c08_psi25_tpi_native import OPEN, PRE, SOURCE, require, verify_source_material
from c08_psi25_tpi_run import SEED as BASE_RECEIVER, expected_xml, identity, record

FINE_RECEIVER = TESTS/"outputs/c08_dp03125_tpi_seed_r1"/SEED.name
FINE_PRE = TESTS/"outputs"/PRELOAD_TAG/"data/Part_1000.bi4"
BUILD = TESTS/"outputs/c08_dp03125_tpi_build_r1/build.json"
OUT = TESTS/"figures/c08_positive_localization/refined_preload_profiles.csv"


def prepare_receiver():
    seed = verified_seed()
    build = load(BUILD)
    require(build["seed"]==identity(GEN/"seed.json") and build["executable"]==identity(Path(build["program"])),
            "Private receiver and refined seed are unbound")
    archived_xml = BASE_RECEIVER.with_suffix(".xml")
    require(archived_xml.read_bytes()==expected_xml(), "Sealed positive-only receiver inputs changed")
    previous = ET.parse(archived_xml)
    fine = ET.parse(SEED.with_suffix(".xml"))
    execution = fine.find("execution")
    # Generated geometry, particle IDs, sound speed and particle mass come from the fine seed.
    # Explicitly adopt only the baseline receiver's physics and integration options.
    for field in ("special","parameters"):
        execution.remove(execution.find(field))
        execution.insert(0 if field=="special" else 1,copy.deepcopy(previous.find(f"execution/{field}")))
    special = execution.find("special")
    gravity = special.find("gravitypreload")
    require(gravity.get("release_mkbound")=="2" and gravity.get("keep_bed_overlap")=="false" and
            gravity.get("elastic_source")=="false" and
            special.find("drainage").get("mode")=="freeSeepage" and
            special.find("hydromechanics/HydroMechModel").get("value")=="2" and
            special.find("hydromechanics/HydroMechConductivityCk").get("value")=="2" and
            execution.find("constants/dp").get("value")=="0.03125", "Release policy or spacing mismatch")
    gravity.set("statefile",str(FINE_PRE))
    FINE_RECEIVER.parent.mkdir()
    fine.write(FINE_RECEIVER.with_suffix(".xml"),encoding="utf8",xml_declaration=True)
    paths = [FINE_RECEIVER.with_suffix(".xml")]
    for suffix in (".bi4","_Normals.nbi4"):
        src = SEED.parent/(SEED.name+suffix)
        dest = FINE_RECEIVER.parent/(FINE_RECEIVER.name+suffix)
        shutil.copy2(src,dest)
        require(src.read_bytes()==dest.read_bytes(),f"Copied seed differs: {dest.name}")
        paths.append(dest)
    record(FINE_RECEIVER.parent/"inputs.json",dict(original_receiver=identity(archived_xml),
        refined_seed=identity(GEN/"seed.json"), build=identity(BUILD), future_pre=str(FINE_PRE),
        beta=.04, closed_updates=OPEN-SOURCE, positive_surface_cap=True,
        material=seed["material"], fixed=seed["fixed"], fixed_parts=seed["fixed_parts"],
        files=[identity(p) for p in paths], prepared_only=True))
    print(FINE_RECEIVER,flush=True)


def profile(path, group, dp):
    ini = read(path.with_name("Part_0000.bi4"))
    late = read(path)
    base, final = (r["arrays"] for r in (ini,late))
    require(ini["root"]["values"]["Dp"]==late["root"]["values"]["Dp"]==dp and
            int(late["part"]["values"]["Step"])+1==SOURCE, "Wrong fine or coarse PRE")
    verify_source_material(late["part"]["values"],"psi2p5")
    for arrays in (base, final):
        require(len(arrays)==22, "Expected 22 original fields")
    initial, closing = [np.argsort(arrays["Idp"]) for arrays in (base,final)]
    require(np.array_equal(base["Idp"][initial],final["Idp"][closing]),"Preload material ordering changed")
    nfix = int(late["root"]["values"]["CaseNfixed"])
    xz = base["Posd"][initial[nfix:]][:,[0,2]]
    a = {key:val[closing[nfix:]] for key,val in final.items()}
    central = (xz[:,0]>=1)&(xz[:,0]<3)
    rows = []
    for i in range(1,19):
        zlo, zhi = i/10,(i+1)/10
        layer = central & (xz[:,1]>=zlo) & (xz[:,1]<zhi)
        w = a["PoroCurrentVolume"][layer]
        pw = a["PorePress"][layer].astype(float)/1000
        eff = -a["SigmaState_kk"][layer,2]/1000
        v = a["Vel"][layer]
        require(w.size and (w>0).all(), "Missing center comparison layer")
        means = [float(np.average(vv,weights=w)) for vv in
                 (a["Posd"][layer,2],pw,eff,pw+eff,a["PoroVolumeRatio"][layer])]
        rows.append(dict(run=group,dp_m=dp,absolute_time_s=float(late["part"]["values"]["TimeStep"]),
            z0_lo_m=zlo,z0_hi_m=zhi,soil_count=int(layer.sum()),area_m2=float(w.sum()),mean_current_z_m=means[0],
            p_kPa=means[1],effective_zz_compression_kPa=means[2],total_zz_compression_kPa=means[3],mean_J=means[4],
            max_speed_m_s=float(np.linalg.norm(v,axis=1).max()),max_kappa=float(a["Kplastic"][layer].max())))
    return rows


def compare_preloads():
    receipt = load(LOG/(PRELOAD_TAG+".check.json"))
    require(receipt["passed"] and receipt["frames"]==1001 and receipt["source_schema2"] and
            receipt["final_native"]==identity(FINE_PRE), "Full refined PRE lacks a bound native review")
    rows = [*profile(PRE,"baseline",.04),*profile(FINE_PRE,"refined",DP)]
    require(all(rows[i]["absolute_time_s"]==rows[i+18]["absolute_time_s"] for i in range(18)),
            "Coarse and fine final times differ")
    with OUT.open("x",encoding="utf8",newline="") as f:
        writer = csv.DictWriter(f,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(OUT)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("prepare","compare-preloads"))
    if parser.parse_args().mode=="prepare":
        prepare_receiver()
    else:
        compare_preloads()
