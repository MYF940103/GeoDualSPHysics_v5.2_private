"""Prepare private terminal-rejection printf copies, then compile one CUDA TU and link; never run."""
import argparse, ctypes, difflib, json, os, re, shutil, subprocess, zipfile
from pathlib import Path, PurePosixPath
import upl_c08_asn4_zero_cpu_r2_build as evidence

T = Path(__file__).resolve().parents[1]
S = T.parents[3] / 'src'
L = T / 'logs'
TAG = 'c08_h18_wall_fail_gpu_r1'
NOTE = T / 'notes' / (TAG + '.md')
BASE = L / 'c08_preload_schema2_Release_r1.build.json'
CAP = T / 'outputs' / (TAG + '_source')
OUT = T / 'outputs' / (TAG + '_build')
PROGRAM = OUT / 'DualSPHysics5.2_GEO_win64.exe'
need, read, stat, bind, save, invoke = (
    evidence.need, evidence.read, evidence.stat, evidence.bind, evidence.save, evidence.invoke)


def windows_args(line):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW('tool.exe ' + line, ctypes.byref(count))
    need(bool(pointer), 'Cannot parse original Windows project command')
    try:
        return [pointer[i] for i in range(1, count.value)]
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(ctypes.cast(pointer, ctypes.c_void_p))


def private_source(original):
    """Insert only printf calls at five terminal gates, plus the explicit stdio include."""
    header = (' stage=%u sorted_slot=%u B=(%.17g,%.17g,%.17g)'
              ' normal=(%.9g,%.9g,%.9g)')
    identity = ['stage', 'p1', 'posxy[p1].x', 'posxy[p1].y', 'posz[p1]',
                'bn.x', 'bn.y', 'bn.z']
    fit = (' retried=%u gp=(%.17g,%.17g,%.17g) fitshift=(%.17g,%.17g)'
           ' sumwab=%.17g submerged=%.17g threshold=%.9g',
           ['unsigned(retried)', 'gp.x', 'gp.y', 'gp.z', 'fitshiftx', 'fitshiftz',
            'sumwab', 'submerged', 'double(threshold)'])
    moment = (' moment=(%.17g,%.17g,%.17g;%.17g,%.17g,%.17g;%.17g,%.17g,%.17g)',
              ['moment.a11', 'moment.a12', 'moment.a13', 'moment.a21', 'moment.a22',
               'moment.a23', 'moment.a31', 'moment.a32', 'moment.a33'])
    near = (' nearest2=%.17g near=(%.17g,%.17g) nearest0=%.17g'
            ' receiver_J_before=%.17g solid0=%.17g',
            ['nearest2', 'nearx', 'nearz', 'nearest[0]', 'j[p1]', 'solid0'])
    active_expression = ('unsigned(submerged>0 || sumwab>=double(threshold)'
                         ' || (threshold>=2 && sumwab+2>=double(threshold)))')

    def prints(reason, incomplete, groups, newline):
        result = []
        for number, (detail, values) in enumerate(groups):
            form = ('C08_WALL_FAIL reason=' + reason + ' incomplete=' + str(incomplete)
                    + ' detail=' + str(number) + header + detail + '\n')
            arguments = identity + values
            need(len(arguments) <= 32 and len(re.findall(r'%(?:\.\d+)?[ug]', form)) == len(arguments),
                 'CUDA printf format/32-argument bound differs')
            result.append('printf(' + json.dumps(form) + ','
                          + ','.join(arguments) + ');' + newline)
        return ''.join(result)

    cu_name, wall_name = 'src/source/JSphGpu_ker.cu', 'src/source/JSphGpu_mdbc_ker.cuh'
    cu = original[cu_name].decode('utf-8')
    wall = original[wall_name].decode('utf-8')
    newline = '\r\n' if '\r\n' in wall else '\n'
    need(('\r\n' in cu) == ('\r\n' in wall), 'Archived TU/include newline styles differ')
    atomic = 'atomicMin(invalid,p1);return;'
    receiver = 'if(!CODE_IsFixed(code[p1]) || !isfinite(r2) || !(r2>0)){' + atomic + '}'
    donor = 'if(!isfinite(j[p2]) || j[p2]<=solid0){' + atomic + '}'
    geometry = '    ' + atomic + newline + '  }' + newline + '  const tmatrix3d inv=cumath::InverseMatrix3x3(moment,det);'
    finite = 'if(!isfinite(v[c])){' + atomic + '}'
    domain = '|| !isfinite(tv.x) || !isfinite(tv.y) || !isfinite(tv.z)){' + atomic + '}'
    hooks = [
        (receiver, prints('invalid_receiver', 1, [
            (' code=%u fixed=%u normal_r2=%.17g solid0=%.17g',
             ['unsigned(code[p1])', 'unsigned(CODE_IsFixed(code[p1]))', 'r2', 'solid0'])], newline)),
        (donor, prints('raw_donor_J', 1, [
            (' donor_slot=%u donor_B=(%.17g,%.17g,%.17g) donor_J=%.17g solid0=%.17g',
             ['p2', 'posxy[p2].x', 'posxy[p2].y', 'posz[p2]', 'j[p2]', 'solid0']),
            fit, near,
            (moment[0] + ' partial_det=%.17g partial_active=%u',
             moment[1] + ['cumath::Determinant3x3(moment)', active_expression])], newline)),
        (geometry, prints('geometry_exhausted_or_ineligible', 0, [
            fit, near,
            (moment[0] + ' det=%.17g active=%u', moment[1] + ['det', 'unsigned(active)']),
            (' nearestfinite=%u simulate2d=%u periactive=%u positive_sum=%u'
             ' finite_det=%u abs_det_ge_1e_3=%u',
             ['unsigned(nearestfinite)', 'unsigned(CTE.simulate2d)', 'unsigned(CTE.periactive)',
              'unsigned(sumwab>0)', 'unsigned(isfinite(det))', 'unsigned(fabs(det)>=1e-3)'])], newline)),
        (finite, prints('nonfinite_fitted_component', 1, [
            fit, near,
            (moment[0] + ' det=%.17g active=%u', moment[1] + ['det', 'unsigned(active)']),
            (' field_c=%u value=%.17g nearest_field=%.17g field_sum=%.17g'
             ' grad=(%.17g,%.17g) Jextrap_if_stage0=%.17g',
             ['c', 'v[c]', 'nearest[c]', 'sum[c]', 'gradx', 'gradz',
              '(stage==0? v[0]: 0.)'])], newline)),
        (domain, prints('stage0_domain', 0, [
            fit, near,
            (moment[0] + ' det=%.17g active=%u', moment[1] + ['det', 'unsigned(active)']),
            (' Jextrap=%.17g Jgrad=(%.17g,%.17g) pressure=%.17g'
             ' dv=(%.9g,%.9g,%.9g) tv=(%.9g,%.9g,%.9g) noslip=%u'
             ' normalg=(%.9g,%.9g,%.9g) bad_J=%u bad_pressure=%u bad_dv=%u bad_tv=%u',
             ['v[0]', 'gx[0]', 'gz[0]', 'pressure', 'dv.x', 'dv.y', 'dv.z',
              'tv.x', 'tv.y', 'tv.z', 'unsigned(noslip)', 'normalg.x', 'normalg.y', 'normalg.z',
              'unsigned(v[0]<=solid0)', 'unsigned(!isfinite(pressure) || fabs(pressure)>FLT_MAX)',
              'unsigned(!isfinite(dv.x) || !isfinite(dv.y) || !isfinite(dv.z))',
              'unsigned(!isfinite(tv.x) || !isfinite(tv.y) || !isfinite(tv.z))'])], newline)),
    ]
    edits = [(cu_name, '#include <cfloat>', '#include <stdio.h>' + newline + '#include <cfloat>')]
    for anchor, insertion in hooks:
        need(anchor.count(atomic) == 1, 'A hook must retain exactly its original reject operation')
        edits.append((wall_name, anchor, anchor.replace(atomic, insertion + atomic, 1)))
    text = {cu_name: cu, wall_name: wall}
    derivation = []
    for name, old, new in edits:
        need(text[name].count(old) == 1 and new not in text[name], 'Archived terminal hook is not unique')
        text[name] = text[name].replace(old, new, 1)
        derivation.append(dict(member=name, original_text=old, replacement_text=new, forward_matches=1))
    modified = {name: value.encode('utf-8') for name, value in text.items()}
    inverse = dict(text)
    for name, old, new in reversed(edits):
        need(inverse[name].count(new) == 1, 'Private inverse text hook is not unique')
        inverse[name] = inverse[name].replace(new, old, 1)
    need(all(inverse[name].encode('utf-8') == original[name] for name in text),
         'Removing only inserted printf/include text did not reconstruct original archive bytes')
    need(all(modified[name].count(b'atomicMin(invalid,p1);return;')
             == original[name].count(b'atomicMin(invalid,p1);return;') for name in text),
         'Original atomicMin/return count changed')
    return modified, derivation


def build():
    check = L / (TAG + '.build.json')
    suffixes = ('.build.json', '.compile.call.json', '.compile.log', '.link.call.json', '.link.log')
    need(not CAP.exists() and not OUT.exists() and all(not (L / (TAG + q)).exists() for q in suffixes),
         'Existing complete or partial private build is protected')
    before, calls = [], []
    try:
        baseline = read(BASE)
        need(baseline['passed'] and baseline['configuration'] == 'Release'
             and baseline['consumed_stats_unchanged'], 'Closed schema2 Release build required')
        call_entry = bind(baseline['actual_call'])
        call = read(call_entry['path'])
        need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
             and call['ownership_failure'] is None, 'Original schema2 build did not close successfully')
        capture_entry, archive_entry = bind(baseline['source_capture']), bind(baseline['source_archive'])
        need(read(capture_entry['path'])['archive'] == archive_entry, 'Schema2 source archive binding differs')
        log_entry = bind(call['log'])
        intdir = Path(baseline['intermediate'])
        tlog = intdir / 'DualSPHysics.tlog/link.command.1.tlog'
        lines = tlog.read_text(encoding='utf-16').splitlines()
        need(sum(q.startswith('^') for q in lines) == 1, 'One original link block required')
        link_args = windows_args(' '.join(q for q in lines if q and not q.startswith('^')))
        objects = [Path(q).resolve() for q in link_args if q.lower().endswith('.obj')]
        need(len(objects) == len(set(objects)) == 113 and sum(q.name.lower() == 'main.obj' for q in objects) == 1,
             'Exactly113 unique actual schema2 link objects including original main required')
        replaced = [q for q in objects if q.name.lower() == 'jsphgpu_ker.cu.obj']
        need(len(replaced) == 1 and all(q.parent == intdir.resolve() for q in objects),
             'Exactly one same-schema2 CUDA replacement input required')
        retained = [q for q in objects if q != replaced[0]]
        nvcc_lines = [q.split(b'>', 1)[1].strip().decode('ascii')
                      for q in Path(log_entry['path']).read_bytes().splitlines()
                      if b'nvcc.exe' in q.lower() and b'jsphgpu_ker.cu' in q.lower()]
        need(len(nvcc_lines) == 1, 'One actual ASCII schema2 NVCC command required')
        compile_args = windows_args(nvcc_lines[0])
        nvcc = Path(compile_args.pop(0))
        includes = [q[2:] for q in compile_args if q.startswith('-I')]
        need(len(includes) == 1 and Path(includes[0]).resolve() == (nvcc.parent.parent / 'include').resolve()
             and '-I' not in compile_args and not any(q.startswith('--include-path') for q in compile_args),
             'Original explicit include must be CUDA only')
        runtime_leaves = ('DsphConfig.xml', 'ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll',
                          'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
        runtime = [bind(next(q['destination'] for q in baseline['runtime']
                             if Path(q['destination']['path']).name == leaf)) for leaf in runtime_leaves]
        original_program = bind(baseline['program'])
        need(all(Path(q['path']).parent == Path(original_program['path']).parent for q in runtime),
             'Runtime companions must come from the frozen schema2 Release output')
        before = [stat(BASE), call_entry, capture_entry, archive_entry, log_entry, stat(tlog),
                  original_program, *[stat(q) for q in objects], *runtime, stat(__file__), stat(NOTE),
                  stat(evidence.__file__), stat(evidence.old.__file__)]
        before += [stat(S / 'source' / q) for q in ('JSphGpu_ker.cu', 'JSphGpu_mdbc_ker.cuh')]
        before += [stat(S.parent / 'bin/windows' / q) for q in
                   ('DualSPHysics5.2CPU_win64_debug.exe', 'DualSPHysics5.2_win64_debug.exe',
                    'DualSPHysics5.2CPU_win64.exe', 'DualSPHysics5.2_GEO_win64.exe')
                   if (S.parent / 'bin/windows' / q).is_file()]
        CAP.mkdir()
        OUT.mkdir()
        frozen = OUT / 'frozen/src/source'
        sources = []
        with zipfile.ZipFile(archive_entry['path']) as original:
            names = ('src/source/JSphGpu_ker.cu', 'src/source/JSphGpu_mdbc_ker.cuh')
            raw = {q: original.read(q) for q in names}
            modified, derivation = private_source(raw)
            diff = CAP / 'diagnostic.diff'
            diff.write_text(''.join(''.join(difflib.unified_diff(
                raw[q].decode('utf-8').splitlines(True), modified[q].decode('utf-8').splitlines(True),
                fromfile='schema2/' + q, tofile='private_fail_printf/' + q)) for q in names),
                encoding='utf-8')
            archive = CAP / 'source.zip'
            with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as private:
                for info in original.infolist():
                    member = PurePosixPath(info.filename)
                    need(not member.is_absolute() and '..' not in member.parts, 'Invalid archived source member')
                    data = modified.get(info.filename, original.read(info))
                    private.writestr(info.filename, data)
                    if not info.is_dir() and member.parts[:2] == ('src', 'source'):
                        need(member.suffix.lower() not in ('.obj', '.o', '.pdb', '.exe', '.dll', '.lib'),
                             'Frozen source must not contain binary/object artifacts')
                        target = OUT / 'frozen' / Path(*member.parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with target.open('xb') as stream:
                            stream.write(data)
                        need(target.read_bytes() == data, 'Frozen source differs from private archive')
                        sources.append(stat(target))
        need(all((frozen / q).is_file() for q in
                 ('JSphGpu_ker.cu', 'JSphGpu_ker.h', 'JSphGpu_mdbc_ker.cuh', 'JSphGpu_InOut_iker.cu')),
             'Complete frozen CUDA include closure absent')
        capture = CAP / 'source.json'
        save(capture, dict(stage=TAG + '.source', intervention='terminal_rejection_printf_only',
             baseline_source_capture=capture_entry,
             baseline_source_archive=archive_entry, archive=stat(archive), diff=stat(diff),
             modified_members=list(modified), exact_inverse_original_bytes=True, derivation=derivation,
             private_gpu_source=stat(frozen / 'JSphGpu_ker.cu'),
             private_wall_include=stat(frozen / 'JSphGpu_mdbc_ker.cuh'),
             terminal_rejection_printf_only=True, primary_snapshot_added=False, CXX_locals_added=False,
             public_interfaces_changed=False, physical_arithmetic_changed=False, source_files=sources,
             solver_invocations=0, native_decodes=0, SHA_scans=0))
        before += [stat(capture), stat(archive), stat(diff), *sources]
        pdb_count = 0
        for index, argument in enumerate(compile_args):
            if index and compile_args[index - 1] == '-Xcompiler':
                compile_args[index], count = re.subn(r'(?i)(?<!\S)/Fd[^\s]+', '/Fdphysical.pdb', argument)
                pdb_count += count
        need(pdb_count == 1, 'One original host PDB token required')
        for index, argument in enumerate(compile_args):
            for prefix in (str(intdir), str(intdir).replace('\\', '/')):
                argument = re.sub(re.escape(prefix), lambda _: OUT.as_posix(), argument, flags=re.I)
            compile_args[index] = str(frozen / 'JSphGpu_ker.cu') if Path(argument).name.lower() == 'jsphgpu_ker.cu' else argument
        obj = OUT / 'JSphGpu_ker.cu.obj'
        need(compile_args.count('-o') == compile_args.count('--keep-dir') == 1, 'Original scratch/output flags differ')
        compile_args[compile_args.index('-o') + 1] = str(obj)
        compile_args[compile_args.index('--keep-dir') + 1] = str(OUT)
        compile_args.insert(0, '-I' + str(frozen))
        need(all(q in compile_args for q in ('--compile', '--machine', '64', '-cudart', 'static', '-use_fast_math', '-D_WITHGPU'))
             and any('compute_86' in q and 'sm_86' in q for q in compile_args)
             and any('/O2' in q and '/MT' in q for q in compile_args)
             and not any('C08_STAGE_TRACE' in q or 'C08_CAUSAL_TRACE' in q
                         or q in ('-G', '--device-link', '-dc') or 'rdc=true' in q for q in compile_args),
             'Original macro-off Release/sm86 flags differ')
        outputs = {'/out:': PROGRAM, '/pdb:': OUT / 'DualSPHysics5.2_GEO_win64.pdb',
                   '/implib:': OUT / 'DualSPHysics5.2_GEO_win64.lib',
                   '/ltcgout:': OUT / 'DualSPHysics5.2_GEO_win64.iobj'}
        linked, seen = [], set()
        for argument in link_args:
            if argument.lower().endswith('.obj') and Path(argument).resolve() == replaced[0]:
                argument = str(obj)
            for prefix, target in outputs.items():
                if argument.lower().startswith(prefix):
                    argument = prefix + str(target)
                    seen.add(prefix)
                    break
            linked.append(argument)
        link_objects = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        need(seen == set(outputs) and len(link_objects) == 113
             and set(link_objects) == set(retained) | {obj.resolve()}, 'One replacement plus112 retained objects required')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode == 0, 'MSVC environment setup failed')
        env = dict(os.environ)
        env.update(q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('='))
        need(env['VCTOOLSVERSION'] == '14.36.32532', 'Original MSVC14.36 required')
        for key in list(env):
            if key.upper() in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'):
                env.pop(key)
        need(compile_args.count('-ccbin') == 1, 'One original host-tool directory required')
        link = Path(compile_args[compile_args.index('-ccbin') + 1]) / 'link.exe'
        need('CUDA/v11.7' in nvcc.as_posix() and '/14.36.32532/' in link.as_posix(), 'Original CUDA/MSVC tools required')
        before += [stat(nvcc), stat(link)]
        libdirs = [S / 'VS'] + [(Path(q.split(':', 1)[1]) if Path(q.split(':', 1)[1]).is_absolute()
                   else S / 'VS' / q.split(':', 1)[1]) for q in linked if q.lower().startswith('/libpath:')]
        libdirs += [Path(q) for q in env.get('LIB', '').split(';') if q]
        for argument in linked:
            if argument.lower().endswith('.lib') and not argument.startswith('/'):
                candidates = [Path(argument)] if Path(argument).is_absolute() else [q / argument for q in libdirs]
                library = next((q for q in candidates if q.is_file()), None)
                need(library is not None, 'Original explicit link library missing: ' + argument)
                before.append(stat(library))
        need(all(stat(q['path']) == q for q in before), 'Consumed source/object/runtime changed before compilation')
        calls.append(invoke(TAG + '.compile', [str(nvcc), *compile_args], OUT, env))
        calls.append(invoke(TAG + '.link', [str(link), *linked], S / 'VS', env))
        copied = []
        for entry in runtime:
            destination = OUT / Path(entry['path']).name
            need(not destination.exists(), 'Existing private runtime destination protected')
            shutil.copy2(entry['path'], destination)
            need(Path(entry['path']).read_bytes() == destination.read_bytes()
                 and (stat(destination)['bytes'], stat(destination)['mtime_ns']) == (entry['bytes'], entry['mtime_ns']),
                 'Frozen runtime companion copy differs')
            copied.append(stat(destination))
        need(all(stat(q['path']) == q for q in before), 'Consumed source/object/runtime changed')
        save(check, dict(stage=TAG + '.build', passed=True, program=stat(PROGRAM),
             intervention='terminal_rejection_printf_only', configuration='Release',
             actual_typed_exit_code=0, actual_Win32_exit=0,
             baseline_source_build=stat(BASE), source_capture=stat(capture), source_archive=stat(archive),
             baseline_source_capture=capture_entry, baseline_source_archive=archive_entry,
             private_gpu_source=stat(frozen / 'JSphGpu_ker.cu'),
             private_wall_include=stat(frozen / 'JSphGpu_mdbc_ker.cuh'),
             exact_inverse_original_bytes=True, CXX_locals_added=False,
             original_physical_object=stat(replaced[0]), replacement_physical_object=stat(obj),
             retained_project_objects=[stat(q) for q in retained], physical_objects_recompiled=1,
             retained_physical_objects=112, actual_link_objects=113, compile_invocations=1, link_invocations=1,
             physical_compile_cwd=str(OUT), host_pdb='physical.pdb', runtime=copied, calls=calls,
             terminal_rejection_printf_only=True, primary_snapshot_added=False, trace_macros_enabled=False,
             public_interfaces_changed=False, production_source_changed=False, physical_arithmetic_changed=False,
             consumed=before, consumed_stats_unchanged=True, full_project_builds=0, solver_invocations=0,
             helper_program_invocations=0, smoke_invocations=0, native_decodes=0, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        actual_calls = [stat(L / (TAG + q)) for q in ('.compile.call.json', '.link.call.json')
                        if (L / (TAG + q)).is_file()]
        if not check.exists():
            save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error),
                 calls=actual_calls, consumed=before, full_project_builds=0, solver_invocations=0,
                 helper_program_invocations=0, smoke_invocations=0, native_decodes=0,
                 physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    arguments = parser.parse_args()
    need(arguments.execution_authorized, 'Author-only until root full-read and a later explicit build authorization')
    build()
