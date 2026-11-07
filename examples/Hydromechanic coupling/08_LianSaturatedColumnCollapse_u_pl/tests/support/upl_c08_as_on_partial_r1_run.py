"""Decode the sealed AS-on failure's eleven saved states once; no solver/retry/notification."""
import argparse,csv,json,os,struct,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import psutil
import mdbc_partition_components_r3 as old
from upl_c08_resume_native_r1_run import check_input
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_as_on_partial_r1';OUT=T/'outputs'/TAG
AS='upl_c08_as_short_r1';FAILED=T/'outputs'/(AS+'_on');CONTROL=T/'outputs'/(AS+'_off_native');PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def compare():
    # Matched native material IDs/time; AS option effects are descriptive, never half errors.
    specs=list(csv.DictReader((OUT/'typed22_layout.csv').open(encoding='utf8')));need(len(specs)==22 and (OUT/'typed22_layout.csv').read_bytes()==(CONTROL/'typed22_layout.csv').read_bytes(),'Typed schema differs')
    clocks=[list(csv.DictReader((p/'clocks.csv').open(encoding='utf8'))) for p in (OUT,CONTROL)];need(len(clocks[0])==len(clocks[1])==11,'Actual comparison needs eleven actual saved states')
    fields=[];pairs=[];stride=8+6800*212
    with (OUT/'typed22.bin').open('rb') as a,(CONTROL/'typed22.bin').open('rb') as b:
        need(a.read(12)==b.read(12)==struct.pack('<III',6800,22,11),'Actual typed header differs; no rewrites')
        for part in range(11):
            rawA,rawB=a.read(stride),b.read(stride);need(len(rawA)==len(rawB)==stride,'Incomplete native comparison record');ta=struct.unpack_from('<d',rawA)[0];tb=struct.unpack_from('<d',rawB)[0]
            ca,cb=clocks[0][part],clocks[1][part];need(abs(ta-tb)<=1e-14 and ca['completed_step']==cb['completed_step'] and ca['saved_step']==cb['saved_step'],'Actual matched clock/Step differs')
            signedA,signedB=float(ca['signed_dterror_s']),float(cb['signed_dterror_s']);need(np.isfinite(signedA) and np.isfinite(signedB) and max(signedA,signedB)<=1e-14,'Original independent signed-interval guards failed')
            arraysA={};arraysB={};offset=8
            for spec in specs:
                name=spec['array'];width=int(spec['components']);size=int(spec['bytes_per_particle']);dt={'uint32':'<u4','float32':'<f4','float64':'<f8'}[spec['type']];count=6800*width;nbytes=6800*size
                va=np.frombuffer(rawA,dtype=dt,count=count,offset=offset).reshape(6800,width);vb=np.frombuffer(rawB,dtype=dt,count=count,offset=offset).reshape(6800,width);arraysA[name]=va;arraysB[name]=vb
                ba=np.frombuffer(rawA,dtype='u1',count=nbytes,offset=offset).reshape(6800,size);bb=np.frombuffer(rawB,dtype='u1',count=nbytes,offset=offset).reshape(6800,size);different=np.any(ba!=bb,axis=1);delta=va.astype('float64')-vb.astype('float64')
                fields.append(dict(part=part,array=name,time_ON_s=ta,time_OFF_s=tb,bit_equal=not different.any(),IDs_with_any_bit_difference=int(different.sum()),maxabs=float(np.max(np.abs(delta))),RMS_components=float(np.sqrt(np.mean(delta*delta)))));offset+=nbytes
            need(offset==stride and np.array_equal(arraysA['Idp'],arraysB['Idp']),'Actual typed offsets/material IDs differ');soil=arraysA['Idp'][:,0]>=2060;need(int(soil.sum())==5000,'Actual fixed initial material soil ID domain differs')
            du=(arraysA['Posd'][soil]-arraysB['Posd'][soil])*1000.;dp=(arraysA['PorePress'][soil].astype('float64')-arraysB['PorePress'][soil].astype('float64'));ds=arraysA['SigmaState_kk'][soil]-arraysB['SigmaState_kk'][soil]
            pairs.append(dict(part=part,time_ON_s=ta,time_OFF_s=tb,tau_ON_s=ca['tau_from_actual_release_s'],completed_step=ca['completed_step'],pressure_RMS_ON_minus_OFF_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZmax_ON_minus_OFF_mm=float(np.max(np.abs(du))),mean_dz_ON_minus_OFF_mm=float(np.mean(du[:,2])),effective_normal_stress_RMS_ON_minus_OFF_Pa=float(np.sqrt(np.mean(ds*ds))),signed_dterror_ON_s=signedA,signed_dterror_OFF_s=signedB))
        need(a.read(1)==b.read(1)==b'','Extra native records')
    for leaf,rows in [('AS_option_fields.csv',fields),('AS_option_pairs.csv',pairs)]:
        with (OUT/leaf).open('x',encoding='utf8',newline='') as f:writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return dict(actual_pairs=11,arrays_per_pair=22,all_material_IDs_matched=True,option_changes_are_not_half_errors=True,half_or_theory_acceptance=False,max_pressure_RMS_option_difference_Pa=max(x['pressure_RMS_ON_minus_OFF_Pa'] for x in pairs),max_material_XYZ_option_difference_mm=max(x['material_XYZmax_ON_minus_OFF_mm'] for x in pairs),arrays_with_any_bit_difference=sorted({x['array'] for x in fields if not x['bit_equal']}),signed_dterror_compared_descriptively_not_masked=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full review and single-reader authorization required');check=L/(TAG+'.check.json');need(not OUT.exists() and not check.exists() and not (L/(TAG+'.reader.call.json')).exists() and not (L/(TAG+'.reader.log')).exists(),'Existing/partial decode is protected')
    consumed=[];call=None;result=dict(stage=TAG,passed=False,solver_invocations=0,decoder_invocations=0,physical_acceptance=False,runtime_success_claimed=False,unsaved_failure_stage_reproduced_by_reader=False,SHA_scans=0)
    try:
        sequence=L/(AS+'.run.json');run=L/(AS+'_on.run.json');cp=L/(AS+'_on.solver.call.json');status=L/(AS+'.status.json');offcheck=L/(AS+'_off.native.check.json');r,c,seq,st=read(run),read(cp),read(sequence),read(status)
        need(not seq['passed'] and seq['consumed_stats_unchanged'] and not r['passed'] and r['actual_exit']==r['actual_Win32_exit']==1 and r['reader_invocations']==0 and r['global_cap']==4120000,'Actual AS-on sequence failure/admission differs')
        need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==1 and c['ownership_errors']==[] and st['state']=='terminal_failure' and not st['owned_child_alive'],'Actual target exit/ownership/terminal evidence differs');child=c['child'];argv=c['argv'];exe=Path(child['exe']);need(Path(argv[0]).samefile(exe) and child['argv']==argv and child['parent_pid']==c['owner']['pid'] and argv[-1]=='-nsteps:4120000' and Path(argv[5]).samefile(FAILED),'Original program/argv/output owner differs')
        need(not (T/'outputs'/(AS+'_on_native')).exists() and not (L/(AS+'_on.reader.call.json')).exists(),'Existing ON reader/output discovered; do not decode twice')
        oc=read(offcheck);need(oc['passed'] and oc['pair']['passed'],'Retained OFF eleven-state exact gate was not closed');bind(oc['native_completion']);g=read(bind(r['GenCase_call'])['path']);need(g['actual_Popen_wait_exit']==g['actual_Win32_exit']==0 and g['ownership_failure'] is None and Path(g['child']['exe']).name=='GenCase_win64.exe','Actual GenCase identity/exit differs')
        source_program=next(e for e in seq['consumed'] if Path(e['path'])==exe);bind(source_program);xml=FAILED/(AS+'_on.xml');check_input(xml,PRE);parameters={q.get('key'):q.get('value') for q in ET.parse(xml).getroot().findall('execution/parameters/parameter')};need(all(float(parameters[k])==v for k,v in [('ArtificialStress',1),('ArtificialStressCoef',.2),('ArtificialStressExp',2.55)]),'Actual AS-on input differs')
        text=(FAILED/'Run.out').read_text(encoding='utf-8-sig');need('Finished execution (code=1).' in text and 'GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.' in text and text.count('DynamicPoreWall rejected:')==1,'Actual runtime failure first cause differs');diagnostic=next(x for x in text.splitlines() if x.startswith('DynamicPoreWall rejected:'));need(not (FAILED/'Run.csv').exists(),'Unexpected successful summary; diagnose rather than relabel')
        parts=sorted((FAILED/'data').glob('Part_*.bi4'));need([q.name for q in parts]==['Part_%04d.bi4'%i for i in range(11)],'Actual AS-on eleven saved PARTs differ');bp=L/(TAG+'.build.json');b=read(bp);need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Closed new six-utility reader required');reader=Path(bind(b['program'])['path'])
        need(not any(q.info['exe'] and os.path.normcase(os.path.abspath(q.info['exe']))==os.path.normcase(str(reader)) for q in psutil.process_iter(['exe'])),'Exact new reader is active')
        consumed=[stat(p) for p in (sequence,run,cp,status,offcheck,bp,Path(__file__),Path(old.__file__),T/'support/upl_c08_resume_native_r1_run.py',T/'notes'/(TAG+'.md'),xml,FAILED/'Run.out',PRE,PRE.parent/'Part_Head.ibi4',FAILED/'data/Part_Head.ibi4',*parts)]+[bind(e) for e in seq['consumed']]+[bind(b['program']),bind(b['source']),bind(b['source_capture']),bind(b['source_archive'])]+[stat(CONTROL/n) for n in ('typed22.bin','typed22_layout.csv','clocks.csv','completion.json')]
        result['decoder_invocations']=1;call=invoke(TAG+'.reader',[str(reader),'--read','psi0','GPU',str(FAILED/'data'),str(PRE),'4044000',str(OUT)],T);d=read(OUT/'completion.json')
        expected=dict(samples=11,completed_steps=4044000,last_saved_zero_based_step=4043999,typed_arrays=22,actual_native_IDs_per_frame=6800,soil_IDs=5000,ledger_checks=55000,fixed_marker_checks=19800,P0_bits_checks=74800,rho_cache_bits_checks=55000,kappa_nondecreasing_from_PRE_checks=55000,nonempty_signed_intervals=11)
        need(d['passed'] and d['stage']==TAG and d['diagnostic_partial'] and d['ArtificialStress'] and d['AS_policy']=='ReleaseOnly' and not d['runtime_success_claimed'] and all(d[k]==v for k,v in expected.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original AS-on saved-state safety/coverage failed')
        description=compare();need(all(stat(e['path'])==e for e in consumed),'Consumed AS-on source/program/control changed');result.update(passed=True,original_saved_native_guards_passed=True,actual_saved_end_s=d['actual_end_s'],reader_call=call,native_completion=stat(OUT/'completion.json'),actual_completion=d,actual_runtime_diagnostic_line=diagnostic,diagnostic_step_start_is_not_saved_post_time=True,AS_option_comparison=description,files=[stat(p) for p in sorted(OUT.iterdir()) if p.is_file()],consumed_stats_unchanged=True)
    except Exception as e:result.update(first_failure=str(e),reader_call=call)
    result['consumed']=consumed;save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'),physical_acceptance=False)),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
