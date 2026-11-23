"""Same-beta, same-time descriptive comparison of the two release policies through 0.03 s."""
import argparse
import json
import numpy as np
from c08_m0_coupled_baseline_gpu_review_r1 import load,T,TAG,mature


def main(label):
    result=T/"logs"/(TAG+"_contact_"+label+".json")
    assert not result.exists()
    old=T/"outputs"/("c08_m0_release_mature_gpu_r1_w03_"+label)/"data"
    new=T/"outputs"/(TAG+"_w30_"+label)/"data"
    _,src,_=load(mature.hold.PRE,False)
    s=slice(1805,None);initial=src["Posd"][2060:];near=(initial[:,2]<.04)|(initial[:,0]<.04)
    rows=[]
    for i in range(1,4):
        m,a,h=load(new/f"Part_{12+i:04d}.bi4",True)
        n,b,j=load(old/f"Part_{208+20*i:04d}.bi4",True)
        assert m["TimeStep"]==n["TimeStep"] and m["Step"]==n["Step"]==2000200+i*2000-1
        assert np.array_equal(a["Idp"],b["Idp"]) and np.array_equal(a["Idp"],np.r_[0:1805,2060:7060])
        assert m["DynamicArtificialStressActive"]==m["DynamicNoPenetrationActive"]==1
        assert "DynamicArtificialStressActive" not in n and "DynamicNoPenetrationActive" not in n
        assert h[0]["values"]["Scheme"]==j[0]["values"]["Scheme"]
        pressure=a["PorePress"][s].astype(float)-b["PorePress"][s].astype(float)
        sigma=a["SigmaState_kk"][s]-b["SigmaState_kk"][s]-pressure[:,None]
        shear=a["SigmaState_ij"][s]-b["SigmaState_ij"][s]
        rows.append(dict(step=int(m["Step"])+1,t_s=m["TimeStep"],tau_s=m["TimeStep"]-m["GravityPreloadActualTime"],
            p_rms_Pa=float(np.sqrt(np.mean(pressure**2))),p_maxabs_Pa=float(np.max(np.abs(pressure))),
            p_near_left_bed_rms_Pa=float(np.sqrt(np.mean(pressure[near]**2))),
            displacement_pair_max_mm=float(1000*np.linalg.norm(a["Posd"][s]-b["Posd"][s],axis=1).max()),
            total_stress_Frobenius_rms_Pa=float(np.sqrt(np.mean((sigma**2+2*shear**2).sum(axis=1))))))
    result.write_text(json.dumps(dict(beta=label,near_material=int(near.sum()),both_options="AS .3/n2.55 and release-only plane contact",
                                 individual_contribution_identifiable=False,rows=rows),indent=2))
    print(json.dumps(rows))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("label",choices=("b0","b004"));main(p.parse_args().label)
