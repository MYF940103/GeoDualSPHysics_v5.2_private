"""Build only a standalone frozen-header material diagnostic; never run it."""
import argparse
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_as03_step_r1_build as prior

m, T, L, S = prior.m, prior.T, prior.L, prior.S
TAG = 'c08_h18_material_tangent_r1'
CPP, NOTE = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
OUT = T / 'outputs' / (TAG + '_build')
BASE = L / 'c08_h18_as03_step_r1.build.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    m.need(parser.parse_args().execution_authorized,
           'Independent root build admission required; no component follows')
    receipt = L / (TAG + '.build.json')
    labels = (TAG + '.compile', TAG + '.link')
    m.need(not OUT.exists() and not receipt.exists() and all(
        not (L / (q + suffix)).exists() for q in labels for suffix in ('.call.json', '.log')),
        'Existing complete/partial build protected')
    before, calls = [], []
    try:
        base = m.read(BASE)
        m.need(base['passed'] and base['configuration'] == 'DebugCPU'
               and base['consumed_stats_unchanged'] and base['actual_link_objects'] == 87
               and base['physical_objects_compiled'] == 0 and base['original_Single_no_hook'],
               'Sealed actual AS03 step/shadow build required')
        headers = [m.bind(q) for q in base['archived_headers']]
        selected = [q for q in headers if Path(q['path']).name == 'FunSoilMaterial.h']
        m.need(len(headers) == 160 and len(selected) == 1,
               'Original frozen FunSoilMaterial header qualification required')
        header_root = Path(selected[0]['path']).parent
        before = [m.stat(q) for q in (Path(__file__), CPP, NOTE, BASE, Path(prior.__file__))]
        before += headers + [m.bind(base[k]) for k in ('source_build', 'source_capture', 'source_archive')]
        prior_checks = []
        for part in (38, 76):
            path = L / ('c08_h18_as03_step_r1_p' + str(part) + '.check.json')
            check = m.read(path); done_entry = m.bind(check['completion'])
            done = m.read(done_entry['path'])
            m.need(check['passed'] and check['consumed_stats_unchanged'] and
                   check['physical_steps'] == 1 and done['passed'] and done['source_part'] == part
                   and done['all6_material_sigma_and_policy_kappa_bits_matched']
                   and done['material_shadow_rows'] == 10000 and done['stage_rows'] == 35000,
                   'Each original completed one-step/10000-shadow qualification required')
            folder = Path(done_entry['path']).parent
            before += [m.stat(path), done_entry, m.bind(check['actual_call'])]
            before += [m.stat(folder / q) for q in ('stages.csv', 'material_shadow.csv', 'Run.out')]
            prior_checks.append(m.stat(path))
        xml = T / 'outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1.xml'
        root = ET.parse(xml).getroot()
        expected = dict(phi=25, coh=5000, dlt=0, DilationDecay=0, ModulusE=20e6,
                        PRvs=.33, phi_r=25, n_phi=0, coh_r=1000, n_coh=5)
        soil = root.findall('.//soils')
        m.need(len(soil) == 1 and all(len(soil[0].findall(k)) == 1 and
               float(soil[0].find(k).attrib['value']) == v for k, v in expected.items()),
               'Exact psi0 original material XML required')
        fit = root.findall('.//parameter[@key="DPCtes"]')
        m.need(len(fit) == 1 and fit[0].attrib['value'] == '3', 'Original plane-strain fit required')
        before.append(m.stat(xml))
        cpath, lpath = [L / ('c08_h18_as03_step_r1' + q) for q in
                        ('.compile.call.json', '.link.call.json')]
        compile_call, link_call = m.read(cpath), m.read(lpath)
        m.need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0
                   and q['ownership_failure'] is None for q in (compile_call, link_call)),
               'Actual original successful compiler/linker identities required')
        old = Path(base['program']['path']).parent
        args = []
        for value in compile_call['arguments']:
            if value == str(prior.CPP): value = str(CPP)
            elif not value.startswith('/I'): value = value.replace(str(old), str(OUT))
            args.append(value)
        m.need(args.count(str(CPP)) == 1 and '/I' + str(header_root) in args and
               all(q in args for q in ('/Od', '/MTd', '/RTC1', '/fp:precise', '/std:c++17')),
               'Retained precise DebugCPU compile recipe/frozen includes required')
        exe, obj = OUT / 'C08H18MaterialTangentR1.exe', OUT / 'entry.obj'
        link_args = ['/OUT:' + str(exe), '/NOLOGO', '/DEBUG', '/PDB:' + str(OUT / 'entry.pdb'),
                     '/SUBSYSTEM:CONSOLE', '/MACHINE:X64', str(obj)]
        m.need(sum(q.lower().endswith('.obj') for q in link_args) == 1 and
               not any(q.lower().endswith('.lib') for q in link_args),
               'Standalone entry must not link physical objects or project libraries')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Original MSVC environment unavailable')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in
                   setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Frozen original MSVC version required')
        env.pop('CL', None); env.pop('_CL_', None)
        before += [m.stat(cpath), m.stat(lpath), m.stat(compile_call['program']), m.stat(link_call['program'])]
        m.verify(before); OUT.mkdir()
        calls.append(m.invoke(labels[0], [compile_call['program'], *args], S / 'VS', env))
        dependencies = m.read(OUT / 'dependencies.json')['Data']
        included = {Path(q).resolve() for q in dependencies['Includes']}
        required = {header_root / q for q in ('FunSoilMaterial.h', 'DualSphDef.h', 'TypesDef.h')}
        names = {Path(q['path']).name.lower() for q in headers}
        m.need(Path(dependencies['Source']).resolve() == CPP.resolve() and
               all(q.resolve() in included for q in required) and
               all(q.is_relative_to(header_root.resolve()) for q in included if q.name.lower() in names)
               and all(not q.is_relative_to((S / 'source').resolve()) for q in included),
               'Actual compilation leaked public headers or missed frozen material implementation')
        calls.append(m.invoke(labels[1], [link_call['program'], *link_args], S / 'VS', env))
        m.verify(before)
        m.save(receipt, dict(stage=TAG + '.build', passed=True, configuration='DebugCPU',
            source=m.stat(CPP), note=m.stat(NOTE), program=m.stat(exe),
            original_step_build=m.stat(BASE), original_step_checks=prior_checks,
            source_build=base['source_build'], source_capture=base['source_capture'],
            source_archive=base['source_archive'], archived_headers=headers,
            dependencies=m.stat(OUT / 'dependencies.json'), actual_link_objects=1,
            new_entry_objects=1, retained_physical_objects=0, physical_objects_compiled=0,
            project_libraries_linked=0, standalone_inline_material=True,
            baseline_full_rows_required=10000, baseline_all6_sigma_kappa_bit_gate_required=True,
            selected_points=14, pure_material_calls_only=True, calls=calls, consumed=before,
            consumed_stats_unchanged=True, compile_invocations=1, link_invocations=1,
            component_invocations=0, solver_invocations=0, reader_invocations=0,
            physical_steps=0, GPU_actions=0, SHA_scans=0,
            no_automatic_component_or_solver=True, public_source_changed=False,
            physical_acceptance=False))
    except Exception as error:
        if not receipt.exists():
            m.save(receipt, dict(stage=TAG + '.build', passed=False, first_failure=str(error),
                calls=calls, consumed=before, partial_outputs_preserved=True,
                component_invocations=0, solver_invocations=0, physical_steps=0,
                GPU_actions=0, SHA_scans=0, physical_acceptance=False))
        raise


if __name__ == '__main__': main()
