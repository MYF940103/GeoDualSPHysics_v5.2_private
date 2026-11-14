"""Build original-full Wendland reader for retained AS.3/.5/.7 and exact exponent2.55; never decode."""
import argparse, difflib, os, subprocess
from pathlib import Path
from zipfile import ZipFile
import c08_h18_wend_native_r1_build as old

T, L = old.T, old.L
TAG = 'c08_h18_as255_native_r1'; OUT = T / 'outputs' / (TAG + '_build')
BASE = L / 'c08_h18_wend_native_r1.build.json'
SOURCE = T / 'support' / (TAG + '.cpp'); NOTE = T / 'notes' / (TAG + '.md')
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke
COEFFICIENTS = b'(H18Bits(H18AS,.3f)||H18Bits(H18AS,.5f)||H18Bits(H18AS,.7f))'
ORIGINAL = b'(H18Bits(H18Exp,3.825f)||H18Bits(H18Exp,3.f)||H18Bits(H18Exp,5.f))'
NARROW = b'(H18Bits(H18Exp,2.55f))'


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized', action='store_true'); args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until root full-read and one separate utility build')
    check = L / (TAG + '.build.json')
    need(not OUT.exists() and not check.exists() and all(not (L / (TAG + q)).exists() for q in
         ('.compile.call.json', '.compile.log', '.link.call.json', '.link.log')), 'Existing full or partial utility protected')
    before, calls = [], []
    try:
        baseline = read(BASE)
        need(baseline['stage'] == 'c08_h18_wend_native_r1.build' and baseline['passed'] and baseline['consumed_stats_unchanged']
             and baseline['actual_link_objects'] == 7 and not baseline['JSph_objects_linked']
             and baseline['declared_Kernel_XML_CSV'] == 2 and baseline['source_material_CSV_keys'] == 15
             and baseline['receiver_material_CSV_keys'] == 17, 'Original full Wendland utility baseline required, never a partial reader')
        objects = [bind(q) for q in baseline['objects']]
        need(len(objects) == 6 and {Path(q['path']).stem for q in objects}
             == {'JPartDataBi4', 'JPartDataHead', 'JBinaryData', 'JObject', 'JException', 'Functions'}, 'Exactly six original BI4 utility objects required')
        originals = {Path(q['path']).name: bind(q) for q in baseline['generated']}
        leaves = {'h18_wend_entry_r1.cpp', 'h18_headers_r1.h', 'public22_core_r1.h', 'h18_source_core_r1.cpp', 'h18_receiver_core_r1.cpp', 'h18_profiles_r1.h'}
        need(len(baseline['generated']) == len(originals) == 6 and set(originals) == leaves, 'Sealed original full generated source closure required')
        before = [stat(q) for q in (BASE, Path(__file__), Path(old.__file__), Path(old.e.__file__), SOURCE, NOTE)]
        before += [bind(baseline[q]) for q in ('program', 'source', 'source_archive', 'physical_source_archive', 'source_capture', 'core_derivation')]
        before += objects + list(originals.values()) + [bind(q) for q in baseline['calls']]
        need(len(baseline['calls']) == 2, 'One original CL and LINK call required')
        compile_call, link_call = [read(q['path']) for q in baseline['calls']]
        need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0 and q['ownership_failure'] is None and q['child'] for q in (compile_call, link_call)), 'Original actual typed utility calls must be closed')
        raw = Path(originals['h18_wend_entry_r1.cpp']['path']).read_bytes()
        need(raw.count(ORIGINAL) == 1 and NARROW not in raw and raw.count(COEFFICIENTS) == 1, 'Original exponent and retained coefficient predicates required')
        entry = raw.replace(ORIGINAL, NARROW, 1)
        need(entry.count(NARROW) == 1 and entry.replace(NARROW, ORIGINAL, 1) == raw, 'Exact inverse must recover every original entry byte')
        need(entry.count(COEFFICIENTS) == 1, 'Original AS.3/.5/.7 coefficient domain must remain byte-unchanged')
        OUT.mkdir(); headers = OUT / 'headers'; headers.mkdir()
        # Exactly the original full-reader header/ABI recipe, with its physical schema2 overrides.
        with ZipFile(baseline['source_archive']['path']) as archive:
            for item in archive.infolist():
                if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h', '.hpp', '.inl', '.cuh'):
                    destination = headers / Path(item.filename).name; need(not destination.exists(), 'Duplicate archived header leaf'); destination.write_bytes(archive.read(item))
        with ZipFile(baseline['physical_source_archive']['path']) as archive:
            for leaf in ('JPartDataBi4.h', 'JPartDataHead.h', 'JBinaryData.h', 'TypesDef.h'):
                need((headers / leaf).read_bytes() == archive.read('src/source/' + leaf), 'Original utility/physical ABI header differs: ' + leaf)
            for leaf in ('JGravityPreloadState.h', 'FunSoilMaterial.h'): (headers / leaf).write_bytes(archive.read('src/source/' + leaf))
        generated = []
        for name, original in originals.items():
            destination = OUT / ('h18_as255_entry_r1.cpp' if name == 'h18_wend_entry_r1.cpp' else name)
            payload = entry if name == 'h18_wend_entry_r1.cpp' else Path(original['path']).read_bytes()
            destination.write_bytes(payload); need(destination.read_bytes() == payload, 'Private generated source copy differs'); generated.append(stat(destination))
        diff = OUT / 'entry_profile.diff'
        diff.write_text(''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True), entry.decode('utf-8').splitlines(True), fromfile='sealed_full_wendland/entry', tofile='as255/entry')), encoding='utf-8')
        proof = OUT / 'core_derivation.json'
        save(proof, dict(stage=TAG + '.derive', baseline_build=stat(BASE), baseline_generated=list(originals.values()), original_predicate=ORIGINAL.decode(), replacement_predicate=NARROW.decode(), exact_inverse_original_entry_bytes=True, all_other_entry_bytes_unchanged=True, other_generated_files_byte_identical=True, original_field_and_numerical_guards_changed=False, window_samples=91, formal_samples=301, allowed_AS_coefficients=[.3, .5, .7], explicit_AS_exponent=2.55, coefficient_domain_unchanged=True, actual_coefficient_from_CSV_and_per_frame_header=True, old_files_changed=False))
        before += generated + [stat(diff), stat(proof)] + [stat(q) for q in headers.iterdir()]
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"', stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode == 0, 'Original utility MSVC setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        need(env['VCTOOLSVERSION'] == '14.36.32532', 'Exact original six-object MSVC14.36 required')
        for key in ('CL', '_CL_'): env.pop(key, None)
        oldout = Path(baseline['program']['path']).parent; obj = OUT / 'reader.obj'; exe = OUT / 'C08H18As255NativeR1_win64.exe'
        ca = [str(SOURCE) if q == baseline['source']['path'] else q.replace(str(oldout), str(OUT)) for q in compile_call['arguments']]
        la = [q.replace(baseline['program']['path'], str(exe)).replace(str(oldout), str(OUT)) for q in link_call['arguments']]
        linked = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(all(q in ca for q in ('/std:c++17', '/D_HAS_STD_BYTE=0', '/fp:precise', '/O2', '/MT', '/GL-')) and ca.count(str(SOURCE)) == 1 and '/Fo' + str(obj) in ca and '/I' + str(headers) in ca, 'Preserve original utility ABI/FP recipe with one new entry')
        need(len(linked) == len(set(linked)) == 7 and set(linked) == {Path(q['path']).resolve() for q in objects} | {obj.resolve()}, 'Only one new entry plus six original utility objects, no JSph')
        tools = [Path(q['program']) for q in (compile_call, link_call)]
        need(all('/14.36.32532/' in q.as_posix() for q in tools), 'Actual original MSVC tools required'); before += [stat(q) for q in tools]
        need(all(stat(q['path']) == q for q in before), 'Sealed utility/source inputs changed before build')
        calls.append(invoke(TAG + '.compile', [compile_call['program'], *ca], OUT, env)); calls.append(invoke(TAG + '.link', [link_call['program'], *la], OUT, env))
        need(all(stat(q['path']) == q for q in before), 'Sealed utility/source inputs changed during build')
        save(check, dict(stage=TAG + '.build', passed=True, program=stat(exe), source=stat(SOURCE), note=stat(NOTE), baseline_build=stat(BASE), original_full_build=stat(BASE), source_archive=baseline['source_archive'], physical_source_archive=baseline['physical_source_archive'], source_capture=baseline['source_capture'], objects=objects, actual_link_objects=7, JSph_objects_linked=False, generated=generated, core_derivation=stat(proof), core_diff=stat(diff), calls=calls, consumed=before, consumed_stats_unchanged=True, exact_inverse_original_entry_bytes=True, original_field_and_numerical_guards_changed=False, allowed_AS_coefficients=[.3, .5, .7], explicit_AS_exponent=2.55, coefficient_domain_unchanged=True, actual_coefficient_from_CSV_and_per_frame_header=True, window_samples=91, formal_samples=301, declared_Kernel_XML_CSV=2, source_material_CSV_keys=15, receiver_material_CSV_keys=17, actual_typed_exit_code=0, actual_Win32_exit=0, native_decodes=0, solver_invocations=0, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        actual_calls = [stat(L / (TAG + q)) for q in ('.compile.call.json', '.link.call.json') if (L / (TAG + q)).is_file()]
        if not check.exists(): save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=actual_calls, consumed=before, native_decodes=0, solver_invocations=0, physical_acceptance=False))
        raise


if __name__ == '__main__': main()
