"""Local regression at the two retained opening-event saves; no solver or whole-window reread."""
import csv
import json
import mmap

import numpy as np

from cryer_p3_radial_r1 import RadialPressure
from cryer_p3_verify_r1 import TESTS, T_D, SOIL, TOTAL, need
from upl_tpi_partial_bi4_r1 import _Cursor, _item


def pressure_fields(mapped,part,step):
    cursor=_Cursor(mapped,64)
    _,_,_,children=_item(cursor,0)
    cursor.finish("file")
    node,arrays,types,_=children[0]
    m=node["values"]
    need(m["Cpart"]==part and m["TimeStep"]==step*2**-19 and m["Step"]==step-1, "event clock")
    need(all(types[k]["type_id"]==t for k,t in (("Idp",8),("PorePress",11),("FSType",8))),"native field types")
    order=np.argsort(arrays["Idp"])
    need(np.array_equal(arrays["Idp"][order],np.arange(TOTAL)),"event IDs")
    return arrays["PorePress"][order[SOIL]],arrays["FSType"][order[SOIL]]


def main():
    tag="cryer_p3_radial_local_r1"
    files=[TESTS/"figures"/(tag+".csv"),TESTS/"figures"/(tag+".png"),TESTS/"logs"/(tag+".check.json")]
    need(not any(p.exists() for p in files),"preserve existing regression artifacts")
    ids_csv=TESTS/"outputs/upl_tpi_cryer_cpu_DebugCPU_B_startup128_r1_native_r2/native_ids.csv"
    with ids_csv.open(newline="") as f:
        particles=[r for r in csv.DictReader(f) if r["is_soil"]=="1"]
    need([int(r["id"]) for r in particles]==list(range(8,TOTAL)),"initial sphere identity")
    volume=np.array([float(r["initial_native_volume_m3"]) for r in particles])
    # Using held material geometry avoids reading Part0 again. The same sphere
    # was independently verified on CPU/GPU at startup.
    radius=np.array([float(r["r0_m"]) for r in particles])
    need(np.all(volume==volume[0]) and radius.max()<.05+1e-14,"initial material volume/radius")
    with (TESTS/"figures/cryer_p3_gpu_drain4097_r1.csv").open(newline="") as f:
        history={int(r["part"]):r for r in csv.DictReader(f)}
    # Same legacy Tv as the reference implementation, E=2 MPa, nu=.3, k=1e-5 m/s.
    nu=.3
    E=2e6
    H=E/(3*(1-2*nu))+4*E/(2*(1+nu))/3
    radial=RadialPressure(H*1e-5/(1000*9.81)/.05**2)
    radial.set_materials(radius,volume)
    results=[]
    for part,step in ((64,4096),(65,4097)):
        data=TESTS/"outputs/cryer_p3_gpu_drain4097_r1/data"/f"Part_{part:04d}.bi4"
        with data.open("rb") as f:
            with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
                p,fs_type=pressure_fields(mm,part,step)
        r=history[part]
        row={k:int(r[k]) for k in ("part","completed_step","surface_count","active_drain_count")}
        row.update({k:float(r[k]) for k in ("tau_s","time_s","center18_Pa","mean_pressure_Pa")})
        need(row["time_s"]==step*2**-19,"history time differs")
        radial.observe(row,p,fs_type)
        bins=radial.frames[part][1]
        direct=float(np.mean(p,dtype=np.float64))
        partition=[s for s in bins if s["material_group"]!="all_soil" and s["count"]]
        # Reconstruct the mean only from the two non-overlapping populations.
        weighted=sum(s["pressure_V0mean_Pa"]*s["initial_volume_m3"] for s in partition)/sum(s["initial_volume_m3"] for s in partition)
        active=sum(s["active_drained_count"] for s in partition)
        need(sum(s["count"] for s in partition)==37173 and active==(0 if part==64 else 5153),"partition count")
        need(abs(weighted-direct)<1e-8 and abs(direct-row["mean_pressure_Pa"])<1e-8,"radial all-soil reconstruction")
        if part==64:
            base=p.astype(float)
        fs=np.isin(fs_type,(2,3))
        dx=p.astype(float)-base
        if part==65:
            need(fs.sum()==5153 and (p[fs]==0).all(),"true drained receivers")
        results.append(dict(part=part,time_s=row["time_s"],active_drained=active,
                            fs23=int(fs.sum()),other_soil=int((~fs).sum()),native_mean_Pa=direct,
                            reconstructed_V0mean_Pa=weighted,absolute_difference_Pa=abs(weighted-direct),
                            other_soil_same_ID_delta_Pa=float(dx[~fs].mean()),
                            shell_other_soil_delta_Pa=[s["pressure_minus_tD_same_ID_V0mean_Pa"] for s in bins if s["material_group"]=="other_soil"]))
    info=radial.write(files[0],files[1])
    audit=dict(passed=True,particle_payloads_read=["Idp","PorePress","FSType"],parts_read=[64,65],
               initial_material_source=str(ids_csv.relative_to(TESTS)),initial_volume_m3=float(volume[0]),
               results=results,**info)
    with files[2].open("x",encoding="utf-8") as f:
        json.dump(audit,f,indent=2,allow_nan=False)
    print(json.dumps(results,indent=2))


if __name__=="__main__":
    main()
