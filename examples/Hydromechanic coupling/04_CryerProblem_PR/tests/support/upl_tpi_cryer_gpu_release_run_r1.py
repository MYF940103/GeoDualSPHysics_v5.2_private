"""One independently admitted C04 Release A/B/C 128-update job; no native/chain."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True

T = Path(__file__).resolve().parents[1]
C02SUPPORT = T.parent.parent / '02_TerzaghiConsolidation_q0_PR' / 'tests/support'
sys.path.insert(0, str(C02SUPPORT))
import upl_tpi_gpu_run_r3 as g  # Reuse only genuine tool/target ownership, never its C02 context/check/main.
c = g.c
L = T / 'logs'
STAGE = 'upl_tpi_cryer_gpu_release_run_r1'
PREP = L / 'upl_tpi_cryer_gpu_r2.prepare.json'
BUILD = L / 'upl_tpi_cryer_gpu_Release_r1.build.json'
DEBUG_REVIEW = L / 'upl_tpi_cryer_gpu_Debug_B_debug2steps_r1.native_review_r1.json'
OLD_GPU_CALL = L / 'upl_cryer_freebody_smoke128_GPU_r1.call.json'
PREFIX = T / 'outputs/upl_cryer_freebody_short_r1_seed/upl_cryer_freebody_short_r1'
DT = 2.**-20
HEADER = ['part','time_s','completed_step','saved_step','dt_s']
FIXTURE = 'UplTpiCryerGpuSourceRoleFixtureR1: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0'


class Admission:
    def __init__(self, path):
        self.entry, self.data = c.stat(path), c.read(path)
        c.need(self.data.get('stage') == STAGE + '.run_admission' and self.data.get('passed') is True
               and self.data.get('one_job_only') is True, 'One independent C04 Release128 root admission required')
        self.frozen = {str(Path(e['path']).resolve()):e for e in self.data['inputs']};self.consumed={}
        c.need(len(self.frozen)==len(self.data['inputs']), 'Duplicate frozen input')

    def pin(self, path):
        k=str(Path(path).resolve());c.need(k in self.frozen,'Consumed input absent from root admission: '+k)
        self.consumed[k]=c.same(self.frozen[k]);return self.consumed[k]

    def finish(self):
        for e in self.consumed.values():c.same(e)
        c.same(self.entry);return list(self.consumed.values())


def context(ad):
    for p in (Path(__file__),T/'notes/upl_tpi_cryer_gpu_release_run_r1.md',Path(g.__file__),Path(c.__file__),
              sys.executable,PREP,BUILD,DEBUG_REVIEW,OLD_GPU_CALL,PREFIX.with_suffix('.xml'),PREFIX.with_suffix('.bi4')):
        ad.pin(p)
    old=c.read(OLD_GPU_CALL)
    c.need(old['exit_code']==0 and old['direct_exit'] and old['backend']=='GPU'
           and old['arguments'][:3]==['-gpu','-stable',str(PREFIX)]
           and old['arguments'][-1]=='-nsteps:128', 'Retained actual C04 GPU seed/argument provenance differs')
    prepared,built=c.read(PREP),c.read(BUILD)
    c.need(prepared['passed'] and prepared['source_count']==265 and prepared['private_helper_count']==2
           and prepared['class_or_header_ABI_changed'] is False and prepared['HG_adapters_called'] is False
           and prepared['requires_full_new_111_object_compile'], 'Passed C04 XYZ/HG0 source267 preparation required')
    c.need(built['passed'] and built['configuration']=='Release' and built['object_count']==111
           and built['CL_compile_count']==97 and built['CUDA_compile_count']==14 and built['old_objects_reused']==0
           and built['consumed_stats_unchanged'] and built['prepared']['path']==str(PREP),
           'Genuine passed full111 Release build required; no old-object fallback')
    c.same(built['prepared'])
    program=ad.pin(built['program']['path']);c.same(built['program'])
    c.need(Path(program['path']).name=='DualSPHysics5.2_GEO_win64.exe'
           and Path(program['path']).resolve().is_relative_to((T/'outputs').resolve()),'Actual private GPU Release main required')
    runtime=[]
    for x in built['runtime']:
        runtime.append(ad.pin(x['destination']['path']));c.same(x['destination'])
    for e in [prepared['source_diff'],*prepared['changed_sources']]:ad.pin(e['path']);c.same(e)
    source=Path(prepared['source_root'])/'source'
    for name in ('upl_tpi_cryer_gpu_r1.h','upl_tpi_cryer_gpu_r1.cuh'):ad.pin(source/name)
    root=ET.parse(PREFIX.with_suffix('.xml')).getroot()
    def value(key):
        rows=[e for e in root.iter('parameter') if e.get('key')==key]
        c.need(len(rows)==1,'Unique retained input parameter required: '+key);return float(rows[0].get('value'))
    c.need(value('DtFixed')==value('DtIni')==DT and value('TimeOut')==2.**-13
           and value('TimeMax')==.00830078125 and value('Kernel')==2
           and value('SoilHourglassXi')==value('SoilBoundaryDerivativeSPR')==0,
           'Retained actual Cryer seed dt/cadence/kernel/HG0/SPR0 changed')
    # This is a hard prerequisite, not a statement that pending Debug2 review passed.
    debug=c.read(DEBUG_REVIEW);done=debug['completion']
    c.need(debug['stage']=='upl_tpi_cryer_gpu_debug2_native_r1.review' and debug['passed']
           and debug['tag']=='upl_tpi_cryer_gpu_Debug_B_debug2steps_r1' and debug['consumed_stats_unchanged']
           and debug['sidecar_rows']==74346 and debug['actual_end_row_formula_checks']==37173
           and debug['core_field_bit_checks']==520422 and debug['HG_snapshot_checks']==0
           and debug['ULP_or_absolute_tolerance_added']==0 and done['stage']=='upl_cryer_public_native_r1'
           and done['passed'] and done['declared_backend']=='GPU' and done['samples']==2
           and done['completed_steps']==2 and done['actual_end_s']==2.**-19 and done['dt_s']==DT
           and done['total_native_ids']==37181 and done['soil_ids']==37173 and done['fixed_ids']==8
           and done['native_typed_arrays']==22, 'Actual completed Debug-B2 native/formula review required')
    for key in ('root_admission','native_read_receipt'):ad.pin(debug[key]['path']);c.same(debug[key])
    native=c.read(debug['native_read_receipt']['path'])
    c.need(native['passed'] and native['reader_invocations']==1 and native['completion']==done,
           'Debug qualification must bind one genuine completed native read')
    job=ad.data['job'];tag=job['tag'];scheme=job.get('scheme')
    c.need(scheme in ('A','B','C') and re.fullmatch(r'upl_tpi_cryer_gpu_Release_'+scheme+r'_startup128_r[1-9][0-9]*',tag)
           and job.get('configuration')=='Release' and job.get('window')=='startup128',
           'Only one independently admitted C04 Release A/B/C 128-update profile is permitted')
    checks=[];c.need(ad.data.get('required_passed_checks'),'Root must bind actual prior source/CPU qualification reviews')
    for e in ad.data['required_passed_checks']:
        p=ad.pin(e['path']);c.same(e);c.need(c.read(p['path'])['passed'] is True,'A declared prerequisite failed');checks.append(p)
    out=T/'outputs'/tag
    paths={key:L/(tag+suffix) for key,suffix in [('start','.start.json'),('tool_start','.tool.start.json'),
        ('call','.call.json'),('run','.run.json'),('status','.status.json'),('log','.log'),
        ('memcheck','.memcheck.log'),('plan','.clock.csv')]}
    c.need(not out.exists() and all(not p.exists() for p in paths.values()),'Existing physical output/owner/partial is protected')
    scalar=0.
    for _ in range(128):scalar+=DT
    c.need(scalar==2.**-13,'Genuine scalar ordinary-target 128-update endpoint differs')
    rows=[dict(zip(HEADER,x)) for x in [(0,0.,0,0,DT),(1,scalar,128,127,DT)]]
    with paths['plan'].open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=HEADER);writer.writeheader();writer.writerows(rows)
    return dict(tag=tag,configuration='Release',scheme=scheme,window='startup128',program=program,
        source_build=ad.pin(BUILD),prepared=ad.pin(PREP),debug_native_review=ad.pin(DEBUG_REVIEW),runtime=runtime,prerequisite_reviews=checks,
        input_prefix=str(PREFIX),output_directory=str(out),data=str(out/'data'),
        arguments=['-gpu','-stable',str(PREFIX),str(out),'-dirdataout','data','-svres','-nsteps:128'],
        plan=c.stat(paths['plan']),clock=dict(actual_scalar_end_s=scalar,actual_fixed_dt_s=DT,
            completed_updates=128,frames=2,forced_final=False,post_open_frames=0,event_sample_present=False,
            initial_and_noninitial_native_review_pending=True),paths=paths,memcheck_program=None,
        required_runtime_markers=[],original_seed=[ad.pin(PREFIX.with_suffix(x)) for x in ('.xml','.bi4')],
        native_count=37181,soil_count=37173,fixed_count=8,HG0=True,PART_restart=False)


def check_output(ctx):
    out=Path(ctx['output_directory']);text=(out/'Run.out').read_text(encoding='utf-8-sig')
    c.need(text.count('Finished execution (code=0).')==1 and 'Stable - Pos-Cell - Single-GPU' in text
           and re.search(r'Steps of simulation[.]+:\s*128(?:\s|$)',text)
           and re.search(r'Excluded particles[.]+:\s*0(?:\s|$)',text),'Actual GPU completion/128updates/zero-exclusion differs')
    c.need('SoilHourglass: forcecalls=' not in text,'C04 HG0 must not create an HG force/history object')
    console=ctx['paths']['log'].read_text(encoding='utf-8-sig',errors='replace')
    fixture_count=console.count(FIXTURE)
    c.need(fixture_count==(0 if ctx['scheme']=='A' else 1),
           'Actual16 device source/role fixtures must stay untaken for A and run once for B/C')
    with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
    c.need(len(rows)==1 and int(rows[0]['Steps'])==128 and int(rows[0]['PartFiles'])==2
           and int(rows[0]['Np'])==37181 and int(rows[0]['Nfixed'])==int(rows[0]['Nbound'])==8
           and int(rows[0]['PartsOut'])==0 and 'gpu' in rows[0]['Hardware'].lower(), 'Actual GPU native counts/Run.csv differ')
    c.need(sorted(p.name for p in (out/'data').glob('Part_*.bi4'))==['Part_0000.bi4','Part_0001.bi4'],
           'Actual two raw frames missing/extra; decoding remains pending')
    if ctx['scheme']=='A':
        c.need(not any((out/('UplTpiCryerGpuR1'+x)).exists() for x in ('.policy.json','.csv','.summary.json')),
               'Default A must not enter private history/endpoint/sidecar branch')
        return dict(solver_summary_completed=True,native_frame_presence_only=True,reported_steps=128,reported_native_frames=2,
            actual_device_fixture_marker_count=0,actual_device_fixture_checked_cases=0,fixture_inferred_from_build=False,
            actual_device_from_Run_csv=rows[0]['Hardware'],HG_snapshot_checks=0,private_branch_entered=False,
            retained_GPU_A_control_native_comparison_pending=True,all22_native_ID_clock_signed_ledger_review_pending=True)
    policy=c.read(out/'UplTpiCryerGpuR1.policy.json');summary=c.read(out/'UplTpiCryerGpuR1.summary.json')
    alpha=.5 if ctx['scheme']=='B' else 0.
    name='B_TPI_alpha_0p5_beta0' if ctx['scheme']=='B' else 'C_PPE_t_alpha0_beta0'
    c.need(policy['stage']=='upl_tpi_cryer_gpu_r1' and policy['scheme']==name
           and policy['alpha']==alpha and policy['beta']==0 and policy['M0'] and policy['native_count']==37181
           and policy['soil_count']==37173 and policy['history_ID_owned'] and policy['history_cold_start'],
           'Actual C04 pressure policy differs')
    c.need(summary['stage']=='upl_tpi_cryer_gpu_r1' and summary['completed']
           and summary['scheme']==policy['scheme'] and summary['alpha']==alpha and summary['beta']==0
           and summary['commits']==summary['endpoint_calls']==128 and summary['core_field_bit_checks']==7*37173*128
           and summary['HG_readonly_snapshot_checks']==0 and summary['actual_end']==ctx['clock']['actual_scalar_end_s'],
           'Actual pressure lifecycle/end/core7/HG0 summary differs')
    return dict(solver_summary_completed=True,native_frame_presence_only=True,reported_steps=128,reported_native_frames=2,
        memcheck_invocations=0,private_branch_entered=True,
        actual_device_fixture_marker_count=1,actual_device_fixture_checked_cases=16,
        fixture_inferred_from_build=False,actual_device_from_Run_csv=rows[0]['Hardware'],
        HG_snapshot_checks=0,all22_native_ID_clock_signed_ledger_and_history_review_pending=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true')
    ap.add_argument('--admission',required=True,type=Path);args=ap.parse_args()
    c.need(args.execution_authorized,'One independent C04 Release128 run admission required')
    ad=ctx=None;result=dict(stage=STAGE+'.run',passed=False,failure=None,solver_invocations=0,
        native_invocations=0,GenCase_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,
        physical_acceptance=False,automatic_follow_up=False,old_paused_processes_touched=False)
    try:
        ad=Admission(args.admission);ctx=context(ad);result.update({k:v for k,v in ctx.items() if k!='paths'})
        result['root_admission']=ad.entry;g.run_owned(ad,ctx,result);result.update(check_output(ctx));result['passed']=True
    except Exception as exc:result['failure']=str(exc)
    finally:
        if ctx is not None:
            for name,p in [('console',ctx['paths']['log']),('Run_out',Path(ctx['output_directory'])/'Run.out')]:
                if p.exists():
                    lines=p.read_text(encoding='utf-8-sig',errors='replace').splitlines()
                    result['last_raw_'+name+'_PART_line']=next((x for x in reversed(lines) if re.match(r'^Part_\d+\s',x)),None)
                    result['first_raw_'+name+'_error']=next((x for x in lines if '*** Exception' in x or re.search(r'\berror\b',x,re.I)),None)
            try:result.update(consumed=ad.finish(),consumed_stats_unchanged=True)
            except Exception as exc:result.update(passed=False,consumed_stats_unchanged=False,failure=(result['failure'] or '')+'; '+str(exc))
            out=Path(ctx['output_directory']);result['outputs_stat_only']=[c.stat(p) for p in sorted(out.rglob('*')) if p.is_file()] if out.exists() else []
            c.write_new(ctx['paths']['run'],result);c.write_new(ctx['paths']['status'],dict(stage=ctx['tag']+'.status',
                passed=result['passed'],run=c.stat(ctx['paths']['run']),state='pending_unique_native_review' if result['passed'] else 'failed_preserved',following_action_launched=False))
        print(json.dumps(dict(passed=result['passed'],tag=result.get('tag'),failure=result['failure']),ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
