"""Seal already linked isolated CPU build products only; never compile or run a probe."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

TESTS=Path(__file__).resolve().parents[1]
REPO=TESTS.parents[3]
TAG='cryer_symc_cpu_r1_seal_r2'
OUT=TESTS/'outputs/cryer_symc_cpu_build_r1'
TARGET=TESTS/'logs'/(TAG+'.build.json')


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bound(path):
    path=Path(path).resolve()
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''): h.update(chunk)
    return dict(path=str(path),bytes=int(path.stat().st_size),sha256=str(h.hexdigest()))


def verify(records):
    unique={}
    for entry in records:
        key=str(Path(entry['path']).resolve()).lower()
        if key in unique: assert unique[key]['sha256'].lower()==entry['sha256'].lower()
        unique[key]=dict(path=str(entry['path']),sha256=str(entry['sha256']),bytes=entry.get('bytes'))
    for entry in unique.values():
        now=bound(entry['path'])
        assert now['sha256'].lower()==entry['sha256'].lower(),entry['path']
        if entry['bytes'] is not None: assert now['bytes']==entry['bytes']
    return list(unique.values())


def records(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str): yield value
        else:
            for item in value.values(): yield from records(item)
    elif isinstance(value,list):
        for item in value: yield from records(item)


def main():
    assert not TARGET.exists(),'Never overwrite a sealed build audit'
    # Exact owned wrapper was stopped after link, with no cl/link children; never stop another process here.
    query="Get-CimInstance Win32_Process -Filter 'ProcessId=37900' | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    check=subprocess.run(['powershell','-NoProfile','-Command',query],capture_output=True,text=True,check=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    assert not check.stdout.strip(),'The old owned build wrapper is unexpectedly alive'
    script=TESTS/'support/cryer_symc_cpu_build_r1.ps1'
    text=script.read_text(encoding='utf-8')
    old=re.search(r"\$old=@'\n(.*?)\n'@",text,re.S)[1]
    new=re.search(r"\$new=@'\n(.*?)\n'@",text,re.S)[1]
    original=REPO/'src/source/JSphCpu.cpp'; candidate=OUT/'JSphCpu.cpp'
    canonical_text=original.read_text(encoding='utf-8')
    candidate_text=candidate.read_text(encoding='utf-8')
    assert canonical_text.count(old)==1 and candidate_text==canonical_text.replace(old,new)
    recipepath=TESTS/'logs/cryer_radial_force_r1.build.json'
    recipe=read(recipepath);assert recipe['configuration']=='DebugCPU' and recipe['status']=='built_not_run'
    frozen=verify(recipe['inputs']+recipe['runtime'])
    # Existing pre-build receipts independently retain canonical executable identities.
    controls=[TESTS/'logs'/name for name in ['cryer_start_r1.run.json','cryer_grad_fine_r1.inputs.json',
        'cryer_preload_peak_r1.run.json','cryer_gpu_base_r1.inputs.json','cryer_gpu_base_r1_dbg.run.json',
        'cryer_gpu_continue_r1.inputs.json']]
    available=[]
    for path in controls: available.extend(records(read(path)))
    programs=[]
    for name in ['DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2CPU_win64.exe',
            'DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2_win64_debug.exe']:
        path=REPO/'bin/windows'/name; current=bound(path)
        matches=[r for r in available if str(Path(r['path']).resolve()).lower()==str(path.resolve()).lower()
            and r['sha256'].lower()==current['sha256']]
        programs.append(dict(current=current,preexisting_matching_control=matches[0] if matches else None,
            preexisting_hash_control_found=bool(matches),last_write_epoch_s=path.stat().st_mtime,
            last_write_predates_candidate_source=path.stat().st_mtime<=candidate.stat().st_mtime))
    lianmanifest=REPO/'examples/Hydromechanic coupling/05_LianFlexibleStrip2D_PR/support/server_manifest.json'
    lian=[r for r in read(lianmanifest)['files'] if r['entry'].startswith('support/bin/')]
    verify(lian)
    tlog=REPO/'src/VS/Intermediate/DualSPHysics_DebugCPU_x64/DualSPHysics.tlog/CL.command.1.tlog'
    commands=tlog.read_text(encoding='utf-16').splitlines()
    indexes=[i for i,line in enumerate(commands) if re.fullmatch(r'\^.*\\JSPHCPU\.CPP',line,re.I)]
    assert len(indexes)==1
    command=commands[indexes[0]+1]
    tokens=[token.replace('"','') for token in re.findall(r'(?:[^\s"]|"[^"]*")+',command)]
    cpu=[v for v in tokens if not v.lower().startswith(('/fo','/fd')) and not v.lower().endswith(r'\jsphcpu.cpp')]
    cpu += ['/Fo'+str(OUT/'JSphCpu_symc.obj'),'/Fd'+str(OUT/'cpu_compile.pdb'),
        '/I'+str(REPO/'src/source'),'/sourceDependencies',str(OUT/'cpu.dependencies.json'),str(candidate)]
    oldout=str(TESTS/'outputs/cryer_radial_force_r1_dbg')
    def translate(value): return value.replace(oldout,str(OUT)).replace('cryer_radial_force_r1','cryer_symc_cpu_r1')
    harness=[translate(v) for v in recipe['compile']]
    link=[translate(v) for v in recipe['link']]
    oldobj=str(REPO/'src/VS/Intermediate/DualSPHysics_DebugCPU_x64/JSphCpu.obj')
    assert link.count(oldobj)==1
    link=[str(OUT/'JSphCpu_symc.obj') if v==oldobj else v for v in link]
    files=['JSphCpu_symc.obj','cryer_symc_cpu_r1.obj','cryer_symc_cpu_r1.exe','cpu_compile.pdb','link.pdb',
        'cpu.dependencies.json','compile.dependencies.json']
    assert all((OUT/name).is_file() and (OUT/name).stat().st_size>0 for name in files)
    assert (OUT/'JSphCpu_symc.obj').stat().st_mtime>=candidate.stat().st_mtime
    assert (OUT/'cryer_symc_cpu_r1.exe').stat().st_mtime>=max((OUT/name).stat().st_mtime for name in files[:2])
    logfile=TESTS/'logs/cryer_symc_cpu_r1.build.log'; rawlog=logfile.read_bytes()
    log=rawlog.decode('utf-16' if rawlog.startswith(b'\xff\xfe') else 'utf-8-sig')
    assert 'COMPILE_STAGE isolated_JSphCpu' in log and 'COMPILE_STAGE harness' in log
    assert 'Finished searching libraries' in log and not re.search(r'\b(?:fatal error|error C\d+|error LNK\d+)\b',log)
    includes=[]
    for name in ['cpu.dependencies.json','compile.dependencies.json']:
        includes += read(OUT/name)['Data']['Includes']
    implicit=[]
    for line in log.splitlines():
        match=re.search(r'^\s*Searching ([A-Za-z]:.*\.lib):\s*$',line)
        if match and Path(match[1]).is_file(): implicit.append(match[1])
    paths=[Path(__file__),script,TESTS/'support/cryer_symc_cpu_r1.cpp',TESTS/'notes/cryer_symc_cpu_r1.json',
        TESTS/'logs/cryer_symc_cpu_r1.build_attempt0.json',TESTS/'logs/cryer_symc_cpu_r1_seal_r2.precheck.json',
        recipepath,tlog,original,candidate,logfile,lianmanifest]+controls
    paths += [Path(r['path']) for r in frozen]+[Path(r['path']) for r in lian]+[Path(v) for v in includes+implicit]
    inputs=[bound(p) for p in sorted(set(paths),key=lambda p:str(p).lower())]
    runtime=[bound(p) for p in sorted(OUT.iterdir()) if p.suffix.lower()=='.dll' or p.name in
        ['cryer_symc_cpu_r1.exe','DsphConfig.xml']]
    verify([item['current'] for item in programs])
    warning_codes=sorted(set(re.findall(r'\b(?:D\d{4}|LNK\d{4}|C\d{4})\b',log)))
    result=dict(status='built_not_run',configuration='DebugCPU',utc=datetime.now(timezone.utc).isoformat(),
        probe_executed=False,solver_launched=False,physical_acceptance=False,manifest_repaired_offline=True,
        post_link_wrapper_interrupted=True,old_wrapper_pid=37900,old_wrapper_absent_verified=True,
        failure_description='Owned post-link PowerShell wrapper showed >5.9 GB memory and continuing CPU with no further I/O during manifest generation; it was explicitly stopped. The offending PS object/property was not isolated. Existing products were not rebuilt.',
        first_wrapper_failure='D9035 native stderr under ErrorActionPreference Stop, then missing-log finally masking; preserved attempt0.',
        stage_success_evidence='Both compile exit-code checks and link exit-code check were passed: wrapper reached runtime copies and post-link metadata. Native return values were zero by that control flow; wrapper itself did not exit normally.',
        source_comparison=dict(canonical=bound(original),candidate=bound(candidate),
            exact_normalized_source_is_single_Darcy_replacement=True,removed=old,inserted=new,
            candidate_line_endings='LF; original mixed CRLF/LF untouched',soil_pairs_only=True,boundary_receiver_C_unchanged=True),
        protected_frozen_inputs_verified=True,
        canonical_program_controls_verified=all(item['preexisting_hash_control_found'] for item in programs),
        canonical_programs_unchanged_during_offline_seal=True,Lian_runtime_verified=True,
        canonical_program_controls=programs,preexisting_frozen_input_count=len(frozen),Lian_runtime_files=len(lian),
        program_protection_limitation='The interrupted wrapper did not save its before-program snapshot. Unmatched recently linked canonical programs have only current SHA, earlier mtime, isolated compile/link output-path evidence and seal-interval equality; this is not a recovered prebuild hash proof.',
        authoritative_compile_command=command,cpu_compile=cpu,harness_compile=harness,link=link,
        inputs=inputs,artifacts=[bound(OUT/name) for name in files]+[bound(logfile)],runtime=runtime,
        program=bound(OUT/'cryer_symc_cpu_r1.exe'),warning_codes=warning_codes,
        csv_generated=False,probe_requires_separate_main_agent_review_and_explicit_run=True)
    with TARGET.open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(status=result['status'],manifest=str(TARGET),input_count=len(inputs),
        warnings=warning_codes,probe_executed=False)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seal',action='store_true')
    if parser.parse_args().seal: main()
    else: parser.print_help()
