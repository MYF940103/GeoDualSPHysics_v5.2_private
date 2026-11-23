"""Review a returned public model-2, nu=.30 Cryer 1-Tv run in the local repository."""
import argparse
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"tests/support"))
from cryer_p3_verify_r1 import CENTER, SOIL, T_D, need, physical
from cryer_live_history_review import read_frame
from cryer_p3_radial_r1 import RadialPressure
from cryer_p3_return_r1 import Reference, compare


def public_history(data,steps,radial=None):
    """Read public PARTs including their committed pressure-history child."""
    dt=2.**-19
    names=[f"Part_{i:04d}.bi4" for i in range(len(steps))]
    need(sorted(p.name for p in data.glob("Part_*.bi4"))==names,"Unexpected native frame series")
    rows=[]
    for part,(name,step) in enumerate(zip(names,steps)):
        root,item,a,previous=read_frame(data/name,part,step,dt,step>0,sorted_history=False)
        meta=item["values"]; config=root["values"]
        need(meta.get("HydroMechModel")==2 and meta.get("HydroMechDynamicSeepage")==1 and
             config["Dp"]==.0025 and config["H"]==float(np.float32(.0045)),"Wrong pressure model or sphere")
        error=float(meta["dterror"])
        need(np.isfinite(error) and error<=1e-14 and (not part or error!=-sys.float_info.max),"Invalid signed dt margin")
        if not part:
            initial=a["Posd"].copy()
            need(np.flatnonzero(np.linalg.norm(initial,axis=1)<=.0025+1e-12).tolist()==CENTER,
                 "Initial 18 material IDs differ")
            need(all(not np.any(a[k]) for k in ("Vel","PorePress","SigmaState_kk","SigmaState_ij")),"Initial rest state differs")
            if radial is not None:radial.set_materials(np.linalg.norm(initial[SOIL],axis=1),a["PoroCurrentVolume"][SOIL])
        time=float(meta["TimeStep"])
        row=dict(part=part,completed_step=step,time_s=time,tau_s=time-T_D,signed_dterror_s=error,
                 pressure_history_owners=0 if previous is None else len(previous))
        row.update(physical(a,initial,time>T_D))
        if radial is not None:radial.observe(row,a["PorePress"][SOIL],a["FSType"][SOIL])
        rows.append(row)
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output",type=Path)
    ap.add_argument("destination",type=Path)
    args=ap.parse_args()
    case="CaseCryer_TPI_nu030_1Tv"
    input_xml=ET.parse(args.output/(case+".xml"))
    model=input_xml.find("execution/special/hydromechanics/HydroMechModel")
    need(model is not None and model.get("value")=="2","Public TPI XML required")
    need("HydroMechModel=2" in (args.output/"Run.out").read_text(errors="replace"),"Model 2 run log required")
    with (HERE/"CaseCryer_TPI_P3_nu030_full_r1_schedule.csv").open(newline="") as f:
        steps=[int(row["completed_steps"]) for row in csv.DictReader(f)]
    need(len(steps)==265 and steps[-1]==481685,"Full output schedule differs")
    need(not args.destination.exists(),"Choose a fresh review folder")
    ref=Reference(.3,finite=False)
    radial=RadialPressure(ref.legacy_cv/.05**2)
    history=public_history(args.output/"data",steps,radial)
    frame,summary=compare(history,None,"full",ref)
    args.destination.mkdir(parents=True,exist_ok=False)
    frame.to_csv(args.destination/"native_and_theory.csv",index=False)
    summary["peak_assessment"]="The separate native P3 dense peak missed its 1% amplitude and 2% timing limits."
    summary["radial_pressure"]=radial.write(args.destination/"radial_pressure.csv",args.destination/"radial_pressure.png")
    (args.destination/"physical_review.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    fig,ax=plt.subplots(figsize=(7.2,4.2),layout="constrained")
    rows=frame[frame.legacy_Tv>0]
    ax.plot(rows.legacy_Tv,rows.M0_r18_Pa/1000,label="M0 analytical",color="black")
    ax.plot(rows.legacy_Tv,rows.center18_Pa/1000,".",markersize=3,label="Public TPI, 18 material IDs")
    ax.set(xscale="log",xlabel="Time factor after drainage, Tv",ylabel="Pore pressure (kPa)")
    ax.legend();ax.grid(alpha=.2)
    fig.savefig(args.destination/"center18.png",dpi=180)
    plt.close(fig)


if __name__=="__main__":
    main()
