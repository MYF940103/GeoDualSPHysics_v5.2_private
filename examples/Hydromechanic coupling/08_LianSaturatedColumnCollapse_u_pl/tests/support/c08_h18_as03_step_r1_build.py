"""Build only one AS03 onset-step entry plus86 unchanged original CPU objects."""
import argparse
import os
import shutil
import subprocess
from pathlib import Path
import c08_h18_as03_rhs_r1_build as prior

m, T, L, S = prior.m, prior.T, prior.L, prior.S
TAG = 'c08_h18_as03_step_r1'
CPP, NOTE = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
OUT = T / 'outputs' / (TAG + '_build')
BASE = L / 'c08_h18_as03_rhs_r1.build.json'
RHS = L / 'c08_h18_as03_rhs_r1.check.json'
OLD_CPP = T / 'support/c08_h18_late_step_r1.cpp'
OLD_BUILD = L / 'c08_h18_late_step_r1.build.json'
OLD_CHECK = L / 'c08_h18_late_step_r1_p200.check.json'
SOURCE_CPP = T / 'support/c08_h18_as03_rhs_r1.cpp'


def derivation():
    old = OLD_CPP.read_bytes(); new = CPP.read_bytes()
    replacements = (
        ('c08_h18_late_step_r1', TAG),
        ('c08_h18_n255_full3_r1', 'c08_h18_as03n255_full3_r1'),
        ('c08_h18_n255_full3_native_r1.check.json', 'c08_h18_as03n255_full3_native_r1.check.json'),
        ('c08_h18_n255_full3_review_r1.check.json', 'c08_h18_as03n255_full3_review_r1.check.json'),
        ('c08_h18_late_rhs_r1.check.json', 'c08_h18_as03_rhs_r1.check.json'),
        ('ArtificialStressCoef==.5f', 'ArtificialStressCoef==.3f'),
        ('Need((a.part==200&&completed==2400001)||(a.part==250&&completed==2500001)||(a.part==300&&completed==2600000),"Only three selected completed late states admitted");',
         'Need((a.part==38&&completed==2076001)||(a.part==76&&completed==2152001),"Only two selected completed onset states admitted");'),
        ('Need((requested==200||requested==250||requested==300)&&std::to_string(requested)==argv[5],"Only exact parts200/250/300 admitted");const unsigned selected=(requested==200?0:requested==250?1:2);',
         'Need((requested==38||requested==76)&&std::to_string(requested)==argv[5],"Only exact parts38/76 admitted");const unsigned selected=(requested==38?0:1);'),
    )
    changed = old; counts = []
    for a, b in replacements:
        aa, bb = a.encode(), b.encode(); count = changed.count(aa)
        m.need(count > 0 and bb not in changed, 'Unique original profile/path transform unavailable: ' + a)
        changed = changed.replace(aa, bb); counts.append(dict(old=a, new=b, count=count))
    m.need(new == changed, 'AS03 step entry differs from the exact profile/path-only transformation')
    blocks = (
        (b'struct StepState{', b'  void ExecuteStep('),
        (b'      // Original ComputeStep_Sym call order;', b'    Need(Bits(ddtp,dt)'),
        (b'    // Pure same-input material shadows', b'    // Outer Run owns'),
    )
    for begin, end in blocks:
        m.need(old.count(begin) == old.count(end) == new.count(begin) == new.count(end) == 1,
               'Unique unchanged state/material/step/trace block required')
        m.need(old[old.index(begin):old.index(end)] == new[new.index(begin):new.index(end)],
               'Original state capture, physical step calls or material/trace arithmetic changed')
    raw = SOURCE_CPP.read_bytes()
    access, app = b'class Probe:public JSphCpuSingle{', b'JAppInfo AppInfo("C08H18As03Rhs","r1","14-11-2026");'
    m.need(raw.count(access) == raw.count(app) == 1 and
           b'Parts[2]={38,76},Steps[2]={2076001,2152001}' in raw,
           'Exact previously qualified AS03 two-state loader required')
    shared = raw.replace(access, access + b'\nprotected:', 1).replace(
        app, b'JAppInfo AppInfo("C08H18As03Step","r1","14-11-2026");', 1)
    return shared, dict(exact_entry_replacements=counts,
        unchanged_step_capture_material_trace_blocks=True, original_step=m.stat(OLD_CPP),
        shared_source=m.stat(SOURCE_CPP), shared_transform=['protected access', 'diagnostic AppInfo only'],
        actual_step_call_block_byte_equal=True, public_source_changed=False,
        material_model_or_apex_changed=False, new_physical_steps_authorized_by_build=0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    m.need(p.parse_args().execution_authorized, 'Independent root build admission required; no component execution')
    check = L / (TAG + '.build.json'); stages = (TAG + '.compile', TAG + '.link')
    m.need(not OUT.exists() and not check.exists() and all(not (L / (q + s)).exists()
           for q in stages for s in ('.call.json', '.log')), 'Existing complete/partial build protected')
    before, calls = [], []
    try:
        base, rhs, oldbuild, oldcheck = map(m.read, (BASE, RHS, OLD_BUILD, OLD_CHECK))
        m.need(base['passed'] and base['configuration'] == 'DebugCPU' and base['consumed_stats_unchanged']
               and base['original_Single_no_hook'] and base['physical_objects_compiled'] == 0
               and base['actual_link_objects'] == 87 and base['source'] == m.stat(SOURCE_CPP),
               'Original AS03 RHS/86-object no-hook build required')
        rhsdone = m.read(m.bind(rhs['completion'])['path'])
        m.need(rhs['passed'] and rhs['consumed_stats_unchanged'] and rhs['component_invocations'] == 1
               and rhs['physical_steps'] == 0 and rhsdone['passed'] and rhsdone['source_parts'] == [38, 76]
               and rhsdone['soil_rows'] == rhsdone['literal_final_float_bits_matched'] == 10000,
               'Already completed exact AS03 two-state zero-step qualification required')
        m.need(oldbuild['passed'] and oldbuild['consumed_stats_unchanged'] and
               oldbuild['source'] == m.stat(OLD_CPP) and oldbuild['source_archive'] == base['source_archive']
               and oldbuild['original_Single_no_hook'] and oldbuild['physical_objects_compiled'] == 0
               and oldcheck['passed'] and oldcheck['consumed_stats_unchanged'] and oldcheck['physical_steps'] == 1,
               'Sealed original one-step/shadow policy and actual source archive required')
        shared, proof = derivation()
        cpath, lpath = [L / ('c08_h18_as03_rhs_r1' + suffix) for suffix in
                        ('.compile.call.json', '.link.call.json')]
        c, linkcall = map(m.read, (cpath, lpath))
        m.need(c['actual_Popen_wait_exit'] == c['actual_Win32_exit'] == linkcall['actual_Popen_wait_exit'] ==
               linkcall['actual_Win32_exit'] == 0 and c['ownership_failure'] is linkcall['ownership_failure'] is None,
               'Successful actual original CL/link recipes required')
        objects = [m.bind(q) for q in base['retained_physical_objects']]
        headers = [m.bind(q) for q in base['archived_headers']]
        runtime = [m.bind(q) for q in base['runtime']]
        m.need(len(objects) == 86 and len(headers) == 160 and len(runtime) == 7,
               'Exactly86 original physical objects/160 archived headers/7 companions required')
        before = [m.stat(q) for q in (Path(__file__), NOTE, CPP, OLD_CPP, SOURCE_CPP, Path(prior.__file__),
                  BASE, RHS, OLD_BUILD, OLD_CHECK, cpath, lpath)] + objects + headers + runtime
        before += [m.bind(base[k]) for k in ('source_build', 'source_capture', 'source_archive', 'original_object_list')]
        before += [m.bind(rhs[k]) for k in ('actual_call', 'completion')]
        before += [m.bind(oldcheck[k]) for k in ('actual_call', 'completion')]
        old_root = Path(base['program']['path']).parent
        object_list = m.read(base['original_object_list']['path'])
        lib_tlog = m.bind(object_list['resolved_library_tlog']); before.append(lib_tlog)
        libraries = [Path(q.strip('"')).resolve() for q in Path(lib_tlog['path']).read_text(encoding='utf-16').splitlines()
                     if not q.startswith('^') and q.lower().endswith('.lib')]
        before += [m.stat(q) for q in libraries]
        ca = [str(CPP) if q == str(SOURCE_CPP) else q if q.lower().startswith('/i') else
              q.replace(str(old_root), str(OUT)) for q in c['arguments']]
        exe = OUT / 'C08H18As03StepR1.exe'
        la = [q.replace(str(old_root), str(OUT)).replace(Path(base['program']['path']).name, exe.name)
              for q in linkcall['arguments']]
        roots = [Path(q[2:]).resolve() for q in ca if q.startswith('/I')]
        m.need(sum(q == str(CPP) for q in ca) == 1 and len(roots) == 1 and
               all(q in ca for q in ('/Od', '/MTd', '/RTC1', '/fp:precise', '/openmp', '/std:c++17')),
               'Original frozen-header CPU ABI required')
        headerroot = roots[0]
        final = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        m.need(len(final) == len(set(final)) == 87 and
               set(final) == {Path(q['path']).resolve() for q in objects} | {(OUT / 'entry.obj').resolve()},
               'Only one new entry and86 unchanged original objects may be linked')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Matching original MSVC environment failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in
            setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532' and libraries, 'Original compiler/library ABI required')
        env.pop('CL', None); env.pop('_CL_', None)
        env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        before += [m.stat(c['program']), m.stat(linkcall['program'])]
        m.verify(before); OUT.mkdir(); include = OUT / 'shared.inc'
        with include.open('xb') as f: f.write(shared)
        before.append(m.stat(include))
        calls.append(m.invoke(stages[0], [c['program'], *ca], S / 'VS', env))
        deps = m.read(OUT / 'dependencies.json')['Data']
        includes = {Path(q).resolve() for q in deps['Includes']}
        names = {Path(q['path']).name.lower() for q in headers}
        m.need(Path(deps['Source']).resolve() == CPP.resolve() and include.resolve() in includes and
               all((headerroot / q).resolve() in includes for q in
                   ('JSph.h', 'JSphCpu.h', 'JSphCpuSingle.h', 'FunSoilMaterial.h', 'FunSphKernel.h')) and
               all(q.is_relative_to(headerroot) for q in includes if q.name.lower() in names) and
               all(not q.is_relative_to((S / 'source').resolve()) for q in includes),
               'Actual compile leaked public headers or missed frozen material/shared source')
        calls.append(m.invoke(stages[1], [linkcall['program'], *la], S / 'VS', env))
        copied = []
        for q in runtime:
            dest = OUT / Path(q['path']).name; shutil.copy2(q['path'], dest)
            m.need(dest.read_bytes() == Path(q['path']).read_bytes(), 'Frozen runtime copy differs')
            copied.append(m.stat(dest))
        m.verify(before)
        m.save(check, dict(stage=TAG + '.build', passed=True, configuration='DebugCPU', program=m.stat(exe),
            source=m.stat(CPP), note=m.stat(NOTE), source_build=base['source_build'],
            source_capture=base['source_capture'], source_archive=base['source_archive'],
            generated_shared_include=m.stat(include), shared_source=m.stat(SOURCE_CPP), entry_derivation=proof,
            retained_physical_objects=objects, archived_headers=headers, original_Single_no_hook=True,
            actual_link_objects=87, physical_objects_compiled=0, new_entry_objects=1,
            allowed_parts=[38, 76], each_separate_component_max_physical_steps=1,
            material_shadow_not_feedback=True, all_original_material_and_trace_gates_required=True,
            source_zero_step_qualification=m.stat(RHS), original_one_step_qualification=m.stat(OLD_CHECK),
            dependencies=m.stat(OUT / 'dependencies.json'), runtime=copied, calls=calls,
            consumed=before, consumed_stats_unchanged=True, compile_invocations=1, link_invocations=1,
            component_invocations=0, solver_invocations=0, GPU_actions=0, SHA_scans=0,
            no_automatic_component_or_solver=True, public_source_changed=False, physical_acceptance=False))
    except Exception as error:
        if not check.exists():
            m.save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=calls,
                consumed=before, partial_outputs_preserved=True, component_invocations=0,
                solver_invocations=0, GPU_actions=0, SHA_scans=0, physical_acceptance=False))
        raise


if __name__ == '__main__': main()
