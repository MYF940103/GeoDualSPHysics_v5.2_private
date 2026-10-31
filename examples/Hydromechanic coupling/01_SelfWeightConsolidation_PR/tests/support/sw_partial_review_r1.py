"""Bounded read-only selected-save assessment of the live selfweight run; no full acceptance."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import numpy as np
import pandas as pd
import postprocess_selfweight_freshpr_r1 as post

TESTS=Path(__file__).resolve().parents[1]; TAG='sw_partial_review_r1'
CHECK=TESTS/'logs'/(TAG+'.check.json'); FIG=TESTS/'figures'/(TAG+'.png')
HISTORY=TESTS/'figures'/(TAG+'_history.csv'); PROFILES=TESTS/'figures'/(TAG+'_profiles.csv')

def run():
    assert not any(p.exists() for p in [CHECK,FIG,HISTORY,PROFILES]),'Fresh analysis only'
    if os.name=='nt':
        k=ctypes.WinDLL('kernel32',use_last_error=True); k.GetCurrentProcess.restype=wintypes.HANDLE
        k.SetPriorityClass.argtypes=[wintypes.HANDLE,wintypes.DWORD]; k.SetPriorityClass.restype=wintypes.BOOL
        if not k.SetPriorityClass(k.GetCurrentProcess(),0x4000):raise ctypes.WinError(ctypes.get_last_error())
    runfile=TESTS/'logs/sw_freshpr_run_r2.run.json'; raw=runfile.read_text(encoding='utf8'); state=json.loads(raw)
    assert state['status']=='running' and state['progress']['stage']=='solver'
    m=json.loads(Path(state['monitor']['path']).read_text(encoding='utf8')); assert post.bound(state['monitor']['path'])==state['monitor']
    config=m['job']['config']; assert post.bound(config['path'])==config; p=post.parameters(config['path'])
    reader=next(r for r in m['inputs'] if Path(r['path']).name=='ReadSelfWeightNative.exe'); assert post.bound(reader['path'])==reader
    cap=int(state['progress']['latest_native']['part']); folder=TESTS.parent/(m['job']['name']+'_out')
    B=p['Mf']/(p['M']+p['Mf']); cv=p['k']*p['M']/(p['rho_w']*p['g']); times=np.array(m['clock_plan']['saved_times_s'][:cap+1]); tv=B*cv*times/p['H']**2
    targets=[0.,.005,.05,.1,.25,.5,.7,1.,1.25,1.5]
    parts=sorted(set([int(np.argmin(abs(tv-t))) for t in targets if t<=tv[-1]]+[cap])); inputs=[post.bound(__file__),post.bound(post.__file__),state['monitor'],config,reader,post.bound(folder/'data/Part_Head.ibi4')]
    first=None; history=[]; profiles=[]; vz=[]; selected=[]
    for part in parts:
        path=folder/'data'/f'Part_{part:04d}.bi4'; record=post.bound(path); a=post.native(reader['path'],folder/'data',part)
        assert post.bound(path)==record; inputs.append(record)
        if first is None:first=a.copy(); assert part==0 and post.initial_formula(first,p)['passed']
        assert np.isfinite(a.to_numpy()).all() and a.kplastic.eq(0).all() and a.nout.eq(0).all() and a.rho.gt(0).all()
        assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.native_count.eq(1040).all()
        assert np.array_equal(a.porepress0.to_numpy().view('<u8'),first.porepress0.to_numpy().view('<u8'))
        assert np.array_equal(a[['mass','dp','h']],first[['mass','dp','h']])
        assert np.array_equal(a.excess_native.to_numpy(dtype='<f4').view('<u4'),(a.pressure.to_numpy(dtype='<f4')-a.porepress0.to_numpy(dtype='<f4')).view('<u4'))
        step=m['clock_plan']['saved_steps'][part]; t=float(a.time_s.iloc[0]); assert a.time_s.eq(times[part]).all() and a.saved_step.eq(step-1 if part else 0).all()
        assert t==step*p['dt'] and (part==0 or (a.has_dterror.eq(1).all() and a.dterror_s.max()<=1e-14))
        assert np.array_equal(a.is_boundary,np.r_[np.ones(40),np.zeros(1000)])
        s,s0=a.iloc[40:],first.iloc[40:]; surface=s.fstype.isin([2,3]); assert set(s.id[surface])==set(first.id.iloc[139::100]) and s.pressure[surface].eq(0).all()
        du=s[['x','y','z']].to_numpy()-s0[['x','y','z']].to_numpy(); dx=(du[:,0]+.05)%.1-.05
        assert s.z.gt(0).all() and abs(dx).max()*1000<.5 and np.ptp(s.z.to_numpy().reshape(10,100),axis=0).max()*1000<.5
        pore=p['safety']*(p['rho_w']*p['g']/p['Mf'])*float(a.h.iloc[0])**2/p['k']; assert p['dt']<=pore
        r=s.excess_native.to_numpy()+p['Mf']*(s.sigma_xx+s.sigma_yy+s.sigma_zz).to_numpy()/(3*p['K']); r=r[(s.id.to_numpy().astype(int)-40)%100!=99]
        history.append(dict(dataset='partial_fresh',part=part,time_s=t,elapsed_since_own_initial_s=t,saved_step=int(a.saved_step.iloc[0]),natural_step=step,native_safety_passed=True,
            speed_max_m_s=float(np.linalg.norm(s[['vx','vy','vz']],axis=1).max()),r_990_rms_pa=float(np.sqrt(np.mean(r*r))),r_990_mean_pa=float(r.mean()),r_990_absmax_pa=float(abs(r).max())))
        top=float(s.iloc[99::100].z.mean()); vz.append(s.vz.to_numpy())
        for layer in range(100):
            b,b0=s.iloc[layer::100],s0.iloc[layer::100]; u=dx[layer::100]; x=b0.x.to_numpy(); denominator=float(np.sum((x-x.mean())**2)); strain=float(np.sum((x-x.mean())*(u-u.mean()))/denominator)
            rec=dict(dataset='partial_fresh',part=part,time_s=t,elapsed_since_own_initial_s=t,saved_step=int(a.saved_step.iloc[0]),layer=layer,z0_m=float(b0.z.mean()),z_m=float(b.z.mean()),pressure_pa=float(b.pressure.mean()),porepress0_pa=float(b.porepress0.mean()),excess_native_pa=float(b.excess_native.mean()),
                q_fixed_double_pa=float((b.pressure-b.porepress0).mean()),q_current_pa=float((b.pressure-p['rho_w']*p['g']*np.maximum(top-b.z,0)).mean()),hydro_current_pa=float((p['rho_w']*p['g']*np.maximum(top-b.z,0)).mean()),
                settlement_increment_mm=float((b0.z.to_numpy()-b.z.to_numpy()).mean()*1000),rho_kg_m3=float(b.rho.mean()),eps_xx_material_regression=strain,total_sigma_zz_pa=float((b.sigma_zz-b.pressure).mean()),
                **{key:float(b[key].mean()) for key in post.SIGMA+['vx','vy','vz']})
            rec['hydro_current_minus_fixed_p0_pa']=rec['hydro_current_pa']-rec['porepress0_pa']; profiles.append(rec)
        selected.append(dict(part=part,actual_time_s=t,actual_finite_Tv=float(tv[part]),native_guard_passed=True))
    case=post.enrich(dict(profiles=pd.DataFrame(profiles),history=pd.DataFrame(history),raw_vz=np.asarray(vz),legacy=False),p)
    h,a=case['history'],case['profiles']; final=h.iloc[-1]; latest=a[a.part.eq(cap)].sort_values('layer'); ref=case['references']['H1_finite_']
    h['top_settlement_H1_error_mm']=h.top_settlement_increment_mm-h.H1_finite_top_settlement_increment_mm
    h['bottom_settlement_H1_error_mm']=h.bottom_settlement_increment_mm-h.H1_finite_bottom_settlement_increment_mm
    h['relative_settlement_H1_error_mm']=h.top_minus_bottom_settlement_mm-(h.H1_finite_top_settlement_increment_mm-h.H1_finite_bottom_settlement_increment_mm)
    for path,table in [(HISTORY,h),(PROFILES,a)]:
        with path.open('x',encoding='utf8',newline='') as stream:table.to_csv(stream,index=False,float_format='%.17g')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.25})
    fig,axes=plt.subplots(2,3,figsize=(16,9),constrained_layout=True)
    def series(ax,keys):
        for key in keys:ax.plot(h.finite_Kw_Tv,h[key],'-o',ms=3,label=key)
        ax.set_xlabel('Actual finite-Kw Tv; selected saved states only')
    series(axes[0,0],['bottom_excess_native_pa','bottom_q_current_pa','H1_finite_bottom_q_pa']); axes[0,0].set(title='Bottom pressure: fixed-p0 versus moving-hydro baseline',ylabel='Pa')
    series(axes[0,1],['top_settlement_increment_mm','bottom_settlement_increment_mm','H1_finite_top_settlement_increment_mm','H1_finite_bottom_settlement_increment_mm']); axes[0,1].set(title='Fixed material top/bottom own-initial increments',ylabel='mm')
    series(axes[0,2],['H1_finite_pressure_rms_pa','H1_finite_settlement_rms_mm']); axes[0,2].lines[-1].remove()
    axes[0,2].set(title='Whole-profile total-p error to quasi-static H1',ylabel='Pa')
    for key in ['excess_native_pa','q_current_pa','H1_finite_q_pa']:axes[1,0].plot(latest[key],latest.z0_m,label=key)
    axes[1,0].set(title='Latest excess-pressure profiles',xlabel='Pa',ylabel='Initial material z [m]')
    for key in ['settlement_increment_mm','H1_finite_settlement_increment_mm']:axes[1,1].plot(latest[key],latest.z0_m,label=key)
    axes[1,1].set(title='Latest own-initial settlement profile',xlabel='mm',ylabel='Initial material z [m]')
    for key in ['sigma_zz','H1_finite_sigma_zz_pa','total_sigma_zz_pa','H1_finite_total_sigma_zz_pa']:axes[1,2].plot(latest[key]/1000,latest.z0_m,label=key)
    axes[1,2].set(title='Latest effective and total vertical stresses',xlabel='kPa; tension positive',ylabel='Initial material z [m]')
    for ax in axes.flat:ax.legend(fontsize=6)
    fig.suptitle(f'Provisional selfweight snapshot: {len(parts)} selected native saves through finite Tv={final.finite_Kw_Tv:.5g}\nNot a complete time history, startup convergence, final floor test or physical acceptance',fontsize=12)
    fig.savefig(FIG,dpi=170); plt.close(fig)
    for record in inputs:assert post.bound(record['path'])==record
    result=dict(analysis_checks_passed=True,snapshot_status=state['status'],snapshot_progress_utc=state['progress']['utc'],snapshot_worker_pid=state['worker_pid'],snapshot_checked_frames=state['progress']['checked_frames'],
        selection=selected,parameters=p,history=post.clean(h.to_dict('records')),inputs=inputs,artifacts=[post.bound(x) for x in [HISTORY,PROFILES,FIG]],
        reference_scope='Unchanged H1 finite-Kw quasi-static actual-mode3 own-initial reference; moving-hydro and fixed-p0 distinct; no H/time fitting',
        limitations=['Selected stable saves only; streaming worker retains authority for all-frame safety.','No full HG/end validation or late Tv2 floor test yet.','No full-window half validation or isolated old/new precision comparison.'],physical_acceptance=False,full_run_complete=False,solver_started=False,monitor_modified=False)
    with CHECK.open('x',encoding='utf8') as stream:json.dump(post.clean(result),stream,indent=2,allow_nan=False)
    print(json.dumps(dict(check=str(CHECK),selected_frames=len(parts),latest_finite_Tv=float(final.finite_Kw_Tv),analysis_checks_passed=True)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--review',action='store_true'); args=parser.parse_args()
    if args.review:run()
    else:parser.print_help()
