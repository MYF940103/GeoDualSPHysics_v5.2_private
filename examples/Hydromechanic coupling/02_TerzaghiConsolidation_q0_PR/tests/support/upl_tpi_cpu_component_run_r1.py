"""Root-reviewed isolated compilation and two pure helper-component invocations."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil

T = Path(__file__).resolve().parents[1]
TAG = 'upl_tpi_cpu_component_r1'
ROOT = T / 'outputs' / TAG
CHECK = T / 'logs' / (TAG + '.check.json')
CPP = T / 'support' / (TAG + '.cpp')
NOTE = T / 'notes' / (TAG + '.md')
HELPER = T / 'support/upl_tpi_cpu_r1.h'
PREP = T / 'logs/upl_tpi_cpu_r1.prepare.json'
BUILD = T / 'logs/upl_tpi_cpu_DebugCPU_r2.build.json'
BUILDER = T / 'support/upl_tpi_cpu_build_r2.py'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    p.add_argument('--admission', required=True, type=Path)
    a = p.parse_args()
    if not a.execution_authorized:
        raise RuntimeError('Root full-read/component-only admission required')
    spec = importlib.util.spec_from_file_location('reviewed_tpi_build_tools', BUILDER)
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)  # Guarded module; no main/build/program invocation.
    b.need(not ROOT.exists() and not CHECK.exists(), 'Existing component outputs protected')
    adm = b.read(a.admission)
    b.need(adm.get('stage') == TAG + '.admission' and adm.get('passed') is True
           and adm.get('component_only') is True, 'Independent component admission required')
    frozen = {str(Path(x['path']).resolve()): x for x in adm['inputs']}
    for item in (Path(__file__), CPP, NOTE, HELPER, PREP, BUILD, BUILDER):
        b.need(str(item.resolve()) in frozen, 'Unpinned component input ' + str(item))
    consumed = [b.same(x) for x in frozen.values()] + [b.stat(a.admission)]
    prepared, built = b.read(PREP), b.read(BUILD)
    b.need(prepared['passed'] is True and built['passed'] is True,
           'Prepared overlay and genuine CPU Debug build required')
    source = Path(prepared['source_root'])
    b.need((source / 'upl_tpi_cpu_r1.h').read_bytes() == HELPER.read_bytes(),
           'Component helper differs from frozen candidate')
    consumed += [b.same(x) for x in prepared['files']]
    ROOT.mkdir()
    result = dict(stage=TAG, passed=False, root_admission=b.stat(a.admission),
                  physical_acceptance=False, solver_invocations=0, native_invocations=0,
                  SHA_scans=0, pure_component=True, calls=[], consumed=consumed)
    try:
        cpp = ROOT / 'component.cpp'
        shutil.copy2(CPP, cpp)  # Quote-includes resolve to frozen source, not live support/.
        script = ROOT / 'load_environment.cmd'
        with script.open('x', encoding='mbcs', newline='') as f:
            f.write('@echo off\r\ncall "' + str(b.VCVARS)
                    + '" x64 -vcvars_ver=14.36 >nul\r\n'
                    + 'if errorlevel 1 exit /b %errorlevel%\r\nset\r\n')
        call, raw = b.invoke(TAG + '.environment',
            [os.environ.get('COMSPEC', 'C:/Windows/System32/cmd.exe'), '/d', '/s', '/c', script.name],
            ROOT, os.environ.copy(), True)
        result['calls'].append(call)
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in
                   (line.split('=', 1) for line in raw.decode('mbcs').splitlines()
                    if '=' in line and not line.startswith('=')))
        env.pop('CL', None)
        env.pop('_CL_', None)
        b.need(env.get('VCTOOLSVERSION') == '14.36.32532', 'Reviewed v143 toolset changed')
        cl = Path(env['VCTOOLSINSTALLDIR']) / 'bin/Hostx64/x64/cl.exe'
        exe = ROOT / 'component.exe'
        deps = ROOT / 'dependencies.json'
        args = [str(cl), '/nologo', '/W3', '/WX-', '/EHsc', '/MTd', '/Od', '/Zi',
                '/fp:precise', '/std:c++14', '/I' + str(source),
                '/Fo' + str(ROOT / 'component.obj'), '/Fd' + str(ROOT / 'component_compile.pdb'),
                '/Fe' + str(exe), '/sourceDependencies', str(deps), str(cpp),
                '/link', '/DEBUG', '/PDB:' + str(ROOT / 'component_link.pdb'),
                '/ILK:' + str(ROOT / 'component.ilk')]
        call, _ = b.invoke(TAG + '.compile', args, ROOT, env)
        result['calls'].append(call)
        data = b.read(deps)['Data']
        includes = {Path(x).resolve() for x in data['Includes']}
        b.need(Path(data['Source']).resolve() == cpp.resolve()
               and source / 'upl_tpi_cpu_r1.h' in includes
               and source / 'JSphHourglassCpu.h' in includes
               and source / 'DualSphDef.h' in includes,
               'Actual helper/frozen base header dependency proof missing')
        b.need(all(not x.is_relative_to((b.S / 'source').resolve()) for x in includes),
               'Component consumed a live public header')
        summaries = []
        for scheme in ('B', 'C'):
            dest = ROOT / scheme
            call, _ = b.invoke(TAG + '.' + scheme, [str(exe), '--scheme', scheme, '--output', str(dest)],
                               ROOT, env)
            result['calls'].append(call)
            receipt = dest / 'component.summary.json'
            q = b.read(receipt)
            b.need(q['passed'] is True and q['scheme'] == scheme
                   and q['actual_helper_used'] is True and q['solver_invocations'] == 0
                   and q['native_invocations'] == 0 and q['physical_acceptance'] is False,
                   'Pure component did not genuinely complete')
            summaries.append(dict(receipt=b.stat(receipt), result=q))
        for x in consumed:
            b.same(x)
        result.update(passed=True, program=b.stat(exe), dependency_manifest=b.stat(deps),
                      actual_component_processes=2, summaries=summaries, consumed_stats_unchanged=True,
                      outputs=[b.stat(x) for x in ROOT.rglob('*') if x.is_file()])
    except Exception as exc:
        result.update(first_failure=str(exc), partials_preserved=True, followup_launched=False)
        raise
    finally:
        b.write_new(CHECK, result)
    print(str(CHECK))


if __name__ == '__main__':
    main()
