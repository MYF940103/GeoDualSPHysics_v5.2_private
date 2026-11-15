"""Build only a standalone exact fixed-input HG unloading contract. Never run it."""
import argparse
import os
import subprocess
from pathlib import Path
import c08_h18_plastic_hg_adjoint_r1_build as prior

m, T, L, S = prior.m, prior.T, prior.L, prior.S
TAG = 'c08_h18_hg_unload_contract_r1'
CPP, NOTE = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
OUT = T / 'outputs' / (TAG + '_build')
BASE = L / 'c08_h18_plastic_hg_adjoint_r1.build.json'
CHECK = L / 'c08_h18_plastic_hg_adjoint_r1.check.json'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    m.need(p.parse_args().execution_authorized,
           'Root build admission required; no automatic component follows')
    receipt = L / (TAG + '.build.json')
    labels = [TAG + '.compile', TAG + '.link']
    m.need(not OUT.exists() and not receipt.exists() and all(
        not (L / (q + ext)).exists() for q in labels for ext in ('.log', '.call.json')),
        'Existing complete/partial outputs protected')
    before, calls = [], []
    try:
        gate = m.read(CHECK)
        m.need(gate['passed'] and gate['consumed_stats_unchanged']
               and gate['component_invocations'] == 1 and gate['physical_steps'] == 0
               and gate['solver_invocations'] == gate['native_invocations'] == 0,
               'Actual completed original adjoint component required')
        bref, dref, cref = [m.bind(gate[k]) for k in ('build', 'completion', 'actual_call')]
        m.need(Path(bref['path']).resolve() == BASE.resolve(), 'Original adjoint build identity differs')
        base, done, component = m.read(BASE), m.read(dref['path']), m.read(cref['path'])
        m.need(base['passed'] and base['configuration'] == 'DebugCPU'
               and base['consumed_stats_unchanged'] and base['actual_link_objects'] == 1
               and base['physical_objects_compiled'] == base['retained_physical_objects'] == 0
               and done['passed'] and done['certificate_groups'] == 65
               and done['scalar_certificates'] == 119713
               and done['actual_adjoint_contains_LS_backpropagation']
               and done['basis_P_is_reference_only'] and not done['history_passive']
               and done['unloading_counterexample_observed']
               and component['actual_Popen_wait_exit'] == component['actual_Win32_exit'] == 0
               and component['ownership_failure'] is None,
               'Passed bounded adjoint algebra/known memory counterexample required')
        oldsource = m.bind(base['source'])
        original = Path(oldsource['path']).read_bytes()
        marker = b'using Basis='
        m.need(original.count(marker) == 1, 'Original exact prefix marker changed')
        prefix = original.split(marker, 1)[0]
        authored = CPP.read_bytes()
        m.need(len(prefix) == 6938 and authored.startswith(prefix)
               and authored.count(b'using Basis=') == 0
               and authored.count(b'void RunGraph(') == 1
               and authored.count(b'Step ExactStep(') == 1,
               'New entry must retain exact passed B/V/M/Graph/P/PT prefix without old tests')
        ccpath = L / 'c08_h18_plastic_hg_adjoint_r1.compile.call.json'
        lcpath = L / 'c08_h18_plastic_hg_adjoint_r1.link.call.json'
        cc, lc = m.read(ccpath), m.read(lcpath)
        m.need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0
                   and q['ownership_failure'] is None for q in (cc, lc)),
               'Actual original DebugCPU/CRT compiler and linker calls required')
        before = [m.stat(q) for q in (Path(__file__), CPP, NOTE, CHECK,
                  Path(prior.__file__), ccpath, lcpath, Path(cc['program']), Path(lc['program']))]
        before += [bref, dref, cref, oldsource]
        oldout = Path(base['program']['path']).parent
        args = [str(CPP) if a == str(Path(oldsource['path'])) else
                a.replace(str(oldout), str(OUT)) for a in cc['arguments']]
        m.need(args.count(str(CPP)) == 1 and not any(a.startswith('/I') for a in args)
               and all(q in args for q in ('/Od', '/MTd', '/RTC1', '/fp:precise', '/std:c++17')),
               'Original standalone precise DebugCPU flags must be retained')
        exe = OUT / 'C08H18HgUnloadContractR1.exe'
        linkargs = ['/OUT:' + str(exe), '/NOLOGO', '/DEBUG', '/PDB:' + str(OUT / 'entry.pdb'),
                    '/SUBSYSTEM:CONSOLE', '/MACHINE:X64', str(OUT / 'entry.obj')]
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Original MSVC environment unavailable')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in
                   setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Original MSVC ABI changed')
        env.pop('CL', None)
        env.pop('_CL_', None)
        m.verify(before)
        OUT.mkdir()
        calls.append(m.invoke(labels[0], [str(cc['program']), *args], S / 'VS', env))
        dep = m.read(OUT / 'dependencies.json')['Data']
        m.need(Path(dep['Source']).resolve() == CPP.resolve()
               and all(not Path(q).resolve().is_relative_to((S / 'source').resolve())
                       and not Path(q).resolve().is_relative_to((T / 'outputs').resolve())
                       for q in dep['Includes']),
               'Standalone entry consumed a physical/private project header')
        calls.append(m.invoke(labels[1], [str(lc['program']), *linkargs], S / 'VS', env))
        m.verify(before)
        m.save(receipt, dict(stage=TAG + '.build', passed=True, configuration='DebugCPU',
            source=m.stat(CPP), note=m.stat(NOTE), program=m.stat(exe),
            original_adjoint_check=m.stat(CHECK), original_adjoint_build=bref,
            original_adjoint_completion=dref, original_adjoint_call=cref,
            exact_reference_prefix_source=oldsource, exact_reference_prefix_bytes=len(prefix),
            exact_prefix_reference_marker='using Basis=', exact_prefix_matches=True,
            original_compile_call=m.stat(ccpath), original_link_call=m.stat(lcpath),
            source_archive=base['source_archive'], source_capture=base['source_capture'],
            dependencies=m.stat(OUT / 'dependencies.json'),
            actual_link_objects=1, new_entry_objects=1, retained_physical_objects=0,
            physical_objects_compiled=0, project_libraries_linked=0, runtime_copies=0,
            compile_invocations=1, link_invocations=1, component_invocations=0,
            solver_invocations=0, reader_invocations=0, physical_steps=0,
            material_calls=0, Darcy_calls=0, GPU_actions=0, SHA_scans=0,
            fixed_input_contract_only=True, actual_Symplectic_qualified=False,
            same_stage_Darcy_qualified=False, physical_acceptance=False,
            public_source_changed=False, no_automatic_component_or_solver=True,
            calls=calls, consumed=before, consumed_stats_unchanged=True))
    except Exception as error:
        if not receipt.exists():
            m.save(receipt, dict(stage=TAG + '.build', passed=False, first_failure=str(error),
                calls=calls, consumed=before, partial_outputs_preserved=True,
                component_invocations=0, solver_invocations=0, physical_steps=0,
                GPU_actions=0, SHA_scans=0, physical_acceptance=False))
        raise


if __name__ == '__main__':
    main()
