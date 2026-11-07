"""One reader invocation for an already closed actual r3 GPU psi0 receive; never solve/retry."""
import argparse,csv
from pathlib import Path
import xml.etree.ElementTree as ET
import psutil
import mdbc_partition_components_r3 as old
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_resume_native_r1'
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def check_input(path,pre):
 root=ET.parse(path).getroot();soil=root.find('execution/special/soils');hydro=root.find('execution/special/hydromechanics');event=root.find('execution/special/gravitypreload');parameters=root.find('execution/parameters');need(all(x is not None for x in (soil,hydro,event,parameters)),'Actual executed input sections missing')
 def number(parent,key):
  nodes=parent.findall(key);need(len(nodes)==1,'Missing/duplicate actual input node: '+key);return float(nodes[0].get('value'))
 for k,v in dict(phi=25,coh=5000,dlt=0,DilationDecay=0,ModulusE=20e6,PRvs=.33,phi_r=25,n_phi=0,coh_r=1000,n_coh=5).items():need(number(soil,k)==v,'Only the declared psi0 material is admitted: '+k)
 for k,v in dict(HydroMech=1,HydroMechDynamicSeepage=1,HydroMechConductivityModel=1,HydroMechConductivityCk=2,PoreWaterRho=1000,PoreWaterBulkModulus=1e9,Porosity=.35,HydraulicConductivity=.0002,PoreDtSafety=.1,HydroMechDrainage=0,HydroMechFreeSeepage=1).items():need(number(hydro,k)==v,'Actual hydromechanical input differs: '+k)
 need(float(event.get('time'))==10 and int(event.get('release_mkbound'))==2 and event.get('elastic_source','false').lower() in ('false','0'),'Actual event/source qualification differs');source=Path(event.get('statefile',''));source=source if source.is_absolute() else path.parent/source;need(source.is_file() and source.samefile(pre),'Actual executed XML imports another PRE')
 pairs=[(q.get('key'),q.get('value')) for q in parameters.findall('parameter')];p=dict(pairs);need(len(p)==len(pairs),'Repeated parameter keys in actual input')
 for k,v in dict(DtFixed=.0000025,TimeOut=.01,SavePosDouble=1,DPCtes=3,Kernel=1,PartsOutMax=0).items():need(k in p and float(p[k])==v,'Actual locked input differs: '+k)
 need(float(p['TimeMax']) in (10.1,13.),'Only the bounded/full psi0 total-time inputs are admitted')

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--read',nargs=5,metavar=('GPU','DATA','PRE','EXPECTED_GLOBAL_END','FRESHOUT'),required=True);ap.add_argument('--run-check',type=Path,required=True);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read and explicit one-reader authorization required');backend,data_s,pre_s,end_s,out_s=a.read;need(backend=='GPU' and end_s in ('4040000','5200000'),'Only two declared GPU psi0 windows are admitted');end=int(end_s);data=Path(data_s).resolve();pre=Path(pre_s).resolve();out=Path(out_s).resolve();tag=out.name
 need(out.parent==T/'outputs' and tag.startswith('upl_c08_resume_'),'Fresh shallow C08 resume native result required');check=L/(tag+'.check.json');need(not out.exists() and not check.exists(),'Existing/partial decode protected');consumed=[];call=None
 try:
  rp=a.run_check.resolve();r=read(rp);bp=L/(TAG+'.build.json');b=read(bp);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==end,'Closed original actual solver exit/global count required');need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Closed six-utility reader build required')
  consumed=[stat(rp),stat(bp),stat(__file__),stat(old.__file__),bind(b['program']),bind(b['source']),bind(b['source_build']),bind(b['source_capture']),bind(b['source_archive'])]
  for key in ('program','source_build','source_pre_file','input_xml'):consumed.append(bind(r[key]))
  need(Path(r['source_pre_file']['path']).samefile(pre) and Path(r['input_xml']['path']).parent==data.parent,'Original PRE/input/data directory binding differs');check_input(Path(r['input_xml']['path']),pre)
  solverbuild=read(r['source_build']['path']);need(solverbuild['passed'] and solverbuild['actual_typed_exit_code']==solverbuild['actual_Win32_exit']==0 and solverbuild['source_capture']==b['source_capture'],'Solver is not the current closed r3 capture');need((r['program']['bytes'],r['program']['mtime_ns'])==(solverbuild['program']['bytes'],solverbuild['program']['mtime_ns']),'Executed solver copy differs from its build')
  consumed += [stat(data.parent/'Run.csv'),stat(pre.parent/'Part_Head.ibi4')]
  with (data.parent/'Run.csv').open(newline='',encoding='utf-8-sig') as f:text=f.read();summary=list(csv.DictReader(text.splitlines(),delimiter=';' if ';' in text.splitlines()[0] else ','))
  need(len(summary)==1 and int(summary[0]['Steps'])==end and int(summary[0]['PartFiles'])==r['saved_frames'],'Closed solver receipt/actual Run.csv differs');parts=sorted(data.glob('Part_*.bi4'));need(len(parts)==r['saved_frames'] and [p.name for p in parts]==['Part_%04d.bi4'%i for i in range(len(parts))],'Actual native sequence/count differs');consumed += [stat(p) for p in data.iterdir() if p.is_file()]
  exe=Path(b['program']['path']);need(not any((p.info['name'] or '').lower()==exe.name.lower() and Path(p.info['exe'] or '').resolve()==exe for p in psutil.process_iter(['name','exe'])),'This reader is already active; do not duplicate')
  call=invoke(tag+'.reader',[str(exe),'--read','GPU',str(data),str(pre),str(end),str(out)],T);d=read(out/'completion.json');samples=r['saved_frames'];need(d['passed'] and d['stage']==TAG and d['group']=='psi0' and d['samples']==samples and d['completed_steps']==end and d['new_updates']==end-4000000 and d['source_material_law_version']==1 and d['target_material_law_version']==2,'Actual reader identity/window differs')
  coverage=dict(typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6800,soil_IDs=5000,ledger_checks=5000*samples,fixed_marker_checks=1800*samples,P0_bits_checks=6800*samples,rho_cache_bits_checks=5000*samples,kappa_nondecreasing_from_PRE_checks=5000*samples,nonempty_signed_intervals=samples,source_PREs_read=1);need(all(d[k]==v for k,v in coverage.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and not d['physical_acceptance'],'Original native coverage/safety guards failed')
  need(all(stat(e['path'])==e for e in consumed),'Consumed source/data/program changed during decode');save(check,dict(stage=tag+'.native',passed=True,source_run=stat(rp),reader_build=stat(bp),reader_call=call,native_completion=stat(out/'completion.json'),actual_completion=d,original_native_guards_passed=True,actual_input_psi0_verified=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(p) for p in out.iterdir() if p.is_file()],decoder_invocations=1,solver_invocations=0,SHA_scans=0,physical_acceptance=False));print('NATIVE_PASSED',check,flush=True)
 except Exception as e:
  if not check.exists():save(check,dict(stage=tag+'.native',passed=False,first_failure=str(e),reader_call=call,consumed=consumed,solver_invocations=0,SHA_scans=0,physical_acceptance=False))
  raise
if __name__=='__main__':main()
