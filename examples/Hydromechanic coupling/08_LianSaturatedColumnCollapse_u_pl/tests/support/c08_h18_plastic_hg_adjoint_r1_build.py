"""Build only the fixed 49-point plastic-HG adjoint algebra fixture; never run it."""
import argparse
import os
import subprocess
import zipfile
from pathlib import Path
import c08_h18_material_tangent_r1_build as prior

m, T, L, S = prior.m, prior.T, prior.L, prior.S
TAG = 'c08_h18_plastic_hg_adjoint_r1'
CPP, NOTE = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
OUT = T / 'outputs' / (TAG + '_build')
BASE = L / 'c08_h18_material_tangent_r1.build.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    m.need(parser.parse_args().execution_authorized,
           'Independent root build admission required; no component follows')
    receipt = L / (TAG + '.build.json')
    labels = [TAG + '.compile', TAG + '.link']
    m.need(not OUT.exists() and not receipt.exists() and all(
        not (L / (q + suffix)).exists() for q in labels for suffix in ('.call.json', '.log')),
        'Existing complete/partial build protected')
    consumed, calls = [], []
    try:
        base = m.read(BASE)
        m.need(base['passed'] and base['configuration'] == 'DebugCPU'
               and base['consumed_stats_unchanged'] and base['actual_link_objects'] == 1
               and base['retained_physical_objects'] == 0 and base['physical_objects_compiled'] == 0,
               'Original actual standalone DebugCPU/CRT recipe required')
        ccpath = L / 'c08_h18_material_tangent_r1.compile.call.json'
        lcpath = L / 'c08_h18_material_tangent_r1.link.call.json'
        cc, lc = m.read(ccpath), m.read(lcpath)
        m.need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0
                   and q['ownership_failure'] is None for q in (cc, lc)),
               'Actual successful original compiler/linker calls required')
        source_archive = m.bind(base['source_archive'])
        source_capture = m.bind(base['source_capture'])
        with zipfile.ZipFile(source_archive['path']) as archive:
            hg = archive.read('src/source/JSphHourglassCpu.cpp').decode('utf-8-sig')
            hgh = archive.read('src/source/JSphHourglassCpu.h').decode('utf-8-sig')
        proof = [
            'add(a,b.vol*pair.w);add(b,a.vol*pair.w);',
            'const double beta=Xi*Shear*a.vol*b.vol*pair.w;',
            'const double rx=-beta*.5*(aix+bjx)/Mass,rz=-beta*.5*(aiz+bjz)/Mass;',
            'RateInfo.form+=.25*beta*(aix*aix+aiz*aiz+bjx*bjx+bjz*bjz);',
            'Check(isfinite(det) && lo>0 && hi/lo<1e8,',
            'Check(Stats.spinbound<.01,',
        ]
        m.need(all(hg.count(q) == 1 for q in proof)
               and hgh.count('std::vector<Vec> History,HistoryRate;') == 1
               and hgh.count('std::vector<Pair> Pairs;') == 1,
               'Frozen matched-LS, one-sided form and unchanged guard source proof required')
        consumed = [m.stat(q) for q in (Path(__file__), CPP, NOTE, BASE, ccpath, lcpath,
                    Path(prior.__file__), Path(cc['program']), Path(lc['program']))]
        consumed += [source_archive, source_capture]
        oldout = Path(base['program']['path']).parent
        oldcpp = Path(base['source']['path'])
        args = []
        for a in cc['arguments']:
            if a.startswith('/I'):
                continue  # No material/project header is compiled by this pure fixture.
            if a == str(oldcpp):
                a = str(CPP)
            else:
                a = a.replace(str(oldout), str(OUT))
            args.append(a)
        m.need(args.count(str(CPP)) == 1 and all(q in args for q in
               ('/Od', '/MTd', '/RTC1', '/fp:precise', '/std:c++17', '/EHsc')) and not any(a.startswith('/I') for a in args),
               'Retained original precise one-entry DebugCPU flags required')
        exe, obj = OUT / 'C08H18PlasticHgAdjointR1.exe', OUT / 'entry.obj'
        linkargs = ['/OUT:' + str(exe), '/NOLOGO', '/DEBUG', '/PDB:' + str(OUT / 'entry.pdb'),
                    '/SUBSYSTEM:CONSOLE', '/MACHINE:X64', str(obj)]
        m.need(sum(a.lower().endswith('.obj') for a in linkargs) == 1
               and not any(a.lower().endswith('.lib') for a in linkargs),
               'Only the new entry object and its default CRT libraries may link')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Original MSVC environment unavailable')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in
                   setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Frozen original MSVC ABI required')
        env.pop('CL', None)
        env.pop('_CL_', None)
        m.verify(consumed)
        OUT.mkdir()
        calls.append(m.invoke(labels[0], [str(cc['program']), *args], S / 'VS', env))
        dep = m.read(OUT / 'dependencies.json')['Data']
        includes = [Path(q).resolve() for q in dep['Includes']]
        m.need(Path(dep['Source']).resolve() == CPP.resolve()
               and all(not q.is_relative_to((S / 'source').resolve()) for q in includes)
               and all(not q.is_relative_to((T / 'outputs').resolve()) for q in includes),
               'Standalone compilation unexpectedly consumed a physical/private project header')
        calls.append(m.invoke(labels[1], [str(lc['program']), *linkargs], S / 'VS', env))
        m.verify(consumed)
        m.save(receipt, dict(stage=TAG + '.build', passed=True, configuration='DebugCPU',
            source=m.stat(CPP), note=m.stat(NOTE), program=m.stat(exe),
            original_CRT_build=m.stat(BASE), original_compile_call=m.stat(ccpath),
            original_link_call=m.stat(lcpath), source_archive=source_archive,
            source_capture=source_capture, reference_source_members=[
                'src/source/JSphHourglassCpu.cpp', 'src/source/JSphHourglassCpu.h'],
            reference_source_exact_anchor_proof=proof,
            reference_header_exact_anchors=['std::vector<Vec> History,HistoryRate;',
                'std::vector<Pair> Pairs;'], public_source_changed=False,
            dependencies=m.stat(OUT / 'dependencies.json'), actual_link_objects=1,
            new_entry_objects=1, retained_physical_objects=0, physical_objects_compiled=0,
            project_libraries_linked=0, runtime_copies=0,
            explicit_project_include_paths=0, standalone_fixed_geometry_algebra=True,
            source_equations_are_reference_not_physical_invocations=True,
            clouds=3, nodes_per_cloud=49, prescribed_gamma_only=True,
            history_ODE_integrated=False, history_passive=False,
            physical_acceptance=False, C08_compatibility_qualified=False,
            setup_environment_exit=setup.returncode,
            compile_invocations=1, link_invocations=1, component_invocations=0,
            solver_invocations=0, reader_invocations=0, physical_steps=0,
            GPU_actions=0, SHA_scans=0, no_automatic_component_or_solver=True,
            calls=calls, consumed=consumed, consumed_stats_unchanged=True))
    except Exception as error:
        if not receipt.exists():
            m.save(receipt, dict(stage=TAG + '.build', passed=False, first_failure=str(error),
                calls=calls, consumed=consumed, partial_outputs_preserved=True,
                component_invocations=0, solver_invocations=0, reader_invocations=0,
                physical_steps=0, GPU_actions=0, SHA_scans=0,
                physical_acceptance=False, no_automatic_component_or_solver=True))
        raise


if __name__ == '__main__':
    main()
