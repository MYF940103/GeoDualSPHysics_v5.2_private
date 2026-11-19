"""Build or run a standalone SM86 comparison against the frozen solver's original CUDA kernels."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import struct
import subprocess
import time
from datetime import datetime

import numpy as np

T = Path(__file__).resolve().parents[1]
SUP = T / 'support'
SOURCE = T / 'outputs/cryer_p3_gpu_r2_source'
NATIVE = T / 'outputs/upl_cryer_freebody_peak_GPU_r1_native'
ROUND = T / 'outputs/cryer_p3_gpu_b64_r1/UplTpiP3GpuR1.round3.csv'
NVCC = Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/bin/nvcc.exe')
CCBIN = Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64')
CUDA_DLL = str(NVCC.parent)
FIXED, FLUID, PERIODIC, OUT = 0x0000, 0x1800, 0x3800, 0x7800
PAR = (1.-float(np.float32(.3)), 2100., 1000., 1666666.75+4.*769230.8125/3.,
       2.e8, float(np.float32(1.e-5)), 1000.*9.80665)
FRAMES = (0, 32, 63, 64, 65, 128, 256, 400, 576)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, obj):
    with path.open('x', encoding='utf8') as f:
        json.dump(obj, f, indent=2, allow_nan=False)

def clock():
    return datetime.now().astimezone().isoformat(timespec='milliseconds')

def extract(folder):
    path = SOURCE/'JSphGpu_ker.cu'
    text = path.read_text(encoding='latin1')
    first = text.index('static __device__ __forceinline__ double KerDynamicConductivity(')
    kernel = text.index('__global__ void KerComputePorosityWaveSpeed2(', first)
    wrapper = text.index('void ComputePorosityWaveSpeed2(', kernel)
    last = text.index('\n}', wrapper)+2
    original = text[first:last]
    captured = text[kernel:wrapper]
    edits = [
        ('void KerComputePorosityWaveSpeed2(', 'void CapturedWave('),
        ('bool conductivity,double ck)', 'bool conductivity,double ck,double* cv,double* cd,unsigned char* ce)'),
        ('double value=0.,diffusion=0.;', 'bool rejected=false; double value=0.,diffusion=0.;'),
        ('if(!valid){value=0.;', 'if(!valid){rejected=true;value=0.;'),
        ('  speed2[tid]=value;', '  if(p<np){cv[p]=value;if(cd)cd[p]=diffusion;ce[p]=rejected;}\n  speed2[tid]=value;')]
    for needle, addition in edits:
        assert captured.count(needle) == 1, needle
        captured = captured.replace(needle, addition)
    header = folder/'cryer_dt_original.cuh'
    header.write_text('namespace original_dt {\n'+original+'\n'+captured+'\n}\n', encoding='latin1')
    return hashlib.sha256(original.encode('latin1')).hexdigest()

def fixtures(file):
    meta = []
    def emit(name, j, code, npb=0, p=PAR, failure=0, invalid=None, timed=False, **details):
        arr = np.ascontiguousarray(j, dtype='<f8')
        c = np.ascontiguousarray(code, dtype='<u2')
        n = len(arr)
        assert n == len(c) and 0 <= npb <= n
        bad = (n,n) if invalid is None else invalid
        file.write(struct.pack('<64s6I7d', name.encode('ascii'), n, npb, failure, *bad, int(timed), *p))
        file.write(arr.tobytes())
        file.write(c.tobytes())
        meta.append(dict(name=name, n=n, npb=npb, j_sha256=hashlib.sha256(arr.tobytes()).hexdigest(),
                         eligible=int(np.sum(c[npb:]==FLUID)), **details))

    with (NATIVE/'native_ids.csv').open() as f:
        ids = [(int(r['id']), int(r['is_soil'])) for r in csv.DictReader(f)]
    assert ids == [(i,int(i>=8)) for i in range(37181)]
    code = np.where(np.arange(len(ids))<8,FIXED,FLUID)
    with (NATIVE/'columns.csv').open() as f:
        columns = list(csv.DictReader(f))
    assert columns[8] == {'column':'8','name':'J'}
    with (NATIVE/'common26.bin').open('rb') as f:
        n, count, frame_count = struct.unpack('<III',f.read(12))
        assert (n,count,frame_count) == (len(ids),26,577)
        stride = 8+8*n*count
        for part in FRAMES:
            f.seek(12+part*stride)
            tm, = struct.unpack('<d',f.read(8))
            j = np.frombuffer(f.read(stride-8), dtype='<f8').reshape(n,count)[:,8]
            emit('native_part_'+str(part), j, code, npb=8, timed=part==65,
                 part=part, time_s=tm, min_J=float(j[8:].min()), max_J=float(j[8:].max()))
    # These full-material rows describe the source, half and final J of an actual P3 update.
    field = np.full((3,n), np.nan)
    seen = set()
    with ROUND.open() as f:
        for r in csv.DictReader(f):
            if r['part'] != '1':
                continue
            i = int(r['native_id'])
            assert 8 <= i < n and i not in seen and r['completed_step']=='64' and r['round']=='3'
            seen.add(i)
            field[:,i] = [float(r[key]) for key in ('Jn','Jhalf','Jfull')]
            tm = float(r['actual_save_time_s'])
    assert len(seen)==n-8 and np.isfinite(field[:,8:]).all()
    for label,j in zip(('Jn','Jhalf','Jfull'),field):
        emit('p3_b64_round3_'+label,j,code,npb=8,timed=label=='Jhalf',
             completed_step=64,save_time_s=tm,min_J=float(j[8:].min()),max_J=float(j[8:].max()))

    def change(**args):
        names = 'solid0 rho0 rhow modulus kw k gamma'.split()
        return tuple(args.get(k,v) for k,v in zip(names,PAR))
    tiny = float(np.nextafter(0.,1.))
    def test(name, j, p=PAR, failure=0, invalid=None, code=None, npb=0):
        emit(name,j,[FLUID]*len(j) if code is None else code,npb,p,failure,invalid)
    test('normal_order',[1.,.9,1.01])
    test('npb_fixed_periodic_excluded',[np.nan,np.inf,np.nan,np.nan,.99,np.nan],
         code=[FLUID,FIXED,PERIODIC,OUT,FLUID,FIXED],npb=1)
    test('nan_inf',[1.,np.nan,np.inf],failure=1,invalid=(1,1))
    test('solid_exact_below',[PAR[0],np.nextafter(PAR[0],0.)],failure=1,invalid=(0,0))
    test('solid_nextabove',[np.nextafter(PAR[0],1.),1.])
    test('porosity_rounds_to_one',[1.,2.**60],failure=1,invalid=(1,1))
    test('zero_k',[1.,1.01],p=change(k=0.))
    test('negative_k',[1.],p=change(k=-1.),failure=1,invalid=(0,1))
    test('nan_k',[1.],p=change(k=np.nan),failure=1,invalid=(0,1))
    test('bad_gamma_at_zero_k',[1.],p=change(k=0.,gamma=0.),failure=1,invalid=(0,1))
    test('bad_margin',[1.],p=change(kw=1.),failure=1,invalid=(0,1))
    test('diffusion_overflow',[1.],p=change(k=1e308),failure=1,invalid=(0,1))
    test('skeleton_only_underflow',[1.],p=change(modulus=tiny),failure=2,invalid=(1,0))
    test('distinct_error_precedence',[1.,np.nan],p=change(modulus=tiny),failure=1,invalid=(1,0))
    test('empty_eligible',[np.inf,np.nan],code=[FIXED,OUT],failure=1)
    test('all_prefix',[np.inf,np.nan],npb=2,failure=1)
    test('zero_mixture_density',[1.],p=change(rho0=0.),failure=1,invalid=(0,0))
    j = np.linspace(.98,1.1,513)
    j[[1,262,289,512]] = np.nan
    mask = [FLUID]*513
    mask[262] = PERIODIC
    test('invalid_multiple_blocks',j,code=mask,npb=2,failure=1,invalid=(289,289))
    return meta

def prepare(folder):
    folder.mkdir(exist_ok=False)
    original_hash = extract(folder)
    with (folder/'inputs.bin').open('xb') as f:
        inputs = fixtures(f)
    env_cmd = T/'outputs/upl_tpi_cryer_gpu_Release_r1/load_environment.cmd'
    environ = subprocess.check_output(['cmd.exe','/d','/c',str(env_cmd)],encoding='mbcs')
    env = {k.upper():v for k,v in (line.split('=',1) for line in environ.splitlines() if '=' in line and not line.startswith('='))}
    cmd = list(map(str,[NVCC,'-ccbin',CCBIN,'-gencode=arch=compute_86,code=sm_86',
                        '-use_fast_math','-O3','-D_WITHGPU','-Xcompiler','/EHsc','-I'+str(SOURCE),
                        '-I'+str(SUP),'-I'+str(folder),SUP/'cryer_dt_gpu_r1.cu','-o',folder/'replay.exe']))
    with (folder/'compile.log').open('xb') as f:
        subprocess.run(cmd,env=env,cwd=folder,stdout=f,stderr=subprocess.STDOUT,check=True)
    relevant = [SOURCE/name for name in ('JSphGpu_ker.cu','JSphGpu_ker.h','FunctionsBasic_iker.h','DualSphDef.h','JSphGpu.cpp')]
    relevant += [SUP/name for name in ('cryer_dt_gpu_r1.cu','cryer_dt_gpu_r1.py','cryer_p3_dt_fused_probe_r1.cu','cryer_p3_dt_fused_r1.h')]
    relevant.extend([ROUND,NATIVE/'native_ids.csv',NATIVE/'columns.csv',folder/'replay.exe',folder/'inputs.bin'])
    write_json(folder/'build.json',dict(finished=clock(),command=cmd,nvcc=subprocess.check_output([str(NVCC),'--version'],text=True),
        original_extracted_text_sha256=original_hash, parameters=list(PAR), native_binary=str(NATIVE/'common26.bin'),
        sha256={str(p):digest(p) for p in relevant},samples=inputs))

def gpu_state():
    def output(args):
        return subprocess.check_output(['nvidia-smi']+args,text=True,encoding='utf8',errors='replace').strip().splitlines()
    return dict(gpu=output(['--query-gpu=name,driver_version,utilization.gpu,power.draw,memory.used','--format=csv']),
                compute=output(['--query-compute-apps=pid,process_name','--format=csv']))

def measure(folder):
    provenance=json.loads((folder/'build.json').read_text())
    report,times,runlog = [folder/name for name in ('checks.csv','timings.csv','gpu_run.log')]
    if any(p.exists() for p in (report,times,runlog)):
        raise FileExistsError('Use a fresh --tag for another run')
    for name in ('inputs.bin','replay.exe'):
        assert digest(folder/name)==provenance['sha256'][str(folder/name)]
    cmd=list(map(str,[folder/'replay.exe',folder/'inputs.bin',report,times]))
    env=os.environ.copy()
    env['PATH']=CUDA_DLL+os.pathsep+env['PATH']
    before=gpu_state()
    started=clock()
    t0=time.perf_counter()
    with runlog.open('xb') as f:
        run=subprocess.run(cmd,cwd=folder,env=env,stdout=f,stderr=subprocess.STDOUT)
    wall=time.perf_counter()-t0
    finished=clock()
    after=gpu_state()
    run.check_returncode()
    with report.open() as f:
        rows=list(csv.DictReader(f))
    with times.open() as f:
        samples=list(csv.DictReader(f))
    assert [r['sample'] for r in rows]==[r['name'] for r in provenance['samples']]
    assert all(r['same_summary']==r['same_guard']==r['same_derived']=='1' and r['lane_value_mismatches']==r['lane_flag_mismatches']=='0' for r in rows)
    timings={}
    for label in sorted(set(r['sample'] for r in samples)):
        timings[label]={}
        for metric in ('kernel_us_per_eval','transaction_us_per_eval'):
            series={key:[float(r[metric]) for r in samples if r['sample']==label and r['path']==key] for key in ('old','fused')}
            assert all(len(v)==11 for v in series.values())
            differences=[a-b for a,b in zip(series['old'],series['fused'])]
            series['paired_old_minus_fused']=differences
            timings[label][metric]={k:{'median':statistics.median(v),'min':min(v),'max':max(v)} for k,v in series.items()}
            timings[label][metric]['fused_faster_pairs']=sum(d>0 for d in differences)
    result=dict(passed=True,started=started,finished=finished,wall_s=wall,command=cmd,
        device=runlog.read_text().strip(),gpu_before=before,gpu_after=after,checks=len(rows),
        lane_binary64_checks=sum(3*int(r['lanes']) for r in rows),lane_validity_checks=sum(2*int(r['lanes']) for r in rows),
        per_row_global_checks='three binary64 maxima and two unsigned first-invalid slot indices',
        host_derived_checks=sum(int(r['derived_checks']) for r in rows),timings=timings,
        sha256={str(p):digest(p) for p in [folder/'build.json',report,times,runlog]})
    write_json(T/'logs'/(folder.name+'.check.json'),result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','measure'])
    parser.add_argument('--tag',default='cryer_dt_gpu_r1')
    args=parser.parse_args()
    if not args.tag.startswith('cryer_dt_gpu_') or not args.tag.replace('_','').isalnum():
        parser.error('invalid tag')
    (prepare if args.action=='prepare' else measure)(T/'outputs'/args.tag)
