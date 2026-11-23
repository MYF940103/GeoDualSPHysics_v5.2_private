"""Read only original IDs and coordinates and retain fixed material-shell displacement histories."""
import json
import struct
from pathlib import Path

import numpy as np
import pandas as pd
from cryer_p3_verify_r1 import TESTS, TOTAL
from upl_tpi_partial_bi4_r1 import _Cursor, _values


def require(flag,msg):
    if not flag:raise ValueError(msg)


def u32(fp):
    return struct.unpack("<I",fp.read(4))[0]


def part_positions(path,part):
    # The 20 unused array payloads are skipped using binary seeks, not read into memory.
    with path.open("rb") as f:
        header=f.read(64)
        require(header.startswith(b"#FileJBD JPartDataBi4") and header[58:64]==b"\n\0\0\0\0\0","BI4 identity")
        for level in (0,1):
            d=_Cursor(f.read(u32(f)))
            require(d.string()=="\nITEM\n","BI4 item")
            name=d.string()
            d.boolean();d.boolean();d.string();d.string()
            size,children,nval=d.uint(),d.uint(),d.uint()
            d.finish("definition")
            vals,types=_values(_Cursor(f.read(nval)))
            if level==0:
                require(name=="JPartDataBi4" and (size,children)==(0,1) and vals["CaseNfluid"]==37173
                        and vals["CaseNfixed"]==8,"Native root")
            else:
                require(name==f"PART_{part:04d}" and (size,children)==(22,0) and vals["Cpart"]==part and
                        vals["Step"]==max(0,64*part-1) and vals["TimeStep"]==part*2.**-13 and
                        vals["Npok"]==TOTAL and vals["Nout"]==0,"Native PART clock/identity")
        fields={};seen=set()
        for i in range(size):
            d=_Cursor(f.read(u32(f)));require(d.string()=="\nARRAY","Header")
            key=d.string();d.boolean();tp=d.integer();count=d.uint();nbytes=d.uint();d.finish("array")
            require(key not in seen and count==TOTAL,"Duplicate field or count");seen.add(key)
            if key=="Idp":
                require(tp==8 and nbytes==TOTAL*4,"Original material IDs")
                fields[key]=np.frombuffer(f.read(nbytes),dtype="<u4")
            elif key=="Posd":
                require(tp==23 and nbytes==TOTAL*24,"Double XYZ")
                fields[key]=np.frombuffer(f.read(nbytes),dtype="<f8").reshape(TOTAL,3)
            else:f.seek(nbytes,1)
        require(f.tell()==path.stat().st_size and set(fields)=={"Idp","Posd"},"EOF or fields")
    order=np.argsort(fields["Idp"])
    require(np.array_equal(fields["Idp"][order],np.arange(TOTAL)),"Native material ownership")
    return fields["Posd"][order[8:]]


def main():
    tag="cryer_true_surface_old_r1"
    dest=TESTS/"figures"/(tag+".csv");receipt=TESTS/"logs"/(tag+".check.json")
    if dest.exists() or receipt.exists():raise FileExistsError(tag)
    run="CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
    folder=TESTS.parent/run/run/"data"
    p0=part_positions(folder/"Part_0000.bi4",0);r0=np.linalg.norm(p0,axis=1)
    shell=np.rint(r0/.0025).astype(int)
    outer=r0>=.05-2*float(np.float32(.0045));surface=shell==20
    counts=np.bincount(shell,minlength=21)
    with np.load(TESTS/"outputs/cryer_tet_reference_r1.npz") as geo:
        require(np.array_equal(geo["native_ids"],np.arange(8,TOTAL)) and np.array_equal(geo["x0"],p0)
            and np.array_equal(geo["native_surface"],np.flatnonzero(surface)) and np.array_equal(geo["material_shell"],shell),
            "Initial material geometry")
    require(counts[20]==5153 and np.array_equal(outer,shell>=17),"Surface and band identity")
    old=pd.read_csv(TESTS/"figures/cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv",float_precision="round_trip")
    require(len(old)==577 and np.array_equal(old.part,np.arange(577)),"Sealed history")
    rows=[];err=[];identity=[]
    for r in old.itertuples():
        part=int(r.part);pos=p0 if part==0 else part_positions(folder/f"Part_{part:04d}.bi4",part)
        require(64*part==r.completed_step and part*2.**-13==r.time_s and r.surface_count==5153,"Bound saved clock")
        inward=1000*(r0-np.linalg.norm(pos,axis=1));shellmm=np.bincount(shell,weights=inward)[1:]/counts[1:]
        surface_mm=inward[surface].mean();band=inward[outer].mean()
        row=dict(completed_step=64*part,part=part,time_s=r.time_s,tau_s=r.tau_s,
                 surface_mm=surface_mm,outer_band_mm=band)
        row.update({f"shell_{i:02d}_mm":v for i,v in enumerate(shellmm,1)})
        rows.append(row);err.append(abs(band-r.shell_inward_mm))
        identity.append(abs(surface_mm-shellmm[-1]))
    require(max(err)<2e-14 and max(identity)<2e-14,"Old four-shell aggregate or surface sum")
    df=pd.DataFrame(rows);df.to_csv(dest,index=False)
    result=dict(observation="original returned C04 P3",frames=len(rows),soil_ids=TOTAL-8,
                true_surface_ids=int(surface.sum()),band_ids=int(outer.sum()),shell_counts=counts[1:].tolist(),
                shell_membership="material IDs fixed by initial actual radius; outward reference 0.05 m",
                displacement="mean of 1000*(norm(x0)-norm(x)); positive inward, mm",
                payload_fields_read=["Idp","Posd"],skipped_payloads_per_frame=20,
                max_abs_old_band_difference_mm=max(err),max_abs_surface_means_difference_mm=max(identity),
                max_abs_true_minus_band_mm=float(np.max(abs(df.surface_mm-df.outer_band_mm))))
    receipt.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps(result))


if __name__=="__main__":main()

