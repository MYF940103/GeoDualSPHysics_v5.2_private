"""Check the hydraulic factor at unchanged fixed dt. 'plan' only checks the two sealed baselines."""
import argparse
import csv
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time

import numpy as np

from c02_tpi_cost_r1 import CASE, PLAN, PREFIX, TESTS, directory, need, planned_clock, xml_path
from c02_tpi_cost_review_r1 import FIELDS, SOIL, check_hg, read_native, write_report

TAG = 'c02_tpi_r_fixed4_r1'
LANE = 'tpi40'
DT = 4e-6
CAP = 2501
FACTOR = 2.25


def read_json(path):
    return json.loads(path.read_text(encoding='utf8'))


def setup(backend):
    old = directory(LANE, backend)
    out = TESTS/'outputs'/f'{TAG}_{backend}'
    stem = PLAN['seed_name']
    original = read_json(old/'exit.json')
    start = read_json(old/'start.json')
    certificate = read_json(TESTS/'logs'/f'{PREFIX}_{LANE}_{backend}.json')
    need(original['exit']==0 and original['program_unchanged'] and original['lane']==LANE and original['backend']==backend
         and all(original[k]==v for k,v in start.items()), 'Original solver identity or exit')
    need(certificate['early_100Pa_stress_pass'] and len(certificate['rows'])==13 and certificate['model']==2
         and certificate['steps']==planned_clock(LANE)[-1][0], 'Sealed baseline missing or incomplete')
    need(certificate['host']==original['host']==socket.gethostname(), 'Baseline requires the same host')
    exe = Path(original['program'])
    stat = exe.stat()
    identity = dict(program=str(exe),size=stat.st_size,mtime_ns=stat.st_mtime_ns)
    need(identity==certificate['program_identity'] and all(original[k]==v for k,v in identity.items()), 'Baseline program changed')
    plan = planned_clock(LANE)[:3]
    need([s for s,_,_ in plan]==[0,2500,CAP] and
         [(a['completed'],a['t_s']) for a in certificate['rows'][:3]]==[(s,t) for s,t,_ in plan],
         'Baseline actual event-adjacent clock')
    xml = (old/'seed'/(stem+'.xml')).read_bytes()
    before = b'<HydroMechTpiR value="1.0" />'
    need(xml==xml_path(LANE).read_bytes() and xml.count(before)==1, 'Actual baseline XML or factor changed')
    newxml = xml.replace(before,b'<HydroMechTpiR value="2.25" />')
    for suffix in ('.bi4','_Normals.nbi4'):
        need((old/'seed'/(stem+suffix)).is_file(), 'Missing original seed '+suffix)
    old_args = [str(exe)]+(['-gpu'] if backend=='gpu' else ['-cpu','-ompthreads:1'])
    old_args += ['-stable','-mdbc_freeslip',str(old/'seed'/stem),str(old/'result'),'-dirdataout','data','-svres',
                 '-nsteps:'+str(certificate['steps'])]
    need(original['argv']==old_args, 'Unexpected baseline command')
    args = [(str(out/'seed'/stem) if a==str(old/'seed'/stem) else str(out/'result') if a==str(old/'result') else a)
            for a in old_args]
    args[-1]=f'-nsteps:{CAP}'
    return old,out,certificate,newxml,dict(backend=backend,host=original['host'],reference=str(old),argv=args,**identity)


def execute(backend):
    old,out,_,newxml,stamp = setup(backend)
    out.mkdir()  # An existing result, even an interrupted one, must be preserved.
    seed = out/'seed'
    seed.mkdir()
    stem = PLAN['seed_name']
    for suffix in ('.bi4','_Normals.nbi4'):
        shutil.copyfile(old/'seed'/(stem+suffix),seed/(stem+suffix))
    (seed/(stem+'.xml')).write_bytes(newxml)
    write_report(out/'start.json',stamp)
    begin = time.perf_counter()
    with (out/'console.log').open('xb') as console:
        rc = subprocess.run(stamp['argv'],cwd=CASE,stdout=console,stderr=subprocess.STDOUT).returncode
    write_report(out/'exit.json',dict(**stamp,exit=rc,wall_s=time.perf_counter()-begin))
    need(rc==0,f'Physical solver exited {rc}; preserved {out}/console.log')


def fields_equal(old,new,ids):
    need(old.keys()==new.keys() and 'Idp' in old,'Different field sets')
    left,right=np.argsort(old['Idp']),np.argsort(new['Idp'])
    need(np.array_equal(old['Idp'][left],ids) and np.array_equal(new['Idp'][right],ids),'Missing or duplicate native ID')
    for key,a in old.items():
        b=new[key]
        need(a.shape==b.shape and a.dtype==b.dtype and a[left].tobytes()==b[right].tobytes(),
             'Changed same-step native field '+key)
    return len(old)


def frame(old,new,part,step,t,baseline):
    _,a,fa,ha=read_native(old,part,2,1.)
    _,b,fb,hb=read_native(new,part,2,FACTOR)
    need(a['Cpart']==part and a['Step']==max(0,step-1) and a['TimeStep']==t and a['SymplecticDtPre']==DT,
         'Reference scalar clock')
    for key in ('Cpart','Step','TimeStep','SymplecticDtPre','dtmin','dtmax','Npok','Nout'):
        need(np.asarray(a[key]).tobytes()==np.asarray(b[key]).tobytes(),'Different clock/count '+key)
    need(a['Nout']==0 and fa.keys()==FIELDS and len(FIELDS)==22,'Reference layout')
    count=fields_equal(fa,fb,np.arange(1040))
    need(a['dterror']==baseline['signed_dterror_s'],'Reference signed interval differs from sealed review')
    history_ids=0
    if part==0:
        need(ha is None and hb is None and a['dterror']==b['dterror']==a['dtmin']==a['dtmax']==0,'Initial metadata')
    else:
        need(np.isfinite([a['dterror'],b['dterror']]).all() and max(a['dterror'],b['dterror'])<=1e-14
             and a['dtmin']==a['dtmax']==DT, 'Independent signed timestep guards')
        need(ha is not None and hb is not None and ha['types']==hb['types']
             and ha['array_types']==hb['array_types']=={'Idp':'DatUint','PorePressPrev':'DatFloat'},'Pressure history types')
        # read_native has verified each history's owner against its own parent RunCode.
        for key in ha['types'].keys()-{'RunCode'}:
            need(np.asarray(ha['values'][key]).tobytes()==np.asarray(hb['values'][key]).tobytes(),'Pressure history '+key)
        need(ha['values']['CompletedUpdates']==step and ha['values']['SavedTime']==t,'Pressure history clock')
        fields_equal(ha['arrays'],hb['arrays'],SOIL)
        history_ids=len(SOIL)
    soil=fb['Idp']>=40
    mask=soil & np.isin(fb['FSType'],(2,3))
    need(mask.sum()==10,'Drained receiver count')
    if step==2500:need(np.max(np.abs(fb['PorePress'][mask]))>0,'Drainage opened before source-clock event')
    if step==CAP:need(np.all(fb['PorePress'][mask]==0),'First post-event drainage')
    return dict(part=part,completed=step,t_s=t,exact_native_arrays=count,native_ids=len(fb['Idp']),
                exact_previous_pressure_ids=history_ids,typed_R={'baseline':'omitted (default 1)','candidate':b['HydroMechTpiR']},
                signed_s={'baseline':a['dterror'],'candidate':b['dterror']},
                interval_min_composite_limit_s=({'baseline':DT-a['dterror'],'candidate':DT-b['dterror']} if part else None))


def review(backend):
    old,out,cert,newxml,stamp=setup(backend)
    dest=TESTS/'logs'/f'{TAG}_{backend}.json'
    need(not dest.exists(),'Existing report is preserved: '+str(dest))
    exit_info=read_json(out/'exit.json')
    need(read_json(out/'start.json')==stamp and all(exit_info[k]==v for k,v in stamp.items()) and exit_info['exit']==0,
         'Candidate run identity/exit')
    stem=PLAN['seed_name']
    need((out/'seed'/(stem+'.xml')).read_bytes()==newxml, 'Candidate endpoint, save plan or parameters changed')
    for suffix in ('.bi4','_Normals.nbi4'):
        need((out/'seed'/(stem+suffix)).read_bytes()==(old/'seed'/(stem+suffix)).read_bytes(),'Different seed '+suffix)
    result=out/'result'
    with (result/'Run.csv').open(encoding='utf-8-sig',errors='replace',newline='') as f:
        rr,=csv.DictReader(f,delimiter=';')
    text=(result/'Run.out').read_text(encoding='utf8',errors='replace')
    need(int(rr['Steps'])==CAP and int(rr['PartFiles'])==3 and int(rr['PartsOut'])==0
         and rr['Hardware']==cert['hardware'] and 'Finished execution (code=0)' in text, 'Solver summary/hardware')
    need(re.findall(r'^\s*HydroMechTpiR=(\S+)\s*$',text,re.M)==['2.25'],'Actual factor configuration')
    hg=check_hg(text,CAP)
    plan=planned_clock(LANE)[:3]
    names=[f'Part_{part:04}.bi4' for part in range(len(plan))]
    need(sorted(p.name for p in (result/'data').glob('Part_*.bi4'))==names,'Unexpected PART schedule')
    rows=[]
    for part,(step,t,_) in enumerate(plan):
        name=names[part]
        row=frame(old/'result/data'/name,result/'data'/name,part,step,t,cert['rows'][part])
        previous=0 if not part else rows[-1]['completed']
        row['interval_updates']=step-previous
        row['elapsed_since_previous_save_s']=0 if not part else t-rows[-1]['t_s']
        rows.append(row)
    write_report(dest,dict(passed=True,scope='Same-backend fixed-step hydraulic-factor implementation regression',
                           original_full_steps=cert['steps'],original_saves=len(cert['rows']),candidate_cap=CAP,
                           common_interval_updates=[r['interval_updates'] for r in rows],
                           omitted_reference_saves=len(cert['rows'])-len(rows),hg_limits=hg,run=exit_info,rows=rows))
    print(dest)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('plan','run','review'))
    parser.add_argument('backend',choices=('cpu','gpu'))
    args=parser.parse_args()
    if args.action=='plan':
        old,out,_,_,stamp=setup(args.backend)
        print(json.dumps(dict(reference=str(old),destination=str(out),argv=stamp['argv'],
                              shared_steps=[s for s,_,_ in planned_clock(LANE)[:3]]),indent=2))
    else:
        if args.action=='run':
            execute(args.backend)
        review(args.backend)

