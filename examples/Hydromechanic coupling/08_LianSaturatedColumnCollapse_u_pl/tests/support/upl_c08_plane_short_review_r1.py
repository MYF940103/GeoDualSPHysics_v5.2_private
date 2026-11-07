"""Two independent read-only reviews: Debug CPU/GPU smoke budgets, or literal NoPen-OFF prefix regression."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,struct,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import upl_c08_wall_geometry_r1 as g

T=Path(__file__).resolve().parents[1];TAG='upl_c08_plane_short_review_r1';L=T/'logs'
OLD=T/'outputs/upl_c08_as_short_r1_off_native';OLD_RECEIPT=L/'upl_c08_as_short_r1_off.native.check.json';OLD_RUN=L/'upl_c08_as_short_r1_off.run.json'
POLICY='FixedPlaneStageProjectionReleaseOnly';BOUND=[]

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def bind(entry):
    g.need(g.stat(entry['path'])==entry,'Consumed stat changed: '+entry['path']);BOUND.append(entry);return Path(entry['path'])
def retain(path):BOUND.append(g.stat(path));return Path(path)
def reader_call(entry):
    call=read(bind(entry));g.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual owned native reader exit failed')
    return call

def bundle(native,receipt,samples,backend,nopen,legacy=False):
    r=read(retain(receipt));g.need(r['passed'] is True,'Native receipt not passed')
    if legacy:
        for e in r['files']:bind(e)
        completion=bind(r['native_completion'])
    else:
        g.need(r['consumed_stats_unchanged'] is True,'Native consumed-stat closure missing')
        for e in r['consumed']+r['outputs']:bind(e)
        completion=bind(r['completion'])
    reader_call(r['actual_call']);g.need(completion.samefile(native/'completion.json'),'Completion binding points to another native set');d=read(completion)
    end=4044000 if legacy else 4000800 if samples==2 else 4012000
    counts=dict(samples=samples,completed_steps=end,typed_arrays=22,actual_native_IDs_per_frame=6800,soil_IDs=5000,ledger_checks=5000*samples,fixed_marker_checks=1800*samples,P0_bits_checks=6800*samples,rho_cache_bits_checks=5000*samples,kappa_nondecreasing_from_PRE_checks=5000*samples,nonempty_signed_intervals=samples)
    g.need(d['passed'] is True and all(d[k]==v for k,v in counts.items()) and d['backend_argument']==backend and not d['backend_proven_by_reader'],'Original native coverage/IDs/backend argument differs')
    g.need(d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original clock/ledger/signed guards failed')
    if not legacy:
        g.need(d['NoPenOn_argument'] is nopen and d['DynamicNoPenetrationActive'] is nopen and d['DynamicNoPenetrationReactionClosed'] is False,'Native NoPen flags differ')
        g.need(d['DynamicNoPenetrationPolicy']==(POLICY if nopen else None),'Native fixed-plane policy differs')
    layout=native/'typed22_layout.csv';rawpath=native/'typed22.bin';clockpath=native/'clocks.csv';rows=g.table(retain(layout));g.need(len(rows)==22,'Exactly22 native layout rows required')
    names=['time'];formats=['<f8'];offsets=[0];extent=8
    for row,(name,kind,nc) in zip(rows,g.SCHEMA):
        dt=g.TYPES[kind];g.need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,nc,dt.itemsize*nc),'Native22 schema differs')
        names.append(name);formats.append((dt,(6800,nc)) if nc>1 else (dt,(6800,)));offsets.append(extent);extent+=6800*nc*dt.itemsize
    retain(rawpath);retain(clockpath)
    with rawpath.open('rb') as f:header=struct.unpack('<III',f.read(12))
    g.need(header==(6800,22,samples) and rawpath.stat().st_size==12+samples*extent,'Actual original header/record size differs')
    a=np.memmap(rawpath,mode='r',offset=12,shape=(samples,),dtype=np.dtype(dict(names=names,formats=formats,offsets=offsets,itemsize=extent)));clocks=g.table(clockpath);g.need(len(clocks)==samples,'Actual clock coverage differs')
    ids=np.r_[np.arange(1800),np.arange(2060,7060)].astype(np.uint32);cadence=400 if samples==2 else 4000
    for i,(frame,c) in enumerate(zip(a,clocks)):
        g.need(np.array_equal(frame['Idp'],ids) and int(c['part'])==i and int(c['completed_step'])==4000000+cadence*(i+1) and int(c['saved_step'])+1==int(c['completed_step']),'Native material IDs/actual saved Step differ')
        g.need(struct.pack('<d',float(c['time_s']))==struct.pack('<d',float(frame['time'])) and c['dterror_interval_empty']=='0' and np.isfinite(float(c['signed_dterror_s'])) and float(c['signed_dterror_s'])<=1e-14,'Actual time/nonempty signed diagnostic failed')
        for name,kind,nc in g.SCHEMA:g.need(np.isfinite(frame[name]).all(),'Nonfinite native field: '+name)
    return d,a,clocks,header,extent

def owner(tag,nopen,backend,legacy=False):
    path=OLD_RUN if legacy else L/(tag+'.run.json');r=read(retain(path));g.need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged'],'Original actual solver closure failed')
    text=bind(r['Run_out']).read_text(encoding='utf-8-sig');g.need('No Penetration='+str(nopen) in text and 'ArtificialStress="None"' in text,'Actual NoPen/AS mode differs')
    if not legacy:
        g.need(('debug' in Path(r['program']['path']).name.lower())==tag.startswith('upl_c08_plane_smoke_'),'Unexpected Debug/Release owner selection')
        hardware=r['summary']['Hardware'];g.need(hardware=='CPU' if backend=='CPU' else hardware.startswith('Gpu_'),'Actual owner Hardware differs from review backend')
    root=ET.parse(bind(r['input_xml'])).getroot();pre=bind(r['source_pre_file']);return r,root,pre

def canonical(node):
    g.need(node is not None,'Physical XML section missing')
    return (node.tag,tuple(sorted((k,v) for k,v in node.attrib.items() if k not in ('comment','units_comment'))),(node.text or '').strip(),tuple(canonical(c) for c in node))
def same_physics(old,new,oldpre,newpre):
    g.need(oldpre.samefile(newpre),'Controls use different PRE files')
    for section in ('execution/special/soils','execution/special/hydromechanics','execution/special/mdbcslip','execution/special/initialize','execution/constants'):
        g.need(canonical(old.find(section))==canonical(new.find(section)),'Physical section changed: '+section)
    def parameters(root):
        pairs=[(p.get('key'),p.get('value')) for p in root.findall('execution/parameters/parameter')];r=dict(pairs);g.need(len(r)==len(pairs),'Duplicate input parameter')
        r.setdefault('NoPenetration','0');r.setdefault('ArtificialStress','0');r.pop('TimeMax');return r
    g.need(parameters(old)==parameters(new),'Parameters differ beyond requested endpoint/default explicit zero flags')
    for root in (old,new):
        e=root.find('execution/special/gravitypreload');g.need(e is not None and float(e.get('time'))==10 and int(e.get('release_mkbound'))==2 and e.get('elastic_source','false').lower() in ('false','0'),'Source/event differs')

def smoke():
    cpu='upl_c08_plane_smoke_CPU_r1';gpu='upl_c08_plane_smoke_GPU_r1';rc,xc,pc=owner(cpu,True,'CPU');rg,xg,pg=owner(gpu,True,'GPU');same_physics(xc,xg,pc,pg)
    c=bundle(T/'outputs'/cpu/'native',L/(cpu+'.native.json'),2,'CPU',True);q=bundle(T/'outputs'/gpu/'native',L/(gpu+'.native.json'),2,'GPU',True)
    g.need(c[0]['source_actual_time_s']==q[0]['source_actual_time_s'],'Smoke source actual scalar time differs');rows=[]
    for i,(a,b) in enumerate(zip(c[1],q[1])):
        g.need(abs(float(a['time'])-float(b['time']))<=1e-14 and c[2][i]['completed_step']==q[2][i]['completed_step'],'Smoke actual clocks/steps do not match')
        dp=np.asarray(a['PorePress'][1800:],float)-b['PorePress'][1800:];dx=a['Posd'][1800:]-b['Posd'][1800:];mx=np.max(np.abs(dx),axis=0)*1000
        row=dict(part=i,time_s=float(a['time']),tau_s=float(a['time'])-c[0]['source_actual_time_s'],completed_step=int(c[2][i]['completed_step']),pressure_RMS_difference_Pa=float(np.sqrt(np.mean(dp*dp))),pressure_max_abs_difference_Pa=float(np.abs(dp).max()),CPU_signed_dterror_s=float(c[2][i]['signed_dterror_s']),GPU_signed_dterror_s=float(q[2][i]['signed_dterror_s']))
        for j,axis in enumerate('xyz'):row[axis+'_max_abs_difference_mm']=float(mx[j]);row[axis+'_worst_native_id']=int(a['Idp'][1800+int(np.argmax(np.abs(dx[:,j])))])
        row['original_pressure_and_xyz_budgets_passed']=bool(row['pressure_RMS_difference_Pa']<=5 and np.all(mx<=.005));rows.append(row)
    return rows,dict(passed=all(r['original_pressure_and_xyz_budgets_passed'] for r in rows),pressure_RMS_budget_Pa=5,each_material_xyz_budget_mm=.005,Debug_CPU_vs_Debug_GPU=True,Debug_Release_bit_equivalence_claimed=False)

def off():
    tag='upl_c08_plane_off_GPU_r1';rn,xn,pn=owner(tag,False,'GPU');ro,xo,po=owner('',False,'GPU',True);same_physics(xo,xn,po,pn)
    new=bundle(T/'outputs'/tag/'native',L/(tag+'.native.json'),3,'GPU',False);old=bundle(OLD,OLD_RECEIPT,11,'GPU',False,True)
    g.need(new[0]['source_actual_time_s']==old[0]['source_actual_time_s'] and new[4]==old[4],'OFF source clock/record layout differs')
    cn=(T/'outputs'/tag/'native/clocks.csv').read_bytes().splitlines(keepends=True);co=(OLD/'clocks.csv').read_bytes().splitlines(keepends=True)
    rows=[];header_equal=cn[0]==co[0];layout_equal=(T/'outputs'/tag/'native/typed22_layout.csv').read_bytes()==(OLD/'typed22_layout.csv').read_bytes()
    for i in range(3):
        g.need(new[2][i]['completed_step']==old[2][i]['completed_step'] and struct.pack('<d',float(new[1][i]['time']))==struct.pack('<d',float(old[1][i]['time'])),'OFF actual time/step differs')
        rows.append(dict(part=i,time_s=float(new[1][i]['time']),completed_step=int(new[2][i]['completed_step']),full_time_and22_record_bytes_equal=new[1][i].tobytes()==old[1][i].tobytes(),clock_header_bytes_equal=header_equal,full_original_clock_row_including_signed_bytes_equal=cn[i+1]==co[i+1],layout_bytes_equal=layout_equal))
    return rows,dict(passed=all(all(r[k] for k in ('full_time_and22_record_bytes_equal','clock_header_bytes_equal','full_original_clock_row_including_signed_bytes_equal','layout_bytes_equal')) for r in rows),new_original_header=list(new[3]),old_original_header=list(old[3]),headers_rewritten=False,old_control=str(OLD),old_NoPen=False,old_ArtificialStress=False,old_failed_runtime_relabelled_success=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('phase',choices=('smoke','off'));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();g.need(a.execution_authorized,'Author-only until root review authorizes execution')
    check=L/(TAG+'.'+a.phase+'.json');table=T/'figures'/(TAG+'_'+a.phase+'.csv');g.need(not check.exists() and not table.exists(),'Existing phase evidence protected')
    retain(__file__);retain(T/'support/upl_c08_wall_geometry_r1.py');retain(T/'support/upl_c08_fsmask_r1.py');result=dict(stage=TAG,phase=a.phase,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0)
    try:
        rows,metrics=smoke() if a.phase=='smoke' else off()
        with table.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        result.update(metrics,rows=rows,output=g.stat(table));g.need(all(g.stat(e['path'])==e for e in BOUND),'Consumed bindings changed during review');result['consumed_stats_unchanged']=True
    except Exception as e:result.update(passed=False,first_failure=str(e))
    result['consumed']=BOUND
    with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(passed=result['passed'],phase=a.phase,receipt=str(check),first_failure=result.get('first_failure')),allow_nan=False));g.need(result['passed'],result.get('first_failure','Declared comparison budget/regression failed'))

if __name__=='__main__':main()
