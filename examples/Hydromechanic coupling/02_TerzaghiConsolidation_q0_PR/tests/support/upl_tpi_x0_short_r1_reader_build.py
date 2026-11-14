"""Build one private DebugCPU reader from a retained MSVC recipe; never run it."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

T = Path(__file__).resolve().parents[1]
R = T.parents[3]
S, L = R/'src', T/'logs'
C8 = T.parent.parent/'08_LianSaturatedColumnCollapse_u_pl/tests'
sys.path.insert(0, str(C8/'support'))
import mdbc_partition_components_r3 as owned

# Reuse the existing actual Win32/Popen owner helper, with this test's log directory.
# This changes only a process-local module variable; no imported file is edited.
owned.L = L
need, read, stat, bind, save, invoke = (owned.need, owned.read, owned.stat,
                                      owned.bind, owned.save, owned.invoke)
TAG = 'upl_tpi_x0_short_r1_reader'
OUT, CHECK = T/'outputs'/(TAG+'_build'), L/(TAG+'.build.json')
CPP = T/'support/upl_tpi_x0_short_r1_native.cpp'
CORE = T/'support/upl_cpu_public_native_r1.cpp'
NOTE = T/'notes/upl_tpi_x0_short_r1.md'
BASE = C8/'logs/c08_h18_as03_rhs_r1.build.json'
COMPILE = C8/'logs/c08_h18_as03_rhs_r1.compile.call.json'
LINK = C8/'logs/c08_h18_as03_rhs_r1.link.call.json'
OLD_CPP = C8/'support/c08_h18_as03_rhs_r1.cpp'


def verify(rows):
    for row in rows:
        bind(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    need(parser.parse_args().execution_authorized, 'Root must review and admit reader build separately')
    calls, before = [], []
    stages = (TAG+'.compile', TAG+'.link')
    need(not OUT.exists() and not CHECK.exists() and all(
        not (L/(tag+suffix)).exists() for tag in stages for suffix in ('.log', '.call.json')),
        'Existing failed/partial/successful reader build protected')
    try:
        b, c, l = read(BASE), read(COMPILE), read(LINK)
        need(b['passed'] and b['configuration']=='DebugCPU' and b['consumed_stats_unchanged']
             and b['original_Single_no_hook'] and b['physical_objects_compiled']==0,
             'Retained authoritative DebugCPU closure required')
        for receipt in (c, l):
            need(receipt['actual_Popen_wait_exit']==receipt['actual_Win32_exit']==0
                 and receipt['ownership_failure'] is None, 'Original compiler/link actual exits differ')
        objects = [bind(q) for q in b['retained_physical_objects']]
        headers = [bind(q) for q in b['archived_headers']]
        runtime = [bind(q) for q in b['runtime']]
        need(len(objects)==86 and len(headers)==160 and len(runtime)==7,
             'Exactly86 retained non-main objects/160 private headers/7 runtime files required')
        before = [stat(q) for q in (Path(__file__), CPP, CORE, NOTE, BASE, COMPILE, LINK,
                                    Path(owned.__file__))] + objects + headers + runtime
        before += [bind(b[k]) for k in ('source_build', 'source_capture', 'source_archive', 'original_object_list')]
        inventory = read(b['original_object_list']['path'])
        tlog = bind(inventory['resolved_library_tlog'])
        libraries = [Path(q.strip('"')).resolve() for q in Path(tlog['path']).read_text(
            encoding='utf-16').splitlines() if not q.startswith('^') and q.lower().endswith('.lib')]
        need(libraries, 'Resolved authoritative library closure missing')
        before += [tlog, *[stat(q) for q in libraries], stat(c['program']), stat(l['program'])]
        oldroot = Path(b['program']['path']).parent
        ca = [str(CPP) if q==str(OLD_CPP) else q if q.lower().startswith('/i') else
              q.replace(str(oldroot), str(OUT)) for q in c['arguments']]
        exe = OUT/'UplTpiX0ShortNative.exe'
        la = [q.replace(str(oldroot), str(OUT)).replace(Path(b['program']['path']).name,
              exe.name) for q in l['arguments']]
        roots = [Path(q[2:]).resolve() for q in ca if q.startswith('/I')]
        need(len(roots)==1 and ca.count(str(CPP))==1 and all(q in ca for q in
             ('/Od', '/MTd', '/RTC1', '/fp:precise', '/std:c++17')),
             'Retained DebugCPU source/header/ABI recipe differs')
        linked = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(len(linked)==len(set(linked))==87 and set(linked)==
             {Path(q['path']).resolve() for q in objects}|{(OUT/'entry.obj').resolve()},
             'Exactly one new reader entry and86 old objects required')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0, 'Original MSVC setup failed')
        env = {k.upper():v for k, v in os.environ.items()}
        env.update((k.upper(),v) for k,v in (q.split('=',1) for q in
            setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        need(env['VCTOOLSVERSION']=='14.36.32532', 'Retained MSVC version required')
        env.pop('CL', None); env.pop('_CL_', None)
        env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        verify(before); OUT.mkdir()
        calls.append(invoke(stages[0], [c['program'], *ca], S/'VS', env))
        dependency = OUT/'dependencies.json'
        dep = read(dependency)['Data']
        actual = {Path(q).resolve() for q in dep['Includes']}
        headerroot = roots[0]
        names = {Path(q['path']).name.lower() for q in headers}
        need(Path(dep['Source']).resolve()==CPP.resolve() and CORE.resolve() in actual
             and all((headerroot/q).resolve() in actual for q in ('JPartDataBi4.h','JBinaryData.h','JAppInfo.h'))
             and all(q.is_relative_to(headerroot) for q in actual if q.name.lower() in names)
             and all(not q.is_relative_to((S/'source').resolve()) for q in actual),
             'Actual reader dependency/source/private-header closure differs')
        calls.append(invoke(stages[1], [l['program'], *la], S/'VS', env))
        copies = []
        for q in runtime:
            dest = OUT/Path(q['path']).name
            shutil.copy2(q['path'], dest)
            need(dest.read_bytes()==Path(q['path']).read_bytes(), 'Runtime copy differs')
            copies.append(stat(dest))
        verify(before)
        save(CHECK, dict(stage=TAG+'.build', passed=True, configuration='DebugCPU',
             program=stat(exe), source=stat(CPP), core=stat(CORE), note=stat(NOTE),
             source_build=b['source_build'], source_capture=b['source_capture'],
             source_archive=b['source_archive'], original_object_list=b['original_object_list'],
             retained_physical_objects=objects, archived_headers=headers, runtime=copies,
             dependencies=stat(dependency), actual_link_objects=87, new_reader_objects=1,
             physical_objects_compiled=0, calls=calls, consumed=before,
             consumed_stats_unchanged=True, compiler_invocations=1, linker_invocations=1,
             reader_invocations=0, solver_invocations=0, help_invocations=0,
             public_source_changed=False, canonical_programs_changed=False,
             SHA_scans=0, physical_acceptance=False))
    except Exception as error:
        if not CHECK.exists():
            save(CHECK, dict(stage=TAG+'.build', passed=False, first_failure=str(error),
                 calls=calls, attempted_call_paths=[str(L/(q+'.call.json')) for q in stages],
                 consumed=before, partial_outputs_preserved=True, reader_invocations=0,
                 solver_invocations=0, SHA_scans=0, physical_acceptance=False))
        raise


if __name__=='__main__':
    main()
