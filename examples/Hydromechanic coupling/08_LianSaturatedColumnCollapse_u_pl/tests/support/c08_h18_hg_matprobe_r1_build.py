"""Prepare/build a Release failure-only one-particle raw capture; never run it."""
import argparse
import difflib
import os
import re
import shutil
import subprocess
from pathlib import Path
import c08_h18_hg_gpu_r1_build as old
import c08_h18_hg_window_r1 as gates

T, L, S = old.T, old.L, old.S
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke
TAG = 'c08_h18_hg_matprobe_r1'
SCRIPT = Path(__file__).resolve()
NOTE = T / 'notes' / (TAG + '.md')
BASE = L / 'c08_h18_hg_gpu_Release_r1.build.json'
FAILURE = L / 'c08_h18_hg_window_GPU_r1.run.json'
AUDIT = L / 'c08_h18_hg_window_failure_r1.check.json'
CAP = T / 'outputs' / (TAG + '_source')
OUT = T / 'outputs' / (TAG + '_build')
PREP = L / (TAG + '.prepare.json')
BUILD = L / (TAG + '.build.json')

# Inserted only among HOST definitions, after all original device definitions.
# No new kernel, device helper, numerical calculation or normal-path D2H is added.
CAPTURE = r'''
// Failure-only Pre raw observation. Actual material status/returned kappa are NOT observed.
std::string MatProbeQuoted(const std::string& text){
  std::ostringstream out;out<<'"';
  for(unsigned char c:text){
    if(c=='"'||c=='\\')out<<'\\'<<char(c);
    else if(c=='\n')out<<"\\n";else if(c=='\r')out<<"\\r";else if(c=='\t')out<<"\\t";
    else if(c<32)out<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(c)<<std::dec;
    else out<<char(c);
  }out<<'"';return out.str();
}
template<class F> void MatProbeValue(std::ostream& out,const std::string& name,F value,bool& comma){
  static_assert(sizeof(F)==4||sizeof(F)==8,"Only native float/double raw values");
  uint64_t bits=0;std::memcpy(&bits,&value,sizeof(F));
  std::ostringstream decimal,hex;decimal<<std::setprecision(17)<<double(value);
  hex<<std::hex<<std::setw(unsigned(sizeof(F)*2))<<std::setfill('0')<<bits;
  if(comma)out<<",\n";comma=true;
  out<<"    {\"name\":"<<MatProbeQuoted(name)<<",\"storage\":\"binary"<<sizeof(F)*8
     <<"\",\"decimal17\":"<<MatProbeQuoted(decimal.str())<<",\"ieee_hex\":"<<MatProbeQuoted(hex.str())<<'}';
}
void CapturePreMismatch(Impl& p,unsigned np,const unsigned* id,const tsymatrix3d* actual_sigma,
  const float* actual_kappa,const tsymatrix3d* base_sigma,const tsymatrix3f* rate,
  const std::string& directory,const std::string& first_error){
  // Preserve the genuinely observed first cause BEFORE any further CUDA read.
  std::string dir=directory;if(!dir.empty()&&dir.back()!='/'&&dir.back()!='\\')dir+='/';
  const std::string first=dir+"C08HGMatProbeFirstError.json",raw=dir+"C08HGMatProbePreRaw.json";
  Need(!std::ifstream(first).good()&&!std::ifstream(raw).good(),"existing material raw evidence protected");
  std::ofstream cause(first);cause<<std::setprecision(17)
    <<"{\"schema\":1,\"phase\":\"PreMaterial\",\"first_error\":"<<MatProbeQuoted(first_error)
    <<",\"source_step\":"<<p.step
    <<",\"reported_clock_is_not_saved_native_state\":true,\"strict_rejection_retained\":true,\"values\":[\n";
  bool first_comma=false;MatProbeValue(cause,"source_time_s",p.time,first_comma);cause<<"\n]}\n";
  cause.flush();Need(bool(cause),"cannot preserve original material first error");
  Failure f={};Cuda(cudaMemcpy(&f,p.failure,sizeof(f),cudaMemcpyDeviceToHost),"failure-only first mismatch download");
  Need(f.bits==MaterialMismatch&&f.claimed&&f.id>=FirstId&&f.id<Original&&f.slot<np&&f.detail<=6,
    "raw capture requires the genuinely claimed isolated material mismatch");
  Need(base_sigma&&rate&&id&&actual_sigma&&actual_kappa,"Pre live base/rate/context missing");
  unsigned actual_id=~0u,mapped=~0u;
  Cuda(cudaMemcpy(&actual_id,id+f.slot,sizeof(actual_id),cudaMemcpyDeviceToHost),"failure-only actual native ID");
  Cuda(cudaMemcpy(&mapped,p.map+f.id,sizeof(mapped),cudaMemcpyDeviceToHost),"failure-only native map");
  Need(actual_id==f.id&&mapped==f.slot,"failure raw ID/map/slot differs");
  Node shadow={};double2 base[3]={},actual[3]={};float2 rsigma[3]={};float actual_old_kappa=0;
  Cuda(cudaMemcpy(&shadow,p.node+(f.id-FirstId),sizeof(shadow),cudaMemcpyDeviceToHost),"failure-only shadow node");
  Cuda(cudaMemcpy(base,reinterpret_cast<const double2*>(base_sigma)+size_t(f.slot)*3,sizeof(base),cudaMemcpyDeviceToHost),"failure-only live SigmaPreg");
  Cuda(cudaMemcpy(rsigma,reinterpret_cast<const float2*>(rate)+size_t(f.slot)*3,sizeof(rsigma),cudaMemcpyDeviceToHost),"failure-only live Rsigma");
  Cuda(cudaMemcpy(actual,reinterpret_cast<const double2*>(actual_sigma)+size_t(f.slot)*3,sizeof(actual),cudaMemcpyDeviceToHost),"failure-only actual half sigma");
  Cuda(cudaMemcpy(&actual_old_kappa,actual_kappa+f.slot,sizeof(actual_old_kappa),cudaMemcpyDeviceToHost),"failure-only predictor old kappa");
  Need(shadow.slot==f.slot,"material shadow and actual Pre slot differ");
  const double b[6]={base[0].x,base[0].y,base[1].x,base[1].y,base[2].x,base[2].y};
  const float r[6]={rsigma[0].x,rsigma[0].y,rsigma[1].x,rsigma[1].y,rsigma[2].x,rsigma[2].y};
  const double a[6]={actual[0].x,actual[0].y,actual[1].x,actual[1].y,actual[2].x,actual[2].y};
  const double e[6]={shadow.expected.xx,shadow.expected.xy,shadow.expected.xz,shadow.expected.yy,shadow.expected.yz,shadow.expected.zz};
  const char* component[6]={"xx","xy","xz","yy","yz","zz"};
  std::ofstream out(raw);out<<"{\n  \"schema\":1,\"capture\":\"failure_only_PreMaterial\",\"native_id\":"<<f.id
    <<",\"sorted_slot\":"<<f.slot<<",\"failure_bits\":"<<f.bits<<",\"failure_component\":"<<f.detail
    <<",\"source_step\":"<<p.step<<",\"shadow_status\":"<<shadow.status
    <<",\"shadow_status_is_actual_status\":false,\"actual_material_status_observed\":false"
    <<",\"actual_returned_kappa_observed\":false,\"actual_Pre_kappa_array_still_old\":true"
    <<",\"packed_order\":\"(xx,xy)/(xz,yy)/(yz,zz)\",\"base_is_live_SigmaPreg\":true"
    <<",\"strict_rejection_retained\":true,\"saved_native_failure_state_claimed\":false"
    <<",\"first_error\":"<<MatProbeQuoted(first_error)<<",\n  \"values\":[\n";
  bool comma=false;
  MatProbeValue(out,"source_time_s",p.time,comma);MatProbeValue(out,"operator_width_s",StepDt*.5,comma);
  for(unsigned k=0;k<6;k++)MatProbeValue(out,std::string("base_sigma.")+component[k],b[k],comma);
  for(unsigned k=0;k<6;k++)MatProbeValue(out,std::string("sigma_rate.")+component[k],r[k],comma);
  for(unsigned k=0;k<6;k++)MatProbeValue(out,std::string("actual_half_sigma.")+component[k],a[k],comma);
  for(unsigned k=0;k<6;k++)MatProbeValue(out,std::string("shadow_expected_sigma.")+component[k],e[k],comma);
  MatProbeValue(out,"actual_Pre_kappa_array_old",actual_old_kappa,comma);
  MatProbeValue(out,"shadow_old_kappa",shadow.old_kappa,comma);MatProbeValue(out,"shadow_returned_kappa",shadow.new_kappa,comma);
  MatProbeValue(out,"shadow_qtrial",shadow.qtrial,comma);MatProbeValue(out,"shadow_qreturn",shadow.qreturn,comma);
  MatProbeValue(out,"shadow_gamma",shadow.gamma.v,comma);MatProbeValue(out,"shadow_root_ratio",shadow.root_ratio,comma);
  for(unsigned k=0;k<4;k++)MatProbeValue(out,"failure_reported_value_"+std::to_string(k),f.value[k],comma);
  out<<"\n  ]\n}\n";out.flush();Need(bool(out),"failure-only material raw write failed");
}
'''

CHECK = r'''
  try{p.ErrorNow();}
  catch(const std::exception& original){
    if(!corrector&&p.latest.error==MaterialMismatch){
      try{CapturePreMismatch(p,np,id,sigma,kappa,diagnostic_base,diagnostic_rate,diagnostic_dir,original.what());}
      catch(const std::exception& dump){std::ostringstream note;note<<"\nPrivate HG matprobe capture failed: "<<dump.what()
        <<"; original strict first error retained: "<<original.what()<<"\n";const std::string text=note.str();std::fwrite(text.data(),1,text.size(),stderr);}
    }
    throw;
  }
'''


def verify(entries):
    need(all(stat(q['path']) == q for q in entries), 'Frozen input/program/source/object changed')


def context():
    b = read(BASE)
    need(b['passed'] and b['configuration'] == 'Release' and b['consumed_stats_unchanged']
         and b['retained_original_objects'] == 112 and b['private_objects'] == 2 and b['actual_link_objects'] == 114
         and b['original_physical_CUDA_objects_retained'] and not b['public_source_changed']
         and not b['class_or_CTE_layout_changed'] and b['operator'] == 'EnergyNormalizedAdjointLoadingOnly'
         and b['xi'] == .1 and b['policy_schema'] == 1 and not b['Debug_first_n_snapshot_macro_enabled'],
         'Actual unchanged private HG Release114-object parent required')
    source = read(bind(b['source_capture'])['path'])
    need(source['passed'] and source['prepared_only'] and source['exact_reverse_original_host_bytes']
         and source['private_sources'] == b['private_sources'], 'Original frozen private source capture required')
    failed = read(FAILURE);call = read(bind(failed['actual_call'])['path']);audit = read(AUDIT)
    need(not failed['passed'] and not failed['solver_completed'] and failed['solver_invocations'] == 1
         and failed['actual_exit'] == failed['actual_Win32_exit'] == failed['actual_tool_exit'] == 1
         and failed['ownership_failure'] is None and failed['consumed_stats_unchanged']
         and failed['program'] == b['program'] and call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 1
         and call['ownership_failure'] is None and audit['audit_completed']
         and audit['reported_phase'] == 'PreMaterial' and audit['reported_stage_start_step'] == 2000731
         and audit['actual_returned_kappa_not_observed'] and audit['reported_failure_clock_is_not_saved_state'],
         'Genuine retained first Pre shadow mismatch required; not a completed solver retry')
    before = gates.implementation_gates() + [stat(q) for q in (SCRIPT, NOTE, Path(old.__file__), Path(gates.__file__),
        T/'support/c08_h18_hg_gpu_jobs_r1.py', BASE, FAILURE, AUDIT)]
    before += [bind(b[key]) for key in ('program', 'source_capture', 'source_archive', 'baseline_source_capture')]
    before += [bind(q) for q in b['private_sources'].values()]
    before += [bind(failed[key]) for key in ('actual_call', 'console_log', 'source_pre_file', 'source_run', 'source_native', 'input_xml', 'planned_steps')]
    return b, source, before


def changed(data, edits, name):
    result, proof = data, []
    for label, original, replacement in edits:
        need(result.count(original) == 1, 'Unique '+name+' anchor differs: '+label)
        result = result.replace(original, replacement, 1)
        proof.append(dict(label=label, original=original.decode(), replacement=replacement.decode(), matches=1))
    reverse = result
    for _, original, replacement in reversed(edits):
        need(reverse.count(replacement) == 1, 'Reverse '+name+' anchor ambiguous')
        reverse = reverse.replace(replacement, original, 1)
    need(reverse == data, 'Unexpected '+name+' source modification')
    return result, proof


def derive(b):
    source = {key: Path(bind(value)['path']).read_bytes() for key, value in b['private_sources'].items()}
    def text(value, data):
        newline = b'\r\n' if b'\r\n' in data else b'\n'
        return value.replace('\r\n','\n').replace('\n',newline.decode()).encode('utf-8')
    api = 'const tsymatrix3d* sigma,const float* kappa,bool corrector'
    extended = api+',const tsymatrix3d* diagnostic_base,const tsymatrix3f* diagnostic_rate,const std::string& diagnostic_dir'
    header, hp = changed(source['header'], [
        ('private failure context',api.encode()+b');',extended.encode()+b');'),
        ('host failure logging declaration',b'#include <string>',b'#include <string>'+text('\n#include <cstdio>',source['header']))], 'header')
    pre = b'C08HgState->CheckMaterial(Np,Npb,Idpg,Codeg,Sigmag,Kplasticg,false);'
    cor = b'C08HgState->CheckMaterial(Np,Npb,Idpg,Codeg,Sigmag,Kplasticg,true);'
    host, pp = changed(source['host'], [
        ('Pre live base/rate only',pre,pre.replace(b'false);',b'false,SigmaPreg,Rsigmag,DirOut);')),
        ('Corr no dead base access',cor,cor.replace(b'true);',b'true,NULL,NULL,DirOut);'))], 'host')
    signature = b'const tsymatrix3d* sigma,const float* kappa,bool corrector){'
    oldline = b'CheckMaterialKernel<<<(Nodes+Block-1)/Block,Block>>>(np,id,p.map,sigma,kappa,corrector,p.node,p.failure);Cuda(cudaGetLastError(),"actual material bit check launch");p.ErrorNow();'
    newprefix = oldline[:-len(b'p.ErrorNow();')]
    insertion = b'} // anonymous namespace'
    cuda, cp = changed(source['CUDA'], [
        ('host-only API signature',signature,extended.encode()+b'){'),
        ('host-only failure capture definitions',insertion,text(CAPTURE,source['CUDA'])+insertion),
        ('preserve original rejection around failure I/O',oldline,newprefix+text(CHECK,source['CUDA']))], 'CUDA')
    marker = b'void Need(bool b,const std::string& s)'
    before = source['CUDA'].split(marker,1)[0]
    after = cuda.split(marker,1)[0]
    need(len(before)>10000 and before == after, 'All original device definitions/prefix must remain exact')
    need(cuda.count(b'__global__') == source['CUDA'].count(b'__global__')
         and cuda.count(b'__device__') == source['CUDA'].count(b'__device__'), 'No new/edited device function is admitted')
    return dict(host=host,CUDA=cuda,header=header),dict(host=pp,CUDA=cp,header=hp),len(before)


def prepare():
    need(not CAP.exists() and not PREP.exists(), 'Existing complete/partial preparation protected')
    b, _, before = context()
    sources, proof, prefix_bytes = derive(b)
    verify(before);CAP.mkdir();files={}
    for key, data in sources.items():
        path = CAP / Path(b['private_sources'][key]['path']).name
        with path.open('xb') as f:f.write(data)
        files[key]=stat(path)
    diffs={}
    for key in sources:
        original=Path(b['private_sources'][key]['path']).read_text(encoding='utf-8')
        path=CAP/(key+'.diff')
        with path.open('x',encoding='utf-8',newline='')as f:f.write(''.join(difflib.unified_diff(original.splitlines(True),sources[key].decode().splitlines(True),fromfile='passed_HG/'+key,tofile=TAG+'/'+key)))
        diffs[key]=stat(path)
    verify(before)
    capture=CAP/'source.json'
    save(capture,dict(stage=TAG+'.source',passed=True,prepared_only=True,parent_build=stat(BASE),parent_source_capture=b['source_capture'],
        source_archive=b['source_archive'],baseline_source_capture=b['baseline_source_capture'],private_sources=files,proof=proof,diffs=diffs,
        exact_reverse_parent_sources=True,original_device_prefix_bytes=prefix_bytes,original_device_prefix_byte_identical=True,
        NodeKernel_numeric_body_unchanged=True,new_device_functions=0,new_kernels=0,public_source_changed=False,
        public_class_or_CTE_layout_changed=False,private_API_failure_context_only=True,Pre_only_capture=True,Corr_capture=False,
        actual_returned_kappa_observed=False,actual_material_status_observed=False,strict_material_bit_guard_unchanged=True,
        normal_path_new_CUDA_reads=0,solver_invocations=0,reader_invocations=0,physical_acceptance=False))
    save(PREP,dict(stage=TAG+'.prepare',passed=True,prepared_only=True,source_capture=stat(capture),private_sources=files,
        parent_build=stat(BASE),failure_audit=stat(AUDIT),consumed=before,consumed_stats_unchanged=True,
        compiler_invocations=0,solver_invocations=0,reader_invocations=0,queue_invocations=0,SHA_scans=0,physical_acceptance=False))


def environment():
    q=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    need(q.returncode==0,'Original MSVC environment unavailable')
    env={k.upper():v for k,v in os.environ.items()}
    env.update((k.upper(),v)for k,v in (line.split('=',1)for line in q.stdout.decode('mbcs').splitlines()if '='in line and not line.startswith('=')))
    need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 ABI required')
    for key in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key,None)
    return env


def tool(label, argv, cwd, env, calls):
    path=L/(TAG+'.'+label+'.call.json')
    try:return invoke(TAG+'.'+label,argv,cwd,env)
    finally:
        if path.exists():calls.append(stat(path))


def build():
    intdir=Path(os.environ['TEMP'])/TAG/'Release'
    need(' 'not in str(intdir.resolve())and not OUT.exists()and not intdir.exists()and not BUILD.exists()
         and all(not(L/(TAG+'.'+label+suffix)).exists()for label in ('host_compile','cuda_compile','link')for suffix in ('.call.json','.log')),
         'Fresh private build/IntDir/receipts required')
    before,calls=[],[]
    try:
        b,_,before=context();prep=read(PREP);capture=read(bind(prep['source_capture'])['path'])
        need(prep['passed']and prep['consumed_stats_unchanged']and capture['passed']and capture['prepared_only']
             and capture['parent_build']==stat(BASE)and capture['exact_reverse_parent_sources']
             and capture['original_device_prefix_byte_identical']and capture['NodeKernel_numeric_body_unchanged']
             and capture['new_kernels']==capture['new_device_functions']==0,'Reviewed failure-only source preparation required')
        before += [stat(PREP),bind(prep['source_capture'])]+[bind(q)for q in capture['private_sources'].values()]+[bind(q)for q in capture['diffs'].values()]
        derived,_,prefix=derive(b)
        need(prefix==capture['original_device_prefix_bytes']and all(Path(bind(capture['private_sources'][k])['path']).read_bytes()==derived[k]for k in derived),
             'Prepared source no longer equals the exact reversible derivation')
        recipes=[read(bind(q)['path'])for q in b['calls']]
        need(len(recipes)==3 and all(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure']is None for q in recipes),
             'Three actual passed parent CL/NVCC/link calls required')
        before += [bind(q)for q in b['calls']]+[stat(q['program'])for q in recipes]
        retained=[bind(q)for q in b['retained_object_stats']]
        oldprivate=[bind(q)for q in b['new_private_objects']]
        need(len(retained)==112 and len(oldprivate)==2 and len({Path(q['path']).resolve()for q in retained})==112,
             'Original112 plus two parent private objects required')
        before += retained+oldprivate+[bind(q)for q in b['runtime']]
        verify(before);OUT.mkdir();intdir.mkdir(parents=True)
        oldroot=Path(b['OutDir'])/'frozen';newroot=OUT/'frozen';frozen=[]
        names={Path(q['path']).name:k for k,q in capture['private_sources'].items()}
        for entry in b['frozen_sources']:
            before.append(bind(entry));source=Path(entry['path']);relative=source.relative_to(oldroot)
            dest=newroot/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            data=derived[names[source.name]]if source.name in names else source.read_bytes()
            with dest.open('xb')as f:f.write(data)
            frozen.append(stat(dest))
        frozen_root=newroot/'src/source'
        need(all((frozen_root/Path(q['path']).name).read_bytes()==derived[k]for k,q in capture['private_sources'].items()),
             'Fresh full frozen header/source closure differs')
        before += frozen
        oldout,oldint=str(Path(b['OutDir'])),str(Path(b['IntDir']))
        def relocated(args):return[q.replace(oldout,str(OUT)).replace(oldint,str(intdir))for q in args]
        clargs,cuargs,linkargs=[relocated(q['arguments'])for q in recipes]
        objects=[Path(q).resolve()for q in linkargs if q.lower().endswith('.obj')]
        newprivate=[intdir/Path(q['path']).name for q in oldprivate]
        need(len(objects)==len(set(objects))==114 and set(objects)=={Path(q['path']).resolve()for q in retained}|{q.resolve()for q in newprivate},
             'Exactly112 original plus two new private link objects required')
        need(clargs.count('/I'+str(frozen_root))==1 and clargs.count(str(frozen_root/'JSphGpuSingle.cpp'))==1
             and all(q in clargs for q in ('/O2','/MT','/fp:precise','/openmp'))and cuargs.count('-I'+str(frozen_root))==1
             and cuargs.count(str(frozen_root/'c08_h18_hg_gpu_r1.cu'))==1 and '-use_fast_math'in cuargs
             and not any('fmad'in q.lower()or 'C08_HG_DEBUG_SNAPSHOT'in q or 'rdc=true'in q for q in cuargs),
             'Original Release host/CUDA arithmetic flags and independent private paths required')
        for arg in linkargs:
            for flag in ('/out:','/pdb:','/implib:','/ltcgout:','/ilk:','/map:','/manifestfile:','/pgd:','/tlbout:','/winmdfile:'):
                if arg.lower().startswith(flag):
                    dest=Path(arg[len(flag):]).resolve()
                    need(dest.is_relative_to(OUT.resolve())or dest.is_relative_to(intdir.resolve()),'Link output escaped isolated private paths')
        need(all(oldout not in q and oldint not in q for args in (clargs,cuargs,linkargs)for q in args),'Old build output path retained in new tool arguments')
        env=environment();cudaenv=dict(env);ccbin=Path(cuargs[cuargs.index('-ccbin')+1])
        cudaenv['PATH']=str(ccbin)+os.pathsep+env.get('PATH','')
        verify(before)
        tool('host_compile',[recipes[0]['program'],*clargs],intdir,env,calls)
        tool('cuda_compile',[recipes[1]['program'],*cuargs],intdir,cudaenv,calls)
        tool('link',[recipes[2]['program'],*linkargs],Path(recipes[2]['cwd']),env,calls)
        deps=read(intdir/'host.dependencies.json')['Data'];includes={Path(q).resolve()for q in deps['Includes']}
        need(Path(deps['Source']).resolve()==(frozen_root/'JSphGpuSingle.cpp').resolve()
             and all((frozen_root/name).resolve()in includes for name in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','c08_h18_hg_gpu_r1.hpp')),
             'New host consumed another header/API closure')
        runtime=[]
        for q in b['runtime']:
            source=Path(q['path']);dest=OUT/source.name;need(not dest.exists(),'Private runtime destination exists')
            shutil.copy2(source,dest);v=stat(dest)
            need((v['bytes'],v['mtime_ns'])==(q['bytes'],q['mtime_ns'])and dest.read_bytes()==source.read_bytes(),'Runtime copy differs')
            runtime.append(v)
        program=OUT/Path(b['program']['path']).name;verify(before)
        warnings=[line for entry in calls for line in Path(read(entry['path'])['log']['path']).read_bytes().decode('mbcs',errors='replace').splitlines()if re.search(r'\bwarning\b',line,re.I)]
        save(BUILD,dict(stage=TAG+'.build',passed=True,configuration='Release',program=stat(program),parent_HG_build=stat(BASE),
            parent_program=b['program'],source_capture=stat(CAP/'source.json'),source_archive=b['source_archive'],
            baseline_source_capture=b['baseline_source_capture'],private_sources=capture['private_sources'],frozen_sources=frozen,
            retained_original_objects=112,private_objects=2,actual_link_objects=114,retained_object_stats=retained,
            new_private_objects=[stat(q)for q in newprivate],actual_link_inputs=[str(q)for q in objects],runtime=runtime,
            IntDir=str(intdir),OutDir=str(OUT),calls=calls,original_physical_CUDA_objects_retained=True,
            original_device_prefix_byte_identical=True,original_device_prefix_bytes=prefix,NodeKernel_numeric_body_unchanged=True,
            Release_arithmetic_flags_unchanged=True,private_API_failure_context_only=True,new_kernels=0,new_device_functions=0,
            strict_material_bit_guard_unchanged=True,Pre_only_capture=True,Corr_capture=False,
            actual_returned_kappa_observed=False,actual_material_status_observed=False,normal_path_new_CUDA_reads=0,
            warning_lines=warnings,
            public_source_changed=False,public_class_or_CTE_layout_changed=False,compile_invocations=2,link_invocations=1,
            solver_invocations=0,reader_invocations=0,queue_invocations=0,help_invocations=0,GPU_program_invocations=0,
            SHA_scans=0,consumed=before,consumed_stats_unchanged=True,physical_acceptance=False,automatic_next_job=False))
    except Exception as error:
        if not BUILD.exists():save(BUILD,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,
            partial_outputs_preserved=True,solver_invocations=0,reader_invocations=0,queue_invocations=0,SHA_scans=0,physical_acceptance=False))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('prepare','build'))
    parser.add_argument('--execution-authorized',action='store_true')
    args=parser.parse_args();need(args.execution_authorized,'Independent root review/prepare/build authorization required')
    if args.phase=='prepare':prepare()
    else:build()
