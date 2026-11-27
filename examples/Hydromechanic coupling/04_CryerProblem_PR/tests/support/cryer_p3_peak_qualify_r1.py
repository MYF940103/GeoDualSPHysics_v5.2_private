"""Review one returned peak with the exact shipped package, issuing full admission only on pass."""
import argparse
import csv
import hashlib
import json
from pathlib import Path, PureWindowsPath
import tempfile
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

from pack_cryer_tpi_p3_r1 import BIN, CASE, DT, MANIFEST, PACKAGE, PROFILES, SEED, SOLVER, physics_signature, stem
from cryer_p3_sidecar_review_r1 import inspect

TAG = 'CaseCryer_TPI_P3_nu030_peak_r1'
REVIEW = 'cryer_tpi_p3_peak_review.json'


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, doc):
    with path.open('x',encoding='utf-8') as f:
        json.dump(doc,f,indent=2,allow_nan=False)


def bind(package, folder, stage='peak'):
    tag=stem(stage)
    steps,frames,_=PROFILES[stage]
    read_member=lambda p:package.read(p.as_posix())
    m=json.loads(read_member(MANIFEST))
    entries={i['name']:i for i in m['files']}
    need(m['method']=='Cryer P3 Eq40 Rh1' and m['scheme']=='B' and m['rounds']==3
         and m['nu']==.30 and m['dt_s']==float(DT),'wrong package/method')
    def checked(p):
        data=read_member(p)
        e=entries[p.as_posix()]
        need(len(data)==e['bytes'] and sha(data)==e['sha256'],f'Packaged input changed: {p}')
        return data
    definition=checked(Path(tag+'_Def.xml'))
    template=checked(SEED.with_suffix('.xml'))
    bi4=checked(SEED.with_suffix('.bi4'))
    checked(BIN/SOLVER)
    need(entries[(BIN/SOLVER).as_posix()]['sha256']==m['program_sha256'],'packaged executable binding')
    peak_definition=definition if stage=='peak' else checked(Path(TAG+'_Def.xml'))
    need(sha(peak_definition+template+bi4)==m['peak_input_sha256'],'packaged peak binding')
    need((folder/(tag+'.bi4')).read_bytes()==bi4,'returned initial particle file')
    actual=ET.parse(folder/(tag+'.xml')).getroot()
    base=ET.fromstring(template)
    new=ET.fromstring(definition)
    for key in ('special','parameters'):
        block=base.find('execution'); block.remove(block.find(key)); block.append(new.find('execution/'+key))
    # File formatting and generated case dates are distinct from solver input.
    for loc in ('casedef','execution/special','execution/parameters','execution/particles',
                'execution/constants','execution/uservars','execution/motion','execution/vtkout'):
        need(physics_signature(actual.find(loc))==physics_signature(base.find(loc)),f'returned XML: {loc}')
    schedule=checked(Path('support')/(tag+'_schedule.csv'))
    run=read(folder/'server_run.json')
    launch=read(folder/'launch.json')
    for rec in (launch,run):
        need(rec['profile']==stage and rec['package_id']==m['package_id']
             and rec['program_sha256']==m['program_sha256'] and rec['peak_input_sha256']==m['peak_input_sha256']
             and rec['selectors']==m['selectors'],'run/program or input binding')
        cmd=rec['arguments']
        need(len(cmd)==8 and cmd[:2]==['-gpu','-stable'] and PureWindowsPath(cmd[2]).name==tag
             and PureWindowsPath(cmd[3]).name==tag+'_GPU_out'
             and cmd[4:]==['-dirdataout','data','-svres',f'-nsteps:{steps}'],'command binding')
    need(run['arguments']==launch['arguments'] and run['solver']==launch['solver']
         and PureWindowsPath(run['solver']).name==SOLVER
         and run['status'] in ('completed_pending_native_physical_review','solver_completed_summary_needs_review')
         and run['solver_exit']==0,'server completion')
    # Only use uniquely indexed Run.csv fields. Timer/telemetry columns may repeat.
    lines=(folder/'Run.csv').read_bytes().decode('utf-8-sig',errors='replace').splitlines()
    need(len(lines)==2,'Run.csv row count')
    keys=lines[0].lstrip('#').split(';'); vals=lines[1].split(';')
    required=('Steps','PartFiles','PartsOut','Hardware','Np')
    need(len(keys)==len(vals) and all(keys.count(k)==1 for k in required),'Run.csv headers')
    fields={k:vals[keys.index(k)] for k in required}
    need([int(fields[k]) for k in ('Steps','PartFiles','PartsOut','Np')]==[steps,frames,0,37181]
         and 'gpu' in fields['Hardware'].lower() and 'nvidia' in fields['Hardware'].lower(),'Run.csv values')
    for name,value in (('steps',steps),('part_files',frames),('hardware',fields['Hardware'])):
        need(run[name] is None or run[name]==value,'Conflicting server summary: '+name)
    need('Finished execution (code=0).' in (folder/'Run.out').read_text(encoding='utf-8',errors='replace'),'Run.out terminal')
    return m,schedule


def review_run(folder,raw_plan,review,stage):
    need(not review.exists(),'Review destination must be fresh; preserve and inspect any previous analysis.')
    plan=list(csv.DictReader(raw_plan.decode('ascii').splitlines()))
    steps=[int(r['completed_steps']) for r in plan]
    last,count,_=PROFILES[stage]
    need(len(steps)==count and steps[:65]==list(range(0,4097,64)) and steps[-1]==last
         and all(b>a for a,b in zip(steps,steps[1:])), 'Packaged schedule shape')
    if stage=='peak':
        need(steps==list(range(0,last+1,64)), 'Peak schedule shape')
    with (folder/'UplTpiP3DtR1.csv').open(newline='') as f:
        dt_rows=list(csv.DictReader(f))
    need([int(r['completed_updates']) for r in dt_rows]==steps and
         [float(r['actual_save_time_s']) for r in dt_rows]==[float(r['time_s']) for r in plan],
         'Method clock differs from shipped plan')
    review.mkdir(parents=True)
    side=inspect(folder,last)
    need(side['passed'] and side['frames']==count and side['actual_post_open_frames']==count-65
         and side['pressure_rounds']==3 and side['dt_phases']==5 and side['device_and_saved_body_receivers']==37173
         and side['completely_audited_saved_ids_per_round']==18 and side['inspected_pressure_rows']==count*18*3,
         'Incomplete five-phase or pressure-round coverage')
    write(review/'sidecar_review.json',side)
    with tempfile.TemporaryDirectory(prefix='cryer_return_') as name:
        target=Path(name)/'schedule.csv'
        target.write_bytes(raw_plan)
        # This downstream analyzer is the sole BI4 reader in this workflow.
        proc=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('cryer_p3_return_r1.py')),
                             str(folder),str(target),str(review/'physical')],check=False)
        need(proc.returncode==0,'Native/physical analysis failed; preserve output and diagnose offline.')
    ph=read(review/'physical/physical_review.json')
    with (review/'physical/native_and_theory.csv').open(newline='') as f:
        native=list(csv.DictReader(f))
    need([int(r['completed_step']) for r in native]==steps and
         all(float(n['time_s'])==float(d['time_s']) for n,d in zip(native,plan)), 'Native clock plan')
    need(all(int(r['active_drain_count'])==0 for r in native[:65]) and
         all(int(r['active_drain_count'])>0 and float(r['surface_p_absmax_Pa'])==0 for r in native[65:]),
         'True drained receivers')
    need(ph['stage']==stage and ph['center_material_ids']==18,'Unexpected physical scope')
    return ph,native,side,steps


def qualify(folder,package,review):
    with zipfile.ZipFile(package) as z:
        manifest,raw_plan=bind(z,folder)
    ph,native,side,steps=review_run(folder,raw_plan,review,'peak')
    phys_flags=ph['criteria']
    need(set(phys_flags)=={'sampling','peak_within_one_percent','no_worse_than_A_plus_0p10pp','peak_time'}
         and ph['stage']=='peak' and ph['center_material_ids']==18,'Unexpected physical scope')
    bindings=[dict(name=f,sha256=sha((folder/f).read_bytes())) for f in ('Run.csv','server_run.json')]
    approval=dict(peak_qualified=bool(ph['peak_physical_criteria_met'] and all(phys_flags.values())),
                  scheme='B',rounds=3,nu=.30,dt_s=float(DT),package_id=manifest['package_id'],
                  program_sha256=manifest['program_sha256'],peak_input_sha256=manifest['peak_input_sha256'],
                  peak_steps=steps[-1],peak_server_files=bindings,
                  native=dict(frames=len(native),end_s=float(native[-1]['time_s']),post_open_frames=len(native)-65,
                              drained_receivers_checked=sum(int(r['active_drain_count']) for r in native)),
                  sidecar=dict(pressure_rounds=side['pressure_rounds'],dt_phases=side['dt_phases'],rows=side['inspected_pressure_rows']),
                  physics=dict(sampling=phys_flags['sampling'],amplitude=phys_flags['peak_within_one_percent'],
                               amplitude_vs_A=phys_flags['no_worse_than_A_plus_0p10pp'],phase=phys_flags['peak_time'],
                               amplitude_error_pct=ph['amplitude_error_pct'],phase_error_s=ph['phase_error_s']),
                  local_evidence=[dict(name=s,sha256=sha((review/s).read_bytes())) for s in
                                  ('sidecar_review.json','physical/physical_review.json','physical/native_and_theory.csv')])
    write(review/(REVIEW if approval['peak_qualified'] else 'peak_rejected.json'),approval)
    return approval['peak_qualified']


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output',type=Path);ap.add_argument('destination',type=Path)
    ap.add_argument('--package',type=Path,default=PACKAGE)
    args=ap.parse_args()
    sys.exit(0 if qualify(args.output.resolve(),args.package.resolve(),args.destination.resolve()) else 1)

