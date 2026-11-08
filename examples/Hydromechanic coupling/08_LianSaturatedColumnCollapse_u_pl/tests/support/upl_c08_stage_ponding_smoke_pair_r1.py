"""Two-state CPU/GPU functional pairing; not half-step, bitwise or physical acceptance."""
import argparse,csv,json,struct
from pathlib import Path
import numpy as np
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];TAG='upl_c08_stage_ponding_smoke_pair_r1'
SPECS=(('CPU_Debug','upl_c08_stage_ponding_smoke_CPUdebug_r1'),('GPU_Debug','upl_c08_stage_ponding_smoke_GPUdebug_r2'),('GPU_Release','upl_c08_stage_ponding_smoke_Release_r2'))

def load(label,tag,before):
    p=T/'logs'/(tag+'.native.json');c=e.read(p);e.need(c['passed'] and c['original_native_guards_passed'] and c['consumed_stats_unchanged'],'Passed native required: '+tag);before.append(e.stat(p))
    refs=[e.bind(c[k]) for k in ('source_run','actual_call','completion','metadata')];before.extend(refs);r=e.read(refs[0]['path']);call=e.read(refs[1]['path']);d=e.read(refs[2]['path']);m=e.read(refs[3]['path'])
    e.need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and d['passed'] and d['stage']=='upl_c08_stage_ponding_native_r1' and d['samples']==2 and d['completed_steps']==4000800 and d['actual_native_IDs_per_frame']==6805 and d['typed_arrays']==22,'Actual normal smoke/native coverage differs')
    e.need(m['passed'] and m['FreeSeepagePondingPolicy']=='ReleasedSubstages' and m['FreeSeepagePondingActive'] and m['samples']==2 and m['AS_exponent_float_reference']==3. and m['AS_coefficient_float_reference']==float(np.float32(.2)),'Actual new ponding/AS metadata differs')
    before.extend(e.bind(r[k]) for k in ('source_pre_file','source_capture'));entries={Path(v['path']).name:v for v in c['outputs']};files={name:Path(e.bind(entries[name])['path']) for name in ('typed22.bin','typed22_layout.csv','clocks.csv')};before.extend(entries[name] for name in files)
    with files['typed22_layout.csv'].open(newline='') as f:layout=list(csv.DictReader(f))
    e.need(len(layout)==22 and len({q['array'] for q in layout})==22,'Exact22 unique typed arrays required');types={'uint32':'<u4','float32':'<f4','float64':'<f8'};fields=[('time','<f8')]
    for q in layout:
        count=int(q['components']);dt=np.dtype(types[q['type']]);e.need(dt.itemsize*count==int(q['bytes_per_particle']),'Typed layout width differs');fields.append((q['array'],dt,(6805,) if count==1 else (6805,count)))
    dtype=np.dtype(fields)
    with files['typed22.bin'].open('rb') as f:e.need(struct.unpack('<III',f.read(12))==(6805,22,2),'Original header differs')
    e.need(files['typed22.bin'].stat().st_size==12+2*dtype.itemsize,'Two original records required');payload=np.memmap(files['typed22.bin'],mode='r',dtype=dtype,offset=12,shape=(2,))
    with files['clocks.csv'].open(newline='') as f:clocks=list(csv.DictReader(f))
    e.need(len(clocks)==2 and [int(q['completed_step']) for q in clocks]==[4000400,4000800] and all(float(q['time_s'])==float(payload[i]['time']) for i,q in enumerate(clocks)),'Original actual saved clocks/steps differ')
    return dict(label=label,run=r,done=d,data=payload,dtype=dtype,clocks=clocks)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Root full-read before one offline pairing required');check=T/'logs'/(TAG+'.check.json');table=T/'figures'/(TAG+'.csv');e.need(not check.exists() and not table.exists(),'Fresh derived outputs required');before=[e.stat(__file__),e.stat(T/'notes'/(TAG+'.md'))];rows=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,half_step_comparison=False,bitwise_equality_claimed=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,queue_invocations=0,SHA_scans=0)
    try:
        groups=[load(*spec,before) for spec in SPECS];base=groups[0]
        for g in groups[1:]:
            e.need(g['dtype']==base['dtype'] and g['run']['source_capture']==base['run']['source_capture'] and g['run']['source_pre_file']==base['run']['source_pre_file'] and g['done']['source_actual_time_s']==base['done']['source_actual_time_s'],'Same source_r2/PRE/source clock and typed layout required')
            for part in range(2):
                x,y=base['data'][part],g['data'][part];ids=x['Idp'];soil=ids>=2060;e.need(np.array_equal(ids,y['Idp']) and np.array_equal(ids[soil],np.arange(2060,7060,dtype=np.uint32)),'Same all native IDs and5000 fixed material IDs required');clock=abs(float(y['time'])-float(x['time']));dp=y['PorePress'][soil].astype(float)-x['PorePress'][soil];du=y['Posd'][soil]-x['Posd'][soil];prms=float(np.sqrt(np.mean(dp*dp)));umax=float(1000*np.linalg.norm(du,axis=1).max())
                ds=y['SigmaState_kk'][soil]-y['PorePress'][soil,None]-(x['SigmaState_kk'][soil]-x['PorePress'][soil,None]);di=y['SigmaState_ij'][soil]-x['SigmaState_ij'][soil];dv=y['Vel'][soil].astype(float)-x['Vel'][soil]
                row=dict(pair=base['label']+'_vs_'+g['label'],part=part,completed_step=int(base['clocks'][part]['completed_step']),CPU_actual_time_s=float(x['time']),GPU_actual_time_s=float(y['time']),actual_tau_s=float(x['time'])-base['done']['source_actual_time_s'],clock_difference_s=clock,soil_IDs=5000,pressure_RMS_Pa=prms,material_XYZ_displacement_difference_max_mm=umax,total_stress_difference_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(di*di,axis=1)))),velocity_difference_RMS_m_s=float(np.sqrt(np.mean(np.sum(dv*dv,axis=1)))))
                for name in ('PoroVolumeRatio','PoroPorosity','PoroHydraulicConductivity','Kplastic'):row[name+'_max_abs_difference']=float(np.abs(y[name][soil].astype(float)-x[name][soil]).max())
                rows.append(row);e.need(all(np.isfinite(v) for v in row.values() if isinstance(v,(int,float))) and clock<=1e-14 and prms<=5 and umax<=.005,'Original functional pairing limits failed; retain descriptive row without changing thresholds')
        e.need(all(e.stat(q['path'])==q for q in before),'Consumed native/source bindings changed');result.update(passed=True,functional_pairing_passed=True,rows=4,pressure_RMS_limit_Pa=5,material_XYZ_max_limit_mm=.005,actual_clock_limit_s=1e-14,Debug_Release_configuration_difference_disclosed=True,individual_native_guards_reused_not_rescanned=True)
    except Exception as error:result['first_failure']=str(error)
    if rows:
        with table.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result.update(consumed=before,files=[e.stat(table)] if table.exists() else []);e.save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
