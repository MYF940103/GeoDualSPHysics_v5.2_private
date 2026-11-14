"""Build one private zero-advance pressure-feedback entry; never run the component."""
import argparse
import os
import shutil
import subprocess
from pathlib import Path
import c08_h18_as03_rhs_r1_build as prior

m, T, L, S = prior.m, prior.T, prior.L, prior.S
TAG = 'c08_h18_pressure_feedback_r1'
CPP, NOTE = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
OUT = T / 'outputs' / (TAG + '_build')
BASE, RHS, MODES = (L / q for q in ('c08_h18_as03_rhs_r1.build.json',
    'c08_h18_as03_rhs_r1.check.json', 'c08_h18_global_modes_r1.check.json'))
RHS_CPP = T / 'support/c08_h18_as03_rhs_r1.cpp'
MODE_CPP = T / 'support/c08_h18_global_modes_r1.cpp'


def block(raw, begin, end):
    m.need(raw.count(begin) == raw.count(end) == 1, 'Frozen shared-fragment anchors differ')
    a, b = raw.index(begin), raw.index(end)
    m.need(a < b, 'Frozen shared-fragment ordering differs')
    return raw[a:b]


def fragments():
    raw, force = RHS_CPP.read_bytes(), MODE_CPP.read_bytes()
    access = b'class Probe:public JSphCpuSingle{'
    app = b'JAppInfo AppInfo("C08H18As03Rhs","r1","14-11-2026");'
    m.need(raw.count(access) == raw.count(app) == 1 and
        b'Parts[2]={38,76},Steps[2]={2076001,2152001}' in raw,
        'Original qualified AS03 two-state completed loader required')
    shared = raw.replace(access, access + b'\nprotected:', 1).replace(app,
        b'JAppInfo AppInfo("C08H18PressureFeedback","r1","14-11-2026");', 1)
    parts = {
        'shared.inc': shared,
        'interior_mask.inc': block(force, b'  std::vector<byte> InteriorMask()const{', b'  std::array<unsigned,2> GlobalModes('),
        'setup.inc': block(raw, b'    AppName=AppInfo.GetFullName();', b'    std::ofstream soil('),
        'rhs_literal.inc': block(raw, b'        // Literal original raw-FS source operation order,', b'        const auto H=z.gp+ai*rho;'),
    }
    # Reversal proves the only changes to the complete original source are access and AppInfo.
    inverse = shared.replace(access + b'\nprotected:', access, 1).replace(
        b'JAppInfo AppInfo("C08H18PressureFeedback","r1","14-11-2026");', app, 1)
    m.need(inverse == raw, 'Unexpected original loader/RHS edit')
    return parts, dict(shared_transform=['protected access', 'diagnostic AppInfo'],
        shared_inverse_byte_equal=True, original_rhs=m.stat(RHS_CPP),
        original_force=m.stat(MODE_CPP), literal_RHS_and_interior_mask_fragments_byte_equal=True,
        actual_original_force_called_without_reimplementation=True, original_state_and_Assemble_unchanged=True,
        public_source_changed=False, physical_objects_recompiled=0)


def bound_file(receipt, path):
    target = path.resolve()
    return m.bind(next(q for q in receipt['files'] if Path(q['path']).resolve() == target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    m.need(parser.parse_args().execution_authorized,
           'Independent root build admission required; no component invocation is included')
    check = L / (TAG + '.build.json'); stages = (TAG + '.compile', TAG + '.link')
    m.need(not OUT.exists() and not check.exists() and all(not (L / (q + suffix)).exists()
           for q in stages for suffix in ('.call.json', '.log')),
           'Existing failed/partial/complete build is immutable')
    before, calls = [], []
    try:
        base, rhs, modes = map(m.read, (BASE, RHS, MODES))
        m.need(base['passed'] and base['configuration'] == 'DebugCPU' and
            base['consumed_stats_unchanged'] and base['original_Single_no_hook'] and
            base['physical_objects_compiled'] == 0 and base['actual_link_objects'] == 87 and
            base['source'] == m.stat(RHS_CPP), 'Passed original AS03 frozen86-object build required')
        for receipt in (rhs, modes):
            call = m.read(m.bind(receipt['actual_call'])['path'])
            done = m.read(m.bind(receipt['completion'])['path'])
            m.need(receipt['passed'] and receipt['consumed_stats_unchanged'] and
                receipt['component_invocations'] == 1 and receipt['physical_steps'] == 0 and
                call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and done['passed'],
                'Already passed original RHS/global-mode implementations required')
        rd, md = [m.read(m.bind(q['completion'])['path']) for q in (rhs, modes)]
        m.need(rd['source_parts'] == [38, 76] and rd['actual_force_calls'] == 2 and
            rd['soil_rows'] == rd['literal_final_float_bits_matched'] == 10000 and
            md['source_parts'] == [38, 76, 92, 300] and md['force_calls'] == 4 and
            md['mode_field_rows'] == 140000, 'Original numeric/phase coverage differs')
        modebuild = m.read(m.bind(modes['build'])['path'])
        m.need(modebuild['passed'] and modebuild['source'] == m.stat(MODE_CPP) and
            modebuild['source_archive'] == base['source_archive'], 'Force/pressure archive mismatch')
        generated, proof = fragments()
        cpath, lpath = [L / ('c08_h18_as03_rhs_r1' + q) for q in
                       ('.compile.call.json', '.link.call.json')]
        c, link = map(m.read, (cpath, lpath))
        m.need(c['actual_Popen_wait_exit'] == c['actual_Win32_exit'] ==
            link['actual_Popen_wait_exit'] == link['actual_Win32_exit'] == 0 and
            c['ownership_failure'] is link['ownership_failure'] is None,
            'Original real compiler/link recipes must be successful')
        objects = [m.bind(q) for q in base['retained_physical_objects']]
        headers = [m.bind(q) for q in base['archived_headers']]
        runtime = [m.bind(q) for q in base['runtime']]
        m.need(len(objects) == 86 and len(headers) == 160 and len(runtime) == 7,
               'Exactly86 physical objects/160 archived headers/7 runtime files required')
        before = [m.stat(q) for q in (Path(__file__), CPP, NOTE, RHS_CPP, MODE_CPP,
                  Path(prior.__file__), BASE, RHS, MODES, cpath, lpath)] + objects + headers + runtime
        before += [m.bind(base[k]) for k in ('source_build', 'source_capture', 'source_archive', 'original_object_list')]
        for receipt in (rhs, modes):
            before += [m.bind(receipt[k]) for k in ('actual_call', 'completion', 'build')]
        before += [bound_file(rhs, T / 'outputs/c08_h18_as03_rhs_r1/soil_rhs.csv'),
                   bound_file(modes, T / 'outputs/c08_h18_global_modes_r1/mode_fields.csv')]
        native = T / 'outputs/c08_h18_as03n255_full3_r1/native_r1'
        reviewpath = L / 'c08_h18_as03n255_full3_review_r1.check.json'
        review = m.read(reviewpath)
        m.need(review['analysis_complete'] and review['consumed_stats_unchanged'] and
               review['actual_samples'] == 301, 'Retained full301 review required')
        before.append(m.stat(reviewpath))
        for leaf in ('typed22.bin', 'typed22_layout.csv', 'clocks.csv'):
            target = (native / leaf).resolve()
            before.append(m.bind(next(q for q in review['consumed'] if Path(q['path']).resolve() == target)))
        oldroot = Path(base['program']['path']).parent
        object_list = m.read(m.bind(base['original_object_list'])['path'])
        lib_tlog = m.bind(object_list['resolved_library_tlog']); before.append(lib_tlog)
        libraries = [Path(q.strip('"')).resolve() for q in Path(lib_tlog['path']).read_text(encoding='utf-16').splitlines()
                     if not q.startswith('^') and q.lower().endswith('.lib')]
        before += [m.stat(q) for q in libraries]
        ca = [str(CPP) if q == str(RHS_CPP) else q if q.lower().startswith('/i') else
              q.replace(str(oldroot), str(OUT)) for q in c['arguments']]
        exe = OUT / 'C08H18PressureFeedbackR1.exe'
        la = [q.replace(str(oldroot), str(OUT)).replace(Path(base['program']['path']).name, exe.name)
              for q in link['arguments']]
        roots = [Path(q[2:]).resolve() for q in ca if q.startswith('/I')]
        m.need(sum(q == str(CPP) for q in ca) == 1 and len(roots) == 1 and
            all(q in ca for q in ('/Od', '/MTd', '/RTC1', '/fp:precise', '/openmp', '/std:c++17')),
            'Original CPU compiler/header ABI required')
        headerroot = roots[0]
        final = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        m.need(len(final) == len(set(final)) == 87 and set(final) ==
            {Path(q['path']).resolve() for q in objects} | {(OUT / 'entry.obj').resolve()},
            'Only one new entry plus86 original objects may be linked')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Original MSVC setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in
            setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532' and libraries, 'Matching MSVC/library ABI required')
        env.pop('CL', None); env.pop('_CL_', None)
        env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        before += [m.stat(c['program']), m.stat(link['program'])]
        m.verify(before); OUT.mkdir(); includes = []
        for name, content in generated.items():
            dest = OUT / name
            with dest.open('xb') as stream: stream.write(content)
            includes.append(m.stat(dest))
        before += includes
        calls.append(m.invoke(stages[0], [c['program'], *ca], S / 'VS', env))
        deps = m.read(OUT / 'dependencies.json')['Data']
        actual = {Path(q).resolve() for q in deps['Includes']}
        names = {Path(q['path']).name.lower() for q in headers}
        m.need(Path(deps['Source']).resolve() == CPP.resolve() and
            all(Path(q['path']).resolve() in actual for q in includes) and
            all((headerroot / q).resolve() in actual for q in
                ('JSph.h', 'JSphCpu.h', 'JSphCpuSingle.h', 'FunSoilMaterial.h', 'FunSphKernel.h')) and
            all(q.is_relative_to(headerroot) for q in actual if q.name.lower() in names) and
            all(not q.is_relative_to((S / 'source').resolve()) for q in actual),
            'Actual compilation missed frozen fragments or leaked public headers')
        calls.append(m.invoke(stages[1], [link['program'], *la], S / 'VS', env))
        copied = []
        for q in runtime:
            dest = OUT / Path(q['path']).name; shutil.copy2(q['path'], dest)
            m.need(dest.read_bytes() == Path(q['path']).read_bytes(), 'Frozen runtime copy differs')
            copied.append(m.stat(dest))
        m.verify(before)
        m.save(check, dict(stage=TAG + '.build', passed=True, configuration='DebugCPU',
            program=m.stat(exe), source=m.stat(CPP), note=m.stat(NOTE), source_build=base['source_build'],
            source_capture=base['source_capture'], source_archive=base['source_archive'],
            original_object_list=base['original_object_list'], retained_physical_objects=objects,
            archived_headers=headers, runtime=copied, generated_includes=includes, entry_derivation=proof,
            dependencies=m.stat(OUT / 'dependencies.json'), actual_link_objects=87,
            new_entry_objects=1, physical_objects_compiled=0, original_Single_no_hook=True,
            allowed_parts=[38, 76], component_max_actual_force_calls=34,
            conditional_pressure_only=True, eighth_numeric_residual_separate=True,
            source_RHS=m.stat(RHS), source_global_modes=m.stat(MODES), calls=calls,
            consumed=before, consumed_stats_unchanged=True, compile_invocations=1, link_invocations=1,
            component_invocations=0, solver_invocations=0, GPU_actions=0, SHA_scans=0,
            public_source_changed=False, canonical_programs_changed=False,
            no_automatic_component=True, physical_acceptance=False))
    except Exception as error:
        if not check.exists():
            m.save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=calls,
                consumed=before, partial_outputs_preserved=True, component_invocations=0,
                solver_invocations=0, GPU_actions=0, SHA_scans=0, physical_acceptance=False))
        raise


if __name__ == '__main__': main()
