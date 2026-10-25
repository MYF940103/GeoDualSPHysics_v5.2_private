"""Frozen Cryer force moments and load-only correction counterexample.

No solver state or physical operator is modified. Read the saved native load,
then evaluate a double-arithmetic reproduction on its rounded saved geometry.
"""
from pathlib import Path
import sys
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

CASE=Path(__file__).resolve().parents[2]
TESTS=CASE/'tests'
LIAN=CASE.parent/'05_LianFlexibleStrip2D_PR/tests/scripts'
sys.path.insert(0,str(LIAN))
from lian_release_r1 import native,bound,write_json,READER

TAG='cryer_load_audit_r1'


def moments(a,load,q=10000.,radius=.05):
    x=a[['x','y','z']].to_numpy();m=a.mass.to_numpy();force=m[:,None]*load
    volume=4*np.pi*radius**3/3
    tensor=-force.T@x/(q*volume)
    r=np.linalg.norm(x,axis=1)
    return dict(radial_force_over_geometric_area_q=float(-np.sum(force*x/np.where(r>0,r,1)[:,None])/(q*4*np.pi*radius**2)),
                net_force_over_area_q=float(np.linalg.norm(force.sum(axis=0))/(q*4*np.pi*radius**2)),
                affine_work_over_3qV=float(np.trace(tensor)/3),moment_tensor_over_qV=tensor.tolist())


def frozen(a):
    x=a[['x','y','z']].to_numpy();rho=a.rho.to_numpy();m=a.mass.to_numpy();h=float(a.h.iloc[0]);q=10000.
    ij=cKDTree(x).query_pairs(2*h,output_type='ndarray');i,j=ij.T
    d=x[i]-x[j];r=np.linalg.norm(d,axis=1)
    # Production uses rounded decimal Wendland constants, not exact 21/(16*pi).
    fac=(-2.08891/h**5)*(1-.5*r/h)**3
    g=fac[:,None]*d
    ai=(q*m[j]*(rho[i]**-2+rho[j]**-2))[:,None]*g
    aj=-(q*m[i]*(rho[i]**-2+rho[j]**-2))[:,None]*g
    raw=np.zeros_like(x);np.add.at(raw,i,ai);np.add.at(raw,j,aj)
    moment=np.zeros((len(x),3,3))
    for row in range(3):
        for col in range(3):
            term=-d[:,row]*g[:,col]
            np.add.at(moment[:,row,col],i,m[j]/rho[j]*term)
            np.add.at(moment[:,row,col],j,m[i]/rho[i]*term)
    correction=np.linalg.inv(moment)
    corrected=np.einsum('nij,nj->ni',correction,raw)
    # Manufactured sigma=-qI, p=0: original internal force is exactly -raw.
    # Correcting only load leaves (C-I)raw, even in this uniform-stress field.
    residue=corrected-raw
    stored=a[['load_ax','load_ay','load_az']].to_numpy()
    return raw,corrected,dict(pair_count=len(ij),moment_condition_max=float(np.linalg.cond(moment).max()),
        reproduced_vs_saved_relative_rms=float(np.linalg.norm(raw-stored)/np.linalg.norm(stored)),
        load_only_correction_uniform_stress_residual_rms_m_s2=float(np.sqrt(np.mean(residue**2))),
        load_only_correction_uniform_stress_residual_max_m_s2=float(np.linalg.norm(residue,axis=1).max()),
        original_manufactured_uniform_stress_residual_m_s2=0.,
        raw=moments(a,raw),load_only_corrected=moments(a,corrected))


def main():
    receipt=TESTS/'logs'/(TAG+'.json');assert not receipt.exists()
    folder=CASE/'CaseCryerProblem_PR_out'
    parts=sorted((folder/'data').glob('Part_*.bi4'));assert len(parts)>50
    initial=native(folder,0)
    radius=np.linalg.norm(initial[['x','y','z']],axis=1)
    qvolume=4*np.pi*.05**3/3
    rows=[];evidence=[bound(__file__),bound(READER),bound(LIAN/'lian_release_r1.py'),bound(folder/'Run.out'),bound(parts[0])]
    first=None
    for part in [1,50,len(parts)-1]:
        a=native(folder,part)
        assert np.array_equal(a.id,initial.id) and a.load_available.eq(1).all() and np.isfinite(a.to_numpy()).all()
        if first is None:first=a
        stats=moments(a,a[['load_ax','load_ay','load_az']].to_numpy())
        rows.append(dict(part=part,time_s=float(a.time_s.iloc[0]),**{k:v for k,v in stats.items() if not isinstance(v,list)}))
        evidence.append(bound(parts[part]))
    raw,corrected,screen=frozen(first)
    bins=[]
    r=np.linalg.norm(first[['x','y','z']],axis=1);unit=first[['x','y','z']].to_numpy()/np.where(r>0,r,1)[:,None]
    stored=first[['load_ax','load_ay','load_az']].to_numpy()
    for left,right in zip(np.linspace(0,.055,23)[:-1],np.linspace(0,.055,23)[1:]):
        mask=(r>=left)&(r<right)
        if not mask.any():continue
        bins.append(dict(radius_mid_m=(left+right)/2,count=int(mask.sum()),
                         saved_inward_acc_m_s2=float(-(stored[mask]*unit[mask]).sum(axis=1).mean()),
                         raw_double_inward_acc_m_s2=float(-(raw[mask]*unit[mask]).sum(axis=1).mean()),
                         load_only_corrected_inward_acc_m_s2=float(-(corrected[mask]*unit[mask]).sum(axis=1).mean())))
    history=pd.DataFrame(rows);profile=pd.DataFrame(bins)
    csvs=[TESTS/'figures'/(TAG+s) for s in ('_moments.csv','_profile.csv')]
    history.to_csv(csvs[0],index=False,float_format='%.17g');profile.to_csv(csvs[1],index=False,float_format='%.17g')
    fig,axes=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
    for field,color,style in [('saved_inward_acc_m_s2','#215a8a','-'),('raw_double_inward_acc_m_s2','#b56b28','--'),('load_only_corrected_inward_acc_m_s2','#6a7450',':')]:
        axes[0].plot(profile.radius_mid_m*1000,profile[field],style,color=color,label=field.replace('_inward_acc_m_s2',''))
    axes[0].set(xlabel='Saved radius (mm)',ylabel='Mean inward load acceleration (m/s2)');axes[0].legend(fontsize=8)
    axes[1].plot(history.time_s,history.radial_force_over_geometric_area_q,'o-',label='Radial force / qA')
    axes[1].plot(history.time_s,history.affine_work_over_3qV,'s--',label='Affine virtual work / 3qV')
    axes[1].axhline(1,color='.4',lw=.8);axes[1].set(xlabel='Actual retained time (s)',ylabel='Dimensionless load descriptors');axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('Frozen Cryer load audit - load-only correction is NOT a coupled candidate')
    png=TESTS/'figures'/(TAG+'.png');fig.savefig(png,dpi=160);plt.close(fig)
    result=dict(scope='Frozen diagnostic only; no production/formal changes or solver run',soil_count=len(initial),
        saved_initial_radius_max_m=float(radius.max()),native_volume_over_sphere=float((initial.mass/initial.rho).sum()/qvolume),
        rows=rows,frozen_screen=screen,sources=evidence,artifacts=[bound(p) for p in csvs+[png]],
        limits=['An unweighted radial-force sum is not by itself the true boundary traction error of a distributed force.',
                'Saved old positions are float; reproduction is not a 0-ULP clone of original neighbor arithmetic.',
                'Double offline arithmetic does not implement a double-precision coupled trajectory.',
                'C_i times load alone breaks the manufactured uniform-stress cancellation; no physical repair is accepted here.'])
    write_json(receipt,result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
