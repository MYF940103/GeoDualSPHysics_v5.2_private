"""Localize the analytical Cryer momentum residual at the original particle positions."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from cryer_load_pair_r1 import add_pair, batches, correction
from cryer_p3_peak_shells import ordered
from cryer_peak_paired_manufactured import TAG as PAIR_TAG, radial_state
from cryer_shell_equilibrium import TESTS, Q, R, Reference, need, write


TAG = "cryer_peak_force_moments_r1"


def multiply(tensor, vector):
    return np.einsum("nij,nj->ni", tensor, vector)


def rms(vector):
    return np.sqrt(np.mean(np.sum(vector**2, axis=1)))


def main(output):
    source = json.loads((TESTS/"logs"/(PAIR_TAG+".check.json")).read_text(encoding="utf8"))
    baseline = pd.read_csv(TESTS/"figures"/(PAIR_TAG+"_regions.csv"))
    table = TESTS/"figures"/(TAG+"_regions.csv")
    shells = TESTS/"figures"/(TAG+"_shells.csv")
    check = TESTS/"logs"/(TAG+".check.json")
    need(not any(p.exists() for p in (table,shells,check)), "Preserve earlier analyses")
    st = ordered(output/"data", 0, ["Posd","PoroCurrentVolume","PoroMixtureDensity","FSType"])
    x, v, rho = (st[name] for name in ("Posd","PoroCurrentVolume","PoroMixtureDensity"))
    er = x/np.linalg.norm(x,axis=1)[:,None]
    sid = np.rint(np.linalg.norm(x,axis=1)/.0025).astype(int)
    ref = Reference(.3,finite=False)
    ref.cv = ref.H*ref.kappa
    ref.decay = ref.xi**2*ref.cv/R**2
    p, rr, tt, _ = radial_state(ref,np.arange(1,21)*.0025,source["tau_s"])
    need(abs(p[0]-source["pressure_center_Pa"])<1e-8,"Reproduce same M0 pressure")
    T = ((tt+Q-p)[sid-1,None,None]*np.eye(3)
         +(rr-tt)[sid-1,None,None]*er[:,:,None]*er[:,None,:])
    h = float(np.float32(.0045))
    pairs = cKDTree(x).query_pairs(2*h,output_type="ndarray")
    C,_ = correction(x,v*rho,rho,h,pairs)
    mass = v*rho
    total = np.zeros((2,len(x),3))
    constant = np.zeros_like(total)
    gradient = np.zeros_like(total)
    for i,j,dr,g in batches(x,pairs,h):
        dv = (v[i]*v[j])[:,None]
        dT = T[j]-T[i]
        for method,(gi,gj) in enumerate(((g,g),(multiply(C[i],g),multiply(C[j],g)))):
            # Endpoint i sees its own constant tensor acting on both gradients.
            # Endpoint j uses its own tensor, so only the recombined force is antisymmetric.
            gg = gi+gj
            direct = dv*(multiply(T[i],gi)+multiply(T[j],gj))
            add_pair(total[method],i,j,direct,-direct)
            add_pair(constant[method],i,j,dv*multiply(T[i],gg),-dv*multiply(T[j],gg))
            add_pair(gradient[method],i,j,dv*multiply(dT,gj),dv*multiply(dT,gi))
    total /= mass[None,:,None]
    constant /= mass[None,:,None]
    gradient /= mass[None,:,None]
    max_recomb = float(abs(total-constant-gradient).max())
    need(max_recomb<1e-8, "Pointwise recombination for all particles and components")
    region_rows, shell_rows = [],[]
    groups = ((name,mask) for name,mask in (
        ("center18",sid==1),("inner10",sid<=10),("all",sid>=1),
        ("true_surface",np.isin(st["FSType"],(2,3)))))
    masks = list(groups)+[(f"shell{j:02d}",sid==j) for j in range(1,21)]
    for k,label in enumerate(("A_raw","D_pair_adjoint")):
        for name,mask in masks:
            a, c, d = (vec[k,mask] for vec in (total,constant,gradient))
            inward = lambda vec: -np.mean(np.einsum("ij,ij->i",vec,er[mask]))
            rms_total,rms_c,rms_d = (rms(vec) for vec in (a,c,d))
            cross = np.sum(c*d,axis=1).mean()
            need(abs(rms_total**2-rms_c**2-rms_d**2-2*cross)<1e-8,
                 "Quadratic residual decomposition")
            row = dict(operator=label,region=name,count=int(mask.sum()),total_rms_m_s2=rms_total,
                constant_rms_m_s2=rms_c,difference_rms_m_s2=rms_d,
                mean_inward_total_m_s2=inward(a),mean_inward_constant_m_s2=inward(c),
                mean_inward_difference_m_s2=inward(d),mean_constant_dot_difference=cross,
                vector_cosine=cross/(rms_c*rms_d))
            if name.startswith("shell"):
                shell_rows.append(row)
            else:
                prior = baseline.loc[(baseline.geometry=="initial_reference_sphere")
                                     &(baseline.operator==label)&(baseline.region==name)]
                need(len(prior)==1 and abs(prior.iloc[0].vector_rms_m_s2-rms_total)<1e-8,
                     "Reproduce previously reported region RMS")
                region_rows.append(row)
    write(table,region_rows);write(shells,shell_rows)
    with check.open("x",encoding="utf8") as f:
        json.dump(dict(part=source["part"],tau_s=source["tau_s"],pairs=len(pairs),
            particles=len(x),max_recombination_component_m_s2=max_recomb,
            method="Every target decomposes its original force into a locally constant tensor times the pair gradients and a neighbor tensor difference. They recombine; neither summand alone is an admissible conservative force."),f,indent=2,allow_nan=False)
    print(pd.DataFrame(region_rows).to_string(index=False))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output",type=Path)
    main(ap.parse_args().output)
