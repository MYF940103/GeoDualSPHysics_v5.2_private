"""Build only: exact three-material private HG host guard, one CL TU and link."""
import argparse
import difflib
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T, C, L = m.T, m.C, m.L
S = T.parents[3] / 'src'
TAG = 'c08_h18_hg_groups_build_r1'
SCRIPT = Path(__file__).resolve()
NOTE = T / 'notes/c08_h18_hg_groups_build_r1.md'
BASE = L / 'c08_h18_wall_c_retry_GPU_r1.build.json'
OPT = L / 'c08_h18_hg_opt_Release_r1.build.json'
ADMISSION = L / (TAG + '.root_build_admission.json')
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
MEMBER = 'src/source/JSphGpuSingle.cpp'


def private_source(raw):
    original = raw.decode('utf-8')
    nl = '\r\n' if '\r\n' in original else '\n'
    anchor = '    if(!GravityPreloadReleased || !GravityPreload || !IsGravityPreloadHandoff() || GravityPreloadElasticSource'
    declaration = nl.join((
        '    // Private exact material admission only; the cached material law is unchanged.',
        '    // Match JSph::Read... float(TORAD*ReadElementFloat), including signed dilation.',
        '    const bool c08MaterialGroup=',
        '      (SoilCte.coh==5000.f && SoilCte.dlt==0.f && SoilCte.psiDecay==0.f)',
        '      || (SoilCte.coh==5000.f && SoilCte.dlt==float(TORAD*2.5f) && SoilCte.psiDecay==.2f)',
        '      || (SoilCte.coh==7500.f && SoilCte.dlt==float(TORAD*-5.f) && SoilCte.psiDecay==.2f);'))
    old_guard = (
        '      || SoilCte.dlt!=0.f || SoilCte.psiDecay!=0.f || SoilCte.coh!=5000.f || SoilCte.coh_r!=1000.f || SoilCte.n_coh!=5.f' + nl
        + '      || SoilCte.n_phi!=0.f || SoilCte.phi!=SoilCte.phi_r || Gravity.x!=0 || Gravity.y!=0 || Gravity.z!=-9.81f)')
    new_guard = (
        '      || !c08MaterialGroup || SoilCte.coh_r!=1000.f || SoilCte.n_coh!=5.f || SoilCte.n_phi!=0.f' + nl
        + '      || SoilCte.phi!=float(TORAD*25.f) || SoilCte.phi_r!=float(TORAD*25.f)' + nl
        + '      || Gravity.x!=0 || Gravity.y!=0 || Gravity.z!=-9.81f)')
    old_message = 'Private H1.8 energy-normalized plastic HG requires unchanged schema2 psi0 Wendland/AS.3n2.55/5us/bedroles released target.'
    new_message = 'Private H1.8 energy-normalized plastic HG requires one exact schema2 psi0/psi2p5/psim5 Wendland/AS.3n2.55/5us/bedroles released target.'
    changes = [(anchor, declaration + nl + anchor), (old_guard, new_guard), (old_message, new_message)]
    changed, proof = original, []
    for old, new in changes:
        m.need(changed.count(old) == 1 and new not in changed, 'Unique original material-guard anchor absent')
        changed = changed.replace(old, new, 1)
        proof.append(dict(original_text=old, replacement_text=new, matches=1))
    inverse = changed
    for old, new in reversed(changes):
        m.need(inverse.count(new) == 1, 'Inverse material-guard anchor ambiguous')
        inverse = inverse.replace(new, old, 1)
    m.need(inverse.encode('utf-8') == raw, 'Inverse transform did not restore every original host byte')
    return changed.encode('utf-8'), proof


def dependency_keys(data, root):
    """Normalize only the frozen source root; external dependency identities stay absolute."""
    root = root.resolve()
    result = set()
    for name in data['Data']['Includes']:
        path = Path(name).resolve()
        result.add('project/' + path.relative_to(root).as_posix().lower() if path.is_relative_to(root)
                   else 'external/' + path.as_posix().lower())
    return result


def build():
    check = L / (TAG + '.build.json')
    cap, out = T / 'outputs' / (TAG + '_source'), T / 'outputs' / (TAG + '_build')
    intdir = Path(os.environ['TEMP']) / TAG
    m.need(' ' not in str(intdir) and not intdir.exists() and not cap.exists() and not out.exists()
           and all(not (L / (TAG + suffix)).exists() for suffix in
                   ('.build.json', '.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
           'Any existing complete or partial groups build is protected; no retry')
    before, calls, setup_result = [], [], None
    try:
        ad = m.read(ADMISSION)
        m.need(ad['authorized'] and ad['allowed_stage'] == TAG and ad['configuration'] == 'Release'
               and ad['execution_script'] == m.stat(SCRIPT) and ad['note'] == m.stat(NOTE)
               and ad['source_build'] == m.stat(BASE) and ad['optimized_build'] == m.stat(OPT)
               and ad['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD
               and ad['build_only'] and not ad['automatic_solver'] and not ad['automatic_reader'],
               'Exact separate current-root build-only admission required')
        b, opt = m.read(BASE), m.read(OPT)
        m.need(b['passed'] and b['configuration'] == 'Release' and b['consumed_stats_unchanged']
               and b['actual_link_objects'] == 114 and b['host_fault_capture_retained']
               and b['numerical_C_quality_retry'] and b['original_guards_unchanged']
               and b['private_HG_Node_material_recompiled'] is False
               and opt['passed'] and opt['consumed_stats_unchanged']
               and b['original_optimized_build'] == m.stat(OPT), 'Current C-retry/optimized baseline required')
        before = [m.stat(q) for q in (SCRIPT, NOTE, ADMISSION, BASE, OPT, Path(m.__file__))]
        before += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive')]
        before += [m.bind(q) for q in b['frozen_sources'] + b['runtime']]
        for entry in b['calls'] + opt['calls']:
            before.append(m.bind(entry))
            actual = m.read(entry['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0
                   and actual['ownership_failure'] is None, 'Original actual owned CL/NVCC/link exits required')
        link_call = m.read(b['calls'][-1]['path'])
        host_call = m.read(opt['calls'][0]['path'])
        original_link = link_call['child']['argv']
        original_cl = host_call['child']['argv']
        m.need(original_link == [link_call['program'], *link_call['arguments']]
               and original_cl == [host_call['program'], *host_call['arguments']], 'Original actual argv differs')
        cl, link = Path(original_cl[0]), Path(original_link[0])
        m.need(cl.name.lower() == 'cl.exe' and link.name.lower() == 'link.exe'
               and all('/14.36.32532/' in q.as_posix() for q in (cl, link)), 'Actual original MSVC14.36 tools required')
        objects = [Path(q).resolve() for q in original_link[1:] if q.lower().endswith('.obj')]
        m.need(objects == [Path(q).resolve() for q in b['actual_link_inputs']] and len(set(objects)) == 114,
               'Original actual ordered114-object closure required')
        private = [Path(q['path']).resolve() for q in b['retained_private_opt_objects']]
        replaced = [q for q in private if q.name.lower() == 'jsphgpusingle.obj']
        m.need(len(private) == 3 and len(replaced) == 1 and all(q in objects for q in private),
               'Only the actual optimized JSphGpuSingle host object may be replaced')
        retained = [q for q in objects if q != replaced[0]]
        m.need(len(retained) == 113 and all(Path(b[k]['path']).resolve() in retained for k in
               ('replacement_physical_object', 'retained_capture_host_object'))
               and all(q in retained for q in private if q != replaced[0]),
               'Retain C-quality CUDA, host capture and two remaining private HG objects')
        before += [m.stat(q) for q in objects] + [m.stat(cl), m.stat(link)]
        old_frozen = Path(b['program']['path']).parent / 'frozen'
        old_opt_frozen = Path(opt['OutDir']) / 'frozen'
        original_host = old_frozen / MEMBER
        m.need(all(Path(q['path']).resolve().is_relative_to(old_frozen.resolve()) for q in b['frozen_sources']),
               'Frozen source member outside declared actual baseline')
        m.need(original_host.read_bytes() == Path(opt['private_sources']['host']['path']).read_bytes(),
               'Current frozen host must match the actually compiled optimized host bytes')
        jsph = (old_frozen / 'src/source/JSph.cpp').read_text(encoding='utf-8-sig')
        types = (old_frozen / 'src/source/TypesDef.h').read_text(encoding='utf-8-sig')
        for expression in ('SoilCte.phi=float(TORAD*sxml->ReadElementFloat(solidNode,"phi","value",true));',
                           'SoilCte.dlt=float(TORAD*sxml->ReadElementFloat(solidNode,"dlt","value",true));',
                           'float(TORAD*sxml->ReadElementFloat(solidNode,"phi_r","value",true))'):
            m.need(expression in jsph, 'Actual frozen XML angle-to-float expression differs')
        m.need('#define TORAD 0.017453292519943295769' in types, 'Actual frozen TORAD definition differs')
        raw = original_host.read_bytes()
        changed, derivation = private_source(raw)
        old_dep_path = Path(original_cl[original_cl.index('/sourceDependencies') + 1])
        old_dep = m.read(old_dep_path); before.append(m.stat(old_dep_path))
        m.need(Path(old_dep['Data']['Source']).resolve() == (old_opt_frozen / MEMBER).resolve(),
               'Actual original host sourceDependencies source differs')
        external = {Path(q).resolve() for q in old_dep['Data']['Includes']
                    if not Path(q).resolve().is_relative_to(old_opt_frozen.resolve())}
        before += [m.stat(q) for q in sorted(external)]
        sdk = {q.parts[q.parts.index('Include') + 1] for q in external
               if 'Include' in q.parts and 'Windows Kits' in q.parts and '10' in q.parts}
        # Windows path spelling in dependencies may be lower case. Infer from the literal SDK pattern.
        if not sdk:
            sdk = {q.as_posix().lower().split('/windows kits/10/include/')[1].split('/')[0]
                   for q in external if '/windows kits/10/include/' in q.as_posix().lower()}
        m.need(sdk == {'10.0.22000.0'}, 'Original GPU host actual SDK header set must be the single22000 release')
        frozen, archive = out / 'frozen', cap / 'source.zip'
        physical = frozen / 'src/source'
        m.verify(before)
        cap.mkdir(); out.mkdir(); intdir.mkdir(parents=True)
        copied = []
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for entry in b['frozen_sources']:
                origin = Path(entry['path']); rel = origin.relative_to(old_frozen); target = frozen / rel
                m.need(not rel.is_absolute() and '..' not in rel.parts and not target.exists(), 'Invalid or existing source member')
                data = changed if rel.as_posix() == MEMBER else origin.read_bytes()
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
                m.need(target.read_bytes() == data, 'New frozen source member differs')
                z.writestr(rel.as_posix(), data); copied.append(m.stat(target))
        diff = cap / 'host_material_guard.diff'
        diff.write_text(''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True), changed.decode('utf-8').splitlines(True),
            fromfile='actual_psi0/JSphGpuSingle.cpp', tofile='three_exact_groups/JSphGpuSingle.cpp')), encoding='utf-8')
        capture = cap / 'source.json'
        m.save(capture, dict(stage=TAG + '.source', base_build=m.stat(BASE), original_source_capture=b['source_capture'],
            original_source_archive=b['source_archive'], archive=m.stat(archive), diff=m.stat(diff),
            source_files=copied, modified_members=[MEMBER], derivation=derivation,
            exact_inverse_original_host_bytes=True, material_guard_only=True, material_algorithms_changed=False,
            phi_guard_tightened_from_equal_to_exact_25deg=True, angle_expression='float(TORAD*XML_float_degrees)',
            common=dict(phi_deg=25,phi_r_deg=25,coh_r=1000,n_coh=5,n_phi=0),
            exact_groups=[dict(group='psi0',coh=5000,dlt_deg=0,decay=0),
                          dict(group='psi2p5',coh=5000,dlt_deg=2.5,decay=.2),
                          dict(group='psim5',coh=7500,dlt_deg=-5,decay=.2)],
            public_source_changed=False, class_or_CTE_ABI_changed=False, physical_acceptance=False, SHA_scans=0))
        before += [m.stat(capture), m.stat(archive), m.stat(diff), *copied]
        obj, dependencies = intdir / 'JSphGpuSingle.obj', intdir / 'host.dependencies.json'
        cl_args, i = [], 1
        while i < len(original_cl):
            arg = original_cl[i]
            if arg.lower().startswith('/fo'): arg = '/Fo' + str(obj)
            elif arg.lower().startswith('/fd'): arg = '/Fd' + str(intdir / 'host.pdb')
            elif arg.lower() == '/sourcedependencies':
                cl_args += [arg, str(dependencies)]; i += 2; continue
            elif arg.lower().startswith('/i') and Path(arg[2:]).resolve() == (old_opt_frozen / 'src/source').resolve():
                arg = '/I' + str(physical)
            elif Path(arg).name.lower() == 'jsphgpusingle.cpp': arg = str(physical / 'JSphGpuSingle.cpp')
            cl_args.append(arg); i += 1
        m.need(cl_args.count('/c') == 1 and '/fp:precise' in cl_args
               and sum(q.lower().startswith('/fo') for q in cl_args) == 1
               and sum(q.lower().startswith('/fd') for q in cl_args) == 1
               and sum(Path(q).name.lower() == 'jsphgpusingle.cpp' for q in cl_args) == 1
               and '/I' + str(physical) in cl_args, 'Only source/include/output/dependency path relocation allowed')
        program = out / Path(b['program']['path']).name
        outputs = {'/out:': program, '/pdb:': out / (program.stem + '.pdb'),
                   '/implib:': out / (program.stem + '.lib'), '/ltcgout:': intdir / (program.stem + '.iobj')}
        linked, seen = [], set()
        for arg in original_link[1:]:
            if arg.lower().endswith('.obj') and Path(arg).resolve() == replaced[0]: arg = str(obj)
            for prefix, path in outputs.items():
                if arg.lower().startswith(prefix): arg = prefix + str(path); seen.add(prefix); break
            linked.append(arg)
        m.need(seen == set(outputs) and [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
               == [obj.resolve() if q == replaced[0] else q for q in objects], 'Ordered link closure changed beyond one host object')
        envcmd = intdir / 'env.cmd'
        envcmd.write_bytes(('@echo off\r\ncall "D:\\Program Files\\VS2022\\VC\\Auxiliary\\Build\\vcvarsall.bat" x64 10.0.22000.0 -vcvars_ver=14.36 >nul\r\n'
                            'if errorlevel 1 exit /b %errorlevel%\r\nset\r\n').encode('ascii'))
        setup_argv = [str(Path(os.environ['SystemRoot']) / 'System32/cmd.exe'), '/d', '/c', str(envcmd)]
        setup = subprocess.run(setup_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        setup_result = dict(argv=setup_argv, environment_cmd=m.stat(envcmd), actual_Popen_wait_exit=setup.returncode,
                            stderr=setup.stderr.decode('mbcs', errors='replace'), stdout_environment_not_written=True)
        m.need(setup.returncode == 0, 'Original GPU host MSVC/SDK environment setup failed')
        env = {key.upper(): value for key, value in os.environ.items()}
        env.update((key.upper(), value) for key, value in
                   (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532' and env['WINDOWSSDKVERSION'].rstrip('\\/') == '10.0.22000.0',
               'Actual original MSVC14.36/SDK22000 environment required')
        env['PATH'] = str(cl.parent) + os.pathsep + env.get('PATH', '')
        m.need(Path(shutil.which('cl.exe', path=env['PATH'])).resolve() == cl.resolve(), 'PATH cl must be actual original tool')
        for key in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'): env.pop(key, None)
        before.append(m.stat(envcmd))
        libdirs = [S / 'VS'] + [(Path(q.split(':', 1)[1]) if Path(q.split(':', 1)[1]).is_absolute()
                   else S / 'VS' / q.split(':', 1)[1]) for q in linked if q.lower().startswith('/libpath:')]
        libdirs += [Path(q) for q in env.get('LIB', '').split(';') if q]
        for arg in linked:
            if arg.lower().endswith('.lib') and not arg.startswith('/'):
                candidates = [Path(arg)] if Path(arg).is_absolute() else [q / arg for q in libdirs]
                library = next((q for q in candidates if q.is_file()), None)
                m.need(library is not None, 'Original explicit link library absent: ' + arg); before.append(m.stat(library))
        m.verify(before)
        calls.append(m.invoke(TAG + '.compile', [str(cl), *cl_args], intdir, env=env))
        actual = m.read(calls[-1]['path'])
        m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
               'Actual owned single-TU CL exits must pass')
        new_dep = m.read(dependencies)
        m.need(Path(new_dep['Data']['Source']).resolve() == (frozen / MEMBER).resolve()
               and dependency_keys(old_dep, old_opt_frozen) == dependency_keys(new_dep, frozen),
               'Actual new header set differs from original host dependencies after root relocation')
        calls.append(m.invoke(TAG + '.link', [str(link), *linked], S / 'VS', env=env))
        actual = m.read(calls[-1]['path'])
        m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
               'Actual owned link exits must pass')
        runtime = []
        for entry in b['runtime']:
            origin = Path(entry['path']); target = out / origin.name
            m.need(not target.exists(), 'Existing private runtime leaf protected'); shutil.copy2(origin, target)
            m.need(target.read_bytes() == origin.read_bytes(), 'Runtime companion copy differs'); runtime.append(m.stat(target))
        m.verify(before)
        m.save(check, dict(stage=TAG + '.build', passed=True, configuration='Release', program=m.stat(program),
            root_admission=m.stat(ADMISSION), base_build=m.stat(BASE), optimized_build=m.stat(OPT),
            source_capture=m.stat(capture), source_archive=m.stat(archive), source_diff=m.stat(diff), frozen_sources=copied,
            original_actual_host_call=opt['calls'][0], original_actual_link_call=b['calls'][-1],
            original_CL_arguments=original_cl, actual_CL_arguments=[str(cl), *cl_args],
            original_link_arguments=original_link, actual_link_arguments=[str(link), *linked],
            original_host_dependencies=m.stat(old_dep_path), actual_host_dependencies=m.stat(dependencies),
            actual_dependency_set_equal_after_project_root_relocation=True, original_replaced_host_object=m.stat(replaced[0]),
            replacement_host_object=m.stat(obj), retained_objects=[q for q in before if Path(q['path']).resolve() in retained],
            actual_link_inputs=[str(obj.resolve()) if q == replaced[0] else str(q) for q in objects],
            actual_link_objects=114, retained_objects_count=113, recompiled_host_objects=1,
            retained_opt_HG_objects=2, C_quality_CUDA_object_retained=True, host_capture_object_retained=True,
            physical_CUDA_objects_recompiled=0, material_law_or_HG_Node_source_changed=False,
            material_guard_only=True, phi_guard_tightened_from_equal_to_exact_25deg=True,
            exact_inverse_original_host_bytes=True, public_source_changed=False, class_or_CTE_ABI_changed=False,
            environment_setup=setup_result, calls=calls, runtime=runtime, consumed=before, consumed_stats_unchanged=True,
            compile_invocations=1, link_invocations=1, full_project_builds=0, help_invocations=0, smoke_invocations=0,
            solver_invocations=0, reader_invocations=0, VTK_invocations=0, original_programs_and_PRE_untouched=True,
            independent_material_probe_pending=True, original_psi0_actual_prefix_pending=True,
            private_capability_not_published_as_public_interface=True, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        if not check.exists():
            actual_calls = [m.stat(L / (TAG + '.' + phase + '.call.json')) for phase in ('compile', 'link')
                            if (L / (TAG + '.' + phase + '.call.json')).is_file()]
            m.save(check, dict(stage=TAG + '.build', passed=False, configuration='Release', first_failure=str(error),
                calls=actual_calls, environment_setup=setup_result, consumed=before, partial_artifacts_preserved=True,
                automatic_retry=False, solver_invocations=0, reader_invocations=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Author-only until root full read and exact separate build admission')
    build()
