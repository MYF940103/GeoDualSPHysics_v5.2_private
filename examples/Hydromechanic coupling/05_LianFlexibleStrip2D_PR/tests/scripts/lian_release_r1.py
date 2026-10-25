"""Real-program u-pw admission, native material histories and retained comparison.

Run from the case root with D:/Anaconda3/python.exe -B tests/scripts/lian_release_r1.py.
Fresh starts only; never deletes or overwrites a retained output directory.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CASE = Path(__file__).resolve().parents[2]
TESTS = CASE/'tests'
REPO = CASE.parents[2]
READER = TESTS/'outputs/hydro_native_r1/ReadHydroNative.exe'
TAG = 'lian_release_r1'
STAGES = {
    'smoke': [('cpu_debug', '.00001', '.002', '.001'), ('gpu_c', '.00001', '.15', '.005'), ('gpu_h', '.000005', '.15', '.005')],
    'drained': [('gpu_c', '.00001', '3', '.05'), ('gpu_h', '.000005', '3', '.05')],
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def bound(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return dict(path=str(path.resolve()), sha256=h.hexdigest(), bytes=path.stat().st_size)


def native(folder, part):
    raw = subprocess.check_output([str(READER), str(Path(folder)/'data'), str(part)])
    return pd.read_csv(io.BytesIO(raw), float_precision='round_trip')


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf8')


def prepare(stage):
    base = (CASE/'CaseLianFlexibleStrip2D_PR_Def.xml').read_text(encoding='utf8')
    for backend, dt, duration, cadence in STAGES[stage]:
        name = f'{TAG}_{stage}_{backend}'
        config = TESTS/'configs'/(name+'_Def.xml')
        bat = TESTS/'configs'/('x'+name+'_win64.bat')
        assert not config.exists() and not bat.exists(), 'Prepared inputs already exist'
        text = base
        for key, value in [('SavePosDouble','1'), ('DtIni',dt), ('DtFixed',dt), ('TimeMax',duration), ('TimeOut',cadence)]:
            text, count = re.subn(r'(<parameter key="'+key+r'" value=")[^"]+', lambda m: m[1]+value, text)
            assert count == 1, key
        # Explicitly isolate the current stress-state implementation. No new SPR/HG/load physics.
        extra = ''.join('            <parameter key="'+key+'" value="0" comment="Disabled to isolate retained u-pw path" />\n'
                        for key in ('SoilStressRateGradCorr','SoilBoundaryDerivativeSPR','SoilHourglassXi'))
        text = text.replace('        <parameters>\n', '        <parameters>\n'+extra)
        config.write_text(text, encoding='utf8')
        program = 'DualSPHysics5.2CPU_win64_debug.exe' if backend == 'cpu_debug' else 'DualSPHysics5.2_GEO_win64.exe'
        flags = '-cpu -ompthreads:8' if backend == 'cpu_debug' else '-gpu'
        # Follow existing case BAT variables and error handling, but refuse retained-output deletion.
        batch = f'''@echo off
setlocal
cd /d "%~dp0..\\.."
set name={name}
set dirout=tests\\outputs\\%name%
set diroutdata=%dirout%\\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="%dirbin%/{program}"
if exist "%dirout%" goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysics% {flags} -stable -mdbc_freeslip %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0
:fail
echo Execution aborted; retained outputs are never deleted.
exit /b 1
'''
        bat.write_text(batch.replace('\n','\r\n'), encoding='utf8', newline='')
    print('Prepared', stage, 'XML/BAT pairs; no solver launched')


def inspect(folder, duration=None):
    files = sorted((Path(folder)/'data').glob('Part_*.bi4'))
    assert files, 'No saved PARTs'
    initial = native(folder, 0)
    ids = initial.id.to_numpy()
    top = initial.z.gt(9.99).to_numpy()
    probes = {name: int(np.argmin((initial.x-x)**2+(initial.z-z)**2))
              for name,(x,z) in {'A':(.1,10), 'A_below':(.1,9.9), 'B':(1.25,8.75)}.items()}
    rows = []
    for i in range(len(files)):
        a = native(folder, i)
        assert np.array_equal(a.id, ids) and np.isfinite(a.to_numpy()).all()
        assert a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.nout.eq(0).all()
        assert (a.x.min()>-.1 and a.x.max()<20.1 and a.z.min()>-.1 and a.z.max()<10.1)
        t = float(a.time_s.iloc[0])
        loaded = a.load_az.abs().gt(0)
        strip = a.x.ge(0) & a.x.le(1.25) & a.z.between(9.95,10.05)
        drained = a.fstype.eq(2) & a.normal_z.gt(0) & ~a.x.between(0,1.25)
        if t > 1.0001:
            assert a.pressure[drained].eq(0).all(), ('Open-top drainage',t)
        if i and a.has_dterror.iloc[0]:
            assert a.dterror_s.iloc[0] <= 1e-14, ('Fixed dt exceeds natural limit', t, a.dterror_s.iloc[0])
        row = dict(part=i, time_s=t, pressure_min_pa=a.pressure.min(), pressure_max_pa=a.pressure.max(),
                   pressure_mean_pa=a.pressure.mean(), pressure_rms_pa=np.sqrt(np.mean(a.pressure**2)),
                   vmax_m_s=np.linalg.norm(a[['vx','vy','vz']],axis=1).max(),
                   top_material_mean_settlement_mm=1000*(initial.z[top].to_numpy()-a.z[top].to_numpy()).mean(),
                   sigma_zz_min_pa=a.sigma_zz.min(), sigma_zz_max_pa=a.sigma_zz.max(),
                   loaded_count=int(loaded.sum()), geometric_strip_count=int(strip.sum()),
                   total_load_N_m=float(-(a.mass*a.load_az).sum()),
                   has_load=bool(a.load_available.iloc[0]), position_double=bool(a.position_double.iloc[0]),
                   stress_double=bool(a.stress_double.iloc[0]))
        for name, index in probes.items():
            row[name+'_native_id'] = int(ids[index])
            row[name+'_pressure_pa'] = float(a.pressure.iloc[index])
            row[name+'_settlement_mm'] = 1000*float(initial.z.iloc[index]-a.z.iloc[index])
        rows.append(row)
    if duration is not None:
        assert abs(rows[-1]['time_s']-float(duration)) < 2e-5, 'Missing actual final time'
    return pd.DataFrame(rows), initial


def pair(coarse, half):
    ca = sorted((coarse/'data').glob('Part_*.bi4'))
    hb = sorted((half/'data').glob('Part_*.bi4'))
    assert len(ca)==len(hb)
    origin = native(coarse,0)
    top = origin.z.gt(9.99).to_numpy()
    rows=[]
    for i in range(len(ca)):
        a,b=native(coarse,i),native(half,i)
        assert np.array_equal(a.id,b.id)
        delta_t=abs(float(a.time_s.iloc[0]-b.time_s.iloc[0]))
        assert delta_t <= 1.01e-5, ('Saved times cannot be paired',i,delta_t)
        p_rms=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
        top_error=1000*float(np.max(abs(a.z.to_numpy()[top]-b.z.to_numpy()[top])))
        rows.append(dict(part=i,coarse_time_s=float(a.time_s.iloc[0]),half_time_s=float(b.time_s.iloc[0]),
                         saved_time_difference_s=delta_t,pressure_rms_difference_pa=p_rms,top_material_max_difference_mm=top_error))
    frame=pd.DataFrame(rows)
    return frame, bool(frame.pressure_rms_difference_pa.le(5).all() and frame.top_material_max_difference_mm.le(.005).all())


def run(stage):
    state=TESTS/'logs'/f'{TAG}_{stage}.status.json'
    assert not state.exists(), 'Never restart an old sequence'
    if stage=='drained':
        previous=json.loads((TESTS/'logs'/f'{TAG}_smoke.review.json').read_text())
        assert previous['passed'] and previous['visual_review_passed'], 'Short physical/visual review first'
    inputs=[bound(__file__),bound(READER),bound(CASE/'CaseLianFlexibleStrip2D_PR_Def.xml')]
    record=dict(status='running',owned_sequence_pid=os.getpid(),started_utc=utc(),stage=stage,runs=[],inputs=inputs,
                git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),production_modified=False)
    write_json(state,record)
    try:
        for backend,dt,duration,cadence in STAGES[stage]:
            name=f'{TAG}_{stage}_{backend}'
            config=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64.bat')
            assert not (TESTS/'outputs'/name).exists()
            program=REPO/'bin/windows'/('DualSPHysics5.2CPU_win64_debug.exe' if backend=='cpu_debug' else 'DualSPHysics5.2_GEO_win64.exe')
            inputs.extend([bound(config),bound(bat),bound(program),bound(REPO/'bin/windows/GenCase_win64.exe')])
            record['current_run']=name
            log=TESTS/'logs'/(name+'.log')
            start=time.perf_counter()
            with log.open('xb') as f:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(bat)],cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                record['owned_wrapper_pid']=child.pid;write_json(state,record)
                code=child.wait()
            entry=dict(name=name,exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-start,log=bound(log))
            record['runs'].append(entry);write_json(state,record)
            assert code==0 and 'Finished execution (code=0)' in log.read_text(errors='replace'), name
            folder=TESTS/'outputs'/name
            history,initial=inspect(folder,duration)
            assert len(initial)==20301 and history.stress_double.all() and history.position_double.all()
            history.to_csv(TESTS/'figures'/(name+'_history.csv'),index=False,float_format='%.17g')
            entry['actual_final_time_s']=float(history.time_s.iloc[-1]);entry['saved_frames']=len(history)
            entry['outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()]
            write_json(TESTS/'logs'/(name+'.run.json'),entry)
            write_json(state,record)
        frame,passed=pair(TESTS/'outputs'/f'{TAG}_{stage}_gpu_c',TESTS/'outputs'/f'{TAG}_{stage}_gpu_h')
        frame.to_csv(TESTS/'figures'/f'{TAG}_{stage}_half.csv',index=False,float_format='%.17g')
        assert passed, ('All-sample half gate failed', frame.max().to_dict())
        for item in inputs:
            assert bound(item['path'])['sha256']==item['sha256'], 'Run input changed'
        record.update(status='completed_pending_review',half_passed=True,
                      pressure_rms_half_max_pa=float(frame.pressure_rms_difference_pa.max()),
                      top_material_half_max_mm=float(frame.top_material_max_difference_mm.max()))
    except Exception as error:
        record.update(status='rejected_or_interrupted',error=repr(error));raise
    finally:
        record['updated_utc']=utc();write_json(state,record)


def review(stage):
    state=TESTS/'logs'/f'{TAG}_{stage}.status.json'
    record=json.loads(state.read_text());assert record['status']=='completed_pending_review'
    output=TESTS/'logs'/f'{TAG}_{stage}.review.json';assert not output.exists()
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for key,color,style in [('gpu_c','#215a8a','-'),('gpu_h','#b56b28','--')]:
        path=TESTS/'figures'/f'{TAG}_{stage}_{key}_history.csv'
        data=pd.read_csv(path)
        for ax,column,label in zip(axes.flat,['A_pressure_pa','B_pressure_pa','A_settlement_mm','total_load_N_m'],
                                   ['A native pressure (Pa)','B native pressure (Pa)','A native settlement (mm)','Actual nodal force (N/m)']):
            ax.plot(data.time_s,data[column],style,color=color,label=key)
            ax.set(xlabel='Actual saved time (s)',ylabel=label);ax.grid(alpha=.2)
    axes[0,0].legend();fig.suptitle('Lian original loading / SPR off / HG off - short admission, not late-time acceptance')
    png=TESTS/'figures'/f'{TAG}_{stage}_history.png';fig.savefig(png,dpi=160);plt.close(fig)
    write_json(output,dict(passed=True,visual_review_passed=False,scope='Native short-window and half-step admission only',
               pressure_rms_half_max_pa=record['pressure_rms_half_max_pa'],top_material_half_max_mm=record['top_material_half_max_mm'],
               sources=[bound(state)]+[bound(TESTS/'figures'/f'{TAG}_{stage}_{k}_history.csv') for k in ('gpu_c','gpu_h')],artifacts=[bound(png)]))
    print(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','run','review'])
    parser.add_argument('--stage',choices=STAGES,default='smoke')
    args=parser.parse_args()
    {'prepare':prepare,'run':run,'review':review}[args.action](args.stage)
