"""Offline two material-branch compatibility check; no solver/reader/build/old-file edits."""
import csv,json,struct,importlib.util
from pathlib import Path
import numpy as np
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_preload_handoff_branch_review_r1';CHECK=L/(TAG+'.check.json');P=T/'figures'/TAG
spec=importlib.util.spec_from_file_location('handoff_review_helpers',T/'support/upl_preload_handoff_review_r1.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
need,stat,read,table,write=base.need,base.stat,base.read,base.table,base.write

def main():
    outputs=[Path(str(P)+suffix) for suffix in ('_pairs.csv','_fields.csv')];need(not any(p.exists() for p in [CHECK,*outputs]),'Retained branch review protected')
    parent=read(L/'upl_preload_handoff_review_r1.check.json');need(parent['passed'] and parent['implementation_continuity'],'Prior four-run source/receiver continuity is not passed')
    source=base.load('source','CPU');reference=[f for f in source['frames'] if f['row']['phase']==1];need(len(reference)==11,'Actual source post11 frames differ');pairs=[];fields=[];summaries={};receipts={}
    for group in ('psi2p5','psim5'):
        tag='upl_preload_handoff_'+group+'_CPU_r1';d=T/'outputs'/(tag+'_native_r1');checkpath=L/(tag+'_native_r1.check.json');check=read(checkpath);run=read(L/(tag+'.run.json'));done=read(d/'completion.json')
        need(check['passed'] and check['original_native_guards_passed'] and check['qualified_elastic_PRE_verified'] and check['consumed_stats_unchanged'],'Closed native branch safety missing')
        need(run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and run['actual_steps']==800 and run['new_updates_from_completed_counters']==420,'Actual branch global/new step or exit mismatch')
        need(check['material_group']==group and check['certified_pre_file']==source['receipt']['certified_pre_file'] and done['phase_saved_frames']==[0,11] and done['completed_steps']==800 and done['max_kappa']==0 and done['receiver_part0_is_not_t0'],'Actual group/source PRE/elastic post11 identity differs')
        for e in [check['native_completion'],*check['files']]:need(stat(e['path'])==e,'Closed branch native output changed')
        layout=table(d/'typed22_layout.csv');need(layout==source['layout'],'Original22 layout changed');clocks=table(d/'clocks.csv');need(len(clocks)==11,'Actual branch clocks differ')
        blob=(d/'phase1_typed22.bin').read_bytes();n=6800;record=8+n*212;need(struct.unpack('<III',blob[:12])==(n,22,11) and len(blob)==12+11*record,'Actual post11 native header/size differs');rows=[]
        for local,(ref,clock) in enumerate(zip(reference,clocks)):
            off=12+local*record;t=struct.unpack_from('<d',blob,off)[0];off+=8;a={};fieldrows=[]
            need(int(clock['completed_step'])==ref['row']['completed_step'] and int(clock['saved_step'])==int(ref['clock']['saved_step']) and t==float(clock['time_s']) and int(clock['phase'])==1 and int(clock['dterror_interval_empty'])==0 and float(clock['signed_dterror_s'])<=1e-14,'Actual matching clocks/signed post interval differ')
            for item in layout:
                name=item['array'];nc=int(item['components']);dt=np.dtype({'uint32':'<u4','float32':'<f4','float64':'<f8'}[item['type']]);v=np.frombuffer(blob,dt,count=n*nc,offset=off);off+=n*nc*dt.itemsize;v=v.reshape(n,nc) if nc>1 else v;need(np.isfinite(v).all(),'Nonfinite original field');a[name]=v;old=ref['a'][name];unequal=np.ascontiguousarray(old).view(np.dtype('<u%d'%dt.itemsize))!=np.ascontiguousarray(v).view(np.dtype('<u%d'%dt.itemsize))
                fieldrows.append(dict(group=group,completed_step=int(clock['completed_step']),actual_time_s=t,array=name,bit_equal=bool(not unequal.any()),unequal_scalar_values=int(unequal.sum()),scalar_values=int(v.size),max_abs_difference=float(np.abs(v.astype(float)-old.astype(float)).max())))
            fields.extend(fieldrows);need(np.array_equal(a['Idp'],ref['a']['Idp']),'Branch original material IDs differ');soil=a['Idp']>=2060;dp=a['PorePress'][soil].astype(float)-ref['p'];du=(a['Posd']-ref['a']['Posd'])*1000;pressure=a['PorePress'][soil].astype(float);total=np.c_[a['SigmaState_kk'][soil]-pressure[:,None],a['SigmaState_ij'][soil]]
            rows.append(dict(group=group,completed_step=int(clock['completed_step']),actual_time_s=t,time_difference_s=abs(t-ref['row']['actual_time_s']),signed_clock_record_bit_equal=base.clockbytes(clock)==base.clockbytes(ref['clock']),pressure_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZ_max_mm=float(np.linalg.norm(du,axis=1).max()),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(base.frob(total-ref['total'])**2))),J_max_difference=float(np.abs(a['PoroVolumeRatio'][soil]-ref['j']).max()),k_max_difference_m_s=float(np.abs(a['PoroHydraulicConductivity'][soil]-ref['k']).max()),all22_fields_bit_equal=all(r['bit_equal'] for r in fieldrows)))
        pairs.extend(rows);exact=blob==source['blobs'][1] and all(r['all22_fields_bit_equal'] and r['signed_clock_record_bit_equal'] for r in rows)
        summaries[group]=dict(actual_matched_pairs=11,new_updates=420,all_phase1_export_bytes_equal=blob==source['blobs'][1],all22_fields_and_signed_clock_exact=exact,pressure_RMS_max_Pa=max(r['pressure_RMS_Pa'] for r in rows),material_XYZ_max_mm=max(r['material_XYZ_max_mm'] for r in rows),total_stress_Frobenius_RMS_max_Pa=max(r['total_stress_Frobenius_RMS_Pa'] for r in rows),time_difference_max_s=max(r['time_difference_s'] for r in rows));receipts[group]=stat(checkpath)
    write(outputs[0],pairs);write(outputs[1],fields);passed=all(s['all22_fields_and_signed_clock_exact'] for s in summaries.values())
    result=dict(stage=TAG,passed=passed,short_three_group_interface_compatibility=passed,source_native_check=source['check'],branch_native_checks=receipts,previous_four_run_review=stat(L/'upl_preload_handoff_review_r1.check.json'),summaries=summaries,outputs=[stat(p) for p in outputs],all22_fields_reported=True,native_saved_arrays_or_clocks_rewritten=False,primary_import_before_advance_independently_observed=False,scope='Two CPU elastic short receivers sharing certified psi0 CPU source; no plastic branch trajectory or 10 s source certification/full collapse proof',physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0)
    base.save(CHECK,result);print(json.dumps(result,indent=2));need(passed,'Elastic material branch differs from source post records; retain all evidence and diagnose')
if __name__=='__main__':main()
