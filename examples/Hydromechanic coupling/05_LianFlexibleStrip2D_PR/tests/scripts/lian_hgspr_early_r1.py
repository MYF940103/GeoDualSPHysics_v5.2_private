"""One fresh 0-1s GPU save-cadence supplement; no watcher, restart or production edits."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, READER, native, bound, utc
from lian_hg_short_r1 import hg_stats
from lian_hg_prefix_r2 import compare_prefix

TAG='lian_hgspr_early_r1'
LOGS=TESTS/'logs'; OUT=TESTS/'outputs'/TAG
CONFIG=TESTS/'configs'/(TAG+'_Def.xml'); BAT=CONFIG.with_name('x'+TAG+'_win64_GPU.bat')
PREP=LOGS/(TAG+'.inputs.json'); RUN=LOGS/(TAG+'.run.json')
COMPLETE=LOGS/(TAG+'.completion.json'); CHECK=LOGS/(TAG+'.check.json')
PREFIX=LOGS/(TAG+'.prefix.json'); HISTORY=TESTS/'figures'/(TAG+'_history.csv')
FORMAL=CASE/'CaseLianFlexibleStrip2D_PR_release_HGSPR_out'
PROGRAM=CASE/'support/bin/DualSPHysics5.2_GEO_win64.exe'
EXPECTED_PROGRAM='260c3d4c845db380f93257f96fba77034b1c6e2047d6780702b2483b974c933c'


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path,value):
    with Path(path).open('x',encoding='utf8') as stream: json.dump(value,stream,indent=2,allow_nan=False)


def verify(entries):
    for entry in entries:
        actual=bound(entry['path'])
        assert actual['sha256'].lower()==entry['sha256'].lower() and actual['bytes']==entry['bytes'],entry['path']


def active_gpu():
    query="Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2_win64_debug.exe') } | Select-Object ProcessId,ParentProcessId,ExecutablePath | ConvertTo-Json -Compress"
    result=subprocess.run(['powershell','-NoProfile','-Command',query],capture_output=True,text=True,check=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    value=json.loads(result.stdout) if result.stdout.strip() else []
    return value if isinstance(value,list) else [value]


def physics(root):
    def clean(e):
        attrs={k:v for k,v in e.attrib.items() if k not in ['comment','units_comment','date']}
        if e.tag=='parameter' and attrs.get('key') in ['TimeMax','TimeOut']: attrs['value']='cadence_only'
        return [e.tag,sorted(attrs.items()),(e.text or '').strip(),[clean(c) for c in e]]
    return clean(root)


def prepare():
    assert not any(p.exists() for p in [PREP,RUN,COMPLETE,CHECK,PREFIX,HISTORY,OUT]),'Fresh tag only'
    assert not active_gpu(),'A GPU solver is already active'
    original=ET.parse(CASE/'CaseLianFlexibleStrip2D_PR_release_Def.xml').getroot()
    candidate=ET.parse(CONFIG).getroot(); assert physics(original)==physics(candidate),'Unexpected physical XML difference'
    params={p.get('key'):p.get('value') for p in candidate.findall('.//parameter')}
    assert float(params['TimeMax'])==1 and float(params['TimeOut'])==.01
    assert float(params['DtFixed'])==float(params['DtIni'])==1e-5
    final=read(LOGS/'lian_server_return_r1.final_review.json')
    assert final['native_full_history_passed'] and final['all_matching_csvs_present']
    manifest=read(CASE/'support/server_manifest.json')
    package=[dict(path=e['path'],sha256=e['sha256'],bytes=e['bytes']) for e in manifest['files'] if e['entry'].startswith('support/bin/')]
    verify(package); assert bound(PROGRAM)['sha256']==EXPECTED_PROGRAM
    files=[Path(__file__),CONFIG,BAT,TESTS/'notes'/(TAG+'.md'),READER,
        CASE/'CaseLianFlexibleStrip2D_PR_release_Def.xml',CASE/'xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat',
        TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_hg_prefix_r2.py',TESTS/'scripts/lian_hg_short_r1.py',
        CASE/'support/postprocess_lian_hgspr_r1.py',CASE/'support/postprocess_lian_release.py',
        LOGS/'lian_hgspr100_r1.check.json',LOGS/'lian_server_return_r1.final_review.json',
        LOGS/'lian_server_return_r1_poredt.check.json',CASE/'figures/lian_hgspr100_r1_history.csv',
        CASE/'support/server_manifest.json']
    seal(PREP,dict(status='prepared',utc=utc(),inputs=[bound(p) for p in files]+package,
        program=bound(PROGRAM),changes={'TimeMax':[100,1],'TimeOut':[.05,.01]},dt_s=1e-5,
        expected_frames=101,expected_nominal_steps=100000,physical_accepted=False))
    print('PREPARED',PREP,flush=True)


def publish(state):
    temporary=RUN.with_suffix('.tmp')
    temporary.write_text(json.dumps(state,indent=2,allow_nan=False),encoding='utf8'); os.replace(temporary,RUN)


def run():
    assert PREP.exists() and not any(p.exists() for p in [OUT,RUN,COMPLETE,CHECK]),'Never rerun an old worker'
    prepared=read(PREP);verify(prepared['inputs']+[prepared['program']]);assert not active_gpu(),'Another GPU solver is active'
    state=dict(status='running',stage='solver',utc=utc(),owned_sequence_pid=os.getpid(),program=prepared['program'],
        prepared_inputs=bound(PREP),physical_accepted=False)
    publish(state); child=None; started=time.perf_counter(); logfile=LOGS/(TAG+'.log')
    try:
        with logfile.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(BAT),'--unattended'],cwd=CASE,
                stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid']=child.pid;publish(state)
            while child.poll() is None:
                time.sleep(5)
                if time.perf_counter()-started>=state.get('last_report_seconds',-60)+60:
                    state['last_report_seconds']=time.perf_counter()-started
                    state['observed_gpu_processes']=active_gpu();publish(state)
                    print('RUNNING',TAG,'wrapper',child.pid,'wall_s',round(state['last_report_seconds']),flush=True)
        text=(OUT/'Run.out').read_text(errors='replace') if (OUT/'Run.out').exists() else ''
        finished=child.returncode==0 and 'Finished execution (code=0)' in text
        seal(COMPLETE,dict(solver_finished=finished,owned_exited=True,exit_code=child.returncode,
            utc=utc(),owned_wrapper_pid=child.pid,program=prepared['program'],prepared_inputs=bound(PREP),
            outputs=[bound(p) for p in OUT.rglob('*') if p.is_file()]+[bound(logfile)]))
        state.update(status='completed_pending_analysis' if finished else 'solver_failed',exit_code=child.returncode,
            owned_exited=True,solver_wall_seconds=time.perf_counter()-started,sealed_completion=bound(COMPLETE))
        publish(state); assert finished,'Actual solver did not complete normally'
        analyze()
    except BaseException as error:
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True);child.wait(timeout=20)
        state.update(status='rejected_or_analysis_failed',error=repr(error),traceback=traceback.format_exc(),
            owned_exited=child is None or child.poll() is not None);publish(state)
        print(state['error'],flush=True);raise


def analyze():
    assert not any(p.exists() for p in [CHECK,PREFIX,HISTORY]),'Fresh offline analysis artifacts required'
    prepared,completion=read(PREP),read(COMPLETE)
    verify(prepared['inputs']+[prepared['program']]);verify(completion['outputs'])
    assert completion['solver_finished'] and completion['owned_exited'] and completion['exit_code']==0
    assert not active_gpu(),'Solver must be closed before review'
    text=(OUT/'Run.out').read_text(errors='replace');assert 'RTX 3050' in text and 'Finished execution (code=0)' in text
    assert int(re.search(r'PART files\.*:\s*(\d+)',text)[1])==101
    for mk,mode in [(0,'Free slip'),(1,'No-slip'),(2,'Free slip')]:
        assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode,text)
    assert 'SPR stationary wall planes (one per mk): 3' in text
    assert 'SoilStressRateGradCorr="KernelGradient"' in text and 'SoilBoundaryDerivativeSPR="MirroredWallDerivatives"' in text
    hg=hg_stats(text);assert hg['steps'] in [100000,100001]
    dtcheck=read(LOGS/'lian_server_return_r1_poredt.check.json');assert dtcheck['passed'] and 1e-5<=dtcheck['pore_diffusion_limit_s']
    formal=read(LOGS/'lian_hgspr100_r1.check.json'); old=pd.read_csv(CASE/'figures/lian_hgspr100_r1_history.csv',float_precision='round_trip')
    old_by_key={(float(v.time_s),int(v.saved_step)):int(v.part) for v in old[old.part.le(20)].itertuples()}
    expected_old={str(Path(e['path']).resolve()).lower():e for e in formal['sources']}
    files=sorted((OUT/'data').glob('Part_*.bi4'));assert [p.name for p in files]==[f'Part_{i:04d}.bi4' for i in range(101)]
    initial=native(OUT,0); assert len(initial)==initial.id.nunique()==20301
    ids=initial.id.to_numpy(); xyz=initial[['x','y','z']].to_numpy();rows=[];prefix=[]
    stencils={name:[(int(np.flatnonzero(ids==e['native_id'])[0]),e['weight']) for e in points]
        for name,points in formal['paper_material_stencils'].items()}
    masks={key:(np.isclose(initial[col],value,atol=1e-9,rtol=0),col) for key,col,value in
        [('left_normal','x',0),('right_normal','x',20),('bottom_normal','z',0),('bottom_tangent','x',0)]}
    masks['bottom_tangent']=(np.isclose(initial.z,0,atol=1e-9,rtol=0),'x')
    for part in range(101):
        a=initial if part==0 else native(OUT,part);t=float(a.time_s.iloc[0]);step=int(a.saved_step.iloc[0]);source=max(0,t-1e-5)
        assert len(a)==20301 and np.array_equal(a.id,ids) and np.isfinite(a.to_numpy()).all()
        assert a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.nout.eq(0).all()
        assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all()
        assert np.array_equal(a[['mass','h','dp']],initial[['mass','h','dp']])
        assert a.x.between(-.1,20.1).all() and a.z.between(-.1,10.1).all()
        assert abs(t-part*.01)<=1.1e-5 and (part==0 or abs(t-(step+1)*1e-5)<1e-9)
        if part: assert a.has_dterror.eq(1).all() and a.dterror_s.le(1e-14).all()
        contact=a.x.abs().le(1.25);drained=a.fstype.isin([2,3])&~contact;active=source>=1 and t>0
        if active: assert drained.any() and a.pressure[drained].eq(0).all()
        force=float(-(a.mass*a.load_az).sum());expected=13000*min(1,source);assert abs(force-expected)<.002
        displacement=a[['x','y','z']].to_numpy()-xyz;total=a[['sigma_xx','sigma_yy','sigma_zz']].to_numpy()-a.pressure.to_numpy()[:,None]
        corner=a[a.id.eq(1744)].iloc[0]
        row=dict(part=part,time_s=t,saved_step=step,source_prior_time_s=source,
            pressure_min_pa=float(a.pressure.min()),pressure_max_pa=float(a.pressure.max()),pressure_mean_pa=float(a.pressure.mean()),
            pressure_rms_pa=float(np.sqrt(np.mean(a.pressure**2))),vmax_m_s=float(np.linalg.norm(a[['vx','vy','vz']],axis=1).max()),
            total_sigma_zz_min_pa=float(total[:,2].min()),total_sigma_zz_max_pa=float(total[:,2].max()),total_sigma_zz_rms_pa=float(np.sqrt(np.mean(total[:,2]**2))),
            sigma_zz_effective_rms_pa=float(np.sqrt(np.mean(a.sigma_zz**2))),force_N_m=force,expected_force_N_m=expected,
            loaded_count=int(a.load_az.ne(0).sum()),drainage_active=active,potential_drained_count=int(drained.sum()),
            drained_abs_max_pa=float(a.pressure[drained].abs().max()) if active else None,dterror_s=float(a.dterror_s.iloc[0]),
            rho_min_kg_m3=float(a.rho.min()),rho_max_kg_m3=float(a.rho.max()),displacement_max_mm=float(1000*np.linalg.norm(displacement,axis=1).max()),
            id1744_x_m=float(corner.x),id1744_pressure_pa=float(corner.pressure),id1744_load_az=float(corner.load_az),
            id1744_fstype=int(corner.fstype),id1744_contact=bool(abs(corner.x)<=1.25))
        for name,points in stencils.items():
            row[name+'_pressure_pa']=sum(w*float(a.pressure.iloc[k]) for k,w in points)
            row[name+'_settlement_mm']=1000*sum(w*float(initial.z.iloc[k]-a.z.iloc[k]) for k,w in points)
            row[name+'_ux_mm']=1000*sum(w*float(a.x.iloc[k]-initial.x.iloc[k]) for k,w in points)
        for name,(mask,col) in masks.items():row[name+'_max_mm']=1000*float(abs(a.loc[mask,col]-initial.loc[mask,col]).max())
        rows.append(row);key=(t,step)
        if key in old_by_key:
            oldpart=old_by_key[key];p=FORMAL/'data'/f'Part_{oldpart:04d}.bi4'
            verify([expected_old[str(p.resolve()).lower()]]);comparison=compare_prefix(a,native(FORMAL,oldpart))
            prefix.append(dict(new_part=part,formal_part=oldpart,actual_time_s=t,saved_step=step,**comparison))
        if part%20==0:print('CHECKED',part+1,'/101 shared',len(prefix),flush=True)
    assert len(prefix)==21 and {p['formal_part'] for p in prefix}==set(range(21)),'Cadence matching requires reviewed offline diagnosis'
    assert abs(rows[-1]['time_s']-1)<=1.1e-5
    pd.DataFrame(rows).to_csv(HISTORY,index=False,float_format='%.17g')
    seal(PREFIX,dict(passed=True,shared_samples=len(prefix),sole_interval_exception='dterror_s',samples=prefix))
    state=read(RUN);state.update(status='completed_safety_prefix_passed',checked_frames=101,actual_final_time_s=rows[-1]['time_s'],
        actual_gpu=re.search(r'Device default:\s*([^\r\n]+)',text)[1],hg=hg,artifacts=[bound(HISTORY),bound(PREFIX)])
    publish(state)
    seal(CHECK,dict(passed=True,native_safety_passed=True,prefix_passed=True,frames=101,native_ids=20301,
        exact_shared_samples=21,compared_physical_columns=34,actual_final_time_s=rows[-1]['time_s'],hg=hg,
        max_resultant_error_N_m=max(abs(r['force_N_m']-r['expected_force_N_m']) for r in rows),
        active_drained_frames=sum(r['drainage_active'] for r in rows),
        drainage_scope='If zero active frames, this early window does not retest drainage; original100s check remains authoritative.',
        source_links=[bound(PREP),bound(RUN),bound(COMPLETE),bound(PREFIX)],artifacts=[bound(HISTORY)],
        physical_accuracy_changed=False,half_step_tested=False,formal100_rerun=False))
    print('PASSED',CHECK,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);g=parser.add_mutually_exclusive_group()
    g.add_argument('--prepare',action='store_true');g.add_argument('--run',action='store_true');g.add_argument('--analyze',action='store_true')
    args=parser.parse_args()
    if args.prepare:prepare()
    elif args.run:run()
    elif args.analyze:analyze()
    else:parser.print_help()
