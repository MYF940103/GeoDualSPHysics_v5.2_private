"""Separate unique native read and offline exact review for C04 Debug-B2 only."""
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
import upl_tpi_cryer_cpu_build_r1 as b

T,L=b.T,b.L
STAGE='upl_tpi_cryer_gpu_debug2_native_r1'
READER=T/'outputs/upl_cryer_public_native_DebugCPU_r1/reader.exe'
OLD_NATIVE_CALL=L/'upl_cryer_freebody_smoke128_GPU_r1.native.call.json'
RUNNER=T/'support/upl_tpi_cryer_gpu_debug2_run_r1.py'
DT=2.**-20
TAG_RE=re.compile(r'upl_tpi_cryer_gpu_Debug_B_debug2steps_r[1-9][0-9]*\Z')
COLS='part,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,prediction_double_Pa,half_actual_float_Pa,endpoint_q_actual_float_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,raw_final_float_Pa,final_float_Pa,theta_half_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,source_drained,endpoint_drained,commit_drained,commits,endpoint_calls,core_field_bit_checks,hg_snapshot_checks'.split(',')


def bits(x,kind='d'):
    return struct.pack('<'+kind,float(x))


def f32_ftz(x):
    """Actual use_fast_math RN float conversion, signed result-subnormal FTZ."""
    raw=struct.pack('<f',float(x));u=struct.unpack('<I',raw)[0]
    if u & 0x7f800000 == 0:
        u &= 0x80000000
    return struct.unpack('<f',struct.pack('<I',u))[0]


class Admission:
    def __init__(self,path,phase,tag):
        self.entry,self.data=b.stat(path),b.read(path)
        b.need(self.data.get('stage')==STAGE+'.'+phase+'_admission' and self.data.get('passed') is True
               and self.data.get('tag')==tag and (self.data.get('one_native_read_only') is True
               if phase=='native' else self.data.get('offline_only') is True),'Independent matching phase/tag admission required')
        self.frozen={b.key(x['path']):x for x in self.data['inputs']};self.consumed={}
        b.need(len(self.frozen)==len(self.data['inputs']),'Duplicate frozen input')

    def pin(self,path):
        k=b.key(path);b.need(k in self.frozen,'Consumed input absent from root admission: '+str(path))
        self.consumed[k]=b.same(self.frozen[k]);return self.consumed[k]

    def finish(self):
        for x in self.consumed.values():b.same(x)
        b.same(self.entry);return list(self.consumed.values())


def context(ad,tag):
    for p in (Path(__file__),T/'notes/upl_tpi_cryer_gpu_debug2_native_r1.md',RUNNER,Path(b.__file__),
              sys.executable,np.__file__,psutil.__file__):ad.pin(p)
    runpath=L/(tag+'.run.json');ad.pin(runpath);run=b.read(runpath)
    b.need(run['stage']=='upl_tpi_cryer_gpu_debug2_run_r1.run' and run['passed']
           and run['configuration']=='Debug' and run['scheme']=='B' and run['window']=='debug2steps'
           and run['tag']==tag and run['actual_memcheck_zero_errors']
           and run['actual_device_fixture_marker_count']==1 and run['actual_device_fixture_checked_cases']==16
           and run['actual_Popen_wait_exit']==run['actual_Win32_exit']==run['target_actual_Win32_exit']==0,
           'Genuine successful C04 GPU Debug-B2/memcheck/fixture run required')
    startpath=L/(tag+'.start.json');ad.pin(startpath);start=b.read(startpath)
    for name in ('call','program','source_build','prepared','root_admission','plan','memcheck_log'):
        ad.pin(run[name]['path']);b.same(run[name])
    call=b.read(run['call']['path'])
    b.need(call['passed'] and call['tool_is_solver'] is False
           and call['target_handle_acquired_before_wait'] is True
           and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==call['target_actual_Win32_exit']==0
           and call['target']==start['target']==run['target']
           and call['target']['argv'][1:]==call['target_arguments']==run['arguments']
           and b.key(call['target']['exe'])==b.key(run['program']['path'])
           and call['child']['parent']==call['owner']['pid'],'Actual original GPU tool/target identity or exits differ')
    native_created=(call['target_creation_FILETIME_ticks']-116444736000000000)/1e7
    b.need(abs(native_created-call['target']['created'])<=1e-6,'Actual target native creation differs')
    ad.pin(call['program']['path']);b.same(call['program']);ad.pin(call['log']['path']);b.same(call['log'])
    b.need(Path(call['program']['path']).name.lower()=='compute-sanitizer.exe'
           and run['actual_environment']['UPL_TPI_GPU_R1']==call['actual_environment']['UPL_TPI_GPU_R1']=='B',
           'Actual owned memcheck tool/scheme differs')
    mem=Path(run['memcheck_log']['path']).read_text(encoding='utf-8-sig',errors='replace')
    b.need(re.search(r'ERROR SUMMARY:\s*0 errors',mem),'Actual memcheck zero-error summary absent')
    built,prep=b.read(run['source_build']['path']),b.read(run['prepared']['path'])
    b.need(built['passed'] and built['configuration']=='Debug' and built['object_count']==111
           and built['old_objects_reused']==0 and built['program']==run['program'] and prep['passed']
           and built['prepared']['path']==run['prepared']['path'],'Matched actual full111 build/prepare/program required')
    for e in built['runtime']:ad.pin(e['destination']['path']);b.same(e['destination'])
    source=Path(prep['source_root'])/'source';h=source/'upl_tpi_cryer_gpu_r1.h';cu=source/'upl_tpi_cryer_gpu_r1.cuh'
    ad.pin(h);ad.pin(cu)
    body=cu.read_text(encoding='utf-8-sig')
    b.need(body.count('raw=__dadd_rn(double(o.q),__ddiv_rn(o.R,o.S));')==1
           and body.count('o.raw=__double2float_rn(raw);')==1,
           'Actual bound pressure RN source differs; no arithmetic-model fallback')
    flags=built['actual_NVCC_source_commands']['jsphgpu_ker.cu']['flags']
    b.need('-use_fast_math' in flags and '-G' in flags
           and not any(x.startswith(('--ftz=false','--fmad=false')) for x in flags),
           'Actual Debug CUDA RN/use_fast_math/FTZ compiler policy differs')
    plan=Path(run['plan']['path'])
    with plan.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    scalar=0.
    for _ in range(2):scalar+=DT
    b.need(len(rows)==2 and list(rows[0])==['part','time_s','completed_step','saved_step','dt_s'],'Actual five-column clock schema differs')
    for p,row in enumerate(rows):
        b.need(int(row['part'])==p and int(row['completed_step'])==(2 if p else 0)
               and int(row['saved_step'])==(1 if p else 0) and bits(float(row['time_s']))==bits(scalar if p else 0.)
               and bits(float(row['dt_s']))==bits(DT),'Actual scalar clock/zero-based Step differs')
    data=Path(run['data']);out=Path(run['output_directory'])
    b.need(b.key(data)==b.key(out/'data'),'Actual owned raw data directory differs')
    raw=sorted([*data.glob('*.bi4'),*data.glob('*.ibi4')])
    b.need({p.name for p in raw if p.suffix=='.bi4'}=={'Part_0000.bi4','Part_0001.bi4'},'Actual two-frame raw sequence differs')
    for p in raw:ad.pin(p)
    for name in ('Run.out','Run.csv','UplTpiCryerGpuR1.policy.json','UplTpiCryerGpuR1.summary.json','UplTpiCryerGpuR1.csv'):
        ad.pin(out/name)
    return dict(tag=tag,run=run,runpath=runpath,data=data,out=out,plan=plan,
                native=T/'outputs'/(tag+'_native_r1'),arithmetic_source=[b.stat(h),b.stat(cu)],
                arithmetic_policy='Bound actual Debug -G -use_fast_math with source ddiv_rn/dadd_rn/double2float_rn; exact RN+signed f32 FTZ, no ULP tolerance')


def done(directory):
    d=b.read(directory/'completion.json')
    b.need(d['stage']=='upl_cryer_public_native_r1' and d['passed'] and d['declared_backend']=='GPU'
           and d['samples']==2 and d['completed_steps']==2 and bits(d['actual_end_s'])==bits(2.**-19)
           and bits(d['dt_s'])==bits(DT) and d['total_native_ids']==37181 and d['soil_ids']==37173
           and d['fixed_ids']==8 and d['native_typed_arrays']==22 and d['soil_ledger_checks']==74346
           and d['fixed_marker_checks']==16 and d['noninitial_signed_dterror_intervals']==1
           and d['post_open_frames']==d['post_open_FS23_zero_pressure_checks']==0 and d['raw_BI4_modified'] is False,
           'Original native22/IDs/ledger/signed/startup coverage differs')
    return d


def decode(ad,ctx,result):
    native=ctx['native'];tag=ctx['tag']
    b.need(not native.exists() and not (L/(tag+'.native_r1.call.json')).exists()
           and not (L/(tag+'.native_r1.log')).exists(),'Existing/partial native output or reader call must not be repeated')
    ad.pin(READER);ad.pin(OLD_NATIVE_CALL);old=b.read(OLD_NATIVE_CALL)
    b.need(old['exit_code']==0 and old['direct_exit'] and b.key(old['program']['path'])==b.key(READER),
           'The existing actually successful C04 reader implementation is required')
    b.same(old['program'])
    for p in READER.parent.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.xml'):ad.pin(p)
    for proc in psutil.process_iter(['exe','cmdline']):
        if proc.info['exe'] and b.key(proc.info['exe'])==b.key(READER):
            b.need(not any(b.key(x) in {b.key(ctx['data']),b.key(native)} for x in (proc.info['cmdline'] or [])[1:]),
                   'Matching reader is already active; never duplicate')
    env=os.environ.copy();env.pop('UPL_TPI_GPU_R1',None);env.pop('UPL_TPI_CPU_R1',None)
    ad.finish();call,_=b.invoke(tag+'.native_r1',[str(READER),'--read','GPU',str(ctx['data']),str(ctx['plan']),str(native)],READER.parent,env)
    result.update(passed=True,reader_call=call,reader_invocations=1,native_directory=str(native),
                  completion=done(native),products=[b.stat(p) for p in native.iterdir() if p.is_file()],
                  consumed=ad.finish(),consumed_stats_unchanged=True)


def review(ad,ctx,result):
    receipt=L/(ctx['tag']+'.native_r1.json');ad.pin(receipt);decoded=b.read(receipt)
    b.need(decoded['passed'] and decoded['reader_invocations']==1 and b.key(decoded['native_directory'])==b.key(ctx['native']),
           'Existing successful unique native read required; no re-decode path')
    ad.pin(decoded['reader_call']['path']);b.same(decoded['reader_call']);call=b.read(decoded['reader_call']['path'])
    b.need(call['passed'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0,'Actual reader exits failed')
    for p in ctx['native'].iterdir():
        if p.is_file():ad.pin(p)
    completion=done(ctx['native']);raw=(ctx['native']/'common26.bin').read_bytes()
    dtype=np.dtype([('time','<f8'),('v','<f8',(37181,26))])
    b.need(struct.unpack_from('<III',raw)==(37181,26,2) and len(raw)==12+2*dtype.itemsize,'Original common26 header/payload differs')
    values=np.frombuffer(raw,dtype=dtype,offset=12)
    clock=(ctx['native']/'clock.bin').read_bytes()
    b.need(struct.unpack_from('<II',clock)==(2,28) and len(clock)==64,'Original signed clock28 header/payload differs')
    for p in (0,1):
        time,step,dt,error=struct.unpack_from('<dIdd',clock,8+28*p)
        b.need(bits(time)==bits(values['time'][p])==bits(2.**-19 if p else 0.)
               and step==(1 if p else 0) and bits(dt)==bits(DT) and math.isfinite(error) and error<=1e-14
               and (not p or error!=-sys.float_info.max),'Original signed clock/necessary-step interval failed')
    with (ctx['native']/'native_ids.csv').open(encoding='utf-8-sig',newline='') as f:ids=list(csv.DictReader(f))
    b.need(len(ids)==37181 and all(int(x['id'])==k and int(x['is_soil'])==int(k>=8) for k,x in enumerate(ids)),
           'Actual full native material identities/roles differ')
    policy=b.read(ctx['out']/'UplTpiCryerGpuR1.policy.json');summary=b.read(ctx['out']/'UplTpiCryerGpuR1.summary.json')
    b.need(policy['stage']==summary['stage']=='upl_tpi_cryer_gpu_r1' and policy['scheme']==summary['scheme']=='B_TPI_alpha_0p5_beta0'
           and policy['alpha']==summary['alpha']==.5 and policy['beta']==summary['beta']==0 and policy['M0']
           and policy['native_count']==37181 and policy['soil_count']==37173 and policy['history_ID_owned']
           and summary['completed'] and summary['commits']==summary['endpoint_calls']==2
           and summary['core_field_bit_checks']==520422 and summary['HG_readonly_snapshot_checks']==0
           and bits(summary['actual_end'])==bits(2.**-19),'Actual B/C04/HG0 pressure policy/lifecycle differs')
    seen=[set(),set()];rowchecks=0;nonfused=fused=0
    with (ctx['out']/'UplTpiCryerGpuR1.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=csv.DictReader(f);b.need(rows.fieldnames==COLS,'Original28-column sidecar layout differs')
        for row in rows:
            p,k=int(row['part']),int(row['native_id']);b.need(p in (0,1) and 8<=k<37181 and k not in seen[p],'Actual sidecar native row duplicated/new')
            seen[p].add(k);v={x:float(row[x]) for x in COLS if x not in ('part','native_id')}
            b.need(all(math.isfinite(x) for x in v.values()),'Nonfinite actual sidecar field')
            n=2 if p else 0
            b.need(v['source_step_zero_based']==(1 if p else 0) and v['completed_step']==v['commits']==v['endpoint_calls']==n
                   and bits(v['source_time_s'])==bits(DT if p else 0.) and bits(v['actual_save_time_s'])==bits(2.**-19 if p else 0.)
                   and bits(v['dt_s'])==bits(DT) and v['core_field_bit_checks']==7*37173*n and v['hg_snapshot_checks']==0
                   and v['source_drained']==v['endpoint_drained']==v['commit_drained']==0,'Actual2-step lifecycle/source clocks/closed BC differs')
            prediction=f32_ftz(v['pn_Pa'])+.5*(f32_ftz(v['pn_Pa'])-f32_ftz(v['previous_Pa']))
            b.need(bits(prediction)==bits(v['prediction_double_Pa'])
                   and bits(f32_ftz(prediction),'f')==bits(v['half_actual_float_Pa'],'f')==bits(v['endpoint_q_actual_float_Pa'],'f')
                   and bits(v['final_float_Pa'],'f')==bits(values['v'][p,k,6],'f')
                   and bits(v['Jfull'])==bits(values['v'][p,k,8]),'Actual RN/FTZ pressure prediction/native commit or J differs')
            if p:
                b.need(v['S_1_per_m_s']>0,'Nonpositive real pressure row cannot be masked')
                exact=f32_ftz(v['endpoint_q_actual_float_Pa'])+v['Rgamma_Pa_per_m_s']/v['S_1_per_m_s']
                b.need(bits(f32_ftz(exact),'f')==bits(v['raw_final_float_Pa'],'f')==bits(v['final_float_Pa'],'f'),
                       'Actual explicit RN divide/add and signed FTZ float writeback differs')
                product=DT*v['Jhalf'];plain=v['Jn']+product*v['theta_half_for_J_1_per_s']
                fm=float(Fraction.from_float(v['Jn'])+Fraction.from_float(product)*Fraction.from_float(v['theta_half_for_J_1_per_s']))
                a,z=bits(v['Jfull'])==bits(plain),bits(v['Jfull'])==bits(fm)
                b.need(a or z,'Original CUDA J expression matches neither exact permitted compiler path')
                nonfused+=a;fused+=z;rowchecks+=1
            else:
                b.need(v['S_1_per_m_s']==v['Rgamma_Pa_per_m_s']==0. and v['Jn']==v['Jhalf']==v['Jfull']==1.,'Cold initial pressure/J differs')
    b.need(all(s==set(range(8,37181)) for s in seen) and rowchecks==37173,'Incomplete all-material saved sidecar coverage')
    result.update(passed=True,reader_invocations=0,native_directory=str(ctx['native']),native_read_receipt=b.stat(receipt),completion=completion,
        sidecar_rows=74346,actual_end_row_formula_checks=rowchecks,core_field_bit_checks=520422,HG_snapshot_checks=0,
        exact_J_nonfused_matches=nonfused,exact_J_fused_matches=fused,ULP_or_absolute_tolerance_added=0,
        CUDA_pressure_RN_FTZ_policy=ctx['arithmetic_policy'],arithmetic_source=ctx['arithmetic_source'],
        CPU_2dt_reference_claimed=False,raw22_all_array_bit_comparison_performed=False,
        postdrain_or_peak_or_physical_acceptance=False,consumed=ad.finish(),consumed_stats_unchanged=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--phase',choices=('native','review'),required=True)
    ap.add_argument('--tag',required=True);ap.add_argument('--admission',required=True,type=Path)
    ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args()
    b.need(a.execution_authorized and TAG_RE.fullmatch(a.tag),'Explicit root phase and exact C04 Debug-B2 tag required')
    receipt=L/(a.tag+('.native_r1.json' if a.phase=='native' else '.native_review_r1.json'))
    b.need(not receipt.exists(),'Existing successful/failed receipt protected; no retry/overwrite')
    result=dict(stage=STAGE+'.'+a.phase,tag=a.tag,passed=False,solver_invocations=0,build_invocations=0,
        VTK_invocations=0,SHA_scans=0,raw_BI4_modified=False,physical_acceptance=False,automatic_follow_up=False)
    try:
        ad=Admission(a.admission,a.phase,a.tag);result['root_admission']=ad.entry;ctx=context(ad,a.tag)
        (decode if a.phase=='native' else review)(ad,ctx,result)
    except Exception as exc:result.update(passed=False,first_error=str(exc),partials_preserved=True)
    b.write_new(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_error=result.get('first_error')),ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
