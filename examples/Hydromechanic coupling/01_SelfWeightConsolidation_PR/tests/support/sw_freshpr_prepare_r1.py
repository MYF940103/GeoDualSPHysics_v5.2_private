"""Prepare the admitted NEW root fresh-PR package; never run any program or solver."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

TESTS = Path(__file__).resolve().parents[1]
CASE, REPO = TESTS.parent, TESTS.parents[3]
TAG, NAME = 'sw_freshpr_prepare_r1', 'CaseSelfWeightConsolidation_Scenario2_FreshPR'
LOGS, NOTES = TESTS/'logs', TESTS/'notes'
PREP, NOTE = LOGS/(TAG+'.inputs.json'), NOTES/(TAG+'.json')
LONG = LOGS/'sw_mode3_longwin_r1.inputs.json'
CHECK, REVIEW = LOGS/'sw_mode3_longwin_r1.check.json', LOGS/'sw_mode3_longwin_review_r1.check.json'
ADMISSION = NOTES/'sw_full_admission_r1.json'
DT, END, INTERVAL = '0.00000035762786865234375', '7.316858571428572', '0.01821857142857143'
STEPS, FRAMES = 20459420, 403
GPU_SHA = '11ff6c83083cea75ffda2d8e2fe6d64c25497cdab6c096bd1780674594a6e14c'
SOURCE_CLOCK = REPO/'src/source/JDsOutputTime.cpp'
POST = TESTS/'support/postprocess_selfweight_freshpr_r1.py'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def bound(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def verify(records):
    for record in records:
        assert bound(record['path']) == record, ('Changed frozen input', record['path'])


def unique(records):
    result = {}
    for record in records:
        if record['path'] in result:
            assert result[record['path']] == record
        result[record['path']] = record
    return list(result.values())


def save(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def plan():
    dt, interval = float(DT), float(INTERVAL)
    regular = [math.ceil(i*interval/dt) for i in range(math.floor(float(END)/interval)+1)]
    steps = regular + ([STEPS] if regular[-1] != STEPS else [])
    # n*dt = 3*n*2^-23: every integer numerator is exactly representable here.
    assert 3*STEPS < 2**53 and math.ceil(float(END)/dt) == STEPS
    assert len(steps) == FRAMES and len(set(steps)) == FRAMES
    return dict(saved_steps=steps, saved_times_s=[n*dt for n in steps], frames=FRAMES,
        actual_end_s=STEPS*dt, nominal_end_s=float(END), final_partial_interval=True,
        clock='binary64 dyadic repeated addition equals n*dt exactly; no clock rewrite',
        output_clock='JDsOutputTime default tb=0: timeout*nt; first dyadic step >= target, plus final cap',
        cadence_legacy_DeltaTv=.005, finite_Kw_target_Tv=2.)


def xml_text(source):
    text = source
    for key, value in [('TimeMax', END), ('TimeOut', INTERVAL)]:
        text, count = re.subn(r'(<parameter key="'+key+r'" value=")[^"]+', r'\g<1>'+value, text)
        assert count == 1
    text = text.replace('Fresh current Stage1 diagnostic; equilibrium and restart not admitted',
        'Fresh Scenario2 finite-Kw 2Tv candidate; full accuracy acceptance remains pending')
    text = text.replace('Fresh Stage1 short diagnostic; no equilibrium acceptance',
        'Fresh continuous Scenario2 PR; no PART restart')
    text = text.replace('short diagnostic only', 'fresh elastic Scenario2 candidate')
    text = text.replace('Stage 1 baseline: drained free-surface enforcement enabled',
        'Drained free surface from the fresh analytical initial state')
    text = text.replace('Enabled to suppress odd-even pore-pressure oscillation during Stage 1',
        'Disabled; no Shepard pressure smoothing in this candidate')
    def signature(value):
        return [(e.tag, sorted((k,v) for k,v in e.attrib.items() if k not in ['comment','units_comment']))
            for e in ET.fromstring(value).iter() if e.get('key') not in ['TimeMax','TimeOut']]
    assert signature(text) == signature(source), 'Only TimeMax/TimeOut numerical changes are allowed'
    return text


def bat_text():
    return r'''@echo off
setlocal
cd /d "%~dp0"

rem Fresh Windows x64/NVIDIA calculation; never delete outputs or use PART restart.
set name=NAME
set dirout=%name%_out
set diroutdata=%dirout%\data
set dirbin=support/bin
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+Idp,+Mk,+Vel,+Rhop,+Press,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PorePress,+PorePress0,+ExcessPorePress,+HydroMechLoadAce
if not defined PYTHON set PYTHON=python
if /i "%~1"=="-postprocess" goto postprocess
if /i "%~1"=="-post" goto postprocess
if not "%~1"=="" if /i not "%~1"=="-solver-only" goto usage
if exist "%dirout%" goto exists
if not exist "%name%_Def.xml" goto fail
if not exist "%dirbin%/GenCase_win64.exe" goto fail
if not exist "%dirbin%/DualSPHysics5.2_GEO_win64.exe" goto fail
%gencase% "%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%"=="0" goto fail

rem Finite-Kw Tv=2 target; cap gives actual end 7.316858768463135 s.
%dualsphysicsgpu% -gpu -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:20459420
if not "%ERRORLEVEL%"=="0" goto fail
if /i "%~1"=="-solver-only" exit /b 0

:postprocess
rem This mode never invokes GenCase or the physical solver.
if not exist "%diroutdata%/Part_0402.bi4" goto fail
if not exist "%dirbin%/PartVTK_win64.exe" goto fail
if not exist "%dirbin%/ReadSelfWeightNative.exe" goto fail
if not exist "support/postprocess_selfweight_freshpr_r1.py" goto fail
if exist "%dirout%/particles" goto particles_exist
mkdir "%dirout%/particles"
%partvtk% -dirin "%diroutdata%" -savevtk "%dirout%/particles/PartFluid" -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%"=="0" goto fail
%partvtk% -dirin "%diroutdata%" -savevtk "%dirout%/particles/PartBound" -onlytype:-all,bound -vars:%vars%
if not "%ERRORLEVEL%"=="0" goto fail
set legacy=
if exist "tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/data/Part_0000.bi4" set legacy=--legacy-dir "tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out"
if not defined legacy echo Historical comparison pending: old raw data are not present in this package.
"%PYTHON%" "support/postprocess_selfweight_freshpr_r1.py" --config "%name%_Def.xml" --data-dir "%diroutdata%" --figures-dir figures --label "%name%" --reader "%dirbin%/ReadSelfWeightNative.exe" %legacy%
if not "%ERRORLEVEL%"=="0" goto fail
echo Completed calculation and derived particles/figures/CSV. Normal exit is not physical acceptance.
if "%~1"=="" pause
exit /b 0

:particles_exist
echo Existing particles preserved. Run the standalone postprocessor directly to repair only new analysis.
goto fail
:exists
echo Output already exists: %dirout%. Nothing was overwritten, restarted or deleted.
goto fail
:usage
echo Usage: double-click for full calculation and postprocessing; -solver-only; -postprocess.
goto fail
:fail
echo Aborted. Preserve complete and partial outputs; do not rerun the solver blindly.
if "%~1"=="" pause
exit /b 1
'''.replace('NAME', NAME)


def readme_text():
    return '''# Scenario2 FreshPR r1

NEW independent gravity-on analytical-start PR calculation. Existing Stage1/Scenario2 files and results are untouched.

- Double-click `xCaseSelfWeightConsolidation_Scenario2_FreshPR_win64_GPU.bat` for GenCase, fresh solver, particle VTK, then native PNG/CSV analysis. Windows x64, NVIDIA GPU; `support/bin` has the frozen Release program and copied Chrono runtime/tools, not a Debug fallback. The target machine must have the Microsoft Visual C++ 2015-2022 x64 Redistributable (Chrono imports its CRT), a compatible NVIDIA driver, and Python with NumPy, pandas and Matplotlib for plotting (`PYTHON` may select the interpreter). The package is not a self-contained Windows/driver/Python installation.
- `-solver-only` stops after the physical solve. `-postprocess` (alias `-post`) processes a completed output without rerunning GenCase/solver. Existing output folders and particles are refused, not overwritten/deleted. If plotting alone fails, invoke the standalone support postprocessor to repair new analysis only.
- If a failed postprocessor has already written some figures/CSVs, choose a fresh label, for example: `python support/postprocess_selfweight_freshpr_r1.py --config CaseSelfWeightConsolidation_Scenario2_FreshPR_Def.xml --data-dir CaseSelfWeightConsolidation_Scenario2_FreshPR_out/data --figures-dir figures --label CaseSelfWeightConsolidation_Scenario2_FreshPR_review_r2 --reader support/bin/ReadSelfWeightNative.exe`. This never reruns the physical solver. Native double `SigmaState` is authoritative for stress precision; PartVTK `Sigma_kk/ij` are float visualization arrays. `PartExtra` saves normals, not HG history.
- Initial mode3 uses gravity-on hydrostatic p0 plus B*(rho-rhow)*g*(H-z), with physical H=1 m; native top-node plane is 0.995 m and its drained pressure/p0 are zero. Initial coordinates are undeformed, so settlement is the increment from this state, not Stage1's absolute equilibrium settlement. No PART/HG-history restart.
- Physics matches the source-frozen accepted bounded-window candidate: k=1e-3 m/s, dp=.01 m, mDBC velocity=0, SPR=1, stress-gradient correction=1, HG xi=.1, damping=.02, Shepard OFF; stress state double, pore pressure/density float. No new coupled-double, shifting or integration scheme.
- dt=3*2^-23 s; 20,459,420 steps; nominal finite-Kw Tv=2 at 7.316858571428572 s, actual final dyadic step 7.316858768463135 s. Output interval .01821857142857143 s retains legacy DeltaTv=.005; 403 native frames include the final partial interval. Both legacy Cv and finite-Kw B*Cv are reported at ACTUAL saved times, not reconstructed nominal times.
- Root `figures` receives formal candidate plots with matching CSV; raw complete `*_out/data` remains authoritative. About 25.5 hours is an extrapolation from the current RTX3050 bounded run, not a server guarantee. Reserve at least 1 GB for this small-column raw/derived package.
- `q_fixed=p-p0` and excess relative to the current top-node hydrostatic baseline are separate quantities. The roughly 49 Pa initial baseline offset and subsequent geometry shift are exposed, not fitted away. Late-pressure floor budget is <=5 Pa AFTER separating these references; a 100 Pa safety guard is not late-pressure accuracy acceptance.
- The optional retained old `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out` comparison is historical: restart, slip, gradient, step and stress precision differ. It is NOT an isolated double-stress A/B. If this old data is absent on the server, fresh plots proceed and historical comparison is pending copy-back.
- Bounded CPU/GPU/half checks do not establish full-cycle convergence. Final physical acceptance remains pending complete native history, theory/reference review, late-tail, settlement/stress and saved safety checks. Static small-rotation elastic scope only; no general boundary/plasticity/exact restart claim. Secondary gravity-off Scenario1 reference audit remains separate.
'''


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    result = plan(); clock = 0.; dt = float(DT)
    for _ in range(STEPS):
        clock += dt
    assert clock == result['actual_end_s'] == 7.316858768463135
    synthetic = '<case><parameter key="TimeMax" value=".1"/><parameter key="TimeOut" value=".01"/></case>'
    root = ET.fromstring(xml_text(synthetic))
    assert root[0].get('value') == END and root[1].get('value') == INTERVAL
    bat = bat_text().lower()
    assert '-solver-only' in bat and '-postprocess' in bat and '-partbegin' not in bat
    assert 'rd /' not in bat and '-force' not in bat and 'debug' not in bat
    assert '-gpu -ompthreads:1 -stable -mdbc' in bat and 'readselfweightnative.exe' in bat
    return dict(passed=True, files_written=False, programs_started=False, frames=FRAMES,
        steps=STEPS, sequential_clock_exact=True, actual_end_s=clock)


def prepare():
    decision, check, review, prior = read(ADMISSION), read(CHECK), read(REVIEW), read(LONG)
    assert decision['full_run_admitted'] is True and decision['long_review'] == bound(REVIEW) and decision['long_check'] == bound(CHECK)
    assert check['passed'] and len(check['jobs']) == 2 and not check['held_jobs'] and review['analysis_checks_passed']
    proof = [bound(p) for p in [Path(__file__), NOTE, ADMISSION, CHECK, REVIEW, LONG, SOURCE_CLOCK, POST]]+[check['run']]
    for record in check['jobs']:
        result = read(record['path']); completion = result['sealed_completion']; done = read(completion['path'])
        assert result['passed'] and result['hg']['passed'] and len(result['rows']) == 1025
        assert result['initial_reference']['passed'] and result['prefix_all38_including_dterror'] and not result['excluded_fields']
        assert done['solver_finished'] and done['exit_code'] == 0 and done['owned_exited'] and not done['surviving_owned']
        assert len(result['prefixes']) == 257 and all(r['passed'] for r in result['prefixes'])
        assert all(r['passed'] for r in result['pairs'])
        proof += [record, completion]
    old = prior['jobs'][0]; assert old['suffix'] == 'coarse' and old['program']['sha256'] == GPU_SHA and old['dt'] == DT
    assert len(read(check['jobs'][1]['path'])['pairs']) == 1025
    frozen = {Path(r['path']).name:r for r in prior['inputs']}
    sources = [old['program']]+old['runtime']+[frozen['GenCase_win64.exe'], frozen['ReadSelfWeightNative.exe'], bound(REPO/'bin/windows/PartVTK_win64.exe')]
    proof += sources+[old['config'], old['bat']]
    capture = prior['new_build_source_capture']; assert capture['sources_captured_before_build'] and not capture['compiled_from_snapshot']
    proof += [r['snapshot'] for r in capture['selected_snapshots']]
    ast.parse(POST.read_text(encoding='utf8'))
    proof = unique(proof); verify(proof)
    config, bat, readme = CASE/(NAME+'_Def.xml'), CASE/('x'+NAME+'_win64_GPU.bat'), CASE/'README_FreshPR_r1.md'
    manifest, post = CASE/'support/selfweight_freshpr_r1.manifest.json', CASE/'support'/POST.name
    assert not any(p.exists() for p in [config,bat,readme,manifest,post,PREP,CASE/(NAME+'_out')])
    targets = [(record,CASE/'support/bin'/Path(record['path']).name) for record in sources]
    for record,target in targets:
        if target.exists():
            assert target.stat().st_size == record['bytes'] and bound(target)['sha256'] == record['sha256'], ('Refuse different existing runtime',target)
    canonical = [bound(p) for p in (REPO/'bin/windows').glob('DualSPHysics*.exe')]
    for record,target in targets+[(bound(POST),post)]:
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            with Path(record['path']).open('rb') as source, target.open('xb') as destination:
                shutil.copyfileobj(source,destination)
        assert bound(target)['sha256'] == record['sha256'] and target.stat().st_size == record['bytes']
    for path,text,encoding,newline in [(config,xml_text(Path(old['config']['path']).read_text(encoding='utf8')),'utf8',''),(bat,bat_text(),'ascii','\r\n'),(readme,readme_text(),'utf8','\n')]:
        with path.open('x',encoding=encoding,newline=newline) as stream:
            stream.write(text)
    copied = [bound(target) for _,target in targets]
    job = dict(name=NAME,backend='gpu',threads=1,dt=DT,end=END,interval=INTERVAL,steps=STEPS,frames=FRAMES,shepard=40,on=False,
        program=copied[0],runtime=copied[1:5],config=bound(config),bat=bound(bat),parameters=old['parameters'])
    proof += copied+[bound(config),bound(bat),bound(readme),bound(post)]; proof=unique(proof); verify(proof+canonical)
    value = dict(utc=datetime.now(timezone.utc).isoformat(),inputs=proof,jobs=[job],full_admission=bound(ADMISSION),
        capture=capture,new_build_source_capture=capture,clock_plan=plan(),source_clock=bound(SOURCE_CLOCK),
        copied_tools=[dict(source=r,target=bound(t)) for r,t in targets],postprocess=bound(post),
        postprocess_check=str(CASE/'figures'/(NAME+'_nativepr_manifest.json')),
        bat_modes=['default full workflow','-solver-only','-postprocess','-post alias'],physical_acceptance=False,
        formal_candidate_prepared=True,solver_started=False,restart_admitted=False,canonical_programs_unchanged=canonical)
    save(manifest,value); value['manifest']=bound(manifest); save(PREP,value)
    print(json.dumps(dict(prepared=str(PREP),manifest=str(manifest),job=job,solver_started=False)))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    group.add_argument('--selftest',action='store_true'); group.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    if args.selftest: print(json.dumps(selftest()))
    elif args.prepare: prepare()
    else: parser.print_help()
