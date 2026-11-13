"""Private original-archive normal-Taylor candidate: prepare or build CPU component; never run."""
import argparse, difflib, os, shutil, subprocess, zipfile
from pathlib import Path, PurePosixPath
import c08_fs_affine_cpu_r1_build as previous

m = previous.matrix
T, L, S = previous.T, previous.L, previous.S
TAG = 'c08_fs_normal_taylor_r1'
CAP = T / 'outputs' / (TAG + '_source')
OUT = T / 'outputs/c08_fs_normal_taylor_cpu_r1_build'
PREP = L / (TAG + '.prepare.json')
CPU = L / 'c08_fs_normal_taylor_cpu_r1.build.json'
ORIGINAL = L / 'c08_preload_schema2_Release_r1.build.json'
RESTORED = previous.BASE
FIXTURE = T / 'support/c08_fs_normal_taylor_cpu_r1.cpp'
NOTE = T / 'notes/c08_fs_normal_taylor_r1.md'
CHANGED = ('src/source/JSphCpu.cpp', 'src/source/JSphGpu_ker.cu')
INTERVENTION = 'free_surface_normal_taylor_projection'


def patch_original(data, gpu):
    """Exactly two local replacements, preserving archived encoding and line endings."""
    nl = '\r\n' if b'\r\n' in data else '\n'
    flag = 'freeseepage' if gpu else 'HydroMechFreeSeepage'
    test = 'KerHydroMechIsFreeSurface(p1,code,fstype)' if gpu else 'IsFreeSurfaceParticle(unsigned(p1),Codec,FSTypec)'
    ace = 'ace' if gpu else 'Acec'
    old1 = 'if(khyd>0 && closedfs && ' + test + ')'
    new1 = 'if(khyd>0 && (closedfs || ' + flag + ') && ' + test + ')'
    old2 = nl.join((
        '    //-Candidate raw hydraulic term omits the complete (grad p+rho_w*Ace) defect, not just grad p.',
        '    const double lap=(' + flag + ' && ' + test + '?',
        '      lp+rhow*(double(' + ace + '[p1].x)*lx.x+double(' + ace + '[p1].y)*lx.y+double(' + ace + '[p1].z)*lx.z+da):',
        '      lp-gpcorr.x*lx.x-gpcorr.y*lx.y-gpcorr.z*lx.z+rhow*da);'))
    new2 = nl.join((
        '    //-Private candidate: retain tangent hydraulic Taylor defect; normal target only.',
        '    const double lap=lp-gpcorr.x*lx.x-gpcorr.y*lx.y-gpcorr.z*lx.z+rhow*da;'))
    result = data
    for old, new in ((old1, new1), (old2, new2)):
        old, new = old.encode('utf-8'), new.encode('utf-8')
        m.need(result.count(old) == 1, 'Original archive lacks one exact reviewed block')
        result = result.replace(old, new)
    inverse = result.replace(new2.encode('utf-8'), old2.encode('utf-8')).replace(new1.encode('utf-8'), old1.encode('utf-8'))
    m.need(inverse == data, 'Candidate inverse must recover exact original bytes')
    return result


def prepare():
    m.need(not CAP.exists() and not PREP.exists(), 'Existing private source preparation protected')
    base = m.read(ORIGINAL)
    m.need(base['passed'] and base['configuration'] == 'Release' and base['consumed_stats_unchanged'], 'Original schema2 baseline required')
    before = [m.stat(q) for q in (ORIGINAL, Path(__file__), FIXTURE, NOTE, Path(previous.__file__), Path(m.__file__))]
    before += [m.bind(base[q]) for q in ('program', 'source_capture', 'source_archive')]
    with zipfile.ZipFile(base['source_archive']['path']) as old:
        names = old.namelist()
        m.need(len(names) == len(set(names)) and set(CHANGED) <= set(names), 'Unique original archive entries required')
        payload, differences, diff = {}, [], []
        for name in names:
            p = PurePosixPath(name)
            m.need(not p.is_absolute() and '..' not in p.parts, 'Unsafe original archive member')
            raw = old.read(name)
            payload[name] = patch_original(raw, name.endswith('.cu')) if name in CHANGED else raw
            if payload[name] != raw:
                differences.append(name)
                diff += difflib.unified_diff(raw.decode('utf-8').splitlines(True), payload[name].decode('utf-8').splitlines(True),
                                            fromfile='schema2/' + name, tofile='private_normal_taylor/' + name)
        m.need(set(differences) == set(CHANGED), 'Exactly two reviewed source entries must differ')
        m.verify(before)
        CAP.mkdir()
        with zipfile.ZipFile(CAP / 'source.zip', 'x', compression=zipfile.ZIP_DEFLATED) as new:
            for name, raw in payload.items():
                destination = CAP / Path(*PurePosixPath(name).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                new.writestr(name, raw)
        with zipfile.ZipFile(CAP / 'source.zip') as new:
            m.need(new.namelist() == names and all(new.read(q) == payload[q] for q in names), 'Prepared archive round trip differs')
        (CAP / 'source.diff').write_text(''.join(diff), encoding='utf-8')
    m.verify(before)
    capture = CAP / 'source.json'
    m.save(capture, dict(stage=TAG + '.source', intervention=INTERVENTION, baseline_source_build=m.stat(ORIGINAL),
        baseline_source_capture=base['source_capture'], baseline_source_archive=base['source_archive'],
        actual_differences=differences, all_other_archived_bytes_identical=True, exact_inverse_original_bytes=True,
        files=[m.stat(CAP / Path(*PurePosixPath(q).parts)) for q in names], diff=m.stat(CAP / 'source.diff'),
        archive=m.stat(CAP / 'source.zip'), consumed=before, consumed_stats_unchanged=True, SHA_scans=0))
    m.save(PREP, dict(stage=TAG + '.prepare', passed=True, source_capture=m.stat(capture), source_archive=m.stat(CAP / 'source.zip'),
        intervention=INTERVENTION, source_differences=differences, public_source_changed=False,
        build_invocations=0, fixture_invocations=0, solver_invocations=0, GPU_actions=0, physical_acceptance=False))


def cpu_build():
    m.need(not OUT.exists() and not CPU.exists(), 'Existing partial or complete CPU build protected')
    prepared, restored = m.read(PREP), m.read(RESTORED)
    m.need(prepared['passed'] and prepared['intervention'] == INTERVENTION, 'Reviewed private prepare required')
    m.need(restored['passed'] and restored['configuration'] == 'DebugCPU' and restored['restored_original_source']
           and restored['actual_typed_exit_code'] == restored['actual_Win32_exit'] == 0
           and restored['actual_link_objects'] == 87 and restored['consumed_stats_unchanged'], 'Actual restored DebugCPU closure required')
    build_call = m.read(m.bind(restored['actual_call'])['path'])
    roots = [q.split('=', 1)[1] for q in build_call['arguments'] if q.startswith('/p:IntDir=')]
    m.need(build_call['actual_Popen_wait_exit'] == build_call['actual_Win32_exit'] == 0 and len(roots) == 1, 'One actual successful restored build required')
    intdir = Path(roots[0]).resolve()
    m.need(intdir == (Path(os.environ['TEMP']) / 'c08_restore_cpu_r1/DebugCPU/int').resolve(), 'Unexpected restored IntDir')
    ct, lt, rt = (intdir / 'DualSPHysics.tlog' / q for q in ('CL.command.1.tlog', 'link.command.1.tlog', 'link.read.1.tlog'))
    commands, links = previous.blocks(ct), previous.blocks(lt)
    m.need(len(links) == 1, 'One authoritative restored link block required')
    la = previous.arguments(' '.join(links[0][1]))
    objects = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
    replaced = {q.name.lower(): q for q in objects if q.name.lower() in ('main.obj', 'jsphcpu.obj')}
    m.need(len(objects) == len(set(objects)) == 87 and len(replaced) == 2 and all(q.parent == intdir for q in objects), 'Exactly87 restored objects with main and JSphCpu required')
    capture = m.read(m.bind(prepared['source_capture'])['path'])
    before = [m.stat(q) for q in (PREP, RESTORED, ORIGINAL, FIXTURE, NOTE, Path(__file__), Path(previous.__file__), Path(m.__file__), ct, lt, rt)]
    before += [m.bind(q) for q in capture['files']] + [m.bind(prepared[q]) for q in ('source_capture', 'source_archive')]
    before += [m.bind(restored[q]) for q in ('program', 'source_capture', 'source_archive', 'actual_call')]
    before += [m.stat(q) for q in objects]
    libraries = [Path(q.strip('"')).resolve() for q in rt.read_text(encoding='utf-16').splitlines() if not q.startswith('^') and q.lower().endswith('.lib')]
    m.need(libraries and all(q.is_file() for q in libraries), 'Resolved original libraries required')
    before += [m.stat(q) for q in libraries] + [m.bind(q) for q in restored['runtime']]
    setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"', stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    m.need(setup.returncode == 0, 'Matching compiler setup failed')
    env = {k.upper(): v for k, v in os.environ.items()}
    env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
    m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Exact restored MSVC14.36 required')
    for key in ('CL', '_CL_'): env.pop(key, None)
    env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
    cl = Path(env['VCTOOLSINSTALLDIR']) / 'bin/Hostx64/x64/cl.exe'
    before += [m.stat(cl), m.stat(cl.with_name('link.exe'))]
    sources = {'main.cpp': FIXTURE, 'jsphcpu.cpp': CAP / 'src/source/JSphCpu.cpp'}
    replacements = {'main.obj': OUT / 'fixture.obj', 'jsphcpu.obj': OUT / 'candidate_cpu.obj'}
    compile_calls = []
    m.verify(before)
    OUT.mkdir()
    for leaf, source in sources.items():
        found = [q for q in commands if len(q[0]) == 1 and Path(q[0][0]).name.lower() == leaf]
        m.need(len(found) == 1, 'One matching original CPU compile command required')
        ca = previous.arguments(' '.join(found[0][1]))
        m.need(all(q in ca for q in ('/MTd', '/Od', '/RTC1', '/Zi', '/fp:precise', '/openmp')) and not any('_WITHGPU' in q for q in ca), 'Original CPU Debug ABI/FP flags required')
        indices = [i for i, q in enumerate(ca) if Path(q).name.lower() == leaf]
        m.need(len(indices) == 1, 'Exactly one actual source token required')
        ca[indices[0]] = str(source)
        target = replacements['main.obj' if leaf == 'main.cpp' else 'jsphcpu.obj']
        for prefix, output in (('/Fo', target), ('/Fd', OUT / (target.stem + '.pdb'))):
            ids = [i for i, q in enumerate(ca) if q.lower().startswith(prefix.lower())]
            m.need(len(ids) == 1, 'Exactly one output token required')
            ca[ids[0]] = prefix + str(output)
        ca = ['/I' + str(CAP / 'src/source')] + ca + ['/std:c++17', '/D_HAS_STD_BYTE=0']
        compile_calls.append(m.invoke('c08_fs_normal_taylor_cpu_r1.' + target.stem, [str(cl), *ca], S / 'VS', env))
        m.need(target.is_file(), 'Actual case-sensitive /Fo output missing')
    exe = OUT / 'C08FsNormalTaylorCpuR1_win64.exe'
    outputs = {'/out:': exe, '/pdb:': OUT / 'fixture_link.pdb', '/implib:': OUT / 'fixture.lib', '/ltcgout:': OUT / 'fixture.iobj'}
    linked, seen = [], set()
    for q in la:
        if q.lower().endswith('.obj') and Path(q).name.lower() in replaced: q = str(replacements[Path(q).name.lower()])
        for prefix, target in outputs.items():
            if q.lower().startswith(prefix): q = prefix + str(target); seen.add(prefix); break
        linked.append(q)
    final = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
    retained = [q for q in objects if q.name.lower() not in replaced]
    m.need(seen == set(outputs) and len(final) == 87 and set(final) == set(retained) | {q.resolve() for q in replacements.values()}, 'Only main and JSphCpu may be replaced in87-object link')
    link = m.invoke('c08_fs_normal_taylor_cpu_r1.link', [str(cl.with_name('link.exe')), *linked], S / 'VS', env)
    runtime = []
    for entry in restored['runtime']:
        destination = OUT / Path(entry['path']).name
        shutil.copy2(entry['path'], destination)
        m.need(destination.read_bytes() == Path(entry['path']).read_bytes(), 'Runtime bytes differ')
        runtime.append(m.stat(destination))
    m.verify(before)
    m.save(CPU, dict(stage='c08_fs_normal_taylor_cpu_r1.build', passed=True, intervention=INTERVENTION,
        program=m.stat(exe), fixture=m.stat(FIXTURE), source_capture=prepared['source_capture'], source_archive=prepared['source_archive'],
        baseline_source_build=m.stat(ORIGINAL), restored_source_build=m.stat(RESTORED), retained_public_objects=85,
        retained_project_objects=[m.stat(q) for q in retained], replaced_original_objects=[m.stat(q) for q in replaced.values()],
        candidate_object=m.stat(replacements['jsphcpu.obj']), fixture_object=m.stat(replacements['main.obj']), actual_link_objects=87,
        runtime=runtime, calls=compile_calls + [link], consumed=before, consumed_stats_unchanged=True,
        actual_typed_exit_code=0, actual_Win32_exit=0, fixture_invocations=0, solver_invocations=0,
        GPU_actions=0, GPU_stage_held=True, physical_acceptance=False, SHA_scans=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'cpu_build'))
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Author-only until root full-read and action-specific authorization')
    try:
        (prepare if args.action == 'prepare' else cpu_build)()
    except Exception as error:
        receipt = PREP if args.action == 'prepare' else CPU
        if not receipt.exists():
            m.save(receipt, dict(stage=TAG + '.' + args.action, passed=False, first_failure=str(error),
                fixture_invocations=0, solver_invocations=0, GPU_actions=0, physical_acceptance=False))
        raise


if __name__ == '__main__': main()
