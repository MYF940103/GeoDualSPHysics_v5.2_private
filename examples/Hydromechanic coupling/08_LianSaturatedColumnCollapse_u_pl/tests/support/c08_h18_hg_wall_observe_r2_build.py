"""Author-only private failure observations: one original CUDA TU and link per GPU configuration."""
import argparse
import ctypes
import difflib
import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T, C, L = m.T, m.C, m.L
S = T.parents[3] / 'src'
TAG = 'c08_h18_hg_wall_observe_r2'
SCRIPT = Path(__file__).resolve()
NOTE = T / 'notes' / (TAG + '.md')
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
PRE = T / 'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'

# Included inside namespace cusph, after the existing field reader. All new
# calculations/loops below are reached only through an original rejection branch.
HELPER = r'''
// Private failure-only observations; no numerical state is assigned here.
template<TpKernel tker,unsigned stage> __device__ __noinline__ void C08HgWallFailure(
  unsigned reason,bool incomplete,unsigned p1,int scelldiv,int4 nc,int3 cellzero,
  const int2* fluidcells,const double2* posxy,const double* posz,const typecode* code,
  const float3* boundnormal,const byte* boundmode,const double* j,const tmatrix3d* corrmat,
  const float4* poscell,double solid0,double3 gp,bool retried,double shiftx,double shiftz,
  double sumwab,double submerged,float threshold,const tmatrix3d& moment,
  double nearest2,double nearx,double nearz,const double* fitted)
{
  const float3 bn=boundnormal[p1];
  printf("C08_HG_WALL_OBS reason=%u incomplete_M=%u stage=%u slot=%u B=(%.17g,%.17g,%.17g) normal=(%.9g,%.9g,%.9g) boundmode=%u receiver_J=%.17g solid0=%.17g\n",
    reason,unsigned(incomplete),stage,p1,posxy[p1].x,posxy[p1].y,posz[p1],bn.x,bn.y,bn.z,unsigned(boundmode[p1]),j[p1],solid0);
  printf("C08_HG_WALL_OBS_FIT reason=%u stage=%u slot=%u attempt=%u G=(%.17g,%.17g,%.17g) shift=(%.17g,%.17g) sumWV=%.17g submerged=%.17g threshold=%.9g nearest2=%.17g near=(%.17g,%.17g)\n",
    reason,stage,p1,unsigned(retried),gp.x,gp.y,gp.z,shiftx,shiftz,sumwab,submerged,double(threshold),nearest2,nearx,nearz);
  printf("C08_HG_WALL_OBS_M reason=%u stage=%u slot=%u incomplete_M=%u M=(%.17g,%.17g,%.17g;%.17g,%.17g,%.17g;%.17g,%.17g,%.17g) detM=%.17g active=%u\n",
    reason,stage,p1,unsigned(incomplete),moment.a11,moment.a12,moment.a13,moment.a21,moment.a22,moment.a23,moment.a31,moment.a32,moment.a33,
    cumath::Determinant3x3(moment),unsigned(submerged>0 || sumwab>=double(threshold) || (threshold>=2 && sumwab+2>=double(threshold))));
  if(stage==1 && fitted){
    printf("C08_HG_WALL_OBS_RAW_C reason=%u stage=%u slot=%u raw_fitted_C=(%.17g,%.17g,%.17g;%.17g,%.17g,%.17g;%.17g,%.17g,%.17g) detXZ=%.17g asymXZ=%.17g\n",
      reason,stage,p1,fitted[0],fitted[1],fitted[2],fitted[3],fitted[4],fitted[5],fitted[6],fitted[7],fitted[8],
      fitted[0]*fitted[8]-fitted[2]*fitted[6],fitted[2]-fitted[6]);
  }
  // Exact stored physical wall from the original failed call, not a fitted range.
  // This is an observation selector only. The kernel's participation is unchanged.
  if(!(stage==1 && posxy[p1].x==4.9000000000000004 && posxy[p1].y==0.
       && posz[p1]==-0.019999999999999962))return;
  unsigned donors=0,observed_nearest_slot=~0u;double observed_nearest2=DBL_MAX;
  int i1,f1,i2,f2,i3,f3;
  cunsearch::InitCte(gp.x,gp.y,gp.z,scelldiv,nc,cellzero,i1,f1,i2,f2,i3,f3);
  for(int c3=i3;c3<f3;c3+=nc.w)for(int c2=i2;c2<f2;c2+=nc.x){
    unsigned begin,end=0;cunsearch::ParticleRange(c2,c3,i1,f1,fluidcells,begin,end);
    if(end)for(unsigned p2=begin;p2<end;p2++)if(CODE_IsFluid(code[p2])){
      const double dx=gp.x-posxy[p2].x,dz=gp.z-posz[p2];const float rr2=float(dx*dx+dz*dz);
      if(rr2<=CTE.kernelsize2){
        float fac;const double wab=(rr2==0? (fac=0.f,double(cufsph::GetKernel_Wab<tker>(rr2))): double(cufsph::GetKernel_WabFac<tker>(rr2,fac)));
        const double vol=double(CTE.massf)/double(CTE.rhopzero)*j[p2];const double distance2=dx*dx+dz*dz;
        if(distance2<observed_nearest2){observed_nearest2=distance2;observed_nearest_slot=p2;}
        const tmatrix3d c=corrmat[p2];
        printf("C08_HG_WALL_OBS_DONOR reason=%u stage=%u wall_slot=%u index=%u donor_slot=%u code=%u X=(%.17g,%.17g,%.17g) J=%.17g J_valid=%u dx=%.17g dz=%.17g rr2_float=%.9g\n",
          reason,stage,p1,donors,p2,unsigned(code[p2]),posxy[p2].x,posxy[p2].y,posz[p2],j[p2],unsigned(isfinite(j[p2])&&j[p2]>solid0),dx,dz,double(rr2));
        printf("C08_HG_WALL_OBS_DONOR_C reason=%u stage=%u wall_slot=%u donor_slot=%u C=(%.17g,%.17g,%.17g;%.17g,%.17g,%.17g;%.17g,%.17g,%.17g) detXZ=%.17g asymXZ=%.17g\n",
          reason,stage,p1,p2,c.a11,c.a12,c.a13,c.a21,c.a22,c.a23,c.a31,c.a32,c.a33,c.a11*c.a33-c.a13*c.a31,c.a13-c.a31);
        printf("C08_HG_WALL_OBS_DONOR_W reason=%u stage=%u wall_slot=%u donor_slot=%u W=%.17g fac=%.9g V=%.17g WV=%.17g gradWV=(%.17g,%.17g)\n",
          reason,stage,p1,p2,wab,double(fac),vol,wab*vol,double(fac)*dx*vol,double(fac)*dz*vol);
        donors++;
      }
    }
  }
  printf("C08_HG_WALL_OBS_DONORS_END reason=%u stage=%u wall_slot=%u donors=%u observed_nearest_slot=%u observed_nearest2=%.17g input_nearest2=%.17g\n",
    reason,stage,p1,donors,observed_nearest_slot,observed_nearest2,nearest2);
  // Independently observe the current physical-B union used by stage0. This does
  // not rerun/reassign boundmode, and counts every candidate rather than early-out.
  unsigned candidates=0,inside_double=0,inside_fsfloat=0,inside_forcefloat=0,inside_union=0;
  double min_double=DBL_MAX;float min_fs=FLT_MAX,min_force=FLT_MAX;
  cunsearch::InitCte(posxy[p1].x,posxy[p1].y,posz[p1],scelldiv,nc,cellzero,i1,f1,i2,f2,i3,f3);
  for(int c3=i3;c3<f3;c3+=nc.w)for(int c2=i2;c2<f2;c2+=nc.x){
    unsigned begin,end=0;cunsearch::ParticleRange(c2,c3,i1,f1,fluidcells,begin,end);
    if(end)for(unsigned p2=begin;p2<end;p2++)if(CODE_IsFluid(code[p2])){
      candidates++;const double dx=posxy[p1].x-posxy[p2].x,dz=posz[p1]-posz[p2],rr=dx*dx+dz*dz;
      if(rr<min_double)min_double=rr;const bool a=rr<=double(CTE.kernelsize2)&&rr>=ALMOSTZERO;inside_double+=unsigned(a);
      bool b=false,c=false;
      if(poscell){const float4 p=poscell[p1],q=poscell[p2];
        const float x=p.x-q.x+CTE.poscellsize*(PSCEL_GetfX(p.w)-PSCEL_GetfX(q.w));
        const float y=p.y-q.y+CTE.poscellsize*(PSCEL_GetfY(p.w)-PSCEL_GetfY(q.w));
        const float z=p.z-q.z+CTE.poscellsize*(PSCEL_GetfZ(p.w)-PSCEL_GetfZ(q.w));
        const float rf=x*x+z*z,rg=x*x+y*y+z*z;if(rf<min_fs)min_fs=rf;if(rg<min_force)min_force=rg;
        b=rf<=CTE.kernelsize2&&rf>=ALMOSTZERO;c=rg<=CTE.kernelsize2&&rg>=ALMOSTZERO;
      }
      inside_fsfloat+=unsigned(b);inside_forcefloat+=unsigned(c);inside_union+=unsigned(a||b||c);
    }
  }
  printf("C08_HG_WALL_OBS_B reason=%u stage=%u slot=%u boundmode=%u candidates=%u inside_double=%u inside_fsfloat=%u inside_forcefloat=%u inside_union=%u min_r2=(%.17g,%.9g,%.9g) cutoff2=%.9g poscell_present=%u\n",
    reason,stage,p1,unsigned(boundmode[p1]),candidates,inside_double,inside_fsfloat,inside_forcefloat,inside_union,min_double,double(min_fs),double(min_force),double(CTE.kernelsize2),unsigned(poscell!=NULL));
}
'''


def windows_args(line):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW('tool.exe ' + line, ctypes.byref(count))
    m.need(bool(pointer), 'Cannot parse original Windows project command')
    try:
        return [pointer[i] for i in range(1, count.value)]
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes, free.restype = [ctypes.c_void_p], ctypes.c_void_p
        free(ctypes.cast(pointer, ctypes.c_void_p))


def private_source(raw):
    cu_name, wall_name = 'JSphGpu_ker.cu', 'JSphGpu_mdbc_ker.cuh'
    text = {key: raw[key].decode('utf-8') for key in (cu_name, wall_name)}
    nl = '\r\n' if '\r\n' in text[wall_name] else '\n'
    m.need(('\r\n' in text[cu_name]) == ('\r\n' in text[wall_name]), 'Frozen source newline styles differ')
    atomic = 'atomicMin(invalid,p1);return;'
    common = ('p1,scelldiv,nc,cellzero,fluidcells,posxy,posz,code,boundnormal,boundmode,j,corrmat,poscell,solid0,'
              'gp,retried,fitshiftx,fitshiftz,sumwab,submerged,threshold,moment,nearest2,nearx,nearz,')

    def observe(reason, incomplete=False, fitted='NULL'):
        return 'C08HgWallFailure<tker,stage>(' + str(reason) + ',' + ('true' if incomplete else 'false') + ',' + common + fitted + ');'

    receiver = 'if(!CODE_IsFixed(code[p1]) || !isfinite(r2) || !(r2>0)){' + atomic + '}'
    donor = 'if(!isfinite(j[p2]) || j[p2]<=solid0){' + atomic + '}'
    geometry = '    ' + atomic + nl + '  }' + nl + '  const tmatrix3d inv=cumath::InverseMatrix3x3(moment,det);'
    finite = 'if(!isfinite(v[c])){' + atomic + '}'
    domain = '|| !isfinite(tv.x) || !isfinite(tv.y) || !isfinite(tv.z)){' + atomic + '}'
    orientation = 'if(!isfinite(determinant) || determinant<=0){' + atomic + '}'
    acceleration = 'if(!isfinite(a.x) || !isfinite(a.y) || !isfinite(a.z)){' + atomic + '}'
    hooks = [
        (receiver, 'printf("C08_HG_WALL_OBS reason=1 incomplete_M=1 stage=%u slot=%u B=(%.17g,%.17g,%.17g) normal=(%.9g,%.9g,%.9g) code=%u fixed=%u normal_r2=%.17g\\n",stage,p1,posxy[p1].x,posxy[p1].y,posz[p1],bn.x,bn.y,bn.z,unsigned(code[p1]),unsigned(CODE_IsFixed(code[p1])),r2);'),
        (donor, 'printf("C08_HG_WALL_OBS_RAW_J stage=%u slot=%u donor_slot=%u J=%.17g solid0=%.17g\\n",stage,p1,p2,j[p2],solid0);' + observe(2, True)),
        (geometry, observe(3)),
        (finite, 'printf("C08_HG_WALL_OBS_FIELD stage=%u slot=%u field=%u value=%.17g nearest=%.17g sum=%.17g grad=(%.17g,%.17g)\\n",stage,p1,c,v[c],nearest[c],sum[c],gradx,gradz);' + observe(4)),
        (domain, 'printf("C08_HG_WALL_OBS_DOMAIN stage=%u slot=%u J=%.17g pressure=%.17g dv=(%.9g,%.9g,%.9g) tv=(%.9g,%.9g,%.9g)\\n",stage,p1,v[0],pressure,dv.x,dv.y,dv.z,tv.x,tv.y,tv.z);' + observe(5)),
        (orientation, 'printf("C08_HG_WALL_OBS_C stage=%u slot=%u C=(%.17g,%.17g,%.17g;%.17g,%.17g,%.17g;%.17g,%.17g,%.17g) actual_detXZ=%.17g asymXZ=%.17g\\n",stage,p1,m.a11,m.a12,m.a13,m.a21,m.a22,m.a23,m.a31,m.a32,m.a33,determinant,m.a13-m.a31);' + observe(6, fitted='v')),
        (acceleration, 'printf("C08_HG_WALL_OBS_ACE stage=%u slot=%u A=(%.9g,%.9g,%.9g)\\n",stage,p1,a.x,a.y,a.z);' + observe(7)),
    ]
    anchor = 'template<TpKernel tker,unsigned stage> __global__ void KerDynamicPoreWall('
    edits = [(cu_name, '#include <cfloat>', '#include <stdio.h>' + nl + '#include <cfloat>'),
             (wall_name, anchor, HELPER.strip().replace('\n', nl) + nl + nl + anchor)]
    for old, extra in hooks:
        m.need(old.count(atomic) == 1, 'Each terminal hook must keep exactly one original reject')
        edits.append((wall_name, old, old.replace(atomic, extra + nl + atomic, 1)))
    proof = []
    for name, old, new in edits:
        m.need(text[name].count(old) == 1 and new not in text[name], 'Unique frozen failure anchor absent')
        text[name] = text[name].replace(old, new, 1)
        proof.append(dict(member=name, original_text=old, replacement_text=new, matches=1))
    inverse = dict(text)
    for name, old, new in reversed(edits):
        m.need(inverse[name].count(new) == 1, 'Inverse hook is not unique')
        inverse[name] = inverse[name].replace(new, old, 1)
    m.need(all(inverse[key].encode('utf-8') == raw[key] for key in text), 'Inverse did not recover every original frozen byte')
    m.need(all(text[key].count(atomic) == raw[key].decode('utf-8').count(atomic) for key in text), 'Original atomicMin/return counts changed')
    # CUDA printf accepts no more than32 arguments after its format. Count the
    # closed literal formats; nested commas occur only in values, never formats.
    formats = re.findall(r'printf\("((?:[^"\\]|\\.)*)"', HELPER + ''.join(extra for _, extra in hooks))
    m.need(formats and all(len(re.findall(r'%(?:\.\d+)?[ug]', form)) <= 32 for form in formats), 'CUDA printf format exceeds32 values')
    return {key: value.encode('utf-8') for key, value in text.items()}, proof


def build(configuration):
    label = TAG + '_' + configuration
    basepath = L / ('c08_h18_hg_opt_' + configuration + '_r1.build.json')
    check, admission = L / (label + '.build.json'), L / (label + '.root_build_admission.json')
    cap, out = T / 'outputs' / (label + '_source'), T / 'outputs' / (label + '_build')
    intdir = Path(os.environ['TEMP']) / TAG / configuration
    m.need(' ' not in str(intdir) and not intdir.exists() and not cap.exists() and not out.exists()
           and all(not (L / (label + suffix)).exists() for suffix in
                   ('.build.json', '.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
           'Existing complete/partial build protected; no retry')
    before, calls = [], []
    try:
        ad = m.read(admission)
        m.need(ad['authorized'] and ad['configuration'] == configuration and ad['allowed_stage'] == label
               and ad['execution_script'] == m.stat(SCRIPT) and ad['note'] == m.stat(NOTE)
               and ad['source_build'] == m.stat(basepath)
               and ad['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD
               and ad['build_only'] and not ad['automatic_solver'] and not ad['automatic_reader'],
               'Separate exact current-root build-only admission required')
        b = m.read(basepath)
        m.need(b['passed'] and b['configuration'] == configuration and b['consumed_stats_unchanged']
               and b['actual_link_objects'] == 114 and b['retained_original_objects'] == 111
               and b['private_objects'] == 3 and b['optimization_scope'] == 'block_error_snapshot_and_summary_reuse'
               and b['NodeKernel_source_bytes_exact'] and not b['public_source_changed'],
               'Actual frozen optimized114-object build required')
        before = [m.stat(q) for q in (SCRIPT, NOTE, admission, basepath)]
        before += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive', 'baseline_source_capture',
                                             'base_cached_source_capture', 'original_CUDA_recipe_log')]
        before += [m.bind(q) for q in b['private_sources'].values()]
        before += [m.bind(q) for q in b['runtime'] + b['frozen_sources']]
        before.append(m.stat(PRE))
        for entry in b['calls']:
            before.append(m.bind(entry)); actual = m.read(entry['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0
                   and actual['ownership_failure'] is None, 'Actual original optimized compile/link exit required')
        original_link = m.read(b['calls'][-1]['path'])
        actual_link_argv = original_link['child']['argv']
        m.need(actual_link_argv == [original_link['program'], *original_link['arguments']], 'Original actual link argv differs')
        link, link_args = Path(actual_link_argv[0]), actual_link_argv[1:]
        objects = [Path(q).resolve() for q in link_args if q.lower().endswith('.obj')]
        m.need(objects == [Path(q).resolve() for q in b['actual_link_inputs']] and len(set(objects)) == 114,
               'Exact original optimized link ordering and114 unique objects required')
        replaced = [q for q in objects if q.name.lower() == 'jsphgpu_ker.cu.obj']
        private = {Path(q['path']).resolve() for q in b['new_private_objects']}
        m.need(len(replaced) == 1 and len(private) == 3 and private.issubset(objects) and replaced[0] not in private,
               'Exactly one original physicalCUDA object replacement required')
        retained = [q for q in objects if q != replaced[0]]
        m.need(len(retained) == 113 and len(set(retained) - private) == 110, 'Required110 original+3private retained closure differs')
        before += [m.stat(q) for q in objects]
        original_log = Path(b['original_CUDA_recipe_log']['path'])
        nvcc_lines = [q.split(b'>', 1)[1].strip().decode('ascii') for q in original_log.read_bytes().splitlines()
                      if b'nvcc.exe' in q.lower() and b'jsphgpu_ker.cu' in q.lower()]
        m.need(len(nvcc_lines) == 1, 'One original physical NVCC command required')
        original_compile = windows_args(nvcc_lines[0]); nvcc = Path(original_compile[0]); compile_args = list(original_compile[1:])
        m.need(compile_args.count('-o') == compile_args.count('--keep-dir') == compile_args.count('-ccbin') == 1
               and sum(Path(q).name.lower() == 'jsphgpu_ker.cu' for q in compile_args) == 1,
               'Original physical source/output/host/keep recipe differs')
        m.need(all(q in compile_args for q in ('--compile', '--machine', '64', '-cudart', 'static', '-use_fast_math', '-D_WITHGPU'))
               and any('compute_86' in q and 'sm_86' in q for q in compile_args)
               and not any('C08_STAGE_TRACE' in q or 'C08_CAUSAL_TRACE' in q or 'rdc=true' in q or q in ('-dc', '--device-link') for q in compile_args),
               'Original macro-off CUDA11.7/sm86/fast-math recipe required')
        old_frozen = Path(b['OutDir']) / 'frozen'
        frozen = out / 'frozen'; physical = frozen / 'src/source'
        m.need(all(Path(q['path']).resolve().is_relative_to(old_frozen.resolve()) for q in b['frozen_sources']), 'Original frozen source leaves its declared root')
        raw = {name: (old_frozen / 'src/source' / name).read_bytes() for name in ('JSphGpu_ker.cu', 'JSphGpu_mdbc_ker.cuh')}
        modified, proof = private_source(raw)
        m.verify(before)
        cap.mkdir(); out.mkdir(); intdir.mkdir(parents=True)
        copied_sources = []
        archive = cap / 'source.zip'
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for entry in b['frozen_sources']:
                origin = Path(entry['path']); rel = origin.relative_to(old_frozen); target = frozen / rel
                m.need(not rel.is_absolute() and '..' not in rel.parts and not target.exists(), 'Private frozen leaf is invalid or already exists')
                data = modified.get(origin.name, origin.read_bytes()) if rel.parent.as_posix() == 'src/source' else origin.read_bytes()
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
                m.need(target.read_bytes() == data, 'Private frozen copy differs')
                z.writestr(rel.as_posix(), data); copied_sources.append(m.stat(target))
        diff = cap / 'failure_only.diff'
        diff.write_text(''.join(''.join(difflib.unified_diff(raw[name].decode('utf-8').splitlines(True), modified[name].decode('utf-8').splitlines(True),
            fromfile='actual_opt/' + name, tofile='private_failure_observer/' + name)) for name in raw), encoding='utf-8')
        capture = cap / 'source.json'
        m.save(capture, dict(stage=label + '.source', original_build=m.stat(basepath), original_source_capture=b['source_capture'],
            original_source_archive=b['source_archive'], original_frozen_sources=b['frozen_sources'], archive=m.stat(archive), diff=m.stat(diff),
            modified_members=list(modified), derivation=proof, exact_inverse_original_frozen_bytes=True,
            original_reject_atomicMin_return_counts_unchanged=True, failure_only=True, normal_path_extra_loops=False,
            target_stage=1, target_B=[4.9000000000000004, 0., -.019999999999999962], donor_identity='actual_sorted_slot_no_native_ID_array',
            public_source_changed=False, physical_arithmetic_changed=False, threshold_changed=False, source_files=copied_sources,
            solver_invocations=0, reader_invocations=0, physical_acceptance=False, SHA_scans=0))
        before += [m.stat(capture), m.stat(archive), m.stat(diff), *copied_sources]
        obj = intdir / 'JSphGpu_ker.cu.obj'
        pdb_changes = 0
        for index, arg in enumerate(compile_args):
            if index and compile_args[index - 1] == '-Xcompiler':
                compile_args[index], hits = re.subn(r'(?i)(?<!\S)/Fd[^\s]+', lambda _: '/Fd' + str(intdir / 'physical.pdb'), arg)
                pdb_changes += hits
        m.need(pdb_changes == 1, 'Exactly one original host-PDB token required')
        compile_args[compile_args.index('-o') + 1] = str(obj)
        compile_args[compile_args.index('--keep-dir') + 1] = str(intdir)
        compile_args = [str(physical / 'JSphGpu_ker.cu') if Path(q).name.lower() == 'jsphgpu_ker.cu' else q for q in compile_args]
        compile_args.insert(0, '-I' + str(physical))
        program = out / Path(b['program']['path']).name
        outputs = {'/out:': program, '/pdb:': out / (program.stem + '.pdb'),
                   '/implib:': out / (program.stem + '.lib'), '/ltcgout:': intdir / (program.stem + '.iobj')}
        linked, seen = [], set()
        for arg in link_args:
            if arg.lower().endswith('.obj') and Path(arg).resolve() == replaced[0]: arg = str(obj)
            for prefix, target in outputs.items():
                if arg.lower().startswith(prefix): arg = prefix + str(target); seen.add(prefix); break
            linked.append(arg)
        actual_objects = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        m.need(seen == set(outputs) and actual_objects == [obj.resolve() if q == replaced[0] else q for q in objects]
               and len(set(actual_objects)) == 114, 'Only one ordered physicalCUDA replacement plus113retained is allowed')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'MSVC environment setup failed')
        env = {key.upper(): value for key, value in os.environ.items()}
        env.update((key.upper(), value) for key, value in
                   (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Original MSVC14.36 required')
        # NVCC must find the exact authoritative -ccbin compiler first, even
        # though vcvarsall x64 normally selects the equivalent HostX64 driver.
        ccbin = Path(compile_args[compile_args.index('-ccbin') + 1])
        host_cl = ccbin / 'cl.exe'
        m.need(host_cl.is_file() and '/14.36.32532/' in host_cl.as_posix(), 'Authoritative original NVCC host compiler absent')
        env['PATH'] = str(ccbin) + os.pathsep + env.get('PATH', '')
        resolved_cl = shutil.which('cl.exe', path=env['PATH'])
        m.need(resolved_cl is not None and Path(resolved_cl).resolve() == host_cl.resolve(),
               'Actual PATH cl.exe must equal unchanged original -ccbin/cl.exe')
        before.append(m.stat(host_cl))
        for key in list(env):
            if key.upper() in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'): env.pop(key)
        m.need('CUDA/v11.7' in nvcc.as_posix() and '/14.36.32532/' in link.as_posix(), 'Original CUDA/MSVC tools required')
        before += [m.stat(nvcc), m.stat(link)]
        libdirs = [S / 'VS'] + [(Path(q.split(':', 1)[1]) if Path(q.split(':', 1)[1]).is_absolute()
                   else S / 'VS' / q.split(':', 1)[1]) for q in linked if q.lower().startswith('/libpath:')]
        libdirs += [Path(q) for q in env.get('LIB', '').split(';') if q]
        for arg in linked:
            if arg.lower().endswith('.lib') and not arg.startswith('/'):
                candidates = [Path(arg)] if Path(arg).is_absolute() else [q / arg for q in libdirs]
                library = next((q for q in candidates if q.is_file()), None)
                m.need(library is not None, 'Original explicit library missing: ' + arg); before.append(m.stat(library))
        m.verify(before)
        for phase, argv, cwd in [('compile', [str(nvcc), *compile_args], intdir), ('link', [str(link), *linked], S / 'VS')]:
            entry = m.invoke(label + '.' + phase, argv, cwd, env=env); calls.append(entry); actual = m.read(entry['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
                   'Actual owned compile/link normal exit required')
        runtime = []
        for entry in b['runtime']:
            origin = Path(entry['path']); target = out / origin.name
            m.need(not target.exists(), 'Existing private runtime target protected'); shutil.copy2(origin, target)
            m.need(target.read_bytes() == origin.read_bytes() and m.stat(target)['bytes'] == entry['bytes'], 'Runtime copy differs')
            runtime.append(m.stat(target))
        m.verify(before)
        m.save(check, dict(stage=label + '.build', passed=True, configuration=configuration, program=m.stat(program),
            root_admission=m.stat(admission), original_optimized_build=m.stat(basepath), original_actual_link_call=b['calls'][-1],
            original_source_capture=b['source_capture'], original_source_archive=b['source_archive'], source_capture=m.stat(capture), source_archive=m.stat(archive),
            frozen_sources=copied_sources, source_diff=m.stat(diff), original_NVCC_arguments=original_compile,
            actual_compile_arguments=[str(nvcc), *compile_args], original_link_arguments=actual_link_argv, actual_link_arguments=[str(link), *linked],
            retained_objects=[m.stat(q) for q in retained], original_replaced_physical_object=m.stat(replaced[0]), replacement_physical_object=m.stat(obj),
            retained_original_physical_objects=110, retained_private_host_HG_objects=3, recompiled_physical_CUDA_objects=1,
            actual_link_objects=114, compile_invocations=1, link_invocations=1, calls=calls, runtime=runtime,
            private_HG_Node_and_consumers_recompiled=False, old_optimized_operator_source_unchanged=True,
            failure_only=True, exact_inverse_original_frozen_bytes=True, public_source_changed=False,
            physical_arithmetic_changed=False, threshold_changed=False, normal_path_extra_loops=False,
            target_stage=1, target_B=[4.9000000000000004, 0., -.019999999999999962],
            donor_identity='actual_sorted_slot_no_native_ID_array', incomplete_M_explicit=True,
            consumed=before, consumed_stats_unchanged=True, full_project_builds=0, helper_program_invocations=0,
            smoke_invocations=0, solver_invocations=0, reader_invocations=0, VTK_invocations=0,
            new_binary_no_feedback_not_yet_proven=True, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        if not check.exists():
            actual_calls = [m.stat(L / (label + '.' + phase + '.call.json')) for phase in ('compile', 'link')
                            if (L / (label + '.' + phase + '.call.json')).is_file()]
            m.save(check, dict(stage=label + '.build', passed=False, configuration=configuration, first_failure=str(error),
                calls=actual_calls, consumed=before, partial_artifacts_preserved=True, automatic_retry=False,
                full_project_builds=0, solver_invocations=0, reader_invocations=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', choices=('Debug', 'Release'), required=True)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Author-only until a separate exact root build admission')
    build(args.configuration)
