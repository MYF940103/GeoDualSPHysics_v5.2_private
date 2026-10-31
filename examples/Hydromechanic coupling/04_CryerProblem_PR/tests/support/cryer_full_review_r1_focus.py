"""New offline focus views of sealed Cryer review; never overwrites or runs a solver."""
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

TESTS=Path(__file__).resolve().parents[1]
TAG='cryer_full_review_r1_focus'
CHECK=TESTS/'logs'/(TAG+'.check.json')
PNG=TESTS/'figures'/(TAG+'.png')
CSV=TESTS/'figures'/(TAG+'_profile_metrics.csv')

def bound(path):
    path=Path(path)
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha)

def run():
    assert not any(p.exists() for p in [CHECK,PNG,CSV]),'Preserve prior evidence'
    if os.name=='nt':
        kernel=ctypes.WinDLL('kernel32',use_last_error=True); kernel.GetCurrentProcess.restype=wintypes.HANDLE
        kernel.SetPriorityClass.argtypes=[wintypes.HANDLE,wintypes.DWORD]; kernel.SetPriorityClass.restype=wintypes.BOOL
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000):raise ctypes.WinError(ctypes.get_last_error())
    base=TESTS/'logs/cryer_full_review_r1.check.json'
    record=json.loads(base.read_text(encoding='utf8')); assert record['analysis_checks_passed']
    files={Path(r['path']).name:r for r in record['artifacts']+record['inputs']}; inputs=[bound(__file__),bound(base)]
    def table(name):
        r=files[name]; assert bound(r['path'])==r; inputs.append(r)
        return pd.read_csv(r['path'],float_precision='round_trip')
    history=table('cryer_full_review_r1_history.csv'); reference=table('cryer_full_review_r1_theory.csv')
    peaks=table('cryer_full_review_r1_peaks.csv'); profiles=table('cryer_full_review_r1_profiles.csv')
    cloud=table('cryer_full_native_r1_initial_cloud.csv').set_index('id'); rows=[]
    fields=['pressure_pa','radial_displacement_mm','effective_sigma_rr_pa','effective_sigma_tt_pa','total_sigma_rr_pa','total_sigma_tt_pa']
    for part,a in profiles.groupby('part',sort=True):
        weight=cloud.loc[a.id,'volume0_m3'].to_numpy(); weight/=weight.sum()
        row=dict(part=int(part),time_s=float(a.time_s.iloc[0]),tau_s=float(a.tau_s.iloc[0]),legacy_Tv=float(a.legacy_Tv.iloc[0]),plane_nodes=len(a),scope='fixed initial 1709-node material plane; not whole sphere')
        for key in fields:
            error=a[key].to_numpy()-a['theory_'+key].to_numpy()
            row[key+'_error_mean']=float(weight@error); row[key+'_error_rms']=float(np.sqrt(weight@(error*error))); row[key+'_error_absmax']=float(abs(error).max())
        rows.append(row)
    metrics=pd.DataFrame(rows)
    with CSV.open('x',encoding='utf8',newline='') as stream:metrics.to_csv(stream,index=False,float_format='%.17g')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.25})
    fig,axes=plt.subplots(2,2,figsize=(14,10),constrained_layout=True)
    colors=dict(server='black',raw_coarse='#1f77b4',raw_half='#777777',symC_coarse='#d95f02',symC_half='#16853b')
    low=[]; high=[]
    for dataset,a in history.groupby('dataset',sort=False):
        window=a.tau_s.between(.02,.07); a=a.loc[window]
        axes[0,0].plot(a.tau_s*1000,a.center_pressure_mean_pa,color=colors[dataset],label=dataset,lw=1.3)
        low.append(a.center_pressure_mean_pa.min()); high.append(a.center_pressure_mean_pa.max())
    a=reference.loc[reference.tau_s.between(.02,.07)]
    axes[0,0].plot(a.tau_s*1000,a.center18_pressure_pa,'--',color='#b2182b',label='Finite Kw, fixed r0/a=.05')
    low.append(a.center18_pressure_pa.min()); high.append(a.center18_pressure_pa.max())
    p=peaks.loc[peaks.dataset.eq('server')].iloc[0]
    axes[0,0].scatter([p.tau_s*1000],[p.pressure_pa],color='black',s=30,zorder=5)
    axes[0,0].scatter([p.theory_continuous_peak_tau_s*1000],[p.theory_continuous_peak_pressure_pa],color='#b2182b',marker='*',s=70,zorder=5)
    padding=.08*(max(high)-min(low)); axes[0,0].set(xlim=(20,70),ylim=(min(low)-padding,max(high)+padding),xlabel='Actual tau=t-tD [ms]',ylabel='Fixed18 mean p [Pa]',title=f'Peak amplitude {p.amplitude_error_percent:.3f}%; timing {p.time_error_percent:.3f}%')
    server=history.loc[history.dataset.eq('server')&history.legacy_Tv.ge(.005)]
    axes[0,1].plot(server.legacy_Tv,server.center_pressure_mean_pa-server.finite_radius_pressure_pa,color='black',label='Server minus finite-Kw reference')
    axes[0,1].axhline(0,color='#999999',lw=.7); axes[0,1].set(xlabel='Actual legacy Tv',ylabel='Fixed18 pressure error [Pa]',title='Every saved Mandel-window point; no filtering')
    selected=[int(p.part),264,1064]; palette=['#1f77b4','#d95f02','#16853b']
    for part,color in zip(selected,palette):
        a=profiles.loc[profiles.part.eq(part)]; m=metrics.loc[metrics.part.eq(part)].iloc[0]
        for ax,key,unit in [(axes[1,0],'radial_displacement_mm','mm'),(axes[1,1],'effective_sigma_rr_pa','Pa')]:
            error=a[key]-a['theory_'+key]
            ax.scatter(a.r0_over_a,error,s=4,alpha=.35,color=color,label=f'Tv={m.legacy_Tv:.4g}; plane RMS={m[key+"_error_rms"]:.4g} {unit}')
    axes[1,0].set(xlabel='Fixed material r0/a',ylabel='u_r error [mm]',title='Local radial-displacement scatter, not whole-sphere RMS')
    axes[1,1].set(xlabel='Fixed material r0/a',ylabel='Effective sigma_rr error [Pa]',title='Local radial-stress scatter, not whole-sphere RMS')
    for ax in axes.flat:ax.legend(fontsize=7)
    fig.suptitle('Cryer sealed server output: focused accuracy and local-field limitations\nNo native smoothing, fitted clock/radius, inherited half convergence or automatic physical acceptance',fontsize=11)
    fig.savefig(PNG,dpi=180); plt.close(fig)
    result=dict(analysis_checks_passed=True,inputs=inputs,artifacts=[bound(CSV),bound(PNG)],profile_metrics=rows,scope='Offline secondary diagnostic of sealed full-review artifacts only',physical_acceptance=False,solver_started=False,source_changed=False)
    with CHECK.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(check=str(CHECK),analysis_checks_passed=True,physical_acceptance=False)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--review',action='store_true'); args=parser.parse_args()
    if args.review:run()
    else:parser.print_help()
