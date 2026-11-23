"""Audit Eq. (47) sign eligibility on two retained finite-Kw dilative C08 PARTs."""
import hashlib
import csv
import io
import json
import sys
from pathlib import Path
from xml.etree import ElementTree
import numpy as np

T = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(T.parents[1]/"02_TerzaghiConsolidation_q0_PR/tests/support"))
from upl_tpi_partial_bi4_r1 import read

TAG = "c08_eq47_dilative_gate_r1"
RUN = T/"outputs/c08_h18_hg_psi2p5_full3_r1"
WORST = T/"logs/c08_h18_hg_psi2p5_full3_physical_r1.check.json"


def soil(partno):
    path = RUN/"data"/f"Part_{partno:04d}.bi4"
    frame = read(path)
    a, m = frame["arrays"], frame["part"]["values"]
    assert len(a)==22 and m["Cpart"]==partno and m["Nout"]==0 and m["Npok"]==6805
    assert m["SymplecticDtPre"]==5e-6
    assert m["HydroMechDynamicSeepage"] and m["HydroMechFreeSeepage"] and m["GravityPreloadPhase"]==1
    order = np.argsort(a["Idp"])
    ids = a["Idp"][order]
    assert np.array_equal(ids, np.r_[np.arange(1805), np.arange(2060,7060)])
    index = order[1805:]
    field = {key:a[key][index] for key in ("Idp","FSType","PorePress","PorePress0","ExcessPorePress","Kplastic")}
    assert all(np.isfinite(v).all() for v in field.values())
    assert np.array_equal(field["PorePress"]-field["PorePress0"],field["ExcessPorePress"])
    with path.open("rb") as fh:
        digest=hashlib.file_digest(fh,"sha256").hexdigest()
    return field, dict(file=str(path.relative_to(T)),sha256=digest,part=partno,
                       completed_step=int(m["Step"])+1, time_s=float(m["TimeStep"]))


def audit():
    source=json.loads((T/"logs"/(RUN.name+".run.json")).read_text(encoding="utf-8"))
    assert source["passed"] and source["environment_override"]["C08_HG_OPT_H18"]=="1"
    xml=ElementTree.parse(RUN/"c08_h18_as03n255_full3_r1.xml")
    expected={"dlt":2.5,"HydroMechFreeSeepage":1,"HydroMechDrainage":0,"PoreWaterBulkModulus":1e9}
    assert all(float(xml.find(".//"+key).get("value"))==value for key,value in expected.items())
    ref=json.loads(WORST.read_text(encoding="utf-8"))["actual_global_saved_pressure_minimum"]
    old, before=soil(ref["part"]-1)
    current, now=soil(ref["part"])
    assert now["completed_step"]-before["completed_step"]==2000 and now["time_s"]==ref["actual_time_s"]
    p,k,ids=current["PorePress"], current["Kplastic"], current["Idp"]
    fs=np.isin(current["FSType"],[2,3])
    assert np.all(k>=old["Kplastic"]) and np.all(p[fs]<=0)
    peak=np.argmin(p)
    assert ids[peak]==ref["native_id"] and p[peak]==ref["p_Pa"] and fs[peak]
    neg=p<0
    masks={"FS_only":neg&fs,"positive_cumulative_kappa":neg&(k>0),
           "positive_saved_interval_delta_kappa":neg&(k>old["Kplastic"]),
           "negative_excess_instead_of_total":current["ExcessPorePress"]<0}
    comparisons={}
    for key,selected in masks.items():
        missing,extra=neg&~selected,selected&~neg
        comparisons[key]=dict(selected=int(sum(selected)),missed=int(sum(missing)),extra=int(sum(extra)),
                              first_missed_id=int(ids[missing][0]) if missing.any() else None,
                              first_extra_id=int(ids[extra][0]) if extra.any() else None)
    return dict(source_reference=str(WORST.relative_to(T)),inputs=[before,now],physical_steps=0,dt_s=5e-6,
                model="retained finite Kw 1 GPa, psi +2.5 deg, HG enabled",
                total_negative=int(sum(neg)),surface_negative=int(sum(fs&neg)),
                surface_zero=int(sum(fs&(p==0))),surface_positive=int(sum(fs&(p>0))),
                interior_negative=int(sum(~fs&neg)),min_id=int(ids[peak]),min_p_Pa=float(p[peak]),
                min_row_kappa=float(k[peak]),min_row_saved_interval_delta_kappa=float(k[peak]-old["Kplastic"][peak]),
                comparisons=comparisons)


if __name__=="__main__":
    result=audit()
    out=T/"logs"/(TAG+".check.json")
    if out.exists():
        assert json.loads(out.read_text(encoding="utf-8"))==result
    else:
        with out.open("x",encoding="utf-8") as fh:
            fh.write(json.dumps(result,indent=2)+"\n")
    table=io.StringIO()
    writer=csv.writer(table,lineterminator="\n")
    writer.writerow(("criterion","selected","missed","extra"))
    writer.writerow(("negative_total_pressure",result["total_negative"],0,0))
    for label,v in result["comparisons"].items():
        writer.writerow((label,v["selected"],v["missed"],v["extra"]))
    path=T/"figures"/(TAG+".csv")
    if path.exists():
        assert path.read_text(encoding="utf-8")==table.getvalue()
    else:
        with path.open("x",encoding="utf-8",newline="") as fh:
            fh.write(table.getvalue())
    print(json.dumps(result,indent=2))
