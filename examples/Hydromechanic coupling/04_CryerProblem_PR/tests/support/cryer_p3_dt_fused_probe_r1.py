"""CPU replay of separate/fused wave/diffusion reductions; compile CUDA object without running GPU."""
import argparse
import csv
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import sys
import numpy as np

T=Path(__file__).resolve().parents[1]
SUP=T/'support'
CASE=T/'outputs/cryer_p3_gpu_r2_source'
TAG='cryer_p3_dt_fused_probe_r1'
CODE=T/'outputs/upl_cryer_freebody_peak_GPU_r1_native'
COLS=('legacy_c2','skeleton_c2','diffusivity')
class Params(C.Structure):
    _fields_=[(key,C.c_double) for key in ['solid0','rho0','rhow','modulus','kw','conductivity','gamma']]
class Summary(C.Structure):
    _fields_=[(key,C.c_double) for key in COLS]+[(key,C.c_uint) for key in ['invalid_legacy','invalid_skeleton']]

def execute(argv,env,folder,name):
    with (folder/(name+'.log')).open('xb') as f:
        rc=subprocess.run(list(map(str,argv)),env=env,cwd=folder,stdout=f,stderr=subprocess.STDOUT).returncode
    if rc:raise RuntimeError(f'{name} returned {rc}')
    return dict(tool=str(argv[0]),exit=rc,log=str(folder/(name+'.log')))

def probes(folder):
    s=(CASE/'JSphGpu_ker.cu').read_text(encoding='latin1')
    k=s.index('void KerComputePorosityWaveSpeed2')
    beg=s.index('    const double jp=j[p];',k);end=s.index('\n  }\n  speed2[tid]',beg)
    body=s[beg:end]
    assert body.count('atomicMin(invalid,p)')==1 and body.count('KerDynamicConductivity(')==1
    body=body.replace('atomicMin(invalid,p)','invalid=true')
    fn=s[s.index('static __device__ __forceinline__ double KerDynamicConductivity('):]
    fn=fn[:fn.index('\n}')+2].replace('__device__ __forceinline__','inline')
    source='''#include <cmath>
#include <cfloat>
#include <algorithm>
#include "cryer_p3_dt_fused_r1.h"
using std::isfinite;
using namespace cryer_p3_dt;
'''+fn+'''
static void Original(unsigned p,const double* j,Params par,bool all,double& value,double& diffusion,bool& invalid){
  const double m=par.modulus,kw=(all?par.kw:0.),khyd=(all?par.conductivity:0.),gamma=(all?par.gamma:1.);
  const double solid0=par.solid0,rho0=par.rho0,rhow=par.rhow,ck=0.;
  const bool maxdiffusion=all,conductivity=false;value=0.;diffusion=0.;invalid=false;
'''+body+'''
}
extern "C" __declspec(dllexport) unsigned Run(unsigned np,const double* j,const unsigned char* normal,
 const Params* par,bool fused,double* values,unsigned char* flags,Summary* out){
  *out={0.,0.,0.,np,np};
  for(unsigned i=0;i<np;i++){
    Value v={0.,0.,0.,true,true};
    if(normal[i]){
      if(fused)v=Evaluate(j[i],*par);
      else {
        bool bad=false;double dummy=0.;
        Original(i,j,*par,true,v.legacy2,v.diffusion,bad);v.legacy_valid=!bad;
        Original(i,j,*par,false,v.skeleton2,dummy,bad);v.skeleton_valid=!bad;
      }
    }
    values[3*i]=v.legacy2;values[3*i+1]=v.skeleton2;values[3*i+2]=v.diffusion;
    flags[i]=(!v.legacy_valid?1:0)|(!v.skeleton_valid?2:0);
    if(!v.legacy_valid)out->invalid_legacy=std::min(out->invalid_legacy,i);
    if(!v.skeleton_valid)out->invalid_skeleton=std::min(out->invalid_skeleton,i);
    out->legacy2=std::max(out->legacy2,v.legacy2);
    out->skeleton2=std::max(out->skeleton2,v.skeleton2);
    out->diffusion=std::max(out->diffusion,v.diffusion);
  }
  if(fused)return FirstFailure(*out,np);
  if(out->invalid_legacy<np || !isfinite(out->legacy2) || !(out->legacy2>0.) || !isfinite(out->diffusion) || out->diffusion<0.)return 1;
  if(out->invalid_skeleton<np || !isfinite(out->skeleton2) || !(out->skeleton2>0.))return 2;
  return 0;
}
'''
    unit=folder/'two_vs_one.cpp';unit.write_text(source,encoding='ascii')
    b=json.loads((T/'logs/upl_tpi_cryer_gpu_Release_r1.build.json').read_text(encoding='utf8'))
    cmd=['cmd.exe','/d','/c',b['environment_batch']['path']]
    environment=subprocess.check_output(cmd,encoding='mbcs')
    env={k.upper():v for k,v in (line.split('=',1) for line in environment.splitlines() if '=' in line and not line.startswith('='))}
    cuda=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7')
    tools=Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64')
    cpu=execute([tools/'cl.exe','/nologo','/LD','/O2','/EHsc','/fp:precise','/I'+str(SUP),unit,'/link','/OUT:two_vs_one.dll'],env,folder,'cpu_build')
    gpu=execute([cuda/'bin/nvcc.exe','-ccbin',str(tools),'-gencode=arch=compute_86,code=[sm_86,compute_86]','-use_fast_math','-D_WITHGPU','-Xcompiler','/EHsc','-I'+str(CASE),'-I'+str(SUP),'-c',SUP/'cryer_p3_dt_fused_probe_r1.cu','-o','fused.cu.obj'],env,folder,'cuda_compile_only')
    return load_dll(folder),cpu,gpu

def load_dll(folder):
    dll=C.CDLL(str(folder/'two_vs_one.dll'))
    dbl=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');u8=np.ctypeslib.ndpointer(dtype=np.uint8,flags='C_CONTIGUOUS')
    dll.Run.argtypes=[C.c_uint,dbl,u8,C.POINTER(Params),C.c_bool,dbl,u8,C.POINTER(Summary)]
    dll.Run.restype=C.c_uint
    return dll

def check(dll,tag,j,mask,par,expect=0,indices=None):
    j=np.ascontiguousarray(j,dtype=np.float64);mask=np.ascontiguousarray(mask,dtype=np.uint8)
    records=[]
    for fused in (False,True):
        values=np.empty((len(j),3));flags=np.empty(len(j),dtype=np.uint8);summary=Summary()
        first=dll.Run(len(j),j,mask,C.byref(par),fused,values,flags,C.byref(summary))
        records.append((values,flags,summary,first))
    a,b=records
    if not (np.array_equal(a[0].view(np.uint64),b[0].view(np.uint64)) and np.array_equal(a[1],b[1])
            and bytes(a[2])==bytes(b[2]) and a[3]==b[3]==expect):
        raise ValueError(f'{tag}: per-particle values, invalid flags, maxima or exception precedence differed; {a[3]}/{b[3]} expected {expect}')
    ids=(a[2].invalid_legacy,a[2].invalid_skeleton)
    if indices and ids!=indices:raise ValueError(f'{tag}: first invalid indices {ids} expected {indices}')
    return dict(sample=tag,lanes=len(j),normal_soil=int(mask.sum()),first_failure=a[3],invalid_legacy=ids[0],invalid_skeleton=ids[1],
                max_legacy_c2=a[2].legacy_c2,max_skeleton_c2=a[2].skeleton_c2,max_diffusivity=a[2].diffusivity,
                per_lane_values_same_bits=3*len(j),invalid_flags_same=len(j))

def main():
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--reuse-built-fixture',action='store_true')
    reuse=args.parse_args().reuse_built_fixture
    tag=TAG.replace('_r1','_r2') if reuse else TAG
    folder=T/'outputs'/tag;folder.mkdir(exist_ok=False)
    result=dict(passed=False,active_gpu_used=False,throughput_measured=False,scope='constant hydraulic conductivity; host replay and device compile only')
    try:
        if reuse:
            built=T/'outputs'/TAG
            receipt=json.loads((T/'logs'/(TAG+'.check.json')).read_text())
            assert receipt['cpu']['exit']==receipt['cuda_compile']['exit']==0
            dll=load_dll(built);cpu=receipt['cpu'];gpu=receipt['cuda_compile']
            result['reused_unchanged_binaries']=str(built)
        else:
            dll,cpu,gpu=probes(folder)
        result.update(cpu=cpu,cuda_compile=gpu)
        nu=np.float32(.3);E=np.float32(2e6);two=np.float32(2);one=np.float32(1)
        K=float(E/(np.float32(3)*(one-two*nu)));G=float(E/(two*(one+nu)))
        par=Params(1.-float(np.float32(.3)),2100.,1000.,K+4.*G/3.,2.e8,float(np.float32(1e-5)),9806.65)
        # Read only retained predecoded records, skip all other frames. Every ID in the selected frame is present.
        with (CODE/'common26.bin').open('rb') as f:
            npart,ncol,nframes=struct.unpack('<III',f.read(12))
            assert (npart,ncol,nframes)==(37181,26,577)
            cols=list(csv.DictReader((CODE/'columns.csv').open()))
            assert cols[8]=={'column':'8','name':'J'}
            stride=8+8*npart*ncol
            rows=[]
            for part in (0,32,63,64,65,128,256,400,576):
                f.seek(12+part*stride);tm=struct.unpack('<d',f.read(8))[0]
                a=np.frombuffer(f.read(stride-8),dtype='<f8').reshape(npart,ncol)
                mask=np.arange(npart)>=8
                row=check(dll,'native_part_'+str(part),a[:,8],mask,par)
                row.update(actual_time_s=tm,min_native_J=float(a[8:,8].min()),max_native_J=float(a[8:,8].max()));rows.append(row)
        def withp(**kwargs):
            fresh=Params.from_buffer_copy(par)
            for key,value in kwargs.items():setattr(fresh,key,value)
            return fresh
        for fixture_name,js,mask,p,expected,ids in [
           ('normal_order',[1.,.9,1.01],[1,1,1],par,0,(3,3)),
           ('nonfinite_masked',[np.nan,1.,np.inf],[0,1,0],par,0,(3,3)),
           ('nan_and_inf',[1.,np.nan,np.inf],[1,1,1],par,1,(1,1)),
           ('solid_exact_and_below',[par.solid0,np.nextafter(par.solid0,0.)],[1,1],par,1,(0,0)),
           ('solid_above',[np.nextafter(par.solid0,1.),1.],[1,1],par,0,(2,2)),
           ('round_n_to_one',[1.,float(2**60)],[1,1],par,1,(1,1)),
           ('zero_k',[1.,1.01],[1,1],withp(conductivity=0),0,(2,2)),
           ('negative_k',[1.],[1],withp(conductivity=-1.),1,(0,1)),
           ('invalid_gamma_even_when_k0',[1.],[1],withp(conductivity=0.,gamma=0.),1,(0,1)),
           ('margin_failure',[1.],[1],withp(kw=1.),1,(0,1)),
           ('hydraulic_overflow',[1.],[1],withp(conductivity=1e308),1,(0,1)),
           ('skeleton_only_underflow',[1.],[1],withp(modulus=float(np.nextafter(0.,1.))),2,(1,0)),
           ('distinct_first_error_precedence',[1.,np.nan],[1,1],withp(modulus=float(np.nextafter(0.,1.))),1,(1,0)),
           ('empty_eligible',[np.inf,np.nan],[0,0],par,1,(2,2))]:
            rows.append(check(dll,fixture_name,js,mask,p,expected,ids))
        with (T/'figures'/(tag+'.csv')).open('x',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        result.update(passed=True,real_frames=9,source_native=str(CODE),real_soil_material_samples=9*(npart-8),
                      synthetic_cases=len(rows)-9,all_result_bit_comparisons=sum(r['per_lane_values_same_bits'] for r in rows),
                      checks='CPU binary64 per-lane, global max and independent invalid minima plus legacy-before-skeleton priority',
                      min_J=min(r['min_native_J'] for r in rows[:9]),max_J=max(r['max_native_J'] for r in rows[:9]))
    except Exception as e:result['error']=repr(e)
    out=T/'logs'/(tag+'.check.json')
    with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result));return 0 if result['passed'] else 1

if __name__=='__main__':
    sys.exit(main())

