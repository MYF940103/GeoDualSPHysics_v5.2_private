"""Independent C04 Release startup128 native/read-review; no solver or chain."""
from __future__ import annotations
import argparse
import csv
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
sys.dont_write_bytecode=True
import numpy as np
import psutil
import upl_tpi_cryer_gpu_debug2_native_r1 as d  # Only exact bits/f32_FTZ constants; never its context/read/review/main.
b=d.b
T,L=b.T,b.L
STAGE='upl_tpi_cryer_gpu_release_native_r1'
RUNNER=T/'support/upl_tpi_cryer_gpu_release_run_r1.py'
OLD_GPU_CALL=L/'upl_cryer_freebody_smoke128_GPU_r1.call.json'
OLD_NATIVE_CALL=L/'upl_cryer_freebody_smoke128_GPU_r1.native.call.json'
OLD_NATIVE=T/'outputs/upl_cryer_freebody_smoke128_GPU_r1_native'
DT=2.**-20
TAG_RE=re.compile(r'upl_tpi_cryer_gpu_Release_([ABC])_startup128_r[1-9][0-9]*\Z')


class Admission:
    def __init__(self,path,phase,tag):
        self.entry,self.data=b.stat(path),b.read(path)
        b.need(self.data.get('stage')==STAGE+'.'+phase+'_admission' and self.data.get('passed') is True
               and self.data.get('tag')==tag and (self.data.get('one_native_read_only') is True
               if phase=='native' else self.data.get('offline_only') is True),'Independent matching Release128 phase/tag admission required')
        self.frozen={b.key(x['path']):x for x in self.data['inputs']};self.consumed={}
        b.need(len(self.frozen)==len(self.data['inputs']),'Duplicate frozen input')

    def pin(self,path):
        k=b.key(path);b.need(k in self.frozen,'Consumed input absent from root admission: '+str(path))
        self.consumed[k]=b.same(self.frozen[k]);return self.consumed[k]

    def finish(self):
        for e in self.consumed.values():b.same(e)
        b.same(self.entry);return list(self.consumed.values())


def context(ad,tag):
    for p in (Path(__file__),T/'notes/upl_tpi_cryer_gpu_release_native_r1.md',RUNNER,Path(d.__file__),
              Path(b.__file__),sys.executable,np.__file__,psutil.__file__):ad.pin(p)
    scheme=TAG_RE.fullmatch(tag).group(1);runpath=L/(tag+'.run.json');ad.pin(runpath);run=b.read(runpath)
    b.need(run['stage']=='upl_tpi_cryer_gpu_release_run_r1.run' and run['passed']
           and run['configuration']=='Release' and run['scheme']==scheme and run['window']=='startup128'
           and run['tag']==tag and run['actual_Popen_wait_exit']==run['actual_Win32_exit']==run['target_actual_Win32_exit']==0,
           'Genuine passed owned Release128 run required')
    startpath=L/(tag+'.start.json');ad.pin(startpath);start=b.read(startpath)
    for name in ('call','program','source_build','prepared','root_admission','plan','debug_native_review'):
        ad.pin(run[name]['path']);b.same(run[name])
    call=b.read(run['call']['path'])
    b.need(call['passed'] and call['tool_is_solver'] is True and call['target_handle_acquired_before_wait']
           and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==call['target_actual_Win32_exit']==0
           and call['target']==start['target']==run['target']==call['child']
           and call['target']['argv'][1:]==call['target_arguments']==run['arguments']
           and b.key(call['program']['path'])==b.key(call['target']['exe'])==b.key(run['program']['path'])
           and call['target']['parent']==call['owner']['pid'],'Actual direct solver/target ownership/argv/exits differ')
    created=(call['target_creation_FILETIME_ticks']-116444736000000000)/1e7
    b.need(abs(created-call['target']['created'])<=1e-6,'Actual native target creation differs')
    b.need(run['actual_environment']['UPL_TPI_GPU_R1']==call['actual_environment']['UPL_TPI_GPU_R1']==scheme,
           'Actual owned pressure-scheme environment differs')
    ad.pin(call['log']['path']);b.same(call['log'])
    debug=b.read(run['debug_native_review']['path'])
    b.need(debug['passed'] and debug['stage']=='upl_tpi_cryer_gpu_debug2_native_r1.review'
           and debug['sidecar_rows']==74346 and debug['actual_end_row_formula_checks']==37173
           and debug['core_field_bit_checks']==520422 and debug['HG_snapshot_checks']==0
           and debug['ULP_or_absolute_tolerance_added']==0,'Genuine Debug2 memory/native/formula prerequisite differs')
    for name in ('root_admission','native_read_receipt'):ad.pin(debug[name]['path']);b.same(debug[name])
    built,prep=b.read(run['source_build']['path']),b.read(run['prepared']['path'])
    b.need(built['passed'] and built['configuration']=='Release' and built['object_count']==111
           and built['old_objects_reused']==0 and built['program']==run['program'] and prep['passed']
           and built['prepared']['path']==run['prepared']['path'],'Matched actual full111 Release source/program required')
    for e in built['runtime']:ad.pin(e['destination']['path']);b.same(e['destination'])
    source=Path(prep['source_root'])/'source';h=source/'upl_tpi_cryer_gpu_r1.h';cu=source/'upl_tpi_cryer_gpu_r1.cuh'
    ad.pin(h);ad.pin(cu);body=cu.read_text(encoding='utf-8-sig')
    b.need(body.count('raw=__dadd_rn(double(o.q),__ddiv_rn(o.R,o.S));')==1
           and body.count('o.raw=__double2float_rn(raw);')==1,'Bound explicit pressure RN source differs')
    flags=built['actual_NVCC_source_commands']['jsphgpu_ker.cu']['flags']
    b.need('-use_fast_math' in flags and '-G' not in flags
           and not any(x.startswith(('--ftz=false','--fmad=false')) for x in flags),'Actual Release CUDA RN/FTZ/fmad compiler policy differs')
    with Path(run['plan']['path']).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    scalar=0.
    for _ in range(128):scalar+=DT
    b.need(len(rows)==2 and list(rows[0])==['part','time_s','completed_step','saved_step','dt_s'],'Original five-column actual clock plan differs')
    for p,row in enumerate(rows):
        b.need(int(row['part'])==p and int(row['completed_step'])==(128 if p else 0)
               and int(row['saved_step'])==(127 if p else 0) and d.bits(float(row['time_s']))==d.bits(scalar if p else 0.)
               and d.bits(float(row['dt_s']))==d.bits(DT),'Actual scalar clock/zero-based saved Step differs')
    data=Path(run['data']);out=Path(run['output_directory']);b.need(b.key(data)==b.key(out/'data'),'Owned raw-data path differs')
    raw=sorted([*data.glob('*.bi4'),*data.glob('*.ibi4')])
    b.need({p.name for p in raw if p.suffix=='.bi4'}=={'Part_0000.bi4','Part_0001.bi4'},'Actual raw two-frame sequence differs')
    for p in raw:ad.pin(p)
    for name in ('Run.out','Run.csv'):ad.pin(out/name)
    return dict(tag=tag,scheme=scheme,run=run,data=data,out=out,plan=Path(run['plan']['path']),
                native=T/'outputs'/(tag+'_native_r1'),arithmetic_source=[b.stat(h),b.stat(cu)])


def done(directory,backend='GPU'):
    x=b.read(directory/'completion.json')
    b.need(x['stage']=='upl_cryer_public_native_r1' and x['passed'] and x['declared_backend']==backend
           and x['samples']==2 and x['completed_steps']==128 and d.bits(x['actual_end_s'])==d.bits(2.**-13)
           and d.bits(x['dt_s'])==d.bits(DT) and x['total_native_ids']==37181 and x['soil_ids']==37173
           and x['fixed_ids']==8 and x['native_typed_arrays']==22 and x['soil_ledger_checks']==74346
           and x['fixed_marker_checks']==16 and x['noninitial_signed_dterror_intervals']==1
           and x['post_open_frames']==x['post_open_FS23_zero_pressure_checks']==0 and x['raw_BI4_modified'] is False,
           'Original complete native22/IDs/ledger/signed/pre-drain coverage differs')
    return x


def decode(ad,ctx,result):
    native,tag=ctx['native'],ctx['tag']
    b.need(not native.exists() and not (L/(tag+'.native_r1.call.json')).exists()
           and not (L/(tag+'.native_r1.log')).exists(),'Existing/partial decode or call is protected; never repeat')
    ad.pin(d.READER);ad.pin(OLD_NATIVE_CALL);old=b.read(OLD_NATIVE_CALL)
    b.need(old['exit_code']==0 and old['direct_exit'] and b.key(old['program']['path'])==b.key(d.READER),
           'Existing genuinely successful C04 reader required')
    b.same(old['program'])
    for p in d.READER.parent.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.xml'):ad.pin(p)
    for proc in psutil.process_iter(['exe','cmdline']):
        if proc.info['exe'] and b.key(proc.info['exe'])==b.key(d.READER):
            b.need(not any(b.key(x) in {b.key(ctx['data']),b.key(native)} for x in (proc.info['cmdline'] or [])[1:]),
                   'Matching reader already active; never duplicate')
    env=os.environ.copy();env.pop('UPL_TPI_GPU_R1',None);env.pop('UPL_TPI_CPU_R1',None)
    ad.finish();call,_=b.invoke(tag+'.native_r1',[str(d.READER),'--read','GPU',str(ctx['data']),str(ctx['plan']),str(native)],d.READER.parent,env)
    result.update(passed=True,reader_invocations=1,reader_call=call,native_directory=str(native),completion=done(native),
                  products=[b.stat(p) for p in native.iterdir() if p.is_file()],consumed=ad.finish(),consumed_stats_unchanged=True)


def exports(directory):
    raw=(directory/'common26.bin').read_bytes();dtype=np.dtype([('time','<f8'),('v','<f8',(37181,26))])
    b.need(struct.unpack_from('<III',raw)==(37181,26,2) and len(raw)==12+2*dtype.itemsize,'Original common26 header/payload differs')
    values=np.frombuffer(raw,dtype=dtype,offset=12);clock=(directory/'clock.bin').read_bytes()
    b.need(struct.unpack_from('<II',clock)==(2,28) and len(clock)==64,'Original clock28 header/payload differs')
    for p in (0,1):
        time,step,dt,error=struct.unpack_from('<dIdd',clock,8+28*p)
        b.need(d.bits(time)==d.bits(values['time'][p])==d.bits(2.**-13 if p else 0.)
               and step==(127 if p else 0) and d.bits(dt)==d.bits(DT) and math.isfinite(error) and error<=1e-14
               and (not p or error!=-sys.float_info.max),'Original actual signed clocks or necessary-step guard failed')
    return raw,values,clock


def history(ad,ctx,values):
    out,scheme=ctx['out'],ctx['scheme']
    if scheme=='A':
        b.need(not any((out/('UplTpiCryerGpuR1'+x)).exists() for x in ('.csv','.policy.json','.summary.json')),
               'DefaultA entered the private pressure history branch')
        return dict(private_branch_entered=False,HG_snapshot_checks=0)
    for suffix in ('.csv','.policy.json','.summary.json'):ad.pin(out/('UplTpiCryerGpuR1'+suffix))
    policy=b.read(out/'UplTpiCryerGpuR1.policy.json');summary=b.read(out/'UplTpiCryerGpuR1.summary.json')
    alpha=.5 if scheme=='B' else 0.;name='B_TPI_alpha_0p5_beta0' if scheme=='B' else 'C_PPE_t_alpha0_beta0'
    b.need(policy['stage']==summary['stage']=='upl_tpi_cryer_gpu_r1' and policy['scheme']==summary['scheme']==name
           and policy['alpha']==summary['alpha']==alpha and policy['beta']==summary['beta']==0
           and policy['M0'] and policy['history_ID_owned'] and policy['history_cold_start']
           and policy['native_count']==37181 and policy['soil_count']==37173
           and summary['completed'] and summary['commits']==summary['endpoint_calls']==128
           and summary['core_field_bit_checks']==33307008 and summary['HG_readonly_snapshot_checks']==0
           and d.bits(summary['actual_end'])==d.bits(2.**-13),'Actual scheme/native/HG0 lifecycle differs')
    source_time=0.
    for _ in range(127):source_time+=DT
    seen=[set(),set()];nplain=nfused=checked=0
    with (out/'UplTpiCryerGpuR1.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=csv.DictReader(f);b.need(rows.fieldnames==d.COLS,'Original28-column sidecar differs')
        for row in rows:
            p,k=int(row['part']),int(row['native_id']);b.need(p in (0,1) and 8<=k<37181 and k not in seen[p],'Duplicate/new sidecar material ID')
            seen[p].add(k);v={x:float(row[x]) for x in d.COLS if x not in ('part','native_id')}
            b.need(all(math.isfinite(x) for x in v.values()),'Nonfinite actual sidecar value')
            n=128 if p else 0
            b.need(v['source_step_zero_based']==(127 if p else 0) and v['completed_step']==v['commits']==v['endpoint_calls']==n
                   and d.bits(v['source_time_s'])==d.bits(source_time if p else 0.)
                   and d.bits(v['actual_save_time_s'])==d.bits(2.**-13 if p else 0.) and d.bits(v['dt_s'])==d.bits(DT)
                   and v['core_field_bit_checks']==7*37173*n and v['hg_snapshot_checks']==0
                   and v['source_drained']==v['endpoint_drained']==v['commit_drained']==0,'Actual lifecycle/sourceclock/closed BC differs')
            pn=d.f32_ftz(v['pn_Pa']);prediction=pn if alpha==0 else pn+.5*(pn-d.f32_ftz(v['previous_Pa']))
            b.need(d.bits(prediction)==d.bits(v['prediction_double_Pa'])
                   and d.bits(d.f32_ftz(prediction),'f')==d.bits(v['half_actual_float_Pa'],'f')==d.bits(v['endpoint_q_actual_float_Pa'],'f')
                   and d.bits(v['final_float_Pa'],'f')==d.bits(values['v'][p,k,6],'f') and d.bits(v['Jfull'])==d.bits(values['v'][p,k,8]),
                   'Actual RN/FTZ prediction/native pressure or J differs')
            if p:
                b.need(v['S_1_per_m_s']>0,'Nonpositive actual leading-LP row cannot be regularized/masked')
                exact=d.f32_ftz(v['endpoint_q_actual_float_Pa'])+v['Rgamma_Pa_per_m_s']/v['S_1_per_m_s']
                b.need(d.bits(d.f32_ftz(exact),'f')==d.bits(v['raw_final_float_Pa'],'f')==d.bits(v['final_float_Pa'],'f'),
                       'Actual explicit RN divide/add and signed FTZ raw/final pressure differs')
                product=DT*v['Jhalf'];plain=v['Jn']+product*v['theta_half_for_J_1_per_s']
                fused=float(Fraction.from_float(v['Jn'])+Fraction.from_float(product)*Fraction.from_float(v['theta_half_for_J_1_per_s']))
                a,z=d.bits(v['Jfull'])==d.bits(plain),d.bits(v['Jfull'])==d.bits(fused)
                b.need(a or z,'Original CUDA J expression matches neither exact permitted compiler path')
                nplain+=a;nfused+=z;checked+=1
            else:b.need(v['S_1_per_m_s']==v['Rgamma_Pa_per_m_s']==0. and v['Jn']==v['Jhalf']==v['Jfull']==1.,'Cold initial sidecar differs')
    b.need(all(x==set(range(8,37181)) for x in seen) and checked==37173,'Missing all-material saved sidecar records')
    return dict(private_branch_entered=True,sidecar_rows=74346,actual_end_pressure_row_checks=checked,
                core_field_bit_checks=33307008,HG_snapshot_checks=0,J_nonfused_matches=nplain,J_fused_matches=nfused,
                ULP_or_absolute_tolerance_added=0,all_unsaved_rows_independently_observed=False)


def compare(ad,ctx,payload,values,clock):
    if ctx['scheme']=='A':
        for p in (OLD_GPU_CALL,OLD_NATIVE_CALL,OLD_NATIVE/'completion.json',OLD_NATIVE/'common26.bin',OLD_NATIVE/'clock.bin',OLD_NATIVE/'native_ids.csv'):ad.pin(p)
        old,read=b.read(OLD_GPU_CALL),b.read(OLD_NATIVE_CALL)
        b.need(old['exit_code']==read['exit_code']==0 and old['direct_exit'] and read['direct_exit'],
               'Genuine old GPU128 solver/reader calls required; no invented old run/start')
        done(OLD_NATIVE);prior,_,signed=exports(OLD_NATIVE)
        b.need(payload==prior and clock==signed
               and (ctx['native']/'native_ids.csv').read_bytes()==(OLD_NATIVE/'native_ids.csv').read_bytes(),
               'DefaultA differs from true old same-backend GPU128 common26/IDs/clock bytes')
        return dict(old_GPU128_common26_IDs_and_entire_signed_clock_bit_equal=True,
                    raw22_all_array_bit_proof=False,normal_exit_not_physical_acceptance=True)
    proof=ad.data.get('cpu_reference_review');b.need(isinstance(proof,dict),'Explicit corresponding true CPU128 review required')
    ad.pin(proof['path']);b.same(proof);cpu=b.read(proof['path'])
    b.need(cpu['passed'] and cpu['scheme']==ctx['scheme'] and cpu['consumed_stats_unchanged']
           and re.fullmatch('upl_tpi_cryer_cpu_DebugCPU_'+ctx['scheme']+r'_startup128_r[1-9][0-9]*',cpu['tag']),
           'Corresponding actual same-scheme CPU128 reference did not pass')
    directory=Path(cpu['native_directory'])
    ad.pin(cpu['native_read_receipt']['path']);b.same(cpu['native_read_receipt'])
    for p in ('completion.json','common26.bin','clock.bin','native_ids.csv'):ad.pin(directory/p)
    done(directory,'CPU');_,prior,cpclock=exports(directory)
    b.need((ctx['native']/'native_ids.csv').read_bytes()==(directory/'native_ids.csv').read_bytes(),
           'True initial material IDs/XYZ/reference weights differ across backend')
    pressure=[];displacement=[];stress=[];jgap=[]
    for p in (0,1):
        # All clock bytes are retained; signed necessary-step values have their own guard, not a cross-backend equality demand.
        b.need(clock[8+28*p:8+28*p+20]==cpclock[8+28*p:8+28*p+20], 'Actual saved time/Step/dt differ across backend')
        a=values['v'][p,8:];z=prior['v'][p,8:]
        pressure.append(float(np.sqrt(np.mean((a[:,6]-z[:,6])**2))))
        du=((a[:,:3]-values['v'][0,8:,:3])-(z[:,:3]-prior['v'][0,8:,:3]))*1000.
        displacement.append(float(np.max(np.linalg.norm(du,axis=1))))
        ds=a[:,10:16]-z[:,10:16]
        stress.append(float(np.sqrt(np.mean(np.sum(ds[:,[0,3,5]]**2,axis=1)+2*np.sum(ds[:,[1,2,4]]**2,axis=1)))))
        jgap.append(float(np.max(np.abs(a[:,8]-z[:,8]))))
    b.need(max(pressure)<=5. and max(displacement)<=.005, 'Original all-two-sample same-scheme CPU/GPU 5Pa/.005mm gate failed')
    return dict(cpu_reference_review=proof,actual_matched_samples=2,pressure_RMS_Pa_by_frame=pressure,
                material_XYZ_displacement_max_mm_by_frame=displacement,effective_saved_stress_Frobenius_RMS_Pa_by_frame=stress,
                max_saved_J_difference_by_frame=jgap,original_5Pa_0p005mm_bound_passed=True,
                FSNormal_cross_backend_bit_gate=False,signed_dterror_each_original_guard_only=True)


def review(ad,ctx,result):
    receipt=L/(ctx['tag']+'.native_r1.json');ad.pin(receipt);decoded=b.read(receipt)
    b.need(decoded['passed'] and decoded['reader_invocations']==1 and b.key(decoded['native_directory'])==b.key(ctx['native']),
           'Existing successful unique read required, not re-decode')
    ad.pin(decoded['reader_call']['path']);b.same(decoded['reader_call']);call=b.read(decoded['reader_call']['path'])
    b.need(call['passed'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0,'Actual reader tool exits failed')
    for p in ctx['native'].iterdir():
        if p.is_file():ad.pin(p)
    completion=done(ctx['native']);payload,values,clock=exports(ctx['native'])
    with (ctx['native']/'native_ids.csv').open(encoding='utf-8-sig',newline='') as f:ids=list(csv.DictReader(f))
    b.need(len(ids)==37181 and all(int(x['id'])==k and int(x['is_soil'])==int(k>=8) for k,x in enumerate(ids)),
           'Actual native all-material IDs/roles differ')
    result.update(passed=True,scheme=ctx['scheme'],native_directory=str(ctx['native']),completion=completion,
                  native_read_receipt=b.stat(receipt),history=history(ad,ctx,values),comparison=compare(ad,ctx,payload,values,clock),
                  reader_invocations=0,arithmetic_source=ctx['arithmetic_source'],actual_force_stage_budget_independently_recomputed=False,
                  saved_J_load_is_proxy_only=True,postdrain_peak_or_physical_acceptance=False,
                  consumed=ad.finish(),consumed_stats_unchanged=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--phase',choices=('native','review'),required=True)
    ap.add_argument('--tag',required=True);ap.add_argument('--admission',required=True,type=Path)
    ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args()
    b.need(a.execution_authorized and TAG_RE.fullmatch(a.tag),'Explicit root phase and exact Release128 tag required')
    receipt=L/(a.tag+('.native_r1.json' if a.phase=='native' else '.native_review_r1.json'))
    b.need(not receipt.exists(),'Existing passed/failed native-review receipt is protected')
    result=dict(stage=STAGE+'.'+a.phase,tag=a.tag,passed=False,solver_invocations=0,build_invocations=0,
                VTK_invocations=0,SHA_scans=0,raw_BI4_modified=False,physical_acceptance=False,automatic_follow_up=False)
    try:
        ad=Admission(a.admission,a.phase,a.tag);result['root_admission']=ad.entry;ctx=context(ad,a.tag)
        (decode if a.phase=='native' else review)(ad,ctx,result)
    except Exception as exc:result.update(passed=False,first_error=str(exc),partials_preserved=True)
    b.write_new(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_error=result.get('first_error')),ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
