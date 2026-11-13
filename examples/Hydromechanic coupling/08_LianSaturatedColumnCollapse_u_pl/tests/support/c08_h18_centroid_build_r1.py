"""One source capture, then separately authorized ordered CPU Debug/GPU Debug/Release builds; never run."""
import argparse, difflib, os, re, shutil, subprocess, zipfile
from pathlib import Path, PurePosixPath
import c08_h18_wend_matrix_r1 as matrix

T, L = matrix.T, matrix.L
R = T.parents[3]
S = R / 'src'
TAG = 'c08_h18_centroid_build_r1'
NOTE = T / 'notes' / (TAG + '.md')
BASE = L / 'c08_preload_schema2_Release_r1.build.json'
CAP = T / 'outputs/c08_h18_centroid_source_r1'
PREP = L / (TAG + '.prepare.json')
TEMP = Path(os.environ['TEMP']).resolve() / 'c08_centroid_build_r1'
MSBUILD = Path('D:/Program Files/VS2022/MSBuild/Current/Bin/MSBuild.exe')
INTERVENTION = 'dynamic_wall_centroid_retry_once'
CHANGED = {'src/source/JSphCpu_mdbc.cpp', 'src/source/JSphGpu_mdbc_ker.cuh'}
DOC = R / 'doc/xml_format/_FmtXML_ElastoplasticSoil.xml'
SPECS = {
    'DebugCPU': ('DualSPHysics5ReCpu_vs2022.sln', 'DualSPHysics5.2CPU_win64_debug.exe', 87),
    'Debug': ('DualSPHysics5Re.sln', 'DualSPHysics5.2_win64_debug.exe', 113),
    'Release': ('DualSPHysics5Re.sln', 'DualSPHysics5.2_GEO_win64.exe', 113)}
need, read, stat, bind, save, invoke = matrix.need, matrix.read, matrix.stat, matrix.bind, matrix.save, matrix.invoke


def build_tag(configuration):
    return 'c08_h18_centroid_' + configuration + '_r1'


def prepare():
    need(not CAP.exists() and not PREP.exists() and not TEMP.exists(), 'Existing source capture or TEMP chain protected')
    before, differences, inventory = [], [], {}
    try:
        baseline = read(BASE)
        need(baseline['passed'] and baseline['configuration'] == 'Release' and baseline['consumed_stats_unchanged'],
             'Passed frozen schema2 baseline required')
        before = [stat(BASE), bind(baseline['source_capture']), bind(baseline['source_archive']),
                  stat(__file__), stat(NOTE), stat(matrix.__file__), stat(matrix.base.__file__), stat(DOC)]
        globs = ('*.h', '*.hpp', '*.cpp', '*.cu', '*.cuh', '*.inl', '*.c', '*.tpp')
        arguments = ['rg', '--files', 'source']
        for pattern in globs:
            arguments += ['-g', pattern]
        current = {'src/' + Path(q).as_posix() for q in subprocess.check_output(arguments, cwd=S, text=True).splitlines()}
        with zipfile.ZipFile(baseline['source_archive']['path']) as original:
            names = original.namelist()
            archived = {q for q in names if q.startswith('src/source/')}
            inventory = dict(added=sorted(current - archived), missing=sorted(archived - current))
            need(not inventory['added'] and not inventory['missing'], 'Current source inventory differs from frozen schema2')
            payload = {}
            inputs = []
            for name in names:
                member = PurePosixPath(name)
                need(not member.is_absolute() and '..' not in member.parts, 'Invalid original source member')
                path = R / Path(*member.parts)
                inputs.append(stat(path))
                payload[name] = path.read_bytes()
                if payload[name] != original.read(name):
                    differences.append(name)
            need(set(differences) == CHANGED, 'Actual source/project differences must be exactly the two reviewed mDBC files')
            need(all('tker==KERNEL_Wendland' in payload[q].decode('utf-8') for q in CHANGED),
                 'Current Wendland-only candidate guard missing')
            before += inputs
            canonical = [stat(R / 'bin/windows' / q) for q in
                         ('DualSPHysics5.2CPU_win64_debug.exe', 'DualSPHysics5.2_win64_debug.exe',
                          'DualSPHysics5.2CPU_win64.exe', 'DualSPHysics5.2_GEO_win64.exe')
                         if (R / 'bin/windows' / q).is_file()]
            runtime_leaves = ('DsphConfig.xml', 'ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll',
                              'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
            runtime = [bind(next(q['destination'] for q in baseline['runtime']
                                 if Path(q['destination']['path']).name == leaf)) for leaf in runtime_leaves]
            before += canonical + runtime
            matrix.verify(before)
            CAP.mkdir()
            archive = CAP / 'source.zip'
            with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as candidate:
                for name in names:
                    candidate.writestr(name, payload[name])
            diff = CAP / 'source.diff'
            diff.write_text(''.join(''.join(difflib.unified_diff(
                original.read(q).decode('utf-8').splitlines(True), payload[q].decode('utf-8').splitlines(True),
                fromfile='schema2/' + q, tofile='centroid/' + q)) for q in sorted(CHANGED)), encoding='utf-8')
        documentation = CAP / DOC.name
        with documentation.open('xb') as stream:
            stream.write(DOC.read_bytes())
        matrix.verify(before)
        capture = CAP / 'source.json'
        save(capture, dict(stage=TAG + '.source', intervention=INTERVENTION, archive=stat(archive),
             diff=stat(diff), source_files=inputs, actual_differences=sorted(differences),
             current_source_inventory=inventory, all_other_source_project_bytes_match=True,
             baseline_source_build=stat(BASE), baseline_source_capture=baseline['source_capture'],
             baseline_source_archive=baseline['source_archive'], documentation=stat(DOC),
             documentation_copy=stat(documentation), canonical_programs=canonical, runtime=runtime,
             consumed=before, consumed_stats_unchanged=True, SHA_scans=0))
        save(PREP, dict(stage=TAG + '.prepare', passed=True, prepared_only=True,
             source_capture=stat(capture), source_archive=stat(archive), actual_differences=sorted(differences),
             current_source_inventory=inventory, source_byte_comparisons_once=True,
             build_invocations=0, solver_invocations=0, native_decodes=0, SHA_scans=0))
    except Exception as error:
        if not PREP.exists():
            save(PREP, dict(stage=TAG + '.prepare', passed=False, first_failure=str(error),
                 actual_differences=sorted(differences), current_source_inventory=inventory,
                 consumed=before, build_invocations=0, solver_invocations=0, native_decodes=0, SHA_scans=0))
        raise


def build(configuration):
    tag = build_tag(configuration)
    out, intermediate = T / 'outputs' / tag, TEMP / configuration
    check = L / (tag + '.build.json')
    need(not out.exists() and not intermediate.exists() and all(not (L / (tag + q)).exists()
         for q in ('.build.json', '.call.json', '.log')), 'Existing configuration or partial invocation protected')
    need(' ' not in str(TEMP), 'Compiler bin/int root must be a no-space TEMP path')
    before, actual = [], None
    try:
        prepared = read(PREP)
        need(prepared['passed'] and prepared['prepared_only'], 'Successful one-time source prepare required')
        capture_entry, archive_entry = bind(prepared['source_capture']), bind(prepared['source_archive'])
        source = read(capture_entry['path'])
        need(source['intervention'] == INTERVENTION and source['archive'] == archive_entry
             and set(source['actual_differences']) == CHANGED and source['all_other_source_project_bytes_match'],
             'Reviewed two-file centroid capture required')
        before = [stat(PREP), capture_entry, archive_entry, stat(source['diff']['path']),
                  stat(source['documentation_copy']['path']), stat(__file__), stat(NOTE), stat(MSBUILD)]
        before += [bind(q) for q in source['consumed']]
        previous = None
        index = list(SPECS).index(configuration)
        if index:
            previous_path = L / (build_tag(list(SPECS)[index - 1]) + '.build.json')
            previous_build = read(previous_path)
            need(previous_build['passed'] and previous_build['source_capture'] == capture_entry
                 and previous_build['actual_typed_exit_code'] == previous_build['actual_Win32_exit'] == 0,
                 'Build order is DebugCPU, then Debug, then Release')
            previous = stat(previous_path)
            before.append(previous)
        solution, leaf, count = SPECS[configuration]
        project = (S / 'VS/DualSPHysics5Re.vcxproj').read_text(encoding='utf-8-sig')
        need('CUDA 11.7.props' in project and 'CUDA 11.7.targets' in project and 'compute_86,sm_86' in project,
             'Authoritative CUDA11.7/sm86 project differs')
        bin_dir, int_dir = intermediate / 'bin', intermediate / 'int'
        arguments = [str(S / 'VS' / solution), '/m', '/t:Build', '/p:Configuration=' + configuration,
                     '/p:Platform=x64', '/p:VCToolsVersion=14.36.32532', '/p:PostBuildEventUseInBuild=false',
                     '/p:OutDir=' + bin_dir.as_posix() + '/', '/p:IntDir=' + int_dir.as_posix() + '/', '/v:minimal']
        env = dict(os.environ)
        for key in list(env):
            if key.upper() in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'):
                env.pop(key)
        matrix.verify(before)
        out.mkdir()
        bin_dir.mkdir(parents=True)
        int_dir.mkdir()
        actual = invoke(tag, [str(MSBUILD), *arguments], S, env)
        call = read(bind(actual)['path'])
        need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0, 'Actual typed build exits differ')
        objects = [stat(q) for q in sorted(int_dir.glob('*.obj'))]
        need(len(objects) == count and sum(Path(q['path']).name.lower() == 'main.obj' for q in objects) == 1,
             'Actual authoritative project object closure differs')
        temporary_program = stat(bin_dir / leaf)
        shutil.copy2(temporary_program['path'], out / leaf)
        program = stat(out / leaf)
        need((program['bytes'], program['mtime_ns']) == (temporary_program['bytes'], temporary_program['mtime_ns']),
             'Isolated program copy stats differ')
        runtime = []
        for entry in source['runtime']:
            destination = out / Path(entry['path']).name
            shutil.copy2(entry['path'], destination)
            need(Path(entry['path']).read_bytes() == destination.read_bytes(), 'Frozen runtime copy differs')
            runtime.append(stat(destination))
        matrix.verify(before)
        text = (L / (tag + '.log')).read_bytes().decode('mbcs', errors='replace')
        save(check, dict(stage=tag + '.build', passed=True, configuration=configuration, program=program,
             actual_typed_exit_code=0, actual_Win32_exit=0, actual_call=actual, intervention=INTERVENTION,
             source_capture=capture_entry, source_archive=archive_entry, source_differences=source['actual_differences'],
             baseline_source_build=source['baseline_source_build'], baseline_source_capture=source['baseline_source_capture'],
             baseline_source_archive=source['baseline_source_archive'], previous_build=previous,
             temporary_program=temporary_program, intermediate=str(int_dir), compiler_bin_dir=str(bin_dir),
             project_objects=objects, actual_link_objects=count, runtime=runtime, trace_macros_enabled=False,
             postbuild_disabled=True, canonical_programs_unchanged=True, source_stats_unchanged=True,
             consumed=before, consumed_stats_unchanged=True,
             warning_lines=[q for q in text.splitlines() if re.search(r'\bwarning [A-Z]+\d+', q, re.I)],
             build_invocations=1, solver_invocations=0, help_invocations=0, smoke_invocations=0,
             native_decodes=0, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        call_path = L / (tag + '.call.json')
        if actual is None and call_path.is_file():
            actual = stat(call_path)
        if not check.exists():
            save(check, dict(stage=tag + '.build', passed=False, configuration=configuration,
                 first_failure=str(error), actual_call=actual, consumed=before, solver_invocations=0,
                 help_invocations=0, smoke_invocations=0, native_decodes=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=('prepare', *SPECS), default='DebugCPU')
    parser.add_argument('--execution-authorized', action='store_true')
    arguments = parser.parse_args()
    need(arguments.execution_authorized, 'Author-only until root full-read and explicit single-action authorization')
    prepare() if arguments.action == 'prepare' else build(arguments.action)
