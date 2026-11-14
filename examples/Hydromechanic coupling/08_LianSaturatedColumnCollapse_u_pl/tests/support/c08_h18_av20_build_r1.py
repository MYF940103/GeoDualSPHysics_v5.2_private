"""Prepare a reversible schema2 AV.2 host overlay, or build one explicitly selected backend only."""
import argparse, datetime, difflib, os, shutil, subprocess, zipfile
from pathlib import Path
import c08_h18_late_rhs_r1_build as qualified

m, T, L, S = qualified.m, qualified.T, qualified.L, qualified.S
parser_tools = qualified.old
TAG = 'c08_h18_av20_build_r1'
NOTE = T/'notes'/(TAG+'.md')
CAP = T/'outputs/c08_h18_av20_source_r1'
BASES = {'DebugCPU': L/'c08_h18_restore_DebugCPU_r1.build.json',
         'Release': L/'c08_preload_schema2_Release_r1.build.json'}
LATE = L/'c08_h18_late_rhs_r1.build.json'
SOURCES = ('JSph.cpp', 'JSphCpuSingle.cpp', 'JSphGpuSingle.cpp')


def key(path):
    return str(Path(path).resolve()).casefold()


def original_context(configuration):
    """Read only the actual original build/tlogs, never current public source files."""
    bp = BASES[configuration]; b = m.read(bp)
    m.need(b['passed'] and b['configuration'] == configuration and b['consumed_stats_unchanged'],
           'Closed original schema2 backend build required')
    call = m.read(m.bind(b['actual_call'])['path'])
    m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
           and call['ownership_failure'] is None
           and '/p:VCToolsVersion=14.36.32532' in call['arguments'], 'Original owned MSVC14.36 build failed')
    roots = [q.split('=', 1)[1] for q in call['arguments'] if q.startswith('/p:IntDir=')]
    m.need(len(roots) == 1, 'One actual original IntDir required')
    intdir = Path(roots[0]).resolve(); tlog = intdir/'DualSPHysics.tlog'
    clt, linkt, libt = (tlog/q for q in ('CL.command.1.tlog', 'link.command.1.tlog', 'link.read.1.tlog'))
    compile_blocks, links = parser_tools.blocks(clt), parser_tools.blocks(linkt)
    m.need(len(links) == 1, 'One authoritative original link block required')
    link = parser_tools.arguments(' '.join(links[0][1]))
    objects = [Path(q).resolve() for q in link if q.lower().endswith('.obj')]
    expected = 87 if configuration == 'DebugCPU' else 113
    m.need(len(objects) == len(set(objects)) == expected and all(p.parent == intdir for p in objects)
           and sum(p.name.lower() == 'main.obj' for p in objects) == 1, 'Exact original full-program object inventory required')
    names = ('JSph', 'JSphCpuSingle' if configuration == 'DebugCPU' else 'JSphGpuSingle')
    compiles = {}
    for name in names:
        blocks = [q for q in compile_blocks if len(q[0]) == 1 and Path(q[0][0]).name.lower() == name.lower()+'.cpp']
        m.need(len(blocks) == 1, 'One authoritative original host compile required: '+name)
        compiles[name] = parser_tools.arguments(' '.join(blocks[0][1]))
    libraries = [Path(q.strip('"')).resolve() for q in libt.read_text(encoding='utf-16').splitlines()
                 if not q.startswith('^') and q.lower().endswith('.lib')]
    m.need(libraries, 'Actual resolved library tlog required')
    objects_stats = [m.stat(p) for p in objects]
    provenance = 'Original private IntDir and authoritative tlogs; first per-object stat seal is this preparation'
    cuda_tlogs = []
    if configuration == 'DebugCPU':
        seal = m.read(LATE)
        m.need(seal['passed'] and seal['consumed_stats_unchanged'] and seal['actual_link_objects'] == 87
               and seal['source_build'] == m.stat(bp) and seal['source_archive'] == b['source_archive'],
               'Original successful restored CPU object closure required')
        recorded = {key(q['path']): q for q in seal['consumed']}
        for q in objects_stats:
            m.need(key(q['path']) in recorded and m.bind(recorded[key(q['path'])]) == q,
                   'CPU original object differs from its retained successful seal')
        provenance = 'Prior successful late-RHS per-object stat seal, including original main'
    else:
        m.need(Path(b['intermediate']).resolve() == intdir and any(p.name.lower().endswith('.cu.obj') for p in objects),
               'Actual original GPU intermediate and retained CUDA objects required')
        cuda_tlogs = [m.stat(tlog/q) for q in ('CudaCompile.read.1u.tlog','CudaCompile.write.1u.tlog')]
        ended = datetime.datetime.fromisoformat(call['ended_utc']).timestamp()
        m.need(all(q['mtime_ns'] <= int((ended+1.)*1e9) for q in objects_stats),
               'Original private GPU object has a post-build timestamp; diagnose instead of adopting it')
        provenance = ('Dedicated schema2 IntDir, original CL/link and CUDA read/write tlogs; '
                      'all113 objects lie in the original build interval, no later recorded writer observed; '
                      'first per-object stat seal is this preparation, not a retrospective hash proof')
    runtime = [m.bind(q.get('destination', q)) for q in b['runtime']]
    m.need(len(runtime) == 9 and {Path(q['path']).name.lower() for q in runtime} == {
        'gencase_win64.exe','partvtk_win64.exe','dsphconfig.xml','chronoengine.dll','dsphchrono.dll',
        'vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'}, 'Original complete nine-file runtime required')
    consumed = [m.stat(bp), m.bind(b['actual_call']), m.bind(b['program']), m.bind(b['source_capture']),
                m.bind(b['source_archive']), m.stat(clt), m.stat(linkt), m.stat(libt)]
    consumed += cuda_tlogs+objects_stats+runtime+[m.stat(q) for q in libraries]
    m.verify(consumed)
    return dict(configuration=configuration, baseline_source_build=m.stat(bp), base_program=b['program'],
                base_original_source_capture=b['source_capture'], base_original_source_archive=b['source_archive'],
                original_build_call=b['actual_call'], intermediate=str(intdir), compiler_tlog=m.stat(clt),
                linker_tlog=m.stat(linkt), resolved_library_tlog=m.stat(libt), cuda_tlogs=cuda_tlogs, original_objects=objects_stats,
                object_binding_provenance=provenance, compile_arguments=compiles, link_arguments=link,
                resolved_libraries=[m.stat(q) for q in libraries], original_runtime=runtime,
                expected_link_objects=expected, consumed=consumed)


def overlay(original, name):
    nl = b'\r\n' if b'\r\n' in original else b'\n'
    if name == 'JSph.cpp':
        anchor = b'    if(GravityPreload){'+nl+b'      bdpart->SetvUint("GravityPreloadPhase"'
        text = '''    if(IsGravityPreloadHandoff() && GravityPreloadReleased){
      bdpart->SetvText("DynamicArtificialViscosityPolicy","ReleaseOnly");
      bdpart->SetvBool("DynamicArtificialViscosityOverrideActive",Visco==.2f);
      bdpart->SetvFloat("DynamicArtificialViscosityCoef",Visco);
    }
'''
    else:
        anchor = b'  Log->Printf("GravityPreload: phase=released actual='
        text = '''  //-Private, bounded H1.8/psi0 release-only AV test; original PRE/XML contract keeps AV=.1.
  if(!IsGravityPreloadHandoff() || !GravityPreloadReleased || GravityPreloadElasticSource
    || GravityPreloadKeepBedOverlap || !GravityPreloadBedIds.empty()
    || GravityPreloadActualStep!=2000000 || unsigned(Nstep)!=2000000
    || GravityPreloadIdBegin!=1805 || GravityPreloadIdCount!=255 || retired!=255 || Np!=6805 || Npb!=1805
    || !IsDynamicPorePlasticConfig() || !StrainSoftening || !UseDynamicPorePlaneContact()
    || TKernel!=KERNEL_Wendland || Dp!=.04 || KernelH!=.072f
    || !FixedDt || FixedDt->GetFixedValue()!=.000005 || SymplecticDtPre!=.000005
    || !ArtificialStress || ArtificialStressCoef!=.3f || ArtificialStressExp!=2.55f
    || ViscoTime || TVisco!=VISCO_Artificial || Visco!=.1f || ViscoBoundFactor!=1.f
    || SoilCte.coh!=5000.f || SoilCte.dlt!=0.f || SoilCte.psiDecay!=0.f)
    Run_Exceptioon("Private AV.2 requires the original AV.1 schema2 psi0 H1.8/5us AS.3n2.55 bed-role handoff.");
  Visco=.2f;
  Log->Printf("Private AV: policy=ReleaseOnly input_coefficient=%.9g actual_coefficient=%.9g completed_step=%u actual=%.17g; startup Configuration records certified input, native metadata records released AV.",double(.1f),double(Visco),unsigned(Nstep),TimeStep);
'''
        released = b'GravityPreloadActualTime=TimeStep;GravityPreloadActualStep=Nstep;GravityPreloadReleased=true;'
        m.need(original.count(released) == 1 and original.index(released) < original.index(anchor),
               'Override must follow the actual successful retirement/count/release commit')
    insertion = text.encode('ascii').replace(b'\n', nl)
    m.need(original.count(anchor) == 1 and insertion not in original,
           'Unique unmodified original insertion point required: '+name)
    changed = original.replace(anchor, insertion+anchor, 1)
    fragments = [insertion]
    if name != 'JSph.cpp':
        header = ('#include "'+name.removesuffix('.cpp')+'.h"').encode()+nl
        added = b'#include "JDsFixedDt.h"'+nl
        m.need(original.count(header) == 1 and added not in original,
               'One original Single include and no existing direct FixedDt include required')
        changed = changed.replace(header, header+added, 1); fragments.append(added)
    reversed_bytes = changed
    for fragment in fragments:
        m.need(reversed_bytes.count(fragment) == 1, 'Private insertion must remain unique')
        reversed_bytes = reversed_bytes.replace(fragment, b'', 1)
    m.need(reversed_bytes == original,
           'Private host insertion is not byte-reversible: '+name)
    return changed, fragments


def prepare():
    check = L/(TAG+'.prepare.json')
    m.need(not CAP.exists() and not check.exists(), 'Existing source preparation or partials protected')
    contexts = {q: original_context(q) for q in BASES}
    cpu, gpu = contexts['DebugCPU'], contexts['Release']
    m.need(cpu['base_original_source_capture'] == gpu['base_original_source_capture']
           and cpu['base_original_source_archive'] == gpu['base_original_source_archive'],
           'CPU and GPU originals must share the same schema2 source archive')
    archive = m.bind(gpu['base_original_source_archive']); capture = m.read(m.bind(gpu['base_original_source_capture'])['path'])
    m.need(capture['archive'] == archive, 'Actual full-source capture/archive differs')
    before = [m.stat(Path(__file__)), m.stat(NOTE), m.stat(Path(qualified.__file__)),
              m.stat(Path(parser_tools.__file__)), m.stat(Path(m.__file__))]
    before += cpu['consumed']+gpu['consumed']
    calls = []
    try:
        m.verify(before); CAP.mkdir()
        changed, insertions, originals, patches = {}, {}, {}, []
        with zipfile.ZipFile(archive['path']) as source:
            inventory = source.infolist()
            m.need(len({q.filename for q in inventory}) == len(inventory), 'Duplicate source archive member')
            for name in SOURCES:
                old = source.read('src/source/'+name); new, fragments = overlay(old, name)
                originals[name], changed[name], insertions[name] = old, new, fragments
                with (CAP/name).open('xb') as f: f.write(new)
                patches += list(difflib.unified_diff(old.decode('utf-8-sig').splitlines(True),
                    new.decode('utf-8-sig').splitlines(True),fromfile='original/src/source/'+name,
                    tofile='private/src/source/'+name))
            target = CAP/'source.zip'
            with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as output:
                for entry in inventory:
                    data = source.read(entry.filename)
                    name = entry.filename.removeprefix('src/source/')
                    output.writestr(entry, changed[name] if entry.filename == 'src/source/'+name and name in changed else data)
            with zipfile.ZipFile(target) as output:
                m.need([q.filename for q in output.infolist()] == [q.filename for q in inventory], 'Archive member inventory changed')
                other = 0
                for entry in inventory:
                    old, new = source.read(entry.filename), output.read(entry.filename)
                    name = entry.filename.removeprefix('src/source/')
                    if entry.filename == 'src/source/'+name and name in changed:
                        reversed_bytes = new
                        for fragment in insertions[name]: reversed_bytes = reversed_bytes.replace(fragment,b'',1)
                        m.need(new == changed[name] and reversed_bytes == old,
                               'Private archive member does not reverse to original bytes')
                    else:
                        m.need(new == old, 'Unrelated original archive member changed'); other += 1
        diff = CAP/'source.patch'
        with diff.open('x', encoding='utf-8', newline='') as f: f.write(''.join(patches))
        m.verify(before)
        source_record = dict(stage=TAG+'.source', prepared_only=True, passed=True,
            baseline_capture=gpu['base_original_source_capture'], baseline_archive=archive,
            base_original_source_capture=gpu['base_original_source_capture'], base_original_source_archive=archive,
            archive=m.stat(target), private_sources=[m.stat(CAP/name) for name in SOURCES], diff=m.stat(diff),
            source_files_changed=list(SOURCES), reverse_reconstruction_original_bytes_exact=True,
            all_other_archive_member_bytes_exact=True, unchanged_archive_members=other,
            only_release_AV_override_and_actual_metadata_changed=True, class_layout_changed=False,
            public_interfaces_changed=False, CUDA_source_changed=False, trace_macros_enabled=False,
            private_Singles_add_explicit_FixedDt_header=True,
            preload_input_AV_literal='.1f', released_AV_literal='.2f', AV_policy='ReleaseOnly',
            actual_AV_active_is_Visco_equals_02=True, original_schema2_PRE_not_recomputed=True,
            backend_contexts=contexts, consumed=before, consumed_stats_unchanged=True,
            solver_invocations=0, native_decodes=0, physical_acceptance=False, SHA_scans=0)
        m.save(CAP/'source.json', source_record)
        m.save(check, dict(stage=TAG+'.prepare', passed=True, source_capture=m.stat(CAP/'source.json'),
                          source_archive=m.stat(target), consumed=before, consumed_stats_unchanged=True,
                          builds_started=0, solver_invocations=0, physical_acceptance=False, SHA_scans=0))
        print('AV20_SOURCE_PREPARED', str(check), flush=True)
    except Exception as error:
        if not check.exists(): m.save(check, dict(stage=TAG+'.prepare', passed=False, first_failure=str(error),
            partial_outputs_preserved=True, consumed=before, builds_started=0, solver_invocations=0, SHA_scans=0))
        raise


def build(configuration):
    tag = 'c08_h18_av20_'+configuration+'_r1'; out = T/'outputs'/tag; check = L/(tag+'.build.json')
    m.need(not out.exists() and not check.exists() and not any(L.glob(tag+'.*.call.json')),
           'Existing complete or partial private build protected')
    before, calls = [], []
    try:
        preparation = m.read(L/(TAG+'.prepare.json')); sc = m.read(m.bind(preparation['source_capture'])['path'])
        m.need(preparation['passed'] and preparation['consumed_stats_unchanged'] and sc['passed']
               and sc['prepared_only'] and sc['reverse_reconstruction_original_bytes_exact']
               and sc['all_other_archive_member_bytes_exact'] and not sc['class_layout_changed']
               and not sc['CUDA_source_changed'] and not sc['trace_macros_enabled']
               and sc['preload_input_AV_literal'] == '.1f' and sc['released_AV_literal'] == '.2f',
               'Separately prepared reversible schema2-only AV.2 source required')
        ctx = sc['backend_contexts'][configuration]; m.verify(ctx['consumed'])
        m.need(ctx['base_original_source_archive'] == sc['baseline_archive'], 'Original backend/source mismatch')
        names = ('JSph', 'JSphCpuSingle' if configuration == 'DebugCPU' else 'JSphGpuSingle')
        oldobjects = [m.bind(q) for q in ctx['original_objects']]
        originals = {name: next(q for q in oldobjects if Path(q['path']).stem.lower() == name.lower()) for name in names}
        retained = [q for q in oldobjects if q not in originals.values()]
        expected = 87 if configuration == 'DebugCPU' else 113
        m.need(len(oldobjects) == expected and len(retained) == expected-2, 'Exactly two original host objects may be replaced')
        before = [m.stat(Path(__file__)), m.stat(NOTE), m.stat(Path(qualified.__file__)),
                  m.stat(Path(parser_tools.__file__)), m.stat(Path(m.__file__)),
                  m.stat(L/(TAG+'.prepare.json')), m.stat(CAP/'source.json'), m.bind(sc['archive']), m.bind(sc['diff'])]
        before += ctx['consumed']+[m.bind(q) for q in sc['private_sources']]
        m.verify(before); out.mkdir(); frozen = out/'frozen/src/source'; archived = []
        with zipfile.ZipFile(sc['archive']['path']) as z:
            for name in SOURCES: m.need(z.read('src/source/'+name) == (CAP/name).read_bytes(), 'Private source/archive differs')
            for entry in z.infolist():
                relative = Path(entry.filename)
                m.need(not relative.is_absolute() and '..' not in relative.parts, 'Source archive escaped output')
                if entry.is_dir() or relative.parts[:2] != ('src','source'): continue
                m.need(relative.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'), 'Source archive contains binaries')
                dest = out/'frozen'/relative; dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as f: f.write(z.read(entry))
                archived.append(m.stat(dest))
        m.need(len([q for q in archived if Path(q['path']).suffix.lower() in ('.h','.cuh')]) == 160,
               'Original160 archived headers required')
        before += archived
        replacement = {name: out/(name+'.obj') for name in names}; compile_args = {}; dependencies = []
        for name in names:
            args = list(ctx['compile_arguments'][name]); source_ids = [i for i,q in enumerate(args) if Path(q).name.lower() == name.lower()+'.cpp']
            m.need(len(source_ids) == 1 and all(q in args for q in ('/fp:precise','/openmp',
                '/Od' if configuration == 'DebugCPU' else '/O2','/MTd' if configuration == 'DebugCPU' else '/MT'))
                and any('_WITHGPU' in q for q in args) == (configuration == 'Release')
                and not any(q.lower().startswith(('/yu','/yc','/gl','/sourcedependencies')) for q in args)
                and not any('C08_STAGE_TRACE' in q or 'C08_CAUSAL_TRACE' in q for q in args), 'Original host ABI/macros changed')
            args[source_ids[0]] = str(CAP/(name+'.cpp'))
            for prefix, target in (('/fo',replacement[name]),('/fd',out/(name+'.pdb'))):
                indices = [i for i,q in enumerate(args) if q.lower().startswith(prefix)]
                m.need(len(indices) == 1, 'One original compiler output required: '+prefix)
                args[indices[0]] = prefix+str(target)
            dep = out/(name+'.dependencies.json'); dependencies.append(dep)
            compile_args[name] = ['/I'+str(frozen),*args,'/sourceDependencies',str(dep)]
        program = out/Path(ctx['base_program']['path']).name
        targets = {'/out:':program,'/pdb:':out/(program.stem+'.pdb'),
                   '/implib:':out/(program.stem+'.lib'),'/ltcgout:':out/(program.stem+'.iobj')}
        seen = set(); linked = []
        for arg in ctx['link_arguments']:
            if arg.lower().endswith('.obj'):
                for name in names:
                    if key(arg) == key(originals[name]['path']): arg = str(replacement[name]); break
            for prefix,target in targets.items():
                if arg.lower().startswith(prefix): arg = prefix+str(target); seen.add(prefix); break
            linked.append(arg)
        actual_objects = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        m.need(seen == set(targets) and len(actual_objects) == len(set(actual_objects)) == expected
               and set(actual_objects) == {Path(q['path']).resolve() for q in retained}|{p.resolve() for p in replacement.values()},
               'Final link must retain all objects including main and replace exactly two hosts')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Original MSVC14.36 environment failed')
        env = {k.upper():v for k,v in os.environ.items()}
        env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Original compiler ABI required')
        for name in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'): env.pop(name,None)
        env['LIB'] = ';'.join(dict.fromkeys(str(Path(q['path']).parent) for q in ctx['resolved_libraries']))
        cl = Path(env['VCTOOLSINSTALLDIR'])/'bin/Hostx64/x64/cl.exe'; link = cl.with_name('link.exe')
        before += [m.stat(cl),m.stat(link)]; m.verify(before)
        for name in names: calls.append(m.invoke(tag+'.compile_'+name,[str(cl),*compile_args[name]],S/'VS',env))
        calls.append(m.invoke(tag+'.link',[str(link),*linked],S/'VS',env))
        archived_names = {Path(q['path']).name.lower() for q in archived}
        for name, dep in zip(names,dependencies):
            d = m.read(dep)['Data']; includes = {Path(q).resolve() for q in d['Includes']}
            required = ['JSph.h']+(['JSphCpu.h','JSphCpuSingle.h'] if name == 'JSphCpuSingle'
                else ['JSphGpu.h','JSphGpuSingle.h'] if name == 'JSphGpuSingle' else [])
            m.need(Path(d['Source']).resolve() == (CAP/(name+'.cpp')).resolve()
                   and all((frozen/q).resolve() in includes for q in required)
                   and all(q.is_relative_to(frozen.resolve()) for q in includes if q.name.lower() in archived_names)
                   and all(not q.is_relative_to((S/'source').resolve()) for q in includes), 'Actual compiler leaked current public source/header ABI')
        runtime = []
        for q in ctx['original_runtime']:
            src = Path(q['path']); dest = out/src.name; m.need(not dest.exists(), 'Private runtime already exists')
            shutil.copy2(src,dest); m.need(dest.read_bytes() == src.read_bytes(), 'Actual runtime copy differs'); runtime.append(m.stat(dest))
        m.verify(before)
        m.save(check, dict(stage=tag+'.build',passed=True,configuration=configuration,
            allowed_runtime_backend='CPU' if configuration == 'DebugCPU' else 'GPU',program=m.stat(program),
            source_capture=m.stat(CAP/'source.json'),source_archive=m.stat(CAP/'source.zip'),
            base_original_source_capture=ctx['base_original_source_capture'],base_original_source_archive=ctx['base_original_source_archive'],
            base_program=ctx['base_program'],baseline_source_build=ctx['baseline_source_build'],
            private_host_sources=[m.stat(CAP/(name+'.cpp')) for name in names],
            original_replaced_objects=list(originals.values()),replacement_objects=[m.stat(q) for q in replacement.values()],
            retained_physical_objects=retained,actual_link_objects=expected,physical_objects_recompiled=2,
            object_binding_provenance=ctx['object_binding_provenance'],source_dependencies=[m.stat(q) for q in dependencies],
            archived_source_files=archived,runtime=runtime,calls=calls,consumed=before,consumed_stats_unchanged=True,
            compile_invocations=2,link_invocations=1,CUDA_compile_invocations=0,trace_macros_enabled=False,
            class_layout_changed=False,public_interfaces_changed=False,production_source_changed=False,
            AV_policy='ReleaseOnly',preload_input_AV_literal='.1f',released_AV_literal='.2f',
            actual_AV_metadata_key='DynamicArtificialViscosityCoef',solver_invocations=0,native_decodes=0,
            physical_acceptance=False,SHA_scans=0))
        print('AV20_PRIVATE_BUILD_PASSED',configuration,str(program),flush=True)
    except Exception as error:
        if not check.exists(): m.save(check,dict(stage=tag+'.build',passed=False,configuration=configuration,
            first_failure=str(error),calls=calls,consumed=before,partial_outputs_preserved=True,
            solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=('prepare','build'))
    p.add_argument('--configuration',choices=tuple(BASES)); p.add_argument('--execution-authorized',action='store_true')
    a = p.parse_args(); m.need(a.execution_authorized and ((a.action == 'build') == bool(a.configuration)),
        'Root full read and exactly one prepare or selected backend build action required')
    prepare() if a.action == 'prepare' else build(a.configuration)
