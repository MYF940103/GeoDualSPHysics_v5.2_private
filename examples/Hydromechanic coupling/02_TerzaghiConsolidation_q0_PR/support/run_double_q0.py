"""Provenance and overwrite guards for the formal double-state 2Tv BAT.

No solver source edits, build calls, or process launches are performed here.
The BAT calls preflight before GenCase, generated_check before the solver, and
validate_manifest before analysis. A launch manifest is not completion evidence.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile

CASE = Path(__file__).resolve().parent.parent
REPO = next(p for p in CASE.parents if (p / 'src/VS').is_dir())
BASELINE = CASE / 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_out'
CURRENT = CASE / 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_double_out'
NAME = CURRENT.name[:-4]
DEFINITION = CASE / (NAME + '_Def.xml')
BATCH = CASE / ('x' + NAME + '_win64_CPU.bat')
BASE_DEF = CASE / 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_Def.xml'
BASE_XML = BASELINE / (BASELINE.name[:-4] + '.xml')
LOG = CASE / 'tests/logs/pore_double_2tv'
MANIFEST = LOG / 'run_manifest.json'
GENERATED_RECORD = LOG / 'generated_manifest.json'
PREFIX = 'pore_double_q0_k1em4'
EXE = REPO / 'bin/windows/DualSPHysics5.2CPU_win64.exe'
READER = CASE / 'tests/outputs/pore_double_vel0/reader/export_state.exe'
EXPECTED_EXE = '95683EA87702A50CC8246B7C32C7DE9C2B203435985A373378A6FCDDA7347DBD'
STAGE1 = CASE / 'tests/notes/pore_double_stage1_manifest.json'
HISTORICAL = CASE / 'support/precision_q0_k1em4_run.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def save_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def signature(node):
    def normalize(value):
        try:
            return str(Decimal(value).normalize())
        except InvalidOperation:
            return value.strip()
    if node is None:
        return None
    attrs = tuple(sorted((key, normalize(value)) for key,value in node.attrib.items()
                         if 'comment' not in key and not key.startswith('_')))
    return node.tag, attrs, (node.text or '').strip(), tuple(signature(child) for child in node)


def compare_xml(left, right, generated=False):
    a, b = ET.parse(left).getroot(), ET.parse(right).getroot()
    sections = ['casedef', 'execution/special', 'execution/parameters']
    if generated:
        sections += ['execution/constants', 'execution/particles']
    for section in sections:
        require(signature(a.find(section)) == signature(b.find(section)), f'XML settings differ at {section}: {left} / {right}')
    return sections


def source_snapshot():
    stage = json.loads(STAGE1.read_text(encoding='utf-8-sig'))
    snapshot = []
    for item in stage['sources']:
        path = REPO / 'src' / item['file']
        expected = item['current_sha256']
        actual = sha(path) if path.exists() else None
        require(actual == expected, f'Frozen Stage 1 source changed: {path}')
        snapshot.append(dict(path=str(path), sha256=actual))
    old = json.loads(HISTORICAL.read_text(encoding='utf-8-sig'))
    baseline_hashes = {item['file']: item['baseline_sha256'] for item in stage['sources']}
    verified = []
    archive = CASE / stage['archive']
    require(sha(archive) == stage['archive_sha256'], 'Baseline source archive changed')
    with zipfile.ZipFile(archive) as z:
        for item in old['hashes']:
            if not item['path'].startswith('src/source/'):
                continue
            relative = item['path'][4:]
            require(baseline_hashes[relative] == item['sha256'], f'Historical baseline source differs: {relative}')
            packed = hashlib.sha256(z.read(Path(relative).name)).hexdigest().upper()
            require(packed == item['sha256'], f'Archived historical source differs: {relative}')
            verified.append(relative)
    require(len(verified) == 9, 'Historical core-source coverage changed; review provenance')
    return snapshot, dict(historical_core_sources_matching=verified,
        historical_executable_sha256=old['hashes'][0]['sha256'],
        stage1_baseline_executable_sha256='A2CD2B1023F6487EAC3F7D7185F02175494FE680B238C558C478B71E29B6EFF6',
        caveat='Nine recorded core sources match; historical executable differs after relinking. Historical obj/lib/DLL hashes are not complete, so this is not a controlled performance benchmark.')


def preflight():
    require(not CURRENT.exists(), f'Output already exists; nothing will be deleted: {CURRENT}')
    require(not MANIFEST.exists(), f'Launch record already exists: {MANIFEST}')
    require(not GENERATED_RECORD.exists(), f'Generated-input record already exists: {GENERATED_RECORD}')
    require(sha(EXE) == EXPECTED_EXE, 'CPU Release differs from the frozen double-state binary')
    require(READER.is_file(), f'Validated native reader is missing: {READER}')
    reader_build = json.loads((CASE/'tests/logs/pore_double_vel0/reader.build.json').read_text(encoding='utf-8-sig'))
    require(sha(READER) == reader_build['executable_sha256'], 'Native reader differs from the validated build')
    require(shutil.disk_usage(CASE).free > 2 * 1024**3, 'Less than 2 GiB free; do not start full run')
    sections = compare_xml(BASE_DEF, DEFINITION)
    tree = ET.parse(DEFINITION)
    for key,value in {'DtIni':1e-6,'DtFixed':1e-5,'TimeMax':72.8842857142858,'TimeOut':.182185714285714}.items():
        actual = float(tree.find(f"./execution/parameters/parameter[@key='{key}']").get('value'))
        require(actual == value, f'Unexpected formal {key}: {actual}')
    require(len(tree.findall('./execution/special/timeout/tout')) == 2, 'Exact-final output scheduling differs from the retained baseline')
    text = (BASELINE / 'Run.out').read_text(encoding='utf-8-sig')
    require('Finished execution (code=0).' in text, 'Historical baseline is not completed')
    for key,value in (('Excluded particles',0),('DTs adjusted to DtMin',0),('Steps of simulation',7288429),('PART files',402)):
        found = re.search(re.escape(key) + r'\.+:\s*(\d+)',text)
        require(found is not None and int(found[1]) == value, f'Baseline {key} differs')
    sources, provenance = source_snapshot()
    protected = [BASE_DEF, DEFINITION, BATCH, BASE_XML, BASE_XML.with_suffix('.bi4'),
        BASE_XML.with_name(BASE_XML.stem+'_Normals.nbi4'), BASELINE/'Run.out', BASELINE/'Run.csv',
        HISTORICAL, STAGE1, EXE, READER, Path(__file__), CASE/'support/compare_double_q0.py',
        CASE/'support/compare_precision_q0.py', CASE/'support/postprocess_terzaghi_q0.py',
        CASE/'tests/logs/pore_double_vel0/reader.build.json']
    for name in ('GenCase_win64.exe','PartVTK_win64.exe','vcomp140.dll','ChronoEngine.dll','dsphchrono.dll'):
        path = REPO/'bin/windows'/name
        require(path.is_file(), f'Missing dependency: {path}')
        protected.append(path)
    baseline_parts = sorted((BASELINE/'data').glob('Part_[0-9]*.bi4'))
    require(len(baseline_parts) == 402, 'Baseline PART file count differs')
    protected += baseline_parts + [BASELINE/'data/Part_Head.ibi4']
    figure_conflicts = list((CASE/'figures').glob(PREFIX+'_*'))
    require(not figure_conflicts, 'Final comparison artifacts already exist; do not overwrite them')
    record = dict(status='preflight_passed_not_completed', date=datetime.now(timezone.utc).isoformat(),
        batch_pid=os.getppid(), preflight_pid=os.getpid(), case=str(CASE), baseline=str(BASELINE), current=str(CURRENT),
        expected_steps=7288429, expected_frames=402, time_max_s=72.8842857142858, dt_s=1e-5, dt_ini_s=1e-6,
        solver_command=['-cpu','-ompthreads:4','-mdbc',str(CURRENT/NAME),str(CURRENT),'-dirdataout','data','-svres','-svextraparts:1'],
        equivalent_definition_sections=sections, source_snapshot=sources, baseline_provenance=provenance,
        protected_files=[dict(path=str(path.resolve()),sha256=sha(path)) for path in protected],
        completion_requirement='Run.out successful full completion, zero exclusions, complete native comparison and visual QA. This manifest alone is not acceptance.',
        prior_strict_short_pressure_screening='not passed; full run does not silently waive the old 0.01 Pa RMS / 0.1 Pa maximum limits')
    save_new(MANIFEST, record)
    print(f'Preflight passed; frozen source/binary and baseline recorded in {MANIFEST}', flush=True)
    return record


def validate_manifest():
    require(MANIFEST.is_file(), 'No launch manifest; cannot attribute this output to the frozen version')
    record = json.loads(MANIFEST.read_text(encoding='utf-8'))
    require(record['current'] == str(CURRENT) and record['baseline'] == str(BASELINE), 'Manifest paths differ')
    for item in record['protected_files']:
        require(sha(Path(item['path'])) == item['sha256'], f'Protected input/tool changed: {item["path"]}')
    # Production source hashes are historical launch evidence, not a reason to
    # relabel a running executable if the user later edits a source document.
    return record


def generated_check():
    record = validate_manifest()
    xml = CURRENT/(NAME+'.xml')
    sections = compare_xml(BASE_XML, xml, generated=True)
    files = [xml,CURRENT/(NAME+'.bi4'),CURRENT/(NAME+'_Normals.nbi4')]
    fingerprints = [dict(path=str(p.resolve()),sha256=sha(p)) for p in files]
    if GENERATED_RECORD.exists():
        previous = json.loads(GENERATED_RECORD.read_text(encoding='utf-8'))
        require(previous['launch_manifest_sha256'] == sha(MANIFEST), 'Launch manifest changed after generating the case')
        require(previous['generated_files'] == fingerprints, 'Generated case input changed after launch')
    else:
        save_new(GENERATED_RECORD, dict(date=datetime.now(timezone.utc).isoformat(),
            equivalent_generated_sections=sections, generated_files=fingerprints,
            launch_manifest_sha256=sha(MANIFEST), expected_steps=record['expected_steps']))
    print('Generated geometry, physical parameters and output schedule match the retained baseline.', flush=True)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--generated',action='store_true')
    args=parser.parse_args()
    if args.preflight:
        preflight()
    elif args.generated:
        generated_check()
    else:
        validate_manifest()
