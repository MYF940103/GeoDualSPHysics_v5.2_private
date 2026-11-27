"""Prepare the two Cryer P3 profiles and assemble an admitted Windows GPU package."""
import argparse
import csv
from decimal import Decimal as D, ROUND_CEILING
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

CASE = Path(__file__).resolve().parents[2]
SEED = Path('support/upl_seed_nu030_r1/CaseCryerProblem_u_pl_nu030_r1')
OLD_DEF = 'CaseCryerProblem_u_pl_nu030_r1_Def.xml'
RUNNER = Path('support/run_cryer_tpi_p3_r1.ps1')
README = Path('README_Cryer_TPI_P3_nu030_r1.md')
MANIFEST = Path('support/cryer_tpi_p3_package_r1.json')
STAGE_DIR = CASE / 'tests/outputs/cryer_tpi_p3_server_inputs_r1'
ZIP_NAME = 'Cryer_TPI_P3_nu030_Windows_RTXA6000_r1.zip'
PACKAGE = CASE/'tests/outputs/retired_frozen_20261128'/ZIP_NAME
SOLVER = 'DualSPHysics5.2_GEO_win64.exe'
BIN = Path('support/bin_cryer_tpi_p3_r1')
RUNTIME = ('ChronoEngine.dll', 'dsphchrono.dll', 'DsphConfig.xml', 'vcomp140.dll',
           'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
SELECTORS = dict(UPL_TPI_GPU_R1='B', UPL_TPI_P3_ROWS_R1='3', UPL_TPI_M0_DT_R1='EQ40_RH1')
DT = D(2)**-19
DRAIN = D(2)**-7
FINE = D(2)**-13
E, NU, A = D(2_000_000), D('.3'), D('.05')
CV_LEGACY = E*(1-NU)/((1+NU)*(1-2*NU)) * D('1e-5')/(1000*D('9.81'))
TV1 = A*A/CV_LEGACY
CADENCE = D('.005')*TV1
N_FULL = int(((DRAIN + TV1)/DT).to_integral_value(rounding=ROUND_CEILING))
PROFILES = {'peak': (36864, 577, FINE), 'full': (N_FULL, 265, CADENCE)}
ENVELOPE = 'cryer_tpi_p3_nu030_B_dt2m19_r1'


def require(test, msg):
    if not test:
        raise ValueError(msg)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stem(stage):
    return f'CaseCryer_TPI_P3_nu030_{stage}_r1'


def xbytes(node):
    return b"<?xml version='1.0' encoding='utf-8'?>\n" + ET.tostring(node, encoding='utf-8') + b'\n'


def physics_signature(node):
    attrs = {k:v for k,v in node.attrib.items() if k not in ('comment','_rem','units_comment')}
    return (node.tag, attrs, [physics_signature(child) for child in node])


def profile_files(stage):
    steps, frames, interval = PROFILES[stage]
    start = ET.parse(CASE / OLD_DEF).getroot()
    generated = ET.parse(CASE / SEED.with_suffix('.xml')).getroot()
    for section in ('casedef', 'execution/special', 'execution/parameters'):
        require(physics_signature(start.find(section)) == physics_signature(generated.find(section)),
                f'Seed/definition mismatch: {section}')
    timeout = start.find('./execution/special/timeout')
    timeout[1].set('timeout', str(interval))
    for key, value, description in (
        ('DtIni', DT, 'Initial P3 step'), ('DtFixed', DT, 'Fixed P3 step'),
        ('TimeMax', steps*DT, 'Peak window' if stage == 'peak' else 'First step reaching drainage-relative legacy Tv=1'),
        ('TimeOut', interval, 'Pressure peak sampling' if stage == 'peak' else 'Drainage-relative Delta Tv=0.005')):
        node = start.find(f'./execution/parameters/parameter[@key="{key}"]')
        node.set('value', str(value))
        node.set('comment', description)
    start.find('.//HydroMechDynamicSeepage').set('comment', 'Enable dynamic seepage')
    start.find('.//PRvs').set('comment', 'Drained Poisson ratio')
    end_nominal = DRAIN + (D(2)**-4 if stage == 'peak' else TV1)
    grid = [FINE*i for i in range(65)] + [DRAIN + interval*i for i in range(1, frames-64)]
    require(abs(grid[-1]-end_nominal) < D('1e-23'), 'Endpoint target')
    # As in JDsOutputTime, save at the first reached target, plus a forced terminal if needed.
    # dt is dyadic, so repeated binary64 additions are exact at these step indices.
    sb = io.StringIO(newline='')
    writer = csv.writer(sb, lineterminator='\n')
    writer.writerow(['part','completed_steps','native_step','time_s','target_s','drain_open'])
    result = []
    for part, target in enumerate(grid):
        step = int((target / DT).to_integral_value(rounding=ROUND_CEILING))
        require(not result or step > result[-1], 'Repeated planned step')
        result.append(step)
        writer.writerow([part,step,max(0,step-1), str(step*DT),str(target),int(step*DT>DRAIN)])
    require(len(result) == frames and result[64] == 4096 and result[-1] == steps, 'Wrong schedule')
    bat = '\r\n'.join((
        '@echo off','setlocal','set "mode="','set "pause_at_end=1"',
        'if /i "%~1"=="--check-only" set "mode=-CheckOnly"',
        'if /i "%~1"=="--check-only" set "pause_at_end=0"',
        'if /i "%~1"=="--unattended" set "pause_at_end=0"',
        'if not "%~2"=="" exit /b 2',
        'if not "%~1"=="" if "%pause_at_end%"=="1" exit /b 2',
        f'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0support\\run_cryer_tpi_p3_r1.ps1" -Stage {stage} %mode%',
        'set "rc=%ERRORLEVEL%"','if "%pause_at_end%"=="1" pause','exit /b %rc%',''))
    return {Path(stem(stage)+'_Def.xml'):xbytes(start), Path('x'+stem(stage)+'_win64_GPU.bat'):bat.encode('ascii'),
            Path('support')/(stem(stage)+'_schedule.csv'):sb.getvalue().encode('ascii')}


def write_unique(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def input_files():
    return {**profile_files('peak'), **profile_files('full')}


def program_from_gate(path):
    gate = json.loads(path.read_text(encoding='utf-8-sig'))
    require((gate.get('pass') is True or gate.get('passed') is True) and gate.get('scheme') == 'B'
            and gate.get('rounds') == 3 and gate.get('nu') == .3 and gate.get('dt_s') == float(DT),
            'A qualified Cryer P3 B GPU Release at this step is required')
    entries = [gate['program'], *gate['evidence']]
    require(len(entries) >= 2, 'Missing qualification evidence')
    for entry in entries:
        file = Path(entry['path'])
        stat = file.stat()
        require(stat.st_size == entry['bytes'] and stat.st_mtime_ns == entry['mtime_ns'],
                f'Qualification input changed: {file}')
    exe = Path(entries[0]['path'])
    require(exe.suffix.lower() == '.exe' and 'release' in str(exe).lower(), 'Wrong Release program binding')
    return exe


def match_local_seed(inputs):
    """Check the passed startup geometry and constitutive inputs before distribution."""
    short = CASE/'tests/outputs/cryer_p3_local_seed_r1/upl_cryer_freebody_short_r1.xml'
    require(short.with_suffix('.bi4').read_bytes() == (CASE/SEED.with_suffix('.bi4')).read_bytes(),
            'Server seed is not the original local regression particle file')
    src = ET.parse(short).getroot()
    native = ET.parse(CASE/SEED.with_suffix('.xml')).getroot()
    for field in ('execution/particles','execution/constants','casedef'):
        require(physics_signature(src.find(field)) == physics_signature(native.find(field)), field)
    for stage in PROFILES:
        deck = ET.fromstring(inputs[Path(stem(stage)+'_Def.xml')])
        for section in ('casedef','execution/special/soils','execution/special/hydromechanics'):
            require(physics_signature(src.find(section)) == physics_signature(deck.find(section)), section)
        def parameters(root):
            return {p.get('key'):float(p.get('value')) for p in root.findall('execution/parameters/parameter')
                    if p.get('key') not in ('TimeOut','TimeMax')}
        require(parameters(src)==parameters(deck), 'Untested parameter drift')


def archive_payload(exe, files):
    payload = dict(files)
    for rel in (Path('LICENSE'), README, RUNNER, SEED.with_suffix('.xml'), SEED.with_suffix('.bi4')):
        payload[rel] = (CASE/rel).read_bytes()
    payload[BIN/SOLVER] = exe.read_bytes()
    for name in RUNTIME:
        origin = exe.parent/name
        if not origin.is_file():
            require(name in ('msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'),
                    f'Missing build runtime dependency: {origin}')
            origin = CASE/'support/bin_upl_r1'/name
        payload[BIN/name] = origin.read_bytes()
    rows = [dict(name=rel.as_posix(),bytes=len(data),sha256=digest(data)) for rel,data in sorted(payload.items())]
    # Bind both the runtime deck and initial sphere along with the peak definition.
    peak_sig = digest(b''.join(payload[rel] for rel in
        (Path(stem('peak')+'_Def.xml'),SEED.with_suffix('.xml'),SEED.with_suffix('.bi4'))))
    manifest = dict(package_id=ENVELOPE, method='Cryer P3 Eq40 Rh1', scheme='B', rounds=3, nu=.30,
                    dt_s=float(DT), selectors=SELECTORS, program_sha256=digest(payload[BIN/SOLVER]),
                    peak_input_sha256=peak_sig, preflight_scope='short local implementation qualification',
                    legacy_cv_m2_s=float(CV_LEGACY), full_output_delta_tv=.005,
                    profiles={s:dict(steps=n,frames=f,end_s=float(n*DT),postdrain_cadence_s=float(t))
                              for s,(n,f,t) in PROFILES.items()}, files=rows)
    payload[MANIFEST] = (json.dumps(manifest,indent=2)+'\n').encode('ascii')
    return payload


def publish(path):
    exe = program_from_gate(path)
    files = input_files()
    match_local_seed(files)
    payload = archive_payload(exe, files)
    name = PACKAGE
    checksum = name.with_suffix('.zip.sha256')
    receipt = CASE/'tests/logs/cryer_tpi_p3_server_release_r1.check.json'
    # Publish only new formal artifacts. Existing root inputs used by this package remain immutable.
    for dest in (name,checksum,receipt):
        if dest.exists():
            raise FileExistsError(dest)
    for rel,data in payload.items():
        if (CASE/rel).exists():
            require((CASE/rel).read_bytes() == data, f'Existing file differs: {rel}')
    # Same-volume rename publishes a complete, CRC-checked archive. Windows rename
    # also rejects an existing destination if another publisher arrived meanwhile.
    with tempfile.TemporaryDirectory(prefix='cryer_p3_',dir=CASE/'tests/outputs') as tempdir:
        archived = Path(tempdir)/name.name
        with zipfile.ZipFile(archived,'x',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
            for rel,data in payload.items():
                z.writestr(rel.as_posix(),data)
        with zipfile.ZipFile(archived) as z:
            require(len(z.namelist()) == len(payload) and z.testzip() is None, 'ZIP CRC or member count')
            with tempfile.TemporaryDirectory(prefix='Cryer Windows transfer ') as extraction:
                z.extractall(extraction)
                for stage in PROFILES:
                    bat='x'+stem(stage)+'_win64_GPU.bat'
                    preflight=subprocess.run([os.environ['COMSPEC'],'/d','/c',bat,'--check-only'],
                                             cwd=extraction,capture_output=True,check=False)
                    require(preflight.returncode==0, f'{stage} transfer preflight: {preflight.stdout!r} {preflight.stderr!r}')
        for rel,data in payload.items():
            if not (CASE/rel).exists():
                write_unique(CASE/rel,data)
        checksum_text=(digest(archived.read_bytes())+'  '+name.name+'\n').encode('ascii')
        name.parent.mkdir(parents=True, exist_ok=True)
        archived.rename(name)
    write_unique(checksum, checksum_text)
    m=json.loads(payload[MANIFEST])
    check=dict(passed=True,qualification=str(path.resolve()),archive=str(name.resolve()),
               bytes=name.stat().st_size,sha256=checksum_text.decode().split()[0],members=len(payload),
               actual_private_Release=str(exe.resolve()),program_sha256=m['program_sha256'],
               peak_input_sha256=m['peak_input_sha256'],profiles=m['profiles'],
               extracted_real_BAT_preflight=['peak','full'],physical_solver_invocations=0,
               native_reads=0,A6000_execution_observed=False,peak_physics_pending=True)
    write_unique(receipt,(json.dumps(check,indent=2)+'\n').encode('utf-8'))
    print(name)


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    commands=ap.add_subparsers(dest='command',required=True)
    commands.add_parser('prepare')
    publish_parser=commands.add_parser('publish')
    publish_parser.add_argument('qualification',type=Path)
    args=ap.parse_args()
    if args.command == 'prepare':
        files=input_files()
        match_local_seed(files)
        for relative, data in files.items():
            path=STAGE_DIR/relative
            if path.exists():
                require(path.read_bytes() == data, f'Existing preparation differs: {path}')
            else:
                write_unique(path,data)
        print(STAGE_DIR)
    else:
        publish(args.qualification)

