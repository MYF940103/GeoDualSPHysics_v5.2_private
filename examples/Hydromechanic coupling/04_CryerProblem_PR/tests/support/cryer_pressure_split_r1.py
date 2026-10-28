"""Quantify the variable-density pore/stress split on a retained peak state only."""
import argparse
import json
import numpy as np
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import TESTS,REPO,native,bound,batches,add_pair,tensor,write_json
from cryer_darcy_closed_r1 import constants

TAG='cryer_pressure_split_r1'


def main():
    target=TESTS/'logs'/(TAG+'.check.json');assert not target.exists()
    folder=TESTS/'outputs/cryer_preload_peak_r1'
    completion=TESTS/'logs/cryer_preload_peak_r1.completion.json'
    sealed={e['path']:e for e in json.loads(completion.read_text())['outputs']}
    geometry=folder/'data/Part_0444.bi4';record=bound(geometry)
    assert record['sha256']==sealed[record['path']]['sha256']
    initial=folder/'data/Part_0000.bi4';record0=bound(initial)
    assert record0['sha256']==sealed[record0['path']]['sha256']
    a=native(folder,444);a0=native(folder,0)
    assert len(a)==37173 and np.array_equal(a.id,a0.id) and a.rho.gt(0).all()
    assert a.time_s.eq(.05419921875).all() and a.position_double.eq(1).all()
    x=a[['x','y','z']].to_numpy();v=a[['vx','vy','vz']].to_numpy();r0=np.linalg.norm(a0[['x','y','z']],axis=1)
    rho=a.rho.to_numpy();m=a.mass.to_numpy();p=a.pressure.to_numpy();s=tensor(a).astype(np.float32).astype(float)
    h=float(a.h.iloc[0]);config=TESTS/'configs/cryer_preload_peak_r1_Def.xml';c=constants(config,h)
    pairs=cKDTree(x).query_pairs(2*h,output_type='ndarray');delta=np.zeros_like(x);original=np.zeros_like(x)
    consistent=np.zeros_like(x);identity_error=0.
    for i,j,d,g in batches(x,pairs,h):
        g*=c['helper_gradient_scale'];ri,rj=rho[i],rho[j];pi,pj=p[i],p[j]
        split=pi/ri**2+pj/rj**2-(pi+pj)/(ri*rj)
        dr=rj-ri;dp=pj-pi
        factored=(.5*(pi+pj)*dr**2-.5*(ri+rj)*dp*dr)/(ri**2*rj**2)
        identity_error=max(identity_error,float(abs(split-factored).max()))
        dg=split[:,None]*g;add_pair(delta,i,j,m[j,None]*dg,-m[i,None]*dg)
        stress=np.einsum('nij,nj->ni',s[i]/ri[:,None,None]**2+s[j]/rj[:,None,None]**2,g)
        confinement=(10000*(1/ri**2+1/rj**2))[:,None]*g
        ao=stress+confinement-((pi+pj)/(ri*rj))[:,None]*g
        ac=stress+confinement-(pi/ri**2+pj/rj**2)[:,None]*g
        add_pair(original,i,j,m[j,None]*ao,-m[i,None]*ao)
        add_pair(consistent,i,j,m[j,None]*ac,-m[i,None]*ac)
    # This budget verifies double algebra only, not a physical threshold or kernel replay.
    assert identity_error<1e-17 and np.max(abs(original-consistent-delta))<1e-10
    volume=m/rho;surface=a.fstype.isin([2,3]).to_numpy()
    regions=dict(center18=r0<=.0025+1e-12,full_support_core=r0<.05-2*h,
        near_surface_interior=(r0>=.05-2*h)&~surface,all_soil=np.ones(len(a),dtype=bool))
    rows=[]
    for label,mask in regions.items():
        rms=lambda b:float(np.sqrt(np.average(np.sum(b[mask]**2,axis=1),weights=volume[mask])))
        rows.append(dict(region=label,count=int(mask.sum()),split_residual_vector_rms_m_s2=rms(delta),
            original_momentum_vector_rms_m_s2=rms(original),consistent_total_stress_form_vector_rms_m_s2=rms(consistent)))
    power=float(np.sum(m[:,None]*v*delta));net=np.sum(m[:,None]*delta,axis=0)
    prior=TESTS/'logs/cryer_saved_state_audit_r1.check.json';state=json.loads(prior.read_text())
    assert state['analysis_checks_passed'];peak=next(r for r in state['rows'] if r['part']==444)
    defect=peak['corrected_coupling_work_defect_W']-peak['stress_projection_work_difference_W']
    write_json(target,dict(analysis_checks_passed=True,solver_executed=False,production_implemented=False,
        physical_acceptance=False,part=444,tau_s=.04638671875,pair_count=len(pairs),rows=rows,
        coefficient_factorization_abs_error_max=identity_error,
        split_residual_power_W=power,split_power_over_mixed_operator_defect=abs(power/defect),
        split_residual_net_force_norm_N=float(np.linalg.norm(net)),
        identity='Delta a_i=sum_j m_j*[pi/rhoi^2+pj/rhoj^2-(pi+pj)/(rhoi*rhoj)]*grad_i Wij',
        factorization='Coefficient=[pbar*(delta rho)^2-rhobar*(delta p)*(delta rho)]/(rhoi^2*rhoj^2)',
        inputs=[bound(p) for p in [__file__,completion,geometry,initial,config,prior,
            TESTS/'support/cryer_load_pair_r1.py',TESTS/'support/cryer_darcy_closed_r1.py',
            REPO/'src/source/JSphCpu.cpp',REPO/'src/source/JSphGpu_ker.cu']],
        limitations=['One retained actual state; double geometry and sums, not a GPU or previous-stage replay.',
            'Consistent total-stress form is an offline algebraic contrast, not a new admitted force operator.',
            'Uniform total stress with spatial pressure/rho has the stated residual in the original split.',
            'Both pressure pair forms conserve pair momentum; this local balance difference is not global net-force injection.',
            'The original split follows the paper. A nonzero residual alone does not prove the observed peak bias cause.']))
    print(json.dumps(dict(analysis_checks_passed=True,rows=rows,power_W=power,power_ratio=abs(power/defect))),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:main()
    else:parser.print_help()
