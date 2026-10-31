"""Review the completed portable r2b smoke; read-only decoders, never a solver."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import traceback
import zipfile
import numpy as np

TESTS=Path(__file__).resolve().parents[1]; CASE=TESTS.parent; TAG='cryer_release_portable_r2'
PORTABLE=TESTS/'outputs/cryer_release_portable_r2b'; SMOKE=PORTABLE/'CaseCryerProblem_PR_release_r2_smoke_out'
CHECK=TESTS/'logs'/(TAG+'.check.json'); PACKAGE=TESTS/'logs/cryer_release_package_r2.check.json'
MANIFEST=CASE/'support/cryer_server_manifest_r2.json'; RECEIPT=SMOKE/'execution_receipt_r2.json'
ZIP_SHA='c3a89c1167a01109fbd3b69fff45ceae16e5e61c0ec15ace303c02f1740fb9a0'
PROGRAM_SHA='652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096'


def digest(path):
    path=Path(path); h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=h.hexdigest())


def bindings(value):
    if isinstance(value,dict):
        if {'path','bytes','sha256'}<=value.keys():yield value
        else:
            for child in value.values():yield from bindings(child)
    elif isinstance(value,list):
        for child in value:yield from bindings(child)


def review():
    assert not CHECK.exists(),'Fresh review only; never overwrite a retained check'
    state=dict(passed=False,smoke_native_verified=False,errors=[],safety_errors=[],comparisons=[],native_summaries=[],inputs=[],solver_started=False,programs_built=False,queue_used=False,
        physical_acceptance=False,full_cycle_acceptance=False,full_half_validation=False,server_a6000_smoke=False,production_source_changed=False,old_server_executable_attribution_proven=False)
    records={}
    def verify(record):
        actual=digest(record['path']); key=actual['path'].lower()
        assert actual['bytes']==int(record['bytes']) and actual['sha256']==record['sha256'].lower(),('Binding mismatch',record['path'])
        assert key not in records or records[key]==actual,('Conflicting binding',record['path'])
        records[key]=actual; return actual
    def load(path):
        verify(digest(path)); return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    try:
        verify(digest(Path(__file__))); package=load(PACKAGE); assert package['package_consistency_passed'] and package['verified_zip_entries']==15
        for record in bindings(package):verify(record)
        assert package['zip']['sha256']==ZIP_SHA and Path(package['manifest']['path']).resolve()==MANIFEST.resolve()
        negative=load(TESTS/'logs/cryer_release_negative_r2.check.json')
        assert negative['negative_checks_passed'] and negative['all_smoke_hashes_unchanged'] and not negative['solver_or_gencase_started']
        for record in bindings(negative):verify(record)
        manifest=load(MANIFEST); assert manifest['verified_program_sha256']==PROGRAM_SHA and manifest['smoke_steps']==128
        for record in bindings(manifest):verify(record)
        files={x['entry']:x for x in manifest['files']}; assert len(files)==len(manifest['files'])==14
        entries=dict(files); entries['support/cryer_server_manifest_r2.json']=package['manifest']
        with zipfile.ZipFile(package['zip']['path']) as archive:
            names=archive.namelist(); assert len(names)==len(set(names))==15 and set(names)==set(entries),'ZIP whitelist mismatch'
            for name,expected in entries.items():
                data=archive.read(name); assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],('ZIP entry',name)
        for name,expected in files.items():
            for root in [CASE,PORTABLE]:verify(dict(path=str(root/name),bytes=expected['bytes'],sha256=expected['sha256']))
        receipt=load(RECEIPT)
        for record in bindings(receipt):verify(record)
        assert receipt['status']=='solver_exited_zero_pending_native_review' and receipt['mode']=='smoke' and receipt['solver_exited_zero']
        assert receipt['native_completion_verified'] is False and receipt['restart_used'] is False and receipt['physical_acceptance'] is False
        assert receipt['expected_steps']==128 and float(receipt['expected_dt_s'])==2.**-20 and float(receipt['effective_tmax_s'])==2.**-13
        assert Path(receipt['working_directory']).resolve()==PORTABLE.resolve() and Path(receipt['output']).resolve()==SMOKE.resolve()
        launched={x['entry']:x['actual_file'] for x in receipt['actual_payload_at_launch']}; assert set(launched)==set(files)
        for name,record in launched.items():assert record['bytes']==files[name]['bytes'] and record['sha256']==files[name]['sha256']
        stages=receipt['stages']; assert [x['stage'] for x in stages]==['gencase','solver']
        for stage in stages:
            assert stage['status']=='exited' and stage['exit_code']==0 and stage['executable_before']==stage['executable_after']
        assert stages[1]['executable_before']['sha256']==PROGRAM_SHA
        assert '-gpu' in stages[1]['argv'] and '-stable' in stages[1]['argv'] and '-tmax:0.0001220703125' in stages[1]['argv']
        assert receipt['actual_runtime_before_solver']==receipt['actual_runtime_after_solver'] and len(receipt['actual_runtime_before_solver'])==9
        oldcheck=load(TESTS/'logs/cryer_full_native_r1.check.json'); assert oldcheck['passed'] and oldcheck['native_safety_passed']
        verify(oldcheck['inputs_manifest']); oldinputs=load(oldcheck['inputs_manifest']['path'])['inputs']
        selected=[Path(__file__).with_name('cryer_full_native_r1.py'),Path(__file__).with_name('cryer_start_r1.py'),Path(oldcheck['reader_program']['path']),Path(oldcheck['reader_source']['path'])]
        oldfolder=CASE/'CaseCryerProblem_PR_symc_nu030_out'
        selected += [oldfolder/'data'/name for name in ['Part_0000.bi4','Part_0001.bi4','Part_Head.ibi4','PartInfo.ibi4']]
        for path in selected:
            matches=[x for x in oldinputs if Path(x['path']).resolve()==path.resolve()]; assert len(matches)==1; verify(matches[0])
        import cryer_full_native_r1 as native
        assert Path(native.READER).resolve()==Path(oldcheck['reader_program']['path']).resolve()
        verify(oldcheck['reader_program']); verify(oldcheck['reader_source'])
        for name in ['Part_0000.bi4','Part_0001.bi4','Part_Head.ibi4','PartInfo.ibi4']:verify(digest(SMOKE/'data'/name))
        assert sorted(x.name for x in (SMOKE/'data').glob('Part_*.bi4'))==['Part_0000.bi4','Part_0001.bi4']
        p=native.parameters(receipt['generated_xml']['path']); assert p['dt']==2.**-20 and p['TD']==2.**-7 and p['ramp']==2.**-8
        grid,times=native.schedule(p['dt'],963370); assert grid[:2].tolist()==[0,128] and times[:2].tolist()==[0.,2.**-13]
        context=None
        for part in [0,1]:
            a=native.native(SMOKE,part); b=native.native(oldfolder,part)
            if context is None:context=native.context(a)
            row,_,issues=native.inspect(a,context,part,p,grid,times); state['native_summaries'].append(row)
            if issues:state['safety_errors'].append(dict(part=part,issues=issues))
            different=a.to_numpy(dtype='<f8').view('<u8')!=b.to_numpy(dtype='<f8').view('<u8')
            fields=[dict(field=key,count=int(different[:,i].sum()),max_abs_difference=float(np.max(np.abs(a[key]-b[key])))) for i,key in enumerate(native.COLUMNS) if different[:,i].any()]
            state['comparisons'].append(dict(part=part,time_s=row['time_s'],saved_step=row['saved_step'],native_ids=[8,37180],soil_count=len(a),columns=35,all35_including_dterror_0ulp=not different.any(),different_fields=fields))
        text=Path(receipt['run_log']['path']).read_text(errors='replace')
        assert 'NVIDIA GeForce RTX 3050' in text and 'Finished execution (code=0)' in text
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==128 and int(re.search(r'Excluded particles\.*:\s*(\d+)',text)[1])==0
        loop=float(re.search(r'Simulation Runtime\.*:\s*([\d.]+)\s*sec',text)[1]); assert loop==16.232613
        state.update(verified_zip_entries=15,verified_root_and_portable_payload_files=28,execution_stages_exit_codes=[x['exit_code'] for x in stages],original_receipt_native_completion_verified=False,
            actual_hardware='NVIDIA GeForce RTX 3050',actual_steps=128,actual_final_time_s=2.**-13,observed_simulation_runtime_s=loop,controlled_benchmark=False,
            scope='Two closed-surface startup frames only; no peak/full/half accuracy or returned-server EXE identity claim.')
        state['smoke_native_verified']=not state['safety_errors'] and all(x['all35_including_dterror_0ulp'] for x in state['comparisons'])
        if not state['smoke_native_verified']:state['errors'].append('Original native safety or exact35 startup regression failed; differences are retained without exclusions.')
        for record in list(records.values()):verify(record)
        state.update(all_bound_inputs_unchanged=True,passed=state['smoke_native_verified'],checked_frames=2,reference_frames=2)
    except BaseException as failure:state['errors'].append(repr(failure)); state['traceback']=traceback.format_exc()
    state['inputs']=list(records.values()); state['verified_unique_files']=len(records); state['verified_unique_bytes']=sum(x['bytes'] for x in records.values())
    with CHECK.open('x',encoding='utf8') as stream:json.dump(state,stream,indent=2,allow_nan=False)
    return dict(check=str(CHECK),passed=state['passed'],errors=state['errors'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--review',action='store_true'); args=parser.parse_args()
    if args.review:
        result=review(); print(json.dumps(result)); raise SystemExit(0 if result['passed'] else 1)
    else:parser.print_help()
