"""Offline adoption review of the completed C04 full86 DebugCPU build.

Never rebuild, relink, invoke a program/help/reader, or alter the failed r1
receipt. Only a new program/runtime-copy directory and review receipt are written.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes as wt
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
R = T.parents[3]
L = T / 'logs'
STAGE = 'upl_tpi_cryer_cpu_build_review_r2'
OLDTAG = 'upl_tpi_cryer_cpu_DebugCPU_r1'
OLDROOT = T / 'outputs' / OLDTAG
OLDRESULT = L / (OLDTAG + '.build.json')
OLD_BUILD = L / 'upl_cryer_freebody_r1_DebugCPU.build.json'
OLD_CALL = L / 'upl_cryer_freebody_r1_DebugCPU.call.json'
PREP = L / 'upl_tpi_cryer_cpu_overlay_r1.prepare.json'
OUT = T / 'outputs/upl_tpi_cryer_cpu_DebugCPU_r1_review_r2'
RECEIPT = L / (OLDTAG + '.build_review_r2.json')
DEBUG_OMP = Path('D:/Program Files/VS2022/VC/Redist/MSVC/14.36.32532/debug_nonredist/x64/Microsoft.VC143.DebugOpenMP/vcomp140d.dll')
NS = {'m': 'http://schemas.microsoft.com/developer/msbuild/2003'}


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def stat(path):
    p = Path(path).resolve(); s = p.stat()
    need(p.is_file(), 'Not a file: ' + str(p))
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def key(path):
    return str(Path(path).resolve()).casefold()


def same(entry):
    actual = stat(entry['path'])
    need(actual == {k: entry[k] for k in ('path', 'bytes', 'mtime_ns')}, 'Frozen stat changed: ' + entry['path'])
    return actual


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, ensure_ascii=False); f.write('\n')


class Admission:
    def __init__(self, path):
        self.entry = stat(path); self.data = load(path)
        need(self.data.get('stage') == STAGE + '.review_admission' and self.data.get('passed') is True
             and self.data.get('offline_only') is True and self.data.get('configuration') == 'DebugCPU'
             and self.data.get('adopt_completed_failed_postcheck') is True,
             'Independent root offline/adoption-only admission required')
        self.frozen = {key(e['path']): e for e in self.data['inputs']}
        need(len(self.frozen) == len(self.data['inputs']), 'Duplicate input identity')
        self.consumed = {}

    def pin(self, path):
        k = key(path); need(k in self.frozen, 'Consumed input absent from root review admission: ' + str(path))
        self.consumed[k] = same(self.frozen[k]); return self.consumed[k]

    def finish(self):
        for entry in self.consumed.values():
            same(entry)
        same(self.entry)
        return list(self.consumed.values())


def windows_flags(text):
    shell, kernel = ctypes.WinDLL('shell32'), ctypes.WinDLL('kernel32')
    shell.CommandLineToArgvW.argtypes = [wt.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wt.LPWSTR)
    kernel.LocalFree.argtypes = [wt.HLOCAL]
    n = ctypes.c_int(); p = shell.CommandLineToArgvW('dummy.exe ' + text, ctypes.byref(n))
    need(bool(p), 'Flags-only Windows command parse failed')
    try:
        return [p[i] for i in range(1, n.value)]
    finally:
        kernel.LocalFree(p)


def path_spelling(text):
    return text.replace('/', '\\').casefold()


def commands(path):
    """Use the genuine ^ source and suffix BEFORE parsing potentially bare spaces."""
    lines = path.read_text(encoding='utf-16').splitlines()
    need(len(lines) % 2 == 0, 'CL command pairs malformed')
    result = {}
    for i in range(0, len(lines), 2):
        header, raw = lines[i], lines[i + 1].rstrip()
        need(header.startswith('^') and '|' not in header, 'Exactly one real source header required')
        source = header[1:]
        quoted = raw.endswith('"')
        suffix_len = len(source) + (2 if quoted else 0)
        need(len(raw) > suffix_len, 'Missing source suffix')
        suffix = raw[-suffix_len:]
        actual_source = suffix[1:-1] if quoted else suffix
        need((not quoted or (suffix.startswith('"') and suffix.endswith('"')))
             and path_spelling(actual_source) == path_spelling(source)
             and raw[-suffix_len - 1].isspace(),
             'CL line does not end with its complete genuine source spelling')
        prefix = raw[:-suffix_len].rstrip()
        leaf = Path(source).name.casefold()
        need(leaf not in result, 'Duplicate CL source')
        result[leaf] = dict(source=source, flags=windows_flags(prefix),
                            source_unquoted_with_spaces=not quoted and any(x.isspace() for x in source))
    return result


def normalized(flags):
    result, deps = [], []
    i = 0
    while i < len(flags):
        arg = flags[i]; low = arg.casefold()
        if low == '/sourcedependencies':
            need(i + 1 < len(flags), 'Missing actual sourceDependencies path')
            deps.append(flags[i + 1]); i += 2; continue
        if low.startswith('/sourcedependencies:'):
            deps.append(arg.split(':', 1)[1])
        elif not low.startswith(('/fo', '/fd')):
            result.append(arg.upper())
        i += 1
    return result, deps


def review(ad, result):
    for p in (Path(__file__), T / 'notes/upl_tpi_cryer_cpu_build_review_r2.md', sys.executable,
              T / 'support/upl_tpi_cryer_cpu_build_r1.py', OLDRESULT, OLD_BUILD, OLD_CALL, PREP, DEBUG_OMP):
        ad.pin(p)
    failed, old, oldcall, prep = map(load, (OLDRESULT, OLD_BUILD, OLD_CALL, PREP))
    need(failed['passed'] is False and failed['failure'] == 'Actual CL source or dependency argument malformed',
         'Only the actual known completed-build postcheck rejection may be adopted')
    need(failed['configuration'] == 'DebugCPU' and old['passed'] and old['objects'] == 86
         and oldcall['exit_code'] == 0 and prep['passed'] and prep['requires_full_DebugCPU_86_TU_compile'],
         'Original/build/source provenance differs')
    old_admission = Path(failed['root_admission']['path']); ad.pin(old_admission); same(failed['root_admission'])
    original = load(old_admission)
    need(original['stage'] == 'upl_tpi_cryer_cpu_build_r1.build_admission' and original['passed']
         and original['build_only'] and original['configuration'] == 'DebugCPU', 'Original root build admission differs')
    for entry in original['inputs']:
        ad.pin(entry['path']); same(entry)
    for entry in prep['files']:
        ad.pin(entry['path']); same(entry)
    source_root = Path(prep['source_root']).resolve(); source = source_root / 'source'
    need(key(source_root) == key(failed['source_root']), 'Actual completed build consumed another source root')
    intdir = Path(failed['private_IntDir']).resolve(); outdir = OLDROOT / 'out'
    need(key(OLDROOT) == key(failed['private_output_root']), 'Original build output root differs')
    tool_calls = []
    for suffix in ('environment', 'msbuild'):
        p = L / (OLDTAG + '.' + suffix + '.call.json'); ad.pin(p); c = load(p)
        need(c['passed'] and c['actual_Popen_wait_exit'] == c['actual_Win32_exit'] == 0,
             'Actual direct tool did not have both successful exits')
        need(c['owner']['pid'] == c['child']['parent']
             and key(c['child']['exe']) == key(c['program']['path'])
             and c['child']['argv'][1:] == c['arguments'], 'Original actual tool ownership/argv differs')
        native_creation = (c['creation_FILETIME_ticks'] - 116444736000000000) / 1e7
        need(abs(native_creation - c['child']['created']) <= 1e-6, 'Native tool creation capture differs')
        ad.pin(c['program']['path']); same(c['program']); ad.pin(c['log']['path']); same(c['log'])
        tool_calls.append(stat(p))
    msbuild = load(tool_calls[1]['path'])
    need(key(msbuild['cwd']) == key(source_root / 'VS')
         and key(msbuild['arguments'][0]) == key(source_root / 'VS/DualSPHysics5ReCpu_vs2022.sln')
         and '/p:Configuration=DebugCPU' in msbuild['arguments'] and '/p:Platform=x64' in msbuild['arguments']
         and '/p:VCToolsVersion=14.36.32532' in msbuild['arguments']
         and '/p:WindowsTargetPlatformVersion=8.1' in msbuild['arguments'], 'Actual authoritative build/toolchain invocation differs')
    need(failed['selected_toolchain']['VCTOOLSVERSION'] == '14.36.32532'
         and '8.1' in failed['selected_toolchain']['WINDOWSSDKDIR'], 'Original selected toolchain differs')
    project = source_root / 'VS/DualSPHysics5ReCpu.vcxproj'; ad.pin(project)
    active = []
    for item in ET.parse(project).getroot().findall('.//m:ClCompile[@Include]', NS):
        reject = any('DebugCPU|x64' in e.get('Condition', '') and e.text == 'true' for e in item.findall('m:ExcludedFromBuild', NS))
        if not reject:
            active.append(Path(item.get('Include').replace('\\', '/')).name)
    need(len(active) == 86 and len({x.casefold() for x in active}) == 86, 'Project active86 membership differs')
    evaluated = OLDROOT / 'evaluated_compile_sources.txt'; ad.pin(evaluated)
    actual = [Path(x.rsplit('|', 1)[0]).resolve() for x in evaluated.read_text(encoding='utf-8-sig').splitlines()
              if x.rsplit('|', 1)[1].lower() != 'true']
    need(len(actual) == 86 and {key(x) for x in actual} == {key(source / x) for x in active}, 'Actual evaluated86 closure differs')
    objects = []
    for leaf in active:
        p = intdir / (Path(leaf).stem + '.obj'); objects.append(ad.pin(p))
    need({key(p) for p in intdir.glob('*.obj')} == {key(e['path']) for e in objects}, 'Actual object closure not exactly86')
    old_tlogs = Path(next(x.split('=', 1)[1] for x in oldcall['arguments'] if x.startswith('/p:IntDir='))) / 'DualSPHysics.tlog'
    logs = {}
    for name in ('CL.command.1.tlog', 'CL.read.1.tlog', 'link.command.1.tlog', 'link.read.1.tlog'):
        found = list(intdir.rglob(name)); need(len(found) == 1, 'Missing/ambiguous actual new tlog')
        ad.pin(found[0]); logs[name] = found[0]; ad.pin(old_tlogs / name)
    before, after = commands(old_tlogs / 'CL.command.1.tlog'), commands(logs['CL.command.1.tlog'])
    need(set(before) == set(after) == {x.casefold() for x in active}, 'Actual CL source header closure differs')
    dependencies, includes = [], set()
    for leaf in active:
        row = after[leaf.casefold()]; need(key(row['source']) == key(source / leaf), 'Actual CL source-header path differs')
        bflags, bdeps = normalized(before[leaf.casefold()]['flags']); aflags, adeps = normalized(row['flags'])
        dep = intdir / (Path(leaf).stem + '.dependencies.json')
        need(bflags == aflags and not bdeps and len(adeps) == 1 and key(adeps[0]) == key(dep),
             'Original Debug numerical/compiler flags or actual dependency path changed: ' + leaf)
        dependencies.append(ad.pin(dep)); d = load(dep)['Data']
        need(key(d['Source']) == key(source / leaf), 'Per-TU actual sourceDependencies Source differs')
        for name in d['Includes']:
            p = Path(name).resolve()
            need(not p.is_relative_to(R / 'src/source') and (not p.is_relative_to(R) or p.is_relative_to(source)),
                 'Compiler consumed a live/unrelated repository header')
            includes.add(p)
    need(source / 'upl_tpi_cpu_r1.h' in includes, 'Actual generic helper not consumed')
    for p in includes:
        ad.pin(p)
    old_libraries = {Path(x).resolve() for x in (old_tlogs / 'link.read.1.tlog').read_text(encoding='utf-16').splitlines()
                     if not x.startswith('^') and x.casefold().endswith('.lib')}
    need(len(old_libraries) == 23, 'Original library count differs')
    third = {p for p in old_libraries if key(p.parent) == key(R / 'src/lib/vs2022')}
    need(len(third) == 5, 'Original project library count differs')
    private_lib = OLDROOT / 'lib/vs2022'
    for p in old_libraries:
        ad.pin(p)
    for p in third:
        dest = private_lib / p.name; ad.pin(dest)
        need(dest.read_bytes() == p.read_bytes(), 'Actual private project library bytes differ')
    libraries = {Path(x).resolve() for x in logs['link.read.1.tlog'].read_text(encoding='utf-16').splitlines()
                 if not x.startswith('^') and x.casefold().endswith('.lib')}
    need({key(x) for x in libraries} == {key(private_lib / x.name if x in third else x) for x in old_libraries},
         'Actual private-five/system18 link closure differs')
    for p in libraries:
        ad.pin(p)
    for name in ('private_debug.targets', 'load_environment.cmd'):
        ad.pin(OLDROOT / name)
    binlog = L / (OLDTAG + '.binlog'); ad.pin(binlog)
    source_program = ad.pin(outdir / 'DualSPHysics5.2CPU_win64_debug.exe')
    need(source_program['bytes'] > 0, 'Actual linked program empty')
    runtimes = [*old['runtime'], stat(DEBUG_OMP)]
    need(len(runtimes) == 5 and len({Path(e['path']).name.casefold() for e in runtimes}) == 5,
         'Expected four original runtimes plus actual DebugOpenMP')
    for e in runtimes:
        ad.pin(e['path']); same(e)
    ad.finish()
    OUT.mkdir(); runtime_dir = OUT / 'runtime'; runtime_dir.mkdir()
    copies = []
    for e in runtimes:
        dest = runtime_dir / Path(e['path']).name
        with dest.open('xb') as f:
            f.write(Path(e['path']).read_bytes())
        need(dest.read_bytes() == Path(e['path']).read_bytes(), 'New runtime copy differs')
        copies.append(dict(source=e, destination=stat(dest)))
    program_copy = runtime_dir / Path(source_program['path']).name
    with program_copy.open('xb') as f:
        f.write(Path(source_program['path']).read_bytes())
    need(program_copy.read_bytes() == Path(source_program['path']).read_bytes(), 'New completed-program copy differs')
    result.update(passed=True, adopted_completed_build=True, original_build_passed=False,
                  original_failed_build=stat(OLDRESULT), original_failure=failed['failure'],
                  original_root_admission=stat(old_admission), prepared=stat(PREP), source_root=str(source_root),
                  source_program=source_program, program=stat(program_copy), runtime=copies, runtime_directory=str(runtime_dir),
                  program_copied=True, program_copy_byte_equal=True, program_relinked=False,
                  object_count=86, objects=objects, original_objects_reused=0,
                  dependencies=dependencies, actual_compiler_include_stats=[stat(p) for p in sorted(includes, key=key)],
                  actual_tlogs={n: stat(p) for n, p in logs.items()},
                  actual_link_library_stats=[stat(p) for p in sorted(libraries, key=key)],
                  actual_tool_call_receipts=tool_calls, actual_direct_tool_Popen_and_Win32_exits_all_zero=True,
                  source_suffix_recovered_before_flags_parse=True,
                  actual_unquoted_space_source_headers=sum(x['source_unquoted_with_spaces'] for x in after.values()),
                  numerical_flags_match_all86=True, binlog=stat(binlog),
                  compiler_exit_scope='Original MSBuild handles/exits and actual86 dependencies/tlogs; no invented CL/link handles',
                  consumed=ad.finish(), consumed_stats_unchanged=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execution-authorized', action='store_true'); ap.add_argument('--admission', required=True, type=Path)
    args = ap.parse_args(); need(args.execution_authorized, 'Independent root offline review authorization required')
    need(not OUT.exists() and not RECEIPT.exists(), 'Existing review/runtime output is protected; never overwrite or retry')
    result = dict(stage=STAGE, configuration='DebugCPU', passed=False,
                  original_build_passed=False, build_invocations=0, link_invocations=0,
                  program_invocations=0, native_invocations=0, VTK_invocations=0, SHA_scans=0,
                  old_receipt_or_build_output_modified=False, physical_acceptance=False,
                  historical_full_source_capture_claimed=False, following_action_launched=False)
    try:
        ad = Admission(args.admission); result['root_admission'] = ad.entry; review(ad, result)
    except Exception as exc:
        result.update(passed=False, first_error=str(exc), partial_runtime_copy_preserved=OUT.exists())
    result['ended_utc'] = datetime.now(timezone.utc).isoformat()
    write_new(RECEIPT, result)
    print(json.dumps(dict(passed=result['passed'], receipt=str(RECEIPT), first_error=result.get('first_error')), ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
