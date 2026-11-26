"""Frozen Bui-AS test on positive-only C08 saved stress states; not force-stage accelerations."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from c08_h18_wend_partial_review_r1 import kernel
from c08_positive_suction_sites import DP, H, OUT, RUNS, checked
from c08_psi25_tpi_native import SOIL_IDS, TESTS, require


def source_proof(tag):
    build=TESTS/"outputs/c08_psi25_tpi_build_r2"
    base=TESTS/"outputs/c08_m0_gpu_coupled_r1_build"
    linked={Path(s.strip('"')).resolve() for s in (build/"link.rsp").read_text().splitlines() if ".obj" in s.lower()}
    require((base/"JSphGpu_ker.cu.obj").resolve() in linked and (base/"JSphGpu.obj").resolve() in linked,
            "Expected retained host and private physical CUDA objects")
    call=json.loads((TESTS/"logs"/(tag+".call.json")).read_text())
    exe=Path(call["exe"]["path"])
    require(exe.parent==build and exe.stat().st_size==call["exe"]["bytes"] and
            exe.stat().st_mtime_ns==call["exe"]["mtime_ns"],"Different +2.5 degree executable")
    host=(base/"JSphGpu.cpp").read_text(encoding="utf8",errors="replace")
    cu=(base/"JSphGpu_ker.cu").read_text(encoding="utf8",errors="replace")
    require("ArtificialStressg,PorePressg);" in host and all(s in cu for s in (
        "float(sig.xx-pw)","float(sig.yy-pw)","float(sig.zz-pw)","float(sig.xz)","1.f,CTE.artificialstresscoef",
        "rp[a]=(eval[a]>0.f? -coef*eval[a]*rrhop2: 0.f)","maxoff<=1e-6f*scale",
        "porovol2/pororhot1*double(powf(ratio,CTE.artificialstressexp))",
        "const tsymatrix3f sigmap2=KerStressToFloat(sigma[p2]);",
        "double(sigmap1_xx_xy.x)+sigmap2_xx_xy.x-pw")), "Different J-based AS or material stress source")


def spectrum(a):
    diag=a["SigmaState_kk"]
    pw=a["PorePress"].astype(float)
    off=a["SigmaState_ij"]
    require(np.all(off[:,:2]==0),"Nonzero xy or yz requires a full 3D spectral analysis")
    T=(diag-pw[:,None]).astype(np.float32)
    xz=off[:,2].astype(np.float32)
    plane=np.empty((len(pw),2,2))
    plane[:,0,0]=T[:,0]
    plane[:,1,1]=T[:,2]
    plane[:,0,1]=plane[:,1,0]=xz
    lam,vec=np.linalg.eigh(plane)
    positive=(vec*np.maximum(lam,0.)[:,None,:])@vec.swapaxes(1,2)
    eff=np.linalg.eigvalsh(plane+pw[:,None,None]*np.eye(2))[:,1]
    # Replay the xz Jacobi rotations of the private 3D device helper on float inputs.
    # cpu sin/cos/FMA rounding can differ; track actual sign disagreements against eigh.
    xx,zz,upper,lower=T[:,0].copy(),T[:,2].copy(),xz.copy(),xz.copy()
    for _ in range(16):
        rot=abs(upper)>np.float32(1e-6)*(abs(xx)+abs(T[:,1])+abs(zz)+np.float32(1))
        if not np.any(rot): break
        u,v,x,y=xx[rot],zz[rot],upper[rot],lower[rot]
        phi=np.float32(.5)*np.arctan2(np.float32(2)*x,v-u)
        c,sn=np.cos(phi),np.sin(phi)
        p1,p2=c*u-sn*x,c*y-sn*v
        q1,q2=sn*u+c*x,sn*y+c*v
        xx[rot],zz[rot]=c*p1-sn*p2,sn*q1+c*q2
        upper[rot],lower[rot]=c*q1-sn*q2,sn*p1+c*p2
    return lam[:,1],T[:,1],positive,eff,np.maximum(xx,zz)


def run():
    tag=RUNS["beta004"]
    source_proof(tag)
    rec=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
    require(rec["passed"] and rec["tag"]==tag and rec["frames"]==132,"Wrong retained positive baseline")
    partners={6918:None,7014:7015,7015:7014,6965:6966,6966:6965,6969:6970,6970:6969}
    out=[]
    for part in range(72,133):
        m,a,_=checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",rec)
        require(m["DynamicArtificialStressActive"] and m["DynamicArtificialStressPolicy"]=="ReleaseOnly"
                and m["DynamicArtificialStressCoef"]==np.float32(.3)
                and m["DynamicArtificialStressExp"]==np.float32(2.55),"Different actual AS parameters")
        plane,yy,positive,eff,jacobi=spectrum(a)
        full=np.maximum(plane,yy)
        pos=a["Posd"][:,[0,2]]
        fix=len(pos)-len(SOIL_IDS)
        tree=cKDTree(pos)
        ndim_sign_mismatch=int(np.sum((plane[fix:]>0)!=(jacobi[fix:]>0)))
        for rid,partner in partners.items():
            i=int(np.searchsorted(a["Idp"],rid))
            js=np.asarray(tree.query_ball_point(pos[i],2*H),int)
            js=js[js!=i]
            dr=pos[js]-pos[i]
            dist=np.linalg.norm(dr,axis=1)
            require(np.all(dist>0),"Coincident neighbor at target")
            near=dr/dist[:,None]
            bracket=np.einsum("ij,ijk,ik->i",near,positive[i]+positive[js],near)
            if part==72 and rid==6918:
                require(np.all(bracket>=-1e-6),"Negative projected positive spectrum")
            soil=js>=fix
            wall=~soil
            j=int(js[soil][np.argmin(dist[soil])]) if partner is None else int(np.searchsorted(a["Idp"],partner))
            at=int(np.flatnonzero(js==j)[0])
            w,_=kernel(dist**2,H,np.float32(.557/H**2),np.float32(-2.7852/H**3))
            wd,_=kernel(np.asarray([DP**2]),H,np.float32(.557/H**2),np.float32(-2.7852/H**3))
            kernel_ratio=np.power(w/wd[0],float(np.float32(2.55)))
            weight=.3*kernel_ratio
            strength=weight*bracket
            row=dict(part=part,step=m["Step"]+1,tau_s=m["TimeStep"]-rec["release_time_s"],
                     focus=rid,partner=int(a["Idp"][j]),partner_kind="nearest_soil" if partner is None else "original_pair",
                     gap_dp=dist[at]/DP,fs=int(a["FSType"][i]),kappa=a["Kplastic"][i],J=a["PoroVolumeRatio"][i],
                     p_kPa=a["PorePress"][i]/1000,effective_xz_max_kPa=eff[i]/1000,
                     total_xz_max_kPa=plane[i]/1000,total_yy_kPa=float(yy[i])/1000,total_3d_max_kPa=full[i]/1000,
                     total_xz_jacobi_kPa=float(jacobi[i])/1000,pair_n_Tpositive_n_kPa=bracket[at]/1000,
                     AS_weighted_radial_pressure_kPa=-strength[at]/1000,
                     partner_xz_max_kPa=plane[j]/1000,soil_neighbors=int(soil.sum()),
                     soil_tensile_xz=int((plane[js[soil]]>0).sum()),soil_tensile_3d=int((full[js[soil]]>0).sum()),
                     max_neighbor_xz_kPa=float(plane[js[soil]].max()/1000), max_AS_weighted_soil_bracket_kPa=strength[soil].max()/1000,
                     wall_neighbors=int(wall.sum()), wall_tensile_xz_geometry_only=int((plane[js[wall]]>0).sum()),
                     wall_max_xz_geometry_only_kPa=plane[js[wall]].max()/1000 if np.any(wall) else "",
                     cuda_model_sign_mismatch_in_focus_neighbors=int(np.sum((plane[js]>0)!=(jacobi[js]>0)))+int((plane[i]>0)!=(jacobi[i]>0)),
                     cuda_model_sign_mismatch_all_soil=ndim_sign_mismatch)
            out.append(row)
    require(len(out)==427,"Incomplete late-window output")
    with (OUT/"frozen_pair_artstress.csv").open("x",encoding="utf8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=out[0])
        writer.writeheader()
        writer.writerows(out)


def save_pair_brackets():
    """Group the native main stress and artificial stress along each current pair direction."""
    tag=RUNS["beta004"]
    source_proof(tag)
    receipt=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
    require(receipt["passed"] and receipt["tag"]==tag and receipt["frames"]==132,"Different native baseline")
    with (OUT/"frozen_pair_artstress.csv").open(encoding="utf8",newline="") as stream:
        original=list(csv.DictReader(stream))
    focus_ids={6918,7014,6965,6969}
    rows=[]
    for part in range(72,133):
        meta,arrays,_=checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",receipt)
        selected=[r for r in original if int(r["part"])==part and int(r["focus"]) in focus_ids]
        require(len(selected)==4 and {int(r["focus"]) for r in selected}==focus_ids,"Missing pair")
        for row in selected:
            ids=[int(row["focus"]),int(row["partner"])]
            pair=np.searchsorted(arrays["Idp"],ids)
            require(np.array_equal(arrays["Idp"][pair],ids) and int(row["step"])==meta["Step"]+1,"Native clocks or IDs differ")
            d=(arrays["Posd"][pair[1]]-arrays["Posd"][pair[0]])[[0,2]]
            distance=np.linalg.norm(d)
            require(abs(distance/DP-float(row["gap_dp"]))<1e-10,"Different particle positions")
            nx,nz=d/distance
            # The GPU momentum helper casts each effective tensor to float before subtracting gauge pressure.
            diag=arrays["SigmaState_kk"][pair].astype(np.float32).astype(float).sum(axis=0)
            diag-=arrays["PorePress"][pair].sum(dtype=float)
            sxz=arrays["SigmaState_ij"][pair,2].astype(np.float32).sum(dtype=float)
            stress=(diag[0]*nx**2 + 2*sxz*nx*nz + diag[2]*nz**2)/1000
            artstress=float(row["AS_weighted_radial_pressure_kPa"])
            rows.append(dict(part=part,step=row["step"],tau_s=row["tau_s"],focus=ids[0],partner=ids[1],
                             partner_kind=row["partner_kind"],gap_dp=row["gap_dp"],nx=nx,nz=nz,
                             stress_radial_kPa=stress,AS_radial_kPa=artstress,
                             combined_stress_radial_kPa=stress+artstress))
    require(len(rows)==244,"Incomplete pair history")
    with (OUT/"pair_stress_brackets.csv").open("x",encoding="utf8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-brackets",action="store_true",help="also use the retained AS radial table to compare stress contributions")
    if parser.parse_args().pair_brackets:
        save_pair_brackets()
    else:
        run()
