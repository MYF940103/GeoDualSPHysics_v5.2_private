"""Reconstruct one explicit C04 source candidate; no build, program or data read.

This is a new reconstruction, NOT a retroactive full-source capture of the old
freebody DebugCPU build. Read the companion note before authorizing it.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
T02 = TESTS.parent.parent / '02_TerzaghiConsolidation_q0_PR' / 'tests'
LABEL = 'upl_tpi_cryer_cpu_source_r1'
BASE = 'de2492afb5be33e9077f8e4a96bfe755b0ffc7ed'
OUT = TESTS / 'outputs' / 'upl_tpi_cryer_cpu_r1_source'
CHECK = TESTS / 'logs' / (LABEL + '.prepare.json')
SOURCE_RECEIPT = TESTS / 'logs' / 'upl_cryer_freebody_r1.source.json'
BUILD_RECEIPT = TESTS / 'logs' / 'upl_cryer_freebody_r1_DebugCPU.build.json'
CALL_RECEIPT = TESTS / 'logs' / 'upl_cryer_freebody_r1_DebugCPU.call.json'
UPSTREAM_RECEIPT = T02 / 'logs' / 'upl_spr_av_ReleaseCPU_r1.build.json'
ZIP_SOURCES = {
    'JSph.h', 'JSph.cpp', 'JSphCpuSingle.cpp', 'JSphGpuSingle.cpp',
    'JSphCpu.cpp', 'JSphGpu.cpp', 'JSphGpu_ker.h', 'JSphGpu_ker.cu',
}
GIT_RESTORES = {
    'JSphHourglassGpu.cpp', 'JSphHourglassGpu.h',
    'JSphHourglassGpu_ker.cu', 'JSphHourglassGpu_ker.h',
}
EXPECTED_CONTENT_DIFF = GIT_RESTORES | {
    'JSph.cpp', 'JSphGpu.cpp', 'JSphGpu_ker.cu', 'JSphGpuSingle.cpp',
}
ZIP_DOCS = {
    'doc/xml_format/_FmtXML_ElastoplasticSoil.xml': 'docs/_FmtXML_ElastoplasticSoil.xml',
    'examples/Hydromechanic coupling/04_CryerProblem_PR/README.md': 'docs/historical_C04_README.md',
}
PROJECTS = ('DualSPHysics5ReCpu_vs2022.sln', 'DualSPHysics5ReCpu.vcxproj')
MSNS = {'m': 'http://schemas.microsoft.com/developer/msbuild/2003'}


def need(test: bool, message: str) -> None:
    if not test:
        raise RuntimeError(message)


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def stat(path: Path) -> dict:
    s = path.stat()
    need(path.is_file(), f'Not a file: {path}')
    return {'path': str(path), 'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns}


def git(*args: str) -> bytes:
    r = subprocess.run(['git', *args], cwd=REPO, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, check=False)
    need(r.returncode == 0, f'Git read failed: {args}: {r.stderr.decode(errors="replace")}')
    return r.stdout


def blob(relative: str) -> bytes:
    return git('show', BASE + ':' + relative)


def eol(data: bytes) -> bytes:
    return data.replace(b'\r\n', b'\n')


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data)
    need(path.read_bytes() == data, f'New copy byte verification failed: {path}')


def save_new(path: Path, obj: dict) -> None:
    write_new(path, (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Explicit source-preparation authorization required')
    need(not OUT.exists() and not CHECK.exists(), 'New source/check tag already exists; never overwrite or retry')
    before: dict[str, dict] = {}

    def observed(path: Path) -> bytes:
        key = str(path.resolve())
        s = stat(path)
        before.setdefault(key, s)
        need(before[key] == s, f'Input changed before read: {path}')
        data = path.read_bytes()
        need(stat(path) == s and len(data) == s['bytes'], f'Input changed during read: {path}')
        return data

    record = {
        'stage': LABEL, 'started_utc': datetime.now(timezone.utc).isoformat(),
        'passed': False, 'source_reconstruction': True,
        'historical_full_source_capture_claimed': False,
        'historical_object_source_identity_claimed': False,
        'solver_invoked': False, 'build_invoked': False, 'native_invoked': False,
        'hash_scan_performed': False, 'canonical_sources_changed': False,
        'two_TU_TPI_hooks_applied': False, 'physical_acceptance': False,
    }
    try:
        for p in (SOURCE_RECEIPT, BUILD_RECEIPT, CALL_RECEIPT, UPSTREAM_RECEIPT):
            observed(p)
        sr, br, call, upstream = map(load, (SOURCE_RECEIPT, BUILD_RECEIPT, CALL_RECEIPT, UPSTREAM_RECEIPT))
        need(sr['base_commit'] == BASE and sr['changed_source_files'] == 8, 'Freebody base/changed-source contract differs')
        need(br['passed'] and br['configuration'] == 'DebugCPU' and br['exit_code'] == 0
             and br['objects'] == 86 and br['source_and_canonical_stats_unchanged'], 'Original DebugCPU build not valid')
        need(Path(br['source_snapshot']).resolve() == SOURCE_RECEIPT.resolve(), 'Original source receipt binding differs')
        need(call['exit_code'] == 0 and call['direct_exit'], 'Original direct MSBuild call not successful')
        need(upstream['passed'] and upstream['configuration'] == 'ReleaseCPU'
             and upstream['source_code_header_count'] == 265 and upstream['source_bindings_unchanged'],
             'Selected upstream source archive receipt differs')
        need(git('cat-file', '-t', BASE).strip() == b'commit', 'Recorded Git base is not a commit')

        archive = Path(sr['archive']['path'])
        archive_data = observed(archive)
        need(before[str(archive.resolve())]['bytes'] == sr['archive']['bytes']
             and before[str(archive.resolve())]['mtime_ns'] == sr['archive']['mtime_ns'], 'Original eight-file ZIP stat differs')
        import io
        with zipfile.ZipFile(io.BytesIO(archive_data)) as z:
            names = set(z.namelist())
            need(len(names) == 10 and names == {'src/source/' + n for n in ZIP_SOURCES} | set(ZIP_DOCS),
                 'ZIP membership differs; no path traversal or extra files allowed')
            zipped = {n: z.read('src/source/' + n) for n in ZIP_SOURCES}
            docs = {dest: z.read(src) for src, dest in ZIP_DOCS.items()}
        zip_stats = {Path(x['path']).name: x for x in sr['before'] if '/src/source/' in x['path'].replace('\\', '/')}
        need(set(zip_stats) == ZIP_SOURCES and all(len(zipped[n]) == zip_stats[n]['bytes'] for n in ZIP_SOURCES),
             'ZIP source lengths differ from original source receipt')

        pairs = upstream['source_snapshot']
        need(len(pairs) == 265, 'Expected 265 upstream source/header files')
        source_bytes, origin_rows, git_differences = {}, [], []
        for pair in pairs:
            old = Path(pair['snapshot']['path'])
            name = old.name
            need(name not in source_bytes and Path(pair['original']['path']).name == name,
                 'Duplicate/renamed upstream source entry')
            raw = observed(old)
            need(len(raw) == pair['snapshot']['bytes'] == pair['original']['bytes'], 'Upstream recorded source size differs')
            base_data = blob('src/source/' + name)
            relation = 'exact' if raw == base_data else 'EOL-only' if eol(raw) == eol(base_data) else 'content-different'
            if relation == 'content-different':
                git_differences.append(name)
            if name in ZIP_SOURCES:
                value, kind, origin = zipped[name], 'historical_freebody_changed_source_zip', 'src/source/' + name
            elif name in GIT_RESTORES:
                value, kind, origin = base_data, 'recorded_git_base_blob', BASE + ':src/source/' + name
            else:
                need(relation in ('exact', 'EOL-only'), f'Unexpected non-ZIP Git content drift: {name}')
                value, kind, origin = raw, 'upstream_archived_source_bytes', str(old)
            source_bytes[name] = value
            origin_rows.append({'name': name, 'origin_kind': kind, 'origin': origin,
                                'bytes': len(value), 'upstream_vs_recorded_git': relation,
                                'upstream_recorded_sha256_not_recomputed': pair['snapshot']['sha256']})
        need(set(git_differences) == EXPECTED_CONTENT_DIFF, 'Upstream/Git content difference set changed')
        need(Counter(x['origin_kind'] for x in origin_rows) == {
            'historical_freebody_changed_source_zip': 8, 'recorded_git_base_blob': 4,
            'upstream_archived_source_bytes': 253}, 'Source provenance count differs')

        # Retained MSVC tlogs establish actual old file paths, NOT historical bytes.
        args_old = call['arguments']
        int_arg = [x for x in args_old if x.startswith('/p:IntDir=')]
        need(len(int_arg) == 1, 'Original IntDir contract differs')
        tlog_root = Path(int_arg[0].split('=', 1)[1]) / 'DualSPHysics.tlog'
        read_log, command_log = tlog_root / 'CL.read.1.tlog', tlog_root / 'CL.command.1.tlog'
        read_lines = observed(read_log).decode('utf-16').splitlines()
        observed(command_log)
        tus = [Path(x[1:]).name for x in read_lines if x.startswith('^')]
        repo_text = str(REPO).upper()
        local = {Path(x.lstrip('^')).name.upper() for x in read_lines if repo_text in x.upper()}
        source_upper = {x.upper() for x in source_bytes}
        need(len(tus) == 86 and len(set(x.upper() for x in tus)) == 86
             and len(local) == 201 and local <= source_upper, 'Actual old CPU dependency membership differs')
        need(len(local & {x.upper() for x in ZIP_SOURCES}) == 4 and not local & {x.upper() for x in GIT_RESTORES},
             'Expected four changed CPU files / no GPU-HG source dependency')
        projects = {name: blob('src/VS/' + name) for name in PROJECTS}
        root = ET.fromstring(projects['DualSPHysics5ReCpu.vcxproj'])
        effective = []
        for item in root.findall('.//m:ClCompile[@Include]', MSNS):
            excluded = any('DebugCPU|x64' in n.attrib.get('Condition', '') and n.text == 'true'
                           for n in item.findall('m:ExcludedFromBuild', MSNS))
            if not excluded:
                effective.append(Path(item.attrib['Include']).name.upper())
        need(len(effective) == 86 and set(effective) == {x.upper() for x in tus},
             'Recorded authoritative CPU project does not reproduce actual 86-TU membership')

        helper = T02 / 'outputs' / 'upl_tpi_cpu_r1_source' / 'upl_tpi_cpu_r1.h'
        author_helper = T02 / 'support' / 'upl_tpi_cpu_r1.h'
        helper_data = observed(helper)
        need(helper_data == observed(author_helper), 'Previously tested helper differs from author helper; no silent substitution')
        for key, s in before.items():
            need(stat(Path(key)) == s, f'Observed input changed before freeze: {key}')
        OUT.mkdir(parents=False, exist_ok=False)
        for name, value in source_bytes.items():
            write_new(OUT / 'source' / name, value)
        write_new(OUT / 'source' / 'upl_tpi_cpu_r1.h', helper_data)
        for name, value in projects.items():
            write_new(OUT / 'VS' / name, value)
        for relative, value in docs.items():
            write_new(OUT / relative, value)
        manifest = {
            **record, 'passed': True, 'base_commit': BASE, 'source_count': 265,
            'extra_helper_count': 1, 'source_origins': origin_rows,
            'git_content_differences_from_upstream': sorted(git_differences),
            'project_origins': [{'name': n, 'origin': BASE + ':src/VS/' + n, 'bytes': len(v)} for n, v in projects.items()],
            'helper_origin': stat(helper), 'helper_unchanged_byte_copy': True,
            'old_actual_debug_TU_count': 86, 'old_actual_project_header_count': 115,
            'old_actual_local_dependency_count': 201,
            'old_dependency_paths_verified_not_old_dependency_bytes': True,
            'old_build_had_sourceDependencies_json': False,
            'recovered_candidate_requires_new_full_86_object_compile': True,
            'reuse_old_84_or_86_objects_authorized': False,
            'libraries_and_runtime_copied': False,
            'build_library_plan': 'Bind original five Debug project libraries and selected runtime separately before any full build; no current source objects may be mixed.',
            'source_inputs': list(before.values()),
            'current_git_head_for_context_only': git('rev-parse', 'HEAD').decode().strip(),
            'ended_utc': datetime.now(timezone.utc).isoformat(),
        }
        save_new(OUT / 'source_diff.json', manifest)
        record.update({'passed': True, 'output_directory': str(OUT), 'manifest': stat(OUT / 'source_diff.json'),
                       'source_count': 265, 'source_origin_counts': dict(Counter(x['origin_kind'] for x in origin_rows)),
                       'source_inputs_unchanged': all(stat(Path(k)) == v for k, v in before.items())})
        need(record['source_inputs_unchanged'], 'Input stat changed after reconstruction; retain new candidate for diagnosis')
    except Exception as exc:
        record.update({'passed': False, 'first_error': str(exc), 'partial_output_preserved': OUT.exists()})
    record['ended_utc'] = datetime.now(timezone.utc).isoformat()
    save_new(CHECK, record)
    print(json.dumps({'passed': record['passed'], 'check': str(CHECK), 'first_error': record.get('first_error')}, ensure_ascii=False))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
