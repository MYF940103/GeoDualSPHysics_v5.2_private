"""Frozen reconstructions of six retained actual states, not a solver replay."""
import argparse
import json
import re
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import TESTS,REPO,LIAN,READER,R,DP,native,bound,write_json,batches,add_pair,tensor
from cryer_darcy_closed_r1 import constants
from cryer_radial_consistency_r1 import Reference

TAG='cryer_saved_state_audit_r1';PEAK='cryer_preload_peak_r1'
PARTS=[64,105,228,408,444,576]


def reconstruct(a,initial,ctes,cs,q):
    x=a[['x','y','z']].to_numpy();x0=initial[['x','y','z']].to_numpy()
    v=a[['vx','vy','vz']].to_numpy();u=x-x0
    mass=a.mass.to_numpy();rho=a.rho.to_numpy();volume=mass/rho
    volop=(mass.astype(np.float32)/rho.astype(np.float32)).astype(float)
    s=tensor(a);used=s.astype(np.float32).astype(float);p=a.pressure.to_numpy()
    n=len(a);h=float(a.h.iloc[0]);pairs=cKDTree(x).query_pairs(2*h,output_type='ndarray')
    moment=np.zeros((n,3,3));gop=np.zeros_like(moment);gnative=np.zeros_like(moment)
    gmom=np.zeros_like(moment);gu=np.zeros_like(moment)
    forces=np.zeros((4,n,3));lap=np.zeros(n)
    # Pass one: actual-state geometry and velocity/displacement moments.
    for i,j,d,g in batches(x,pairs,h):
        g*=ctes['helper_gradient_scale'];dv=v[j]-v[i];du=u[j]-u[i]
        for row in range(3):
            for col in range(3):
                dg=-d[:,row]*g[:,col];vg=dv[:,row]*g[:,col];ug=du[:,row]*g[:,col]
                for out,left,right in [(moment,dg*volop[j],dg*volop[i]),
                        (gop,vg*volop[j],vg*volop[i]),(gnative,vg*volume[j],vg*volume[i]),
                        (gmom,vg*mass[j]/rho[i],vg*mass[i]/rho[j]),
                        (gu,ug*volop[j],ug*volop[i])]:
                    out[:,row,col]+=np.bincount(i,weights=left,minlength=n)
                    out[:,row,col]+=np.bincount(j,weights=right,minlength=n)
    eig=np.linalg.eigvalsh(moment);assert eig.min()>0
    corr=np.linalg.inv(moment);grad=gop@corr.swapaxes(1,2);grad_u=gu@corr.swapaxes(1,2)
    # Pass two: original raw momentum split into stress/pore/load/viscosity, and current Darcy.
    for i,j,d,g in batches(x,pairs,h):
        g*=ctes['helper_gradient_scale'];rr=np.sum(d*d,axis=1);denom=rr+ctes['eta2_float_m2']
        sig=np.einsum('nij,nj->ni',used[i]/rho[i,None,None]**2+used[j]/rho[j,None,None]**2,g)
        pore=(-(p[i]+p[j])/(rho[i]*rho[j]))[:,None]*g
        load=(q*(1/rho[i]**2+1/rho[j]**2))[:,None]*g
        dot=np.sum(d*(v[i]-v[j]),axis=1)
        pi=-.1*cs*h*np.minimum(dot,0)/(denom*(rho[i]+rho[j])*.5)
        visc=-pi[:,None]*g
        for k,value in enumerate([sig,pore,load,visc]):
            add_pair(forces[k],i,j,mass[j,None]*value,-mass[i,None]*value)
        hi=np.einsum('ni,nij,nj->n',d,corr[i],g)/denom
        hj=np.einsum('ni,nij,nj->n',d,corr[j],g)/denom
        delta=p[i]-p[j]
        lap+=np.bincount(i,weights=2*volop[j]*delta*hi,minlength=n)
        lap+=np.bincount(j,weights=-2*volop[i]*delta*hj,minlength=n)
    mf=ctes['backends']['GPU']['kwn_pa'];kap=ctes['conductivity_float_m_s']/(ctes['water_rho_float_kg_m3']*ctes['backends']['GPU']['ghyd_m_s2'])
    comp=-mf*np.trace(grad,axis1=1,axis2=2);darcy=mf*kap*lap
    speed2=np.sum(v*v,axis=1);cd=4e-5*np.sqrt(2e6/(rho*h*h));damping=-cd[:,None]*v
    power=lambda a:float(np.sum(mass[:,None]*v*a))
    psig=power(forces[0]);ppore=power(forces[1]);pvisc=power(forces[3])
    sigmawork_raw=float(np.einsum('n,nij,nij->',volume,used,gmom))
    pressurework_raw=float(np.sum(volume*p*np.trace(gnative,axis1=1,axis2=2)))
    tol=1e-9*max(abs(psig)+abs(ppore)+abs(sigmawork_raw)+abs(pressurework_raw),1e-6)
    assert abs(psig+sigmawork_raw)<tol and abs(ppore-pressurework_raw)<tol
    assert pvisc<=tol
    jac_inv=np.linalg.det(np.eye(3)-grad_u);assert np.all(jac_inv>0)
    return dict(x=x,v=v,sigma=s,volume=volume,grad=grad,comp=comp,darcy=darcy,
        density_geometric=initial.rho.to_numpy()*jac_inv,
        logstrain_geometric=-np.log(jac_inv),logstrain_density=-np.log(rho/initial.rho.to_numpy()),
        logstrain_sigma=np.trace(s,axis1=1,axis2=2)/(3*Reference().K),
        force_norm=np.linalg.norm(forces.sum(axis=0)+damping,axis=1),
        powers=dict(stress_internal_W=psig,pore_internal_W=ppore,external_load_W=power(forces[2]),
            artificial_viscosity_W=pvisc,kinematic_damping_W=power(damping),
            raw_stress_adjoint_residual_W=psig+sigmawork_raw,raw_pressure_adjoint_residual_W=ppore-pressurework_raw,
            corrected_stress_work_W=float(np.einsum('n,nij,nij->',volume,s,grad)),
            corrected_pressure_compression_work_W=float(-np.sum(volume*p*np.trace(grad,axis1=1,axis2=2))),
            stress_projection_work_difference_W=float(np.einsum('n,nij,nij->',volume,s-used,grad))),
        load_native_reconstruction_vector_rms_m_s2=float(np.sqrt(np.mean(np.sum((forces[2]-a[['load_ax','load_ay','load_az']].to_numpy())**2,axis=1)))),
        moment_min_eigenvalue=float(eig.min()),pair_count=len(pairs))


def main():
    check=TESTS/'logs'/(TAG+'.check.json');history=TESTS/'figures'/(TAG+'_summary.csv')
    radial=TESTS/'figures'/(TAG+'_shells.csv');plot=TESTS/'figures'/(TAG+'.png')
    assert not any(p.exists() for p in [check,history,radial,plot])
    prior=TESTS/'logs/cryer_radial_force_r2.check.json';assert json.loads(prior.read_text())['analysis_checks_passed']
    folder=TESTS/'outputs'/PEAK;completion=TESTS/'logs'/(PEAK+'.completion.json')
    sealed={e['path']:e for e in json.loads(completion.read_text())['outputs']}
    config=TESTS/'configs'/(PEAK+'_Def.xml');log=folder/'Run.out'
    csp=constants(config,.0044999998062849045)
    text=log.read_text(errors='replace');cs=float(re.search(r'^Cs0=([^\r\n]+)',text,re.M)[1])
    assert 'Finished execution (code=0)' in text and 'PoreCompressionSourceMode="PairDivergence"' in text
    inputs=[bound(p) for p in [__file__,TESTS/'notes'/(TAG+'.json'),config,log,completion,prior,READER,LIAN/'lian_release_r1.py',
        TESTS/'support/cryer_load_pair_r1.py',TESTS/'support/cryer_darcy_closed_r1.py',
        TESTS/'support/cryer_radial_consistency_r1.py',REPO/'src/source/JSphCpu.cpp',REPO/'src/source/JSphGpu_ker.cu']]
    for part in [0]+PARTS:
        b=bound(folder/'data'/f'Part_{part:04d}.bi4');assert b['sha256']==sealed[b['path']]['sha256'];inputs.append(b)
    initial=native(folder,0);ids=initial.id.to_numpy();x0=initial[['x','y','z']].to_numpy()
    r0=np.linalg.norm(x0,axis=1);e0=x0/r0[:,None];shell=np.rint(r0/DP).astype(int)
    center=r0<=DP+1e-12;assert center.sum()==18
    ref=Reference();rows=[];shellrows=[]
    for part in PARTS:
        print('Frozen retained-state reconstruction',part,flush=True)
        a=native(folder,part);assert np.array_equal(a.id,ids) and np.isfinite(a.to_numpy()).all()
        assert a.h.eq(csp['h_m']).all() and a.position_double.eq(1).all()
        assert a.nout.eq(0).all() and a.kplastic.eq(0).all() and a.rho.gt(0).all()
        t=float(a.time_s.iloc[0]);assert t==part/8192 and np.array_equal(a.fstype,initial.fstype)
        surface=a.fstype.isin([2,3]).to_numpy();active=t>.0078125
        if active:assert surface.sum()==5153 and a.pressure[surface].eq(0).all()
        v=reconstruct(a,initial,csp,cs,10000.);volume=v['volume'];pressure=a.pressure.to_numpy()
        rms=lambda z:float(np.sqrt(np.average(np.asarray(z)**2,weights=volume)))
        mean=lambda z:float(np.average(z,weights=volume))
        mask=~surface if active else np.ones(len(a),dtype=bool)
        comp=np.where(mask,v['comp'],0);darcy=np.where(mask,v['darcy'],0)
        du=v['x']-x0;transverse=du-np.sum(du*e0,axis=1)[:,None]*e0
        velocity_transverse=v['v']-np.sum(v['v']*e0,axis=1)[:,None]*e0
        row=dict(part=part,time_s=t,tau_s=t-.0078125,surface_ids_changed=0,drainage_active=active,
            center_pressure_pa=float(pressure[center].mean()),center_comp_pa_s=float(comp[center].mean()),
            center_darcy_pa_s=float(darcy[center].mean()),center_net_pa_s=float((comp+darcy)[center].mean()),
            pressure_energy_J=float(np.sum(volume*pressure**2)/(2*ref.Mf)),
            kinetic_energy_J=float(.5*np.sum(a.mass.to_numpy()*np.sum(v['v']**2,axis=1))),
            pressure_darcy_energy_rate_W=float(np.sum(volume*pressure*darcy)/csp['backends']['GPU']['kwn_pa']),
            density_vs_local_geometry_rms_kg_m3=rms(a.rho.to_numpy()-v['density_geometric']),
            density_vs_stress_logstrain_rms=rms(v['logstrain_density']-v['logstrain_sigma']),
            geometry_vs_stress_logstrain_rms=rms(v['logstrain_geometric']-v['logstrain_sigma']),
            transverse_displacement_rms_mm=1000*rms(np.linalg.norm(transverse,axis=1)),
            transverse_speed_rms_m_s=rms(np.linalg.norm(velocity_transverse,axis=1)),
            load_native_reconstruction_vector_rms_m_s2=v['load_native_reconstruction_vector_rms_m_s2'],**v['powers'])
        row['corrected_coupling_work_defect_W']=row['stress_internal_W']+row['pore_internal_W']+row['corrected_stress_work_W']+row['corrected_pressure_compression_work_W']
        if active:
            pf0=ref.field(r0,t-.0078125)['p'];pfx=ref.field(np.linalg.norm(v['x'],axis=1),t-.0078125)['p']
            row['center_theory_initial_r_pa']=float(pf0[center].mean());row['center_theory_current_r_pa']=float(pfx[center].mean())
        for s in np.unique(shell):
            m=shell==s;w=volume[m];p=pressure[m]
            shellrows.append(dict(part=part,time_s=t,shell=int(s),initial_radius_m=float(r0[m].mean()),count=int(m.sum()),
                pressure_mean_pa=float(np.average(p,weights=w)),pressure_angular_rms_pa=float(np.sqrt(np.average((p-np.average(p,weights=w))**2,weights=w))),
                density_min_kg_m3=float(a.rho[m].min()),density_max_kg_m3=float(a.rho[m].max()),
                comp_mean_pa_s=float(np.average(comp[m],weights=w)),darcy_mean_pa_s=float(np.average(darcy[m],weights=w))))
        rows.append(row)
    pd.DataFrame(rows).to_csv(history,index=False,float_format='%.17g');pd.DataFrame(shellrows).to_csv(radial,index=False,float_format='%.17g')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for part in PARTS:
        points=[s for s in shellrows if s['part']==part]
        axes[0].plot([s['initial_radius_m']/R for s in points],[s['pressure_angular_rms_pa'] for s in points],'.-',label=f'Part{part}')
    axes[0].set(xlabel='Initial radius / R',ylabel='Within-shell pressure RMS (Pa)',title='Angular departures on retained native shells');axes[0].legend(fontsize=8)
    for key,label in [('artificial_viscosity_W','Artificial viscosity'),('kinematic_damping_W','Kinematic damping'),
            ('pressure_darcy_energy_rate_W','Darcy pressure-energy rate'),('corrected_coupling_work_defect_W','Mixed-operator work defect')]:
        axes[1].plot([r['tau_s'] for r in rows],[r[key] for r in rows],'.-',label=label)
    axes[1].set(xlabel='Time since drainage (s)',ylabel='Instantaneous frozen power (W)',title='Saved-state diagnostics, not integrated work');axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(True,alpha=.25)
    fig.savefig(plot,dpi=170);plt.close(fig)
    write_json(check,dict(analysis_checks_passed=True,solver_executed=False,production_implemented=False,physical_acceptance=False,
        parts=PARTS,actual_saved_states=6,inputs=inputs,artifacts=[bound(history),bound(radial),bound(plot)],rows=rows,
        limitations=['Double distance and sums with native state and rounded scalar constants; not actual GPU force/rate replay.',
            'Only six saved states. Lines do not resolve unsaved transients and cannot establish integrated dissipation.',
            'Local density/geometry estimate uses inverse initial-coordinate gradient at current positions, not an independent exact Jacobian.',
            'Within-shell angular RMS uses initial shells; it is not the radial theory error.',
            'Raw adjoint identities are algebra checks. Mixed-operator work defect is not a complete finite-deformation energy-balance law.',
            'Saved-state load telemetry belongs to preceding integration stages; current-state reconstruction is not 0-ULP telemetry proof.',
            'No physical threshold relaxed, no geometry/mass change, no pressure/constitutive candidate implemented.']))
    print(json.dumps(dict(analysis_checks_passed=True,actual_saved_states=6,outputs=str(check))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    if p.parse_args().run:main()
    else:p.print_help()
