"""Log-Tv paper-style Cryer figure from sealed data; no solver or old-output overwrite."""
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
import cryer_full_review_r1 as full

TESTS=Path(__file__).resolve().parents[1]; OUT=TESTS.parent/'figures/formal_validation'
TAG='cryer_server_symc_full_r1_log'; CHECK=TESTS/'logs/cryer_full_review_r1_log.check.json'
PNG=OUT/(TAG+'.png'); CSV=OUT/(TAG+'_native.csv'); THEORY=OUT/(TAG+'_theory.csv')

def bound(path):
    path=Path(path)
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha)

def run():
    assert not any(p.exists() for p in [PNG,CSV,THEORY,CHECK]),'New independent figure only'
    if os.name=='nt':
        k=ctypes.WinDLL('kernel32',use_last_error=True); k.GetCurrentProcess.restype=wintypes.HANDLE
        k.SetPriorityClass.argtypes=[wintypes.HANDLE,wintypes.DWORD]; k.SetPriorityClass.restype=wintypes.BOOL
        if not k.SetPriorityClass(k.GetCurrentProcess(),0x4000):raise ctypes.WinError(ctypes.get_last_error())
    base=TESTS/'logs/cryer_full_review_r1.check.json'; check=json.loads(base.read_text(encoding='utf8'))
    assert check['analysis_checks_passed'] and check['native_safety_adopted']; inputs=[bound(__file__),bound(base)]
    records={Path(r['path']).name:r for r in check['artifacts']+check['inputs']}
    def table(name):
        r=records[name]; assert bound(r['path'])==r; inputs.append(r)
        return pd.read_csv(r['path'],float_precision='round_trip')
    history=table('cryer_full_review_r1_history.csv'); data=history.loc[history.dataset.eq('server')].copy()
    reference=table('cryer_full_review_r1_theory.csv'); assert len(data)==len(reference)==1065
    assert np.array_equal(data.tau_s.to_numpy(),reference.tau_s.to_numpy())
    data['p_over_q0']=data.center_pressure_mean_pa/full.Q
    data['finite_Kw_fixed_r0p05a_over_q0']=reference.center18_pressure_pa.to_numpy()/full.Q
    data['paper_incompressible_r0_over_q0']=reference.paper_incompressible_r0_pressure_pa.to_numpy()/full.Q
    data['shown_on_log_Tv_axis']=data.tau_s.gt(0)
    shown=data.loc[data.shown_on_log_Tv_axis]; assert len(shown)==1000
    tv=np.geomspace(shown.legacy_Tv.min(),shown.legacy_Tv.max(),1200); tau=tv*full.R**2/full.LEGACY_CV
    ref=full.theory.Reference(); finite=np.array([ref.field(np.array([.0025]),float(t))['p'][0] for t in tau])/full.Q
    paper=full.paper_center(tau,ref)/full.Q
    curves=pd.DataFrame(dict(legacy_Tv=tv,tau_s=tau,finite_storage_theta=ref.cv*tau/full.R**2,finite_Kw_fixed_r0p05a_over_q0=finite,paper_incompressible_r0_over_q0=paper))
    for path,a in [(CSV,data),(THEORY,curves)]:
        with path.open('x',encoding='utf8',newline='') as stream:a.to_csv(stream,index=False,float_format='%.17g')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':13,'mathtext.fontset':'stix'})
    fig,ax=plt.subplots(figsize=(10,7),constrained_layout=True)
    ax.plot(tv,finite,color='#3b5489',linestyle=(0,(6,4)),lw=2,label=r'Theory: finite $K_w$, fixed $r_0/a=0.05$')
    ax.plot(tv,paper,color='0.55',ls=':',lw=1.3,label=r'Paper limit: incompressible, $r=0$')
    ax.plot(shown.legacy_Tv,shown.p_over_q0,color='#ed4b35',lw=.6,marker='o',markevery=10,ms=4,mfc='none',mew=1,label=r'u-pw-GeoDualSPHysics, symC, $\nu=0.3$')
    ax.set(xscale='log',xlim=(5e-4,1.2),ylim=(0,1.32),xlabel=r'$T_v$',ylabel=r'Normalized pore pressure, $p^w/p_0$')
    ax.grid(True,which='major',color='0.85',lw=.7); ax.grid(True,which='minor',color='0.9',ls=':',lw=.7)
    ax.legend(loc='lower left',frameon=True,fancybox=False,edgecolor='0.35',fontsize=11)
    ax.set_title(r'Cryer: $\nu=0.3$, $d_p=0.0025$ m, $k=10^{-5}$ m/s',fontsize=15)
    fig.supxlabel('Drainage-relative time: tau=t-2^-7 s; legacy Tv uses g=9.81. Fixed 18 material IDs; no native time fit.\nAll 1065 records retained in CSV; 1000 positive-time records plotted. Accuracy review, not automatic physical acceptance.',fontsize=9)
    fig.savefig(PNG,dpi=220); plt.close(fig)
    style=OUT/'cryer_poisson_sweep_dp002_rampclosed_center_r1dp_paper_axes.png'
    inputs += [bound(style),bound(Path(full.__file__)),bound(Path(full.theory.__file__))]
    for r in inputs:assert bound(r['path'])==r
    result=dict(analysis_checks_passed=True,inputs=inputs,artifacts=[bound(p) for p in [PNG,CSV,THEORY]],native_rows=1065,positive_log_time_rows=1000,
        log_axis='x: drainage-relative legacy Tv; y: linear p/q0',all_startup_rows_retained_in_csv=True,old_formal_files_overwritten=False,source_changed=False,solver_started=False,physical_acceptance=False)
    with CHECK.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(check=str(CHECK),png=str(PNG),analysis_checks_passed=True)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--review',action='store_true'); args=parser.parse_args()
    if args.review:run()
    else:parser.print_help()
