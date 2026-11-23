"""Prepare a single common-physics C02 comparison. Only the explicit run command starts a process."""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import socket
import subprocess
import time
import xml.etree.ElementTree as ET

TESTS = Path(__file__).resolve().parents[1]
CASE = TESTS.parent
ROOT = CASE.parents[2]
PREFIX = 'c02_tpi_cost_r1'
PLAN = json.loads((TESTS/'configs'/(PREFIX+'.json')).read_text(encoding='utf8'))
REFERENCES = json.loads((TESTS/'configs/c02_tpi_cost_ref_r1.json').read_text(encoding='utf8'))
if PLAN['lanes'].keys() & REFERENCES['lanes'].keys():
    raise ValueError('Supplementary explicit lanes would overwrite an original definition')
PLAN['lanes'].update(REFERENCES['lanes'])
OPTIONAL=json.loads((TESTS/'configs/c02_tpi_cost_optional_r1.json').read_text(encoding='utf8'))['lanes']
if PLAN['lanes'].keys() & OPTIONAL.keys():
    raise ValueError('Conditional lanes would overwrite an existing definition')
PLAN['lanes'].update(OPTIONAL)
MC = 2e6*(1-.3)/((1+.3)*(1-2*.3))
CV = PLAN['hydraulic_conductivity_m_s']*MC/9810.
EVENT = PLAN['ramp_and_drain_s']
OUTPUT_PERIOD = PLAN['save_delta_Tv']/CV
END = EVENT + PLAN['end_Tv']/CV


def need(ok, message):
    if not ok:
        raise ValueError(message)


def directory(lane, backend):
    return TESTS/'outputs'/(PREFIX+'_'+lane+'_'+backend)


def property_(node, name, value):
    need(node is not None, 'Original column input lacks '+name)
    node.set(name,str(value))


def setup_xml(lane):
    cfg = PLAN['lanes'][lane]
    dt = cfg['dt_s']
    count = math.ceil(END/dt)
    event_step = round(EVENT/dt)
    need(math.isclose(event_step*dt,EVENT,abs_tol=1e-16,rel_tol=0), 'Event must have a fixed-step index')
    path = TESTS/PLAN['seed_directory']/(PLAN['seed_name']+'.xml')
    root = ET.parse(path)
    sp = root.find('execution/special')
    hm = sp.find('hydromechanics')
    need(hm.find('HydroMechModel').get('value')=='2' and hm.find('HydroMechConductivityModel').get('value')=='0','Unexpected seed')
    hm.find('HydroMechModel').set('value',str(cfg['model']))
    hm.find('HydroMechModel').attrib.pop('comment',None)
    hm.find('HydraulicConductivity').set('value',str(PLAN['hydraulic_conductivity_m_s']))
    if cfg['model']==2:
        ET.SubElement(hm,'HydroMechTpiR',value=str(cfg['R']))
    property_(sp.find('drainage'),'start',EVENT)
    property_(sp.find('externalload'),'ramptime',EVENT)
    p = root.find('execution/parameters')
    for key,val in {'DtFixed':dt,'DtIni':dt,'TimeOut':OUTPUT_PERIOD,'TimeMax':END}.items():
        el=p.find("parameter[@key='"+key+"']")
        el.attrib.pop('comment',None)
        property_(el,'value',val)
    # Anchor the two event-adjacent samples to integer steps; normalized saves use the original physical clock.
    timeout=sp.find('timeout')
    timeout.clear()
    timeout.set('active','true')
    for base,interval in ((0.,1.),(EVENT-dt/2,1.),(EVENT+dt/2,1.),(EVENT+OUTPUT_PERIOD,OUTPUT_PERIOD)):
        ET.SubElement(timeout,'tout',time=repr(base),timeout=repr(interval))
    ET.indent(root,space='  ')
    return root,count,event_step


def xml_path(lane):
    return TESTS/'configs'/(PREFIX+'_'+lane+'.xml')


def planned_clock(lane):
    cfg=PLAN['lanes'][lane]
    dt=cfg['dt_s']
    n=math.ceil(END/dt)
    t=0.
    clocks=[t]
    for _ in range(n):
        t+=dt
        clocks.append(t)
    import bisect
    targets=[(0,0.),(round(EVENT/dt),EVENT),(round(EVENT/dt)+1,EVENT+dt)]
    for i in range(1,round(PLAN['end_Tv']/PLAN['save_delta_Tv'])+1):
        target=EVENT+i*OUTPUT_PERIOD
        step=bisect.bisect_left(clocks,target)
        # The cap saves the last state even if the clock rounds below a request.
        targets.append((min(step,n),target))
    return [(step,clocks[step],target) for step,target in targets]


def prepare(lane=None):
    for name in ((lane,) if lane else [k for k in PLAN['lanes'] if k not in OPTIONAL]):
        root,_,_=setup_xml(name)
        encoded=ET.tostring(root.getroot(),encoding='utf-8',xml_declaration=True)
        path=xml_path(name)
        if path.exists():
            need(path.read_bytes()==encoded,'Existing generated XML differs: '+str(path))
        else:
            with path.open('xb') as f:
                f.write(encoded)
        clocks=planned_clock(name)
        print(name, 'updates',clocks[-1][0],'end_s',clocks[-1][1],'frames',len(clocks))


def conditional_evidence(backend):
    # A deliberate run of the named optional lane requests an R>1 alternative.
    # One fully reviewed backend is enough to select the same configuration for the paired backend.
    from c02_tpi_cost_ref_review_r1 import against_reference
    from c02_tpi_cost_summary_r1 import single
    for side in (backend,'cpu' if backend=='gpu' else 'gpu'):
        required=('kw10','tpi40','tpi100')
        if not all((TESTS/'logs'/f'{PREFIX}_{lane}_{side}.json').is_file() for lane in required):
            continue
        anchor=single('kw10',side)[0]
        possible=[anchor]
        if (TESTS/'logs'/f'{PREFIX}_kw125_{side}.json').is_file():
            alternate=single('kw125',side)[0]
            if against_reference(anchor,alternate,anchor)['predeclared_target_noninferiority_pass']:
                possible.append(alternate)
        reference=min(possible,key=lambda v:v['wall_s'])
        checks={lane:against_reference(reference,single(lane,side)[0],anchor)['predeclared_target_noninferiority_pass']
                for lane in ('tpi40','tpi100')}
        if checks=={'tpi40':True,'tpi100':False}:
            return dict(backend=side,anchor=anchor['lane'],reference=reference['lane'],accuracy=checks)
    raise ValueError('Conditional 6.25 us lane requires a reviewed 4 us pass and 10 us accuracy failure')


def run(name,backend,exe_override=None,last_part=None):
    cfg=PLAN['lanes'][name]
    root,n,_=setup_xml(name)
    if last_part is not None:
        clocks=planned_clock(name)
        need(0<last_part<len(clocks),'Execution cap must be an original planned save')
        n=clocks[last_part][0]
    need(xml_path(name).read_bytes()==ET.tostring(root.getroot(),encoding='utf-8',xml_declaration=True), 'Prepared input differs')
    exe=exe_override or ROOT/'bin/windows'/('DualSPHysics5.2_GEO_win64.exe' if backend=='gpu' else 'DualSPHysics5.2CPU_win64.exe')
    exe=exe.resolve(strict=True)
    decision=conditional_evidence(backend) if name in OPTIONAL else None
    output=directory(name,backend)
    output.mkdir()
    seed=output/'seed'
    seed.mkdir()
    src=TESTS/PLAN['seed_directory']
    stem=PLAN['seed_name']
    for ext in ('.bi4','_Normals.nbi4'):
        shutil.copyfile(src/(stem+ext),seed/(stem+ext))
    shutil.copyfile(xml_path(name),seed/(stem+'.xml'))
    args=[str(exe)]+(['-gpu'] if backend=='gpu' else ['-cpu','-ompthreads:1'])
    args+=['-stable','-mdbc_freeslip',str(seed/stem),str(output/'result'),'-dirdataout','data','-svres','-nsteps:'+str(n)]
    identity=exe.stat()
    stamp={'program':str(exe),'size':identity.st_size,'mtime_ns':identity.st_mtime_ns,'host':socket.gethostname(),'lane':name,'backend':backend,'input':str(xml_path(name)),'argv':args}
    if decision is not None:stamp['conditional_selection']=decision
    (output/'start.json').write_text(json.dumps(stamp,indent=2),encoding='utf8')
    t=time.perf_counter()
    with (output/'console.log').open('xb') as log:
        rc=subprocess.run(args,cwd=CASE,stdout=log,stderr=subprocess.STDOUT).returncode
    stamp.update(exit=rc,wall_seconds=time.perf_counter()-t)
    final=exe.stat()
    stamp['program_unchanged']=final.st_size==identity.st_size and final.st_mtime_ns==identity.st_mtime_ns
    (output/'exit.json').write_text(json.dumps(stamp,indent=2),encoding='utf8')
    if rc:
        raise SystemExit(rc)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['prepare','run'])
    ap.add_argument('--lane',choices=PLAN['lanes'])
    ap.add_argument('--backend',choices=['cpu','gpu'])
    ap.add_argument('--exe',type=Path,help='Optional isolated executable with its adjacent runtime DLLs')
    args=ap.parse_args()
    if args.action=='prepare':
        prepare(args.lane)
    else:
        if not args.lane or not args.backend:
            ap.error('run requires --lane and --backend')
        run(args.lane,args.backend,args.exe)
