"""Offline receipt consolidation; no solver, source edit or old receipt rewrite."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from spr_planes_run import TESTS,REPO,bound


def main():
    receipt=TESTS/'logs/spr_gpu_delivery_r1.check.json';assert not receipt.exists()
    checked={};historical=[];unavailable_objects=[]
    def verify(item):
        key=(item['path'],item['sha256'].lower())
        if key in checked:return
        path=Path(item['path']);actual=bound(path)['sha256'].lower()
        if actual!=key[1]:
            if path.suffix=='.obj' and (REPO/'src/VS/x64') in path.parents:
                # MSBuild cache is not an immutable archive. Preserve the old
                # build receipt and verify its linked retained exe separately.
                unavailable_objects.append(item);checked[key]=False;return
            assert path.parent in (REPO/'src/source',REPO/'bin/windows'),path
            candidates=[TESTS/'outputs'/x/path.name for x in ('spr_gpu_planes_base','spr_gpu_planes_preload_verified')]
            matches=[x for x in candidates if x.is_file() and bound(x)['sha256'].lower()==key[1]]
            assert matches,('Retained hash unavailable',path)
            historical.append(dict(original=str(path),retained=bound(matches[0])))
        checked[key]=True
    def walk(value):
        if isinstance(value,dict):
            if 'path' in value and 'sha256' in value:verify(value)
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    tags=['spr_gpu_planes_rel_r1','spr_gpu_planes_dbg_r1','spr_gpu_legacy_rel_r1','spr_gpu_legacy_dbg_r1',
          'spr_gpu_paths_r2','spr_gpu_pulse_r1','spr_gpu_nopen_pulse_r2']
    data={};evidence=[bound(__file__)]
    for tag in tags:
        path=TESTS/'logs'/(tag+'.check.json');r=json.loads(path.read_text());walk(r);data[tag]=r;evidence.append(bound(path))
        if tag!='spr_gpu_pulse_r1':assert r['passed']
    manufactured=data[tags[0]]['runs']+data[tags[1]]['runs'];assert len(manufactured)==18
    assert all(x['metrics']['passed'] and x['metrics']['active_wall_count']==x['metrics']['wall_count'] and x['exit_code']==0 and x['owned_exited'] for x in manufactured)
    legacy=data[tags[2]]['runs']+data[tags[3]]['runs'];assert len(legacy)==36
    assert all(x['metrics']['passed'] and x['exit_code']==0 and x['owned_process_exited'] for x in legacy)
    paths=data['spr_gpu_paths_r2']['pairs'];assert len(paths)==4
    assert all(x['all_fields_0ulp'] and x['frames']==31 and x['native_soil_count']==1000 and x['exit_code']==0 and x['owned_exited'] for x in paths)
    partial=data['spr_gpu_pulse_r1'];missing=data['spr_gpu_nopen_pulse_r2']
    # The frozen first orchestration failed preparing NoPen, AFTER six standard
    # pairs completed. Its top-level failure is retained, not re-labelled passed.
    assert partial['passed'] is False and len(partial['half'])==6 and len(partial['runs'])==12
    assert all(not x['no_pen'] for x in partial['half']) and len(missing['half'])==2
    pairs=partial['half']+missing['half'];runs=partial['runs']+missing['runs'];cross=partial['cpu_gpu']+missing['cpu_gpu']
    assert len(runs)==16 and all(x['exit_code']==0 and x['owned_exited'] and x['energy_ratio_max']<=1.1 for x in runs)
    assert all(x['passed'] and x['pressure_rms_max_pa']<=.5 and x['material_displacement_max_mm']<=1e-5 for x in pairs+cross)
    log=TESTS/'logs/spr_gpu_planes_memcheck_r2.log';text=log.read_text()
    done=TESTS/'outputs/spr_gpu_planes_memcheck_r2/planes_complete.json';r=json.loads(done.read_text())
    assert 'ERROR SUMMARY: 0 errors' in text and r['passed'] and r['active_wall_count']==r['wall_count']==1104
    evidence += [bound(log),bound(done),bound(TESTS/'logs/spr_gpu_planes_Debug_op2.build.json')]
    frame=pd.DataFrame(pairs);frame['case']=[x['geometry']+' S'+str(x['slip'])+(' NoPen' if x['no_pen'] else '') for x in pairs]
    csv=TESTS/'figures/spr_gpu_delivery_r1_pulse.csv';frame.to_csv(csv,index=False,mode='x')
    fig,axes=plt.subplots(1,2,figsize=(12,5.3));y=np.arange(len(frame))
    for ax,key,limit,title in zip(axes,['pressure_rms_max_pa','material_displacement_max_mm'],[.5,1e-5],['Half-step pressure RMS (Pa)','Half-step maximum material displacement (mm)']):
        ax.barh(y,frame[key],color=['#228899' if x else '#5d79a6' for x in frame.no_pen]);ax.set_xscale('log');ax.axvline(limit,color='.3',ls=':',label='Original limit')
        ax.set(yticks=y,yticklabels=frame['case'],xlabel=title);ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.legend(fontsize=9)
    fig.suptitle('GPU fixed multi-plane SPR: eight independent 2-ms half-step pairs')
    fig.tight_layout(rect=(0,.06,1,.93));fig.text(.5,.015,'Nonzero pulse; HG off; dt=1 us / 0.5 us. Not full consolidation or general-boundary acceptance.',ha='center',fontsize=9)
    png=TESTS/'figures/spr_gpu_delivery_r1_pulse.png';assert not png.exists();fig.savefig(png,dpi=160);plt.close(fig)
    result=dict(passed=True,scope='Bounded GPU operator/old-path/pulse/memory checks only',physical_acceptance=False,
        multi_face_manufactured=18,legacy_manufactured=36,single_plane_native_0ulp_paths=4,pulse_half_pairs=8,
        max_aux_error_m_s=max(x['metrics']['max_affine_error'] for x in manufactured),
        pulse_pressure_rms_max_pa=float(frame.pressure_rms_max_pa.max()),pulse_material_max_mm=float(frame.material_displacement_max_mm.max()),
        cpu_gpu_pressure_rms_max_pa=max(x['pressure_rms_max_pa'] for x in cross),cpu_gpu_material_max_mm=max(x['material_displacement_max_mm'] for x in cross),
        memcheck_errors=0,memcheck_scope='Current Debug 3D edge S2, all 1104 walls; not all kernels/all inputs',
        original_partial_worker_passed=False,partial_scope='Six completed standard pairs adopted; only two missing NoPen pairs freshly run',
        unique_file_hashes_verified=sum(checked.values()),historical_inputs=historical,
        overwritten_msbuild_objects_not_reverified=unavailable_objects,historical_build_objects_all_retained=not unavailable_objects,
        evidence=evidence,outputs=[bound(csv),bound(png)],visual_inspected=False)
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','outputs','historical_inputs','overwritten_msbuild_objects_not_reverified')},indent=2))


if __name__=='__main__':main()
