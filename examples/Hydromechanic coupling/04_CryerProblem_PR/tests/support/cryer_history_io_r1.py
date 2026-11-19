"""Native BI4 serializer replay for C04's optional preceding-full-step pressure."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time

T=Path(__file__).resolve().parents[1]
OUT=T/'outputs'
SOURCE=OUT/'cryer_p3_gpu_r2_source'
SUP=T/'support'
CC=Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64/cl.exe')
CASES={
    'CPU':('upl_tpi_cryer_p3_cpu_B64_r1','upl_cryer_freebody_smoke128_CPU_r1',
           'UplTpiP3CpuR1.csv','pressure_round','actual_after_BC_float_Pa'),
    'GPU':('cryer_p3_gpu_b64_r1','cryer_p3_gpu_default128_r1',
           'UplTpiP3GpuR1.round3.csv','round','final_field_float_Pa'),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def now():
    return datetime.now().astimezone().isoformat(timespec='milliseconds')

def extract(path,reference,round_key,final_key):
    by_id={}
    step_dt=1.9073486328125e-6
    with path.open(newline='') as f:
        for r in csv.DictReader(f):
            if r['part']!='1' or r[round_key]!='3':
                continue
            i=int(r['native_id'])
            if i in by_id or (int(r['source_step_zero_based']),int(r['completed_step']),float(r['dt_s']),
                float(r['source_time_s']),float(r['actual_save_time_s']))!=(63,64,step_dt,63*step_dt,64*step_dt):
                raise ValueError('source or time mismatch')
            vals=[float(r[k]) for k in ('pn_Pa','previous_Pa',final_key,'prediction_double_Pa')]
            for v in vals[:3]:
                if struct.unpack('<f',struct.pack('<f',v))[0]!=v:
                    raise ValueError('trace pressure is not an exact binary32 value')
            by_id[i]=struct.pack('<Ifffd',i,*vals)
    if sorted(by_id)!=list(range(8,37181)):
        raise ValueError('material ID set mismatch')
    with reference.open('xb') as f:
        for i in sorted(by_id):
            f.write(by_id[i])

def run(tag):
    if not tag.startswith('cryer_history_io_') or not tag.replace('_','').isalnum():
        raise ValueError('invalid tag')
    folder=OUT/tag
    folder.mkdir(exist_ok=False)
    t0=time.perf_counter()
    result=dict(started=now(),passed=False,backends={},source_sha256={},compile_source=str(SOURCE))
    try:
        env_cmd=OUT/'upl_tpi_cryer_gpu_Release_r1/load_environment.cmd'
        environment=subprocess.check_output(['cmd.exe','/d','/c',str(env_cmd)],encoding='mbcs')
        env={k.upper():v for k,v in (line.split('=',1) for line in environment.splitlines() if '=' in line and not line.startswith('='))}
        names=['Functions','JException','JObject','JBinaryData','JPartDataBi4','JPartDataHead']
        sources=[SUP/'cryer_history_io_r1.cpp']+[SOURCE/(n+'.cpp') for n in names]
        result['source_sha256']={str(p):sha(p) for p in sources+[SOURCE/(n+'.h') for n in names]+[SUP/'TpiPressureRow.h',Path(__file__).resolve()]}
        exe=folder/'history.exe'
        cmd=list(map(str,[CC,'/nologo','/std:c++17','/DWIN32','/D_HAS_STD_BYTE=0','/EHsc','/O2','/MT','/fp:precise','/I'+str(SOURCE),
                          '/I'+str(SUP),*sources,'/Fe:'+str(exe)]))
        result['build_command']=cmd
        with (folder/'compile.log').open('xb') as log:
            subprocess.run(cmd,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        result['exe_sha256']=sha(exe)
        for backend,(b,a,file,rkey,fkey) in CASES.items():
            idir,adir=OUT/b/'data',OUT/a/'data'
            trace=OUT/b/file
            refs=folder/(backend+'_trace.bin')
            native=[idir/'Part_0000.bi4',idir/'Part_0001.bi4',adir/'Part_0001.bi4',trace]
            source_hash={str(p):sha(p) for p in native}
            extract(trace,refs,rkey,fkey)
            cmd=list(map(str,[exe,idir,adir,refs,folder/backend]))
            log=folder/(backend+'.log')
            with log.open('xb') as f:
                subprocess.run(cmd,cwd=folder,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
            # JBinaryData prints the expected missing-Schema exception during two negative tests.
            owners,root_values,part_values,older,frame0,cold,modes=map(int,log.read_text().strip().splitlines()[-1].split(','))
            if owners!=37173 or modes!=16:
                raise ValueError('incomplete native report')
            augmented=folder/backend/'Part_0001.bi4'
            stripped=folder/backend/'stripped.bi4'
            off=folder/backend/'default_A.bi4'
            if sha(stripped)!=source_hash[str(idir/'Part_0001.bi4')] or sha(off)!=source_hash[str(adir/'Part_0001.bi4')]:
                raise ValueError('native file bytes changed')
            if {str(p):sha(p) for p in native}!=source_hash:
                raise ValueError('retained input changed')
            result['backends'][backend]=dict(command=cmd,source_sha256=source_hash,
                output_sha256={str(p):sha(p) for p in (refs,augmented,stripped,off,log)},material_owners=owners,
                native_arrays=22,original_root_values=root_values,original_part_values=part_values,
                native_slot_and_permuted_predictors=2*owners,previous_step_last_predictor_reference=owners,
                prediction_changes_with_previous_Pa=older,prediction_changes_with_Part0=frame0,
                prediction_changes_with_explicit_cold=cold,malformed_payloads=modes,
                added_bytes=augmented.stat().st_size-stripped.stat().st_size,stripped_matches_input=True,default_a_matches_input=True)
        result['passed']=True
    finally:
        result.update(finished=now(),elapsed_s=time.perf_counter()-t0)
        with (T/'logs'/(tag+'.check.json')).open('x',encoding='utf8') as f:
            json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({'passed':result['passed'],'receipt':str(T/'logs'/(tag+'.check.json'))}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',default='cryer_history_io_r1')
    run(parser.parse_args().tag)
