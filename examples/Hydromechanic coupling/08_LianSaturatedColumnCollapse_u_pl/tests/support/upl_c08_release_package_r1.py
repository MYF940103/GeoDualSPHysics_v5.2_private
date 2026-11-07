"""Prepare the reviewed C08 Windows delivery once. Never build or run a program."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

CASE = Path(__file__).resolve().parents[2]
TESTS = CASE / 'tests'
REPO = CASE.parents[2]
C05 = CASE.parent / '05_LianFlexibleStrip2D_PR'
PACKAGE = 'LianCollapse_upl_win64_r1'
GROUPS = [('psi0', 0., 5000., 0.), ('psi2p5', 2.5, 5000., .2), ('psim5', -5., 7500., .2)]
RUNTIME = ['DsphConfig.xml', 'ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll']
CRT = ['msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll']


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    need(path.is_file(), f'Not a file: {path}')
    return {'path': str(path), 'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns}


def bound(entry):
    need(stat(entry['path']) == entry, f'Frozen file changed: {entry["path"]}')
    return Path(entry['path'])


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def encoded(text):
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8')


def checked_programs(final):
    need(final['passed'] is True and final['memcheck_zero_errors_and_leaks'] is True,
         'Combined CPU/GPU/native/comparison check has not passed')
    for key, maximum in [('pressure_RMS_max_Pa', 5.), ('material_XYZ_max_mm', .005), ('time_error_max_s', 1e-14)]:
        x = final[key]
        need(math.isfinite(x) and 0 <= x <= maximum, f'Original comparison bound failed: {key}')
    need(final['physical_acceptance'] is False, 'Do not relabel the short check as physical acceptance')
    programs = {}
    for backend in ['CPU', 'GPU']:
        native = load(bound(final['backend_checks'][backend]))
        run = load(bound(final['run_checks'][backend]))
        build = load(bound(final['source_builds'][backend]))
        program = bound(final['programs'][backend])
        need(native['passed'] is True and run['passed'] is True and build['passed'] is True,
             f'Closed {backend} native/run/build is not passed')
        need(run['program'] == final['programs'][backend] and build['program'] == final['programs'][backend],
             f'{backend} run/build program differs from final comparison binding')
        expected = 'DualSPHysics5.2CPU_win64.exe' if backend == 'CPU' else 'DualSPHysics5.2_GEO_win64.exe'
        need(program.name == expected, f'{backend} is not the selected Release program')
        programs[backend] = program
    return programs


def formal_xml(path, psi, cohesion, decay):
    text = path.read_text(encoding='utf-8')
    root = ET.fromstring(text)
    value = lambda tag: root.find('./execution/special/' + tag).attrib['value']
    need([float(value('soils/' + tag)) for tag in ['dlt', 'coh', 'coh_r', 'n_coh', 'DilationDecay', 'phi', 'phi_r', 'n_phi', 'MaterialReturn']]
         == [psi, cohesion, 1000., 5., decay, 25., 25., 0., 1.], 'Material group differs')
    need([float(value('hydromechanics/' + tag)) for tag in ['HydroMechDynamicSeepage', 'HydroMechConductivityModel', 'HydroMechConductivityCk', 'HydroMechInitZ', 'HydroMechFreeSeepage', 'HydroMechDrainage', 'PoreShepardRegularization', 'PoreShepardInterval']]
         == [1., 1., 2., 2., 1., 0., 1., 40.], 'Dynamic/Ck2/hydrostatic/free-seepage settings differ')
    need(value('hydromechanics/HydroMechInitMode') == 'ConstantZ', 'Fresh hydrostatic initialization required')
    event = root.find('./execution/special/gravitypreload')
    need(float(event.attrib['time']) == 10. and event.attrib['release_mkbound'] == '2', 'Release event differs')
    p = {x.attrib['key']: x.attrib['value'] for x in root.findall('./execution/parameters/parameter')}
    for key, x in {'TimeMax': 13., 'TimeOut': .01, 'DtFixed': 2.5e-6, 'SoilDamping': 1., 'SoilDampingCoef': .02, 'PartsOutMax': 0., 'SavePosDouble': 1., 'DPCtes': 3., 'SoilHourglassXi': 0., 'SoilBoundaryDerivativeSPR': 0., 'Shifting': 0., 'DensityDT': 0.}.items():
        need(float(p[key]) == x, f'Candidate parameter differs: {key}')
    # Only comments change on promotion; no physical node or value is rewritten.
    text, count = re.subn(r'<!-- UNEXECUTED .*? -->', '<!-- Windows server calculation input; bounded compatibility checked, full 13 s physical results remain to be reviewed. -->', text, count=1)
    need(count == 1, 'Expected candidate provenance comment missing')
    text = text.replace('Experimental dynamic u-pl candidate; combined variable-k/material/release review pending', 'Experimental dynamic u-pl; bounded compatibility checked, full13s physical review pending')
    text = text.replace('Existing void-ratio exponential k(J); combined scope pending verification', 'Existing void-ratio exponential k(J); explicit Ck=2')
    return encoded(text)


def launcher(path):
    text = path.read_text(encoding='ascii')
    for old, new in [('cd /d "%~dp0"', 'cd /d "%~dp0.."'), ('set candidate_ready=0\n', ''),
                     ('set dirbin=..\\outputs\\upl_collapse_runtime_PENDING', 'set dirbin=support\\runtime'),
                     ('set dirdef=..\\configs', 'set dirdef=.'), ('set dirout=..\\outputs\\%name%_out', 'set dirout=%name%_out'),
                     ('if not "%candidate_ready%" == "1" goto notready\n', '')]:
        need(text.count(old) == 1, f'Launcher template changed: {old}')
        text = text.replace(old, new, 1)
    start, end = text.index(':notready\n'), text.index(':exists\n')
    text = text[:start] + text[end:]
    text = text.replace('rem UNEXECUTED CANDIDATE. Verify combined scope and package the runtime before unlocking.', 'rem Windows x64 CPU8 / NVIDIA GPU0; preserve retained outputs and run one backend per group.')
    need('PENDING' not in text and 'candidate_ready' not in text and '-partbegin' not in text and '-nsteps' not in text and '-svextraparts' not in text,
         'Unreviewed runtime/restart/step-cap/Extra option remains')
    return encoded(text)


def server_readme(head):
    return encoded(f'''# Lian 2023 饱和土柱塌陷：Windows 运行包

完整解压 `{PACKAGE}.zip` 后运行，不要在 ZIP 内双击。目标为 Windows x64、NVIDIA RTX A6000；GPU入口默认GPU0，CPU入口默认8线程。同一组择一后端，输出已存在会拒绝，绝不删除或自动续算。

根目录三组入口为 `xCaseLianSaturatedColumnCollapse_psi0_r1_win64_GPU.bat`、`..._psi2p5_r1_...`、`..._psim5_r1_...`；CPU入口把GPU换成CPU。可加 `--unattended` 仅关闭结束暂停。各组输出为对应同名 `_out`，请保留并复制整个输出目录回来，包括初始BI4/Normals、全部Part/日志/Run.csv及本运行包。BAT只做GenCase与一次完整求解，不运行Python、不转换VTK、不绘图。

| 组 | 初始剪胀角 | 峰值黏聚力 | 残余黏聚力 | 黏聚力衰减 | 剪胀衰减sf |
|---|---:|---:|---:|---:|---:|
| psi0 | 0° | 5 kPa | 1 kPa | 5 | 0 |
| psi2p5 | +2.5° | 5 kPa | 1 kPa | 5 | 0.2 |
| psim5 | −5° | 7.5 kPa | 1 kPa | 5 | 0.2 |

三组均φ=25°固定、MaterialReturn1、现有Model1/Ck2，dp=.04m、Cubic h/dp1.2、E20MPa、ν=.33、n0=.35、Kw1GPa、k0=2e-4m/s。左/右墙FreeSlip、底NoSlip；床长12m是数值域裕量，不是论文指定尺寸。

每组从零有效应力和ConstantZ H2静水p0开始，真实重力预载10s；同进程撤去右mkbound2后继续3s，TimeMax13s，dt=2.5µs、输出间隔.01s。预载阻尼.02/Shepard40由撤墙事件关闭，p0/J/应力/塑性历史连续，不加载PART、不复用另一材料组的预载。τ应按原生实际撤墙时间计算，不重写保存时钟。保留初始Normals与主22数组，不逐帧重复输出墙法向Extra。

已通过的是受限实现/组合短窗，不是13s论文精度或严格初态平衡验收。保留常k10s预载仍有较弱固结及参考残差；本组三个变k材料预载需各自回看。没有TPI、论文负压松弛、HG、独立SPR、NoPen、shifting、三维塑性或精确重启。负孔压保留；不支持的材料顶点或原稳定门失败会停止，保留部分输出供诊断，不自行放宽限制。

运行库放在 `support/runtime`；附带C05已署名VS14.36应用本地CRT三件组。Windows系统UCRT和适合显卡/程序的NVIDIA驱动由服务器提供；BAT不需要Visual Studio、CUDA Toolkit或Python。本机RTX3050短测不是A6000实机验收。若系统运行库提示缺失，使用微软官方x64 VC++ Redistributable，不复制未知System32 DLL。

复制回来后再生成实际时间的孔压/超孔压、位移/形态、应力、κ/n/k及论文Fig14–17对比PNG和CSV。纸面停止时刻不是强制数值门，孔压负值也不自动等于数值错误。

源码节点 `{head}` 由根线程提供；程序及输入SHA256、构建/短窗来源在 `support/server_manifest_r1.json`，校验清单在 `support/SHA256SUMS_r1.txt`。项目许可证为根目录LICENSE；对应完整修改源码请通过交付者取得。其余来源见 `support/THIRD_PARTY_NOTICES_r1.txt`。本包不含tests或历史输出。
''')


def prepare(head):
    check = TESTS / 'logs/upl_ck2_release_short_r1.check.json'
    final = load(check)
    programs = checked_programs(final)
    manifest05 = C05 / 'support/server_manifest.json'
    old = load(manifest05)
    need(old['runtime']['mode'] == 'signed_MSVC_14_app_local_from_Visual_Studio_redist', 'C05 signed CRT provenance missing')
    old_hash = {Path(x['entry']).name: x['sha256'].lower() for x in old['files']}
    crt_hash = {x['name']: x['sha256'].lower() for x in old['runtime']['files']}
    need(set(crt_hash) == set(CRT) and all(x['signature_status'] == 'Valid' and 'Microsoft' in x['signer'] for x in old['runtime']['files']), 'C05 CRT signature evidence incomplete')
    payload, expected = {}, {}
    def add(relative, source):
        need(relative not in payload, f'Duplicate payload: {relative}')
        payload[relative] = source
    sources = [check, manifest05]
    for group, psi, cohesion, decay in GROUPS:
        stem = f'CaseLianSaturatedColumnCollapse_{group}_r1'
        definition = TESTS / 'configs' / (stem + '_Def.xml')
        sources.append(definition)
        add(stem + '_Def.xml', formal_xml(definition, psi, cohesion, decay))
        for backend in ['CPU', 'GPU']:
            name = 'x' + stem + '_win64_' + backend + '.bat'
            src = TESTS / 'support' / name
            text = src.read_text(encoding='ascii').replace('rem UNEXECUTED candidate; common launcher stays locked pending scope/runtime verification.', 'rem Fresh continuous preload/collapse; run only one backend for this group.')
            text = text.replace('%~dp0upl_collapse_candidate_r1_win64.bat', '%~dp0support\\run_lian_collapse_upl_r1_win64.bat')
            need('UNEXECUTED' not in text and 'candidate_r1_win64.bat' not in text, 'Entry template changed')
            sources.append(src)
            add(name, encoded(text))
    common = TESTS / 'support/upl_collapse_candidate_r1_win64.bat'
    sources.append(common)
    add('support/run_lian_collapse_upl_r1_win64.bat', launcher(common))
    for backend, program in programs.items():
        sources.append(program)
        add('support/runtime/' + program.name, program)
    for name in RUNTIME:
        cpu, gpu = programs['CPU'].parent / name, programs['GPU'].parent / name
        need(cpu.read_bytes() == gpu.read_bytes(), f'CPU/GPU runtime differs: {name}')
        sources += [cpu, gpu]
        add('support/runtime/' + name, gpu)
    for name in ['GenCase_win64.exe'] + CRT:
        source = C05 / 'support/bin' / name
        sources.append(source)
        add('support/runtime/' + name, source)
        expected['support/runtime/' + name] = old_hash[name] if name == 'GenCase_win64.exe' else crt_hash[name]
    license_path = REPO / 'LICENSE'
    sources.append(license_path)
    add('LICENSE', license_path)
    add('support/README_server_r1.md', server_readme(head))
    add('support/SOURCE_VERSION_r1.txt', encoded(f'Root-provided source commit: {head}\nCPU/GPU Release provenance and bounded short-review bindings: support/server_manifest_r1.json\nFull modified source is available from the case maintainer; this binary package is not a source backup.\n'))
    add('support/THIRD_PARTY_NOTICES_r1.txt', encoded('Project license: LICENSE (retained project LGPL text).\nChrono runtime source/license: https://github.com/projectchrono/chrono/blob/main/LICENSE\nMicrosoft signed CRT14.36 source: C05 accepted VS redistributable manifest; full provenance is retained in server_manifest_r1.json.\nMicrosoft runtime/license: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist\nNo missing third-party license text is invented; no Windows UCRT or NVIDIA driver DLL is redistributed here.\n'))
    # Reuse the existing case support CSV read-only; it is not a generated formal target.
    parameters = CASE / 'support/lian2023_collapse_parameters.csv'
    sources.append(parameters)
    add('support/lian2023_collapse_parameters.csv', parameters)
    before = [stat(p) for p in dict.fromkeys(sources)]
    support = CASE / 'support'
    archive = support / (PACKAGE + '.zip')
    special = ['support/server_manifest_r1.json', 'support/SHA256SUMS_r1.txt', 'support/' + PACKAGE + '.zip', 'support/' + PACKAGE + '.zip.sha256']
    for relative in list(payload) + special:
        destination = CASE / relative
        need(destination == parameters or not destination.exists(), f'Retained formal/package target protected: {destination}')
    need(not (support / 'runtime').exists(), 'Retained runtime directory protected')
    (support / 'runtime').mkdir()
    files = []
    for relative, source in payload.items():
        destination = CASE / relative
        if isinstance(source, bytes):
            with destination.open('xb') as f:
                f.write(source)
        elif destination != source:
            with source.open('rb') as a, destination.open('xb') as b:
                shutil.copyfileobj(a, b)
            shutil.copystat(source, destination)
        # One SHA pass per delivered payload; no source/object/raw-data hash sweep.
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        need(relative not in expected or digest == expected[relative], f'Accepted GenCase/CRT payload hash differs: {relative}')
        files.append({'entry': relative, 'bytes': destination.stat().st_size, 'sha256': digest})
    need(before == [stat(p) for p in dict.fromkeys(sources)], 'Frozen inputs changed during packaging')
    manifest = {'stage': 'upl_c08_release_package_r1', 'source_head_from_root': head, 'target': 'Windows x64 / NVIDIA RTX A6000; CPU8 or GPU0', 'bounded_combined_check': stat(check), 'bounded_metrics': {key: final[key] for key in ['pressure_RMS_max_Pa', 'material_XYZ_max_mm', 'time_error_max_s']}, 'run_checks': final['run_checks'], 'native_checks': final['backend_checks'], 'source_builds': final['source_builds'], 'programs': final['programs'], 'runtime_CRT_source': old['runtime'], 'frozen_inputs': before, 'files': files, 'solver_or_GenCase_invoked_by_packager': False, 'full13s_physical_acceptance': False, 'tests_or_raw_outputs_included': False, 'manifest_self_hash': 'Excluded to avoid self-reference; separately included in SHA256SUMS.'}
    m = support / 'server_manifest_r1.json'
    with m.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')
    manifest_hash = hashlib.sha256(m.read_bytes()).hexdigest()
    sums = support / 'SHA256SUMS_r1.txt'
    with sums.open('x', encoding='ascii', newline='\n') as f:
        for x in files:
            f.write(x['sha256'] + '  ' + x['entry'] + '\n')
        f.write(manifest_hash + '  support/server_manifest_r1.json\n')
    entries = list(payload) + ['support/server_manifest_r1.json', 'support/SHA256SUMS_r1.txt']
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for relative in entries:
            z.write(CASE / relative, PACKAGE + '/' + relative)
    with zipfile.ZipFile(archive) as z:
        need(z.namelist() == [PACKAGE + '/' + x for x in entries] and z.testzip() is None, 'ZIP whitelist/CRC verification failed')
    zip_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    with archive.with_suffix('.zip.sha256').open('x', encoding='ascii') as f:
        f.write(zip_hash + '  ' + archive.name + '\n')
    print(json.dumps({'prepared': True, 'zip': str(archive), 'zip_sha256': zip_hash, 'payload_files': len(entries), 'server_readme': str(support / 'README_server_r1.md'), 'solver_executed': False}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Generate fresh formal files/runtime/ZIP only after closed checks')
    parser.add_argument('--source-head', required=True, help='Full source commit supplied by the root thread; no Git command is invoked')
    args = parser.parse_args()
    need(args.prepare and re.fullmatch('[0-9a-fA-F]{40}', args.source_head), 'Explicit --prepare and full source commit required')
    prepare(args.source_head.lower())
