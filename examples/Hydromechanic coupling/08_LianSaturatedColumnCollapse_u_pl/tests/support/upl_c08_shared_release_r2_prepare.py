"""Author-reviewed r2 delivery preparation only; never invoke GenCase or a solver."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

# Reuse the closed r1 packaging helpers, not its admission or generated payload.
from upl_c08_release_package_r1 import CASE, TESTS, REPO, C05, GROUPS, RUNTIME, CRT
from upl_c08_release_package_r1 import need, stat, bound, load, encoded, formal_xml

PACKAGE = 'LianCollapse_upl_win64_r2'
SOURCE = 'CaseLianSaturatedColumnCollapse_shared_preload_r2'
MARKER = '__GRAVITY_PRELOAD_STATE__'
GATE = TESTS / 'logs/upl_preload_handoff_delivery_r2.check.json'


def checked_delivery():
    final = load(GATE)
    need(final['passed'] is True and final['certified_source_and_handoff_verified'] is True,
         'The bounded certified-source/handoff interface review has not passed')
    review = load(bound(final['physical_review']))
    need(review['passed'] is True, 'The new handoff review is not closed/passed')
    need(set(final['builds']) == {'DebugCPU', 'ReleaseCPU', 'Debug', 'Release'},
         'All four r2 build checks are required')
    builds = {key: load(bound(value)) for key, value in final['builds'].items()}
    need(all(x['passed'] is True for x in builds.values()), 'An r2 build failed')
    programs = {}
    for backend, config, filename in [('CPU', 'ReleaseCPU', 'DualSPHysics5.2CPU_win64.exe'),
                                      ('GPU', 'Release', 'DualSPHysics5.2_GEO_win64.exe')]:
        program = bound(final['programs'][backend])
        need(program.name == filename and builds[config]['program'] == final['programs'][backend],
             f'{backend} program is not the r2 Release build binding')
        bound(final['source_archives'][backend])
        programs[backend] = program
    return final, programs


def schedule():
    # Exact constant-interval branch of JDsOutputTime::GetNextTime, plus Run's
    # scalar += dt and forced final/event save. This is scheduling, not certification.
    def next_time(t):
        n = int(t / .01)
        out = .01 * n
        while out <= t:
            out = .01 * n
            n += 1
        return out
    t, next_save, frames, last_step = 0., next_time(0.), 1, 0
    for completed in range(1, 4000001):
        t += .0000025
        if t >= next_save or completed == 4000000:
            frames += 1
            last_step = completed
            next_save = next_time(t)
    need(frames == 1001 and last_step == 4000000, 'Writer schedule changed; do not guess the PRE filename')
    return {'completed_steps': last_step, 'raw_saved_step': last_step - 1,
            'actual_scalar_time': t, 'output_interval': .01, 'dt': .0000025,
            'part_files': frames, 'last_part': f'Part_{frames-1:04d}.bi4',
            'meaning': 'Writer schedule only. Loader must independently certify the actual source PRE.'}


def definition(group, psi, cohesion, decay, source=False):
    candidate = TESTS / 'configs' / f'CaseLianSaturatedColumnCollapse_{group}_r1_Def.xml'
    text = formal_xml(candidate, psi, cohesion, decay).decode('utf-8').replace('\r\n', '\n')
    event = ('<gravitypreload time="10.0" release_mkbound="2" elastic_source="true" '
             'comment="Certify every preload material trial as Elastic; source BAT stops at complete PRE before release" units_comment="seconds" />'
             if source else '<gravitypreload time="10.0" release_mkbound="2" statefile="' + MARKER + '" '
             'comment="Launcher substitutes this backend certified PRE path; loader verifies complete state and contract" units_comment="seconds" />')
    text, count = re.subn(r'<gravitypreload\b[^>]*/>', lambda _: event, text)
    need(count == 1, 'Exactly one event template is required')
    text = text.replace('Windows server calculation input; bounded compatibility checked, full 13 s physical results remain to be reviewed.',
                        'r2 shared-preload calculation input; bounded handoff checked, the actual 10 s source must still certify elasticity and full collapse remains unaccepted.')
    root = ET.fromstring(text)
    e = root.find('./execution/special/gravitypreload')
    need(e.attrib.get('elastic_source') == 'true' if source else e.attrib.get('statefile') == MARKER,
         'Source/receiver role differs')
    return encoded(text), candidate


def launcher(proof):
    return encoded(r'''@echo off
setlocal
cd /d "%~dp0.."
set dirbin=support\runtime_r2
set backend=%~2
set name=
set solver=
set runmode=
if /i "%~1" == "PRELOAD" set name=@SOURCE@
if /i "%~1" == "psi0" set name=CaseLianSaturatedColumnCollapse_psi0_shared_r2
if /i "%~1" == "psi2p5" set name=CaseLianSaturatedColumnCollapse_psi2p5_shared_r2
if /i "%~1" == "psim5" set name=CaseLianSaturatedColumnCollapse_psim5_shared_r2
if /i "%backend%" == "CPU" (
    set backend=CPU
    set solver=DualSPHysics5.2CPU_win64.exe
    set runmode=-cpu -ompthreads:8
)
if /i "%backend%" == "GPU" (
    set backend=GPU
    set solver=DualSPHysics5.2_GEO_win64.exe
    set runmode=-gpu:0
)
if not defined name goto fail
if not defined solver goto fail
set dirout=%name%_%backend%_out
set sourceout=@SOURCE@_%backend%_out
set prepart=@PREPART@
if exist "%dirout%" goto exists
if not exist "%name%_Def.xml" goto fail
for %%F in (GenCase_win64.exe %solver% DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll msvcp140.dll vcruntime140.dll vcruntime140_1.dll) do if not exist "%dirbin%\%%F" goto fail
if /i "%~1" == "PRELOAD" goto preload

rem Run.csv/filename checks establish scheduling only. Native loader certifies PRE.
call :checksource
if not "%ERRORLEVEL%" == "0" goto fail
mkdir "%dirout%"
if not "%ERRORLEVEL%" == "0" goto fail
set prestate=%CD%\%sourceout%\data\%prepart%
set template=%CD%\%name%_Def.xml
set prepared=%CD%\%dirout%\%name%_Def.xml
powershell -NoProfile -Command "try { $t=[IO.File]::ReadAllText($env:template); if(([regex]::Matches($t,'@MARKER@')).Count -ne 1){throw 'Statefile marker differs'}; $t=$t.Replace('@MARKER@',[Security.SecurityElement]::Escape($env:prestate)); [IO.File]::WriteAllText($env:prepared,$t,(New-Object Text.UTF8Encoding($false))) } catch { Write-Error $_; exit 1 }"
if not "%ERRORLEVEL%" == "0" goto fail
"%dirbin%\GenCase_win64.exe" "%dirout%\%name%_Def" "%dirout%\%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail
rem Exactly one receiver process, actual source clock through TimeMax13; no PART restart.
"%dirbin%\%solver%" %runmode% -stable -mdbc_freeslip "%dirout%\%name%" "%dirout%" -dirdataout data -svres
if not "%ERRORLEVEL%" == "0" goto fail
echo Receiver exited normally. Full collapse and paper comparison still require review.
goto done

:preload
"%dirbin%\GenCase_win64.exe" "%name%_Def" "%dirout%\%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail
rem TimeMax13 keeps the event valid; stop at completed4000000 PRE before release.
"%dirbin%\%solver%" %runmode% -stable -mdbc_freeslip "%dirout%\%name%" "%dirout%" -dirdataout data -svres -nsteps:4000000
if not "%ERRORLEVEL%" == "0" goto fail
call :checksource
if not "%ERRORLEVEL%" == "0" goto fail
echo Source exited at scheduled PRE. The receiving loader must certify the actual file.
echo Run the three material BAT files with the SAME backend. Preserve this source output.
goto done

:checksource
if not exist "%sourceout%\Run.csv" exit /b 1
if not exist "%sourceout%\data\%prepart%" exit /b 1
powershell -NoProfile -Command "try { $r=@(Import-Csv -LiteralPath (Join-Path $env:sourceout 'Run.csv') -Delimiter ';'); if($r.Count -ne 1 -or [int]$r[0].Steps -ne 4000000 -or [int]$r[0].PartFiles -ne @PARTFILES@ -or [int]$r[0].PartsOut -ne 0){throw 'Source scheduling or ordinary-loss record differs'} } catch { Write-Error $_; exit 1 }"
exit /b %ERRORLEVEL%

:exists
echo Output already exists: %dirout%. Nothing was overwritten or restarted.
goto failed
:fail
echo Execution aborted. Preserve partial outputs; do not bypass source certification.
:failed
if not "%~3" == "--unattended" pause
exit /b 1
:done
echo Copy COMPLETE source and material output folders back for offline native analysis.
echo This launcher has no Python, plotting, VTK conversion or automatic fallback.
if not "%~3" == "--unattended" pause
exit /b 0
'''.replace('@SOURCE@', SOURCE).replace('@PREPART@', proof['last_part'])
                         .replace('@PARTFILES@', str(proof['part_files'])).replace('@MARKER@', MARKER))


def readme(head, proof):
    return encoded(f'''# r2：一次认证预载，三个材料分支

完整解压 `{PACKAGE}.zip`；Windows x64，NVIDIA RTX A6000，CPU默认8线程/GPU默认0。先选择一个后端，双击 `x{SOURCE}_win64_CPU.bat` 或 GPU入口。预载成功后，用同一个后端分别运行 psi0、psi2p5、psim5 三个 `shared_r2` BAT。源与接收输出均含后端名，CPU/GPU源不混用；已有输出拒绝覆盖。每个BAT只启动一次目标，不自动续算、重试或切换方案。

源：ψ0=0°、cp5kPa，MaterialReturn1；从σ′0、ConstantZ H2静水p0开始真实重力预载。dt2.5µs、TimeOut.01s，event10s/TimeMax13s保持既有事件校验，BAT以 `-nsteps:4000000` 停在完整PRE，尚未撤墙。每次Pre/Cor材料trial必须返回Elastic；保存κ0本身不够。如果进入径向塑性、顶点或其它失败，源停止并保留证据，三个分支不得启动，更不能提高源强度或绕过loader。

按当前writer标量时钟与GetNextTime规则，400万步预计{proof['part_files']}帧，末文件`{proof['last_part']}`；准备记录在support/preload_schedule_r2.json。BAT核实际Run.csv步数/帧数/普通丢失和实际文件存在，仅属调度自检。真正认证由solver读取PRE时核schema、两阶段弹性来源、精确法向/几何/材料合同、22原生数组/实际时钟/状态/稳定守卫。接口短窗验证不代表这个10s源已经跑过或达到严格平衡。

三分支共同φ25°、cr1kPa、黏聚衰减5；psi0为ψ0=0°/cp5kPa/sf0，psi2p5为+2.5°/cp5kPa/sf.2，psim5为−5°/cp7.5kPa/sf.2。源全程合格弹性后才允许此强度/剪胀分支。每组导入实际PRE时钟和完整材料状态，首循环只撤右mkbound2一次，关闭预载阻尼.02和Shepard40，继续到总时刻13s，保留自由渗流、Model1/Ck2和负孔压。τ=t−实际撤墙时间，不重写为假t0。接收输出没有重复PRE伪初帧；首次Part0为真正后续保存状态。

三个根Def的statefile标记由BAT用Windows自带PowerShell替换成对应实际源绝对路径，副本保存在各新out，再GenCase。根模板不被修改。不要直接绕过BAT对带标记Def启动solver。保留源输出、全部接收输出及本包；源不是通用PART重启，不能替换为旧常k或未经认证的历史文件。

几何/材料其它设置沿r1：5000土+2060墙，dp.04m、Cubic h/dp1.2，E20MPa、ν.33、n0.35、Kw1GPa、k0=2e-4m/s、左/右FS和底NS；12m床是数值域裕量。没有TPI、论文负压松弛、HG、独立SPR、NoPen、shifting或三维塑性。实际顶点/原稳定门失败仍停止，不承诺全程成功或论文精度。

运行库在support/runtime_r2；沿C05已签名VS14.36应用本地CRT。服务器提供Windows UCRT和合适NVIDIA驱动，不需Python/VisualStudio/CUDA Toolkit。BAT只GenCase和计算，PNG/CSV在数据复制回来后处理。r1包/结果保持原样。源码节点`{head}`，关键payload校验和、四构建及有界交接来源在support/server_manifest_r2.json/SHA256SUMS_r2.txt。源码归档身份不等于本包包含完整源码；完整修改源码请向维护者取得。
''')


def prepare(head):
    final, programs = checked_delivery()
    proof = schedule()
    old_manifest = C05 / 'support/server_manifest.json'
    old = load(old_manifest)
    need(old['runtime']['mode'] == 'signed_MSVC_14_app_local_from_Visual_Studio_redist', 'Accepted CRT provenance missing')
    old_hash = {Path(x['entry']).name: x['sha256'].lower() for x in old['files']}
    crt_hash = {x['name']: x['sha256'].lower() for x in old['runtime']['files']}
    need(set(crt_hash) == set(CRT) and all(x['signature_status'] == 'Valid' and 'Microsoft' in x['signer'] for x in old['runtime']['files']), 'Accepted CRT signature records differ')
    payload, expected, sources = {}, {}, [GATE, old_manifest, Path(__file__), Path(__file__).with_name('upl_c08_release_package_r1.py')]
    for label, psi, cohesion, decay in [('PRELOAD', 0., 5000., 0.)] + GROUPS:
        group = 'psi0' if label == 'PRELOAD' else label
        stem = SOURCE if label == 'PRELOAD' else f'CaseLianSaturatedColumnCollapse_{label}_shared_r2'
        text, original = definition(group, psi, cohesion, decay, label == 'PRELOAD')
        sources.append(original)
        payload[stem + '_Def.xml'] = text
        for backend in ['CPU', 'GPU']:
            payload[f'x{stem}_win64_{backend}.bat'] = encoded(f'@echo off\nrem r2: one backend source, then its three qualified material branches.\ncall "%~dp0support\\run_lian_collapse_shared_r2_win64.bat" {label} {backend} %*\nexit /b %ERRORLEVEL%\n')
    payload['support/run_lian_collapse_shared_r2_win64.bat'] = launcher(proof)
    for program in programs.values():
        payload['support/runtime_r2/' + program.name] = program
        sources.append(program)
    for name in RUNTIME:
        cpu, gpu = programs['CPU'].parent / name, programs['GPU'].parent / name
        need(cpu.read_bytes() == gpu.read_bytes(), f'CPU/GPU runtime differs: {name}')
        payload['support/runtime_r2/' + name] = gpu
        sources += [cpu, gpu]
    for name in ['GenCase_win64.exe'] + CRT:
        src = C05 / 'support/bin' / name
        payload['support/runtime_r2/' + name] = src
        sources.append(src)
        expected['support/runtime_r2/' + name] = old_hash[name] if name == 'GenCase_win64.exe' else crt_hash[name]
    parameters = CASE / 'support/lian2023_collapse_parameters.csv'
    payload.update({'LICENSE': REPO / 'LICENSE', 'support/lian2023_collapse_parameters.csv': parameters,
                    'support/README_server_r2.md': readme(head, proof),
                    'support/preload_schedule_r2.json': (json.dumps(proof, indent=2) + '\n').encode('utf-8'),
                    'support/SOURCE_VERSION_r2.txt': encoded(f'Root-provided source commit: {head}\nFour build/source archive and bounded interface review: server_manifest_r2.json\nActual10s certification/fullcollapse not implied.\n'),
                    'support/THIRD_PARTY_NOTICES_r2.txt': encoded('Project license: LICENSE.\nChrono: https://github.com/projectchrono/chrono/blob/main/LICENSE\nSigned MSVC14.36 CRT: accepted C05 redistributable provenance, recorded in server_manifest_r2.json.\nMicrosoft: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist\nNo Windows UCRT or NVIDIA driver DLL redistributed.\n')})
    # r1 already delivered the identical project license at the case root.
    # Reuse it read-only, rather than overwriting it or refusing every r2 package.
    retained = [parameters]
    case_license = CASE / 'LICENSE'
    if case_license.exists():
        need(case_license.read_bytes() == (REPO / 'LICENSE').read_bytes(), 'Retained project license differs')
        payload['LICENSE'] = case_license
        retained.append(case_license)
    sources += [REPO / 'LICENSE', payload['LICENSE'], parameters, bound(final['physical_review'])]
    sources += [bound(x) for x in final['builds'].values()] + [bound(x) for x in final['source_archives'].values()]
    before = [stat(p) for p in dict.fromkeys(sources)]
    special = ['support/server_manifest_r2.json', 'support/SHA256SUMS_r2.txt', f'support/{PACKAGE}.zip', f'support/{PACKAGE}.zip.sha256']
    for relative in list(payload) + special:
        destination = CASE / relative
        need(destination in retained or not destination.exists(), f'Retained target protected: {destination}')
    need(not (CASE / 'support/runtime_r2').exists(), 'r2 runtime already exists')
    (CASE / 'support/runtime_r2').mkdir()
    files = []
    for relative, src in payload.items():
        destination = CASE / relative
        if isinstance(src, bytes):
            with destination.open('xb') as stream:
                stream.write(src)
        elif destination != src:
            with src.open('rb') as a, destination.open('xb') as b:
                shutil.copyfileobj(a, b)
            shutil.copystat(src, destination)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        need(relative not in expected or digest == expected[relative], f'Accepted payload hash differs: {relative}')
        files.append({'entry': relative, 'bytes': destination.stat().st_size, 'sha256': digest})
    need(before == [stat(p) for p in dict.fromkeys(sources)], 'Consumed files changed during preparation')
    manifest = {'stage': 'upl_c08_shared_release_r2', 'source_head_from_root': head, 'delivery_gate': stat(GATE),
                'builds': final['builds'], 'programs': final['programs'], 'source_archives': final['source_archives'],
                'bounded_handoff_review': final['physical_review'], 'actual10s_certification_already_completed': False,
                'full13s_physical_acceptance': False, 'runtime_CRT_source': old['runtime'], 'frozen_inputs': before,
                'files': files, 'solver_or_GenCase_executed_by_packager': False, 'tests_or_raw_results_included': False}
    support = CASE / 'support'
    m = support / 'server_manifest_r2.json'
    with m.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    manifest_hash = hashlib.sha256(m.read_bytes()).hexdigest()
    with (support / 'SHA256SUMS_r2.txt').open('x', encoding='ascii', newline='\n') as stream:
        for item in files:
            stream.write(item['sha256'] + '  ' + item['entry'] + '\n')
        stream.write(manifest_hash + '  support/server_manifest_r2.json\n')
    entries = list(payload) + ['support/server_manifest_r2.json', 'support/SHA256SUMS_r2.txt']
    archive = support / (PACKAGE + '.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for relative in entries:
            z.write(CASE / relative, PACKAGE + '/' + relative)
    with zipfile.ZipFile(archive) as z:
        need(z.namelist() == [PACKAGE + '/' + x for x in entries] and z.testzip() is None, 'ZIP whitelist/CRC differs')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with archive.with_suffix('.zip.sha256').open('x', encoding='ascii') as stream:
        stream.write(digest + '  ' + archive.name + '\n')
    print(json.dumps({'prepared': True, 'zip': str(archive), 'sha256': digest, 'payload_files': len(entries),
                      'solver_executed': False, 'actual10s_source_certified': False}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--source-head', required=True)
    args = parser.parse_args()
    need(args.prepare and re.fullmatch('[0-9a-fA-F]{40}', args.source_head), 'Explicit --prepare and full source head required')
    prepare(args.source_head.lower())
