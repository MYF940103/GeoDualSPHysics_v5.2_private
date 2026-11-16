"""Offline review of one genuinely completed psi2p5 Wendland source; no reader or solver."""
import argparse
import inspect
import json
from pathlib import Path
import c08_h18_wend_review_r1 as previous
import c08_h18_wall_c_retry_full3_review_r1 as topology

old,plastic=previous.old,previous.plastic
T,L=old.T,old.T/'logs';np=old.np
need,read,stat,bind=old.need,old.read,old.stat,old.bind
TAG='c08_h18_wend_psi2p5_source_review_r1';SOURCE='c08_h18_wend_branches_psi2p5_pre_r1'
GROUP='psi2p5';NOTE=T/'notes'/(TAG+'.md');NATIVE=L/'c08_h18_wend_psi2p5_native_r2.check.json'
CHECK=L/(TAG+'.check.json');PREFIX=T/'figures'/TAG


def clone(function,replacements,namespace,proofs):
    original=inspect.getsource(function);changed=original
    for before,after in replacements:
        need(changed.count(before)==1,'Narrow adapter must find exactly one literal: '+before)
        changed=changed.replace(before,after,1)
    restored=changed
    for before,after in reversed(replacements):
        need(restored.count(after)==1,'Narrow adapter inverse is ambiguous: '+after)
        restored=restored.replace(after,before,1)
    need(restored==original,'Original function source inverse differs')
    exec(compile(changed,str(Path(__file__))+'::'+function.__name__,'exec'),namespace)
    proofs.append(dict(function=function.__name__,literal_replacements=replacements,exact_inverse_original_source=True))
    return namespace[function.__name__]


def loader(proofs):
    # A private namespace: the archived module and its globals remain untouched.
    ns=dict(vars(previous));ns['SOURCE']=SOURCE
    ns['material_xml']=clone(previous.material_xml,[
        ("p['group']=='psi0'","p['group']=='psi2p5'"),
        ('Exact15-key Wendland/psi0 material CSV required','Exact15-key Wendland/psi2p5 material CSV required'),
        ('dlt=0,DilationDecay=0','dlt=2.5,DilationDecay=.2'),
        ('Outside actual Wendland psi0 material: ','Outside actual Wendland psi2p5 material: ')],ns,proofs)
    load=clone(previous.load,[("d['group']=='psi0'","d['group']=='psi2p5'"),("group='psi0'","group='psi2p5'")],ns,proofs)
    focus=clone(previous.focus_plots,[('Wendland psi0 preload','Wendland psi2p5 preload')],ns,proofs)
    return load,focus


def inputs(consumed):
    n=read(NATIVE);consumed.append(stat(NATIVE))
    need(n['stage']=='c08_h18_wend_psi2p5_native_r2' and n['passed'] and n['reader_invocations']==1
         and n['solver_invocations']==n['build_invocations']==n['VTK_invocations']==0
         and n['prior_reader_invocations']==0 and n['consumed_stats_unchanged']
         and n['saved_FS23_sign_observational_except_original_nonempty_final_certificate_gate']
         and n['source_native_certificate_not_equilibrium'],'One actual passed r2 source qualification required; failed r1 is not a decode')
    for key in ('call','completion','source_run','terminal_review','material_csv','planned_steps'):consumed.append(bind(n[key]))
    need(len(n['files'])==7,'Actual native seven-export seal required')
    consumed += [bind(q) for q in n['files']]
    done=read(n['completion']['path']);run=read(n['source_run']['path']);root=Path(n['completion']['path']).parent
    need(root==T/'outputs'/SOURCE/'native_r2' and done['group']==GROUP and run['stage']==SOURCE
         and run['group']==GROUP and n['material_values']['group']==GROUP,'Actual psi2p5 source/native group binding differs')
    need({Path(q['path']).name for q in n['files']}=={'completion.json','typed22.bin','typed22_layout.csv','clocks.csv','summary.csv','layers.csv','snapshots.csv'}
         and all(Path(q['path']).parent==root for q in n['files']),'Native export paths differ from the actual unique r2 output')
    need(n['source_run']==stat(L/(SOURCE+'.run.json')) and n['planned_steps']==run['planned_steps'],'Native source run/actual plan differ')
    manifest=dict(tag=TAG,native_dir=str(root),native_call=n['call']['path'],material_csv=n['material_csv']['path'],
                  plan=n['planned_steps']['path'],run=n['source_run']['path'],input_xml=run['input_xml']['path'])
    return n,manifest


def geometry(bundle,history):
    # Original Wendland source NN calculations, plus the already reviewed fixed material quads.
    first=bundle['frames'][0]['Posd'][2060:];cells,a0=topology.grid(dict(initial=first));rows=[]
    for part,x in enumerate(bundle['frames']):
        pos=x['Posd'][2060:];tree=old.cKDTree(pos[:,(0,2)]);distance,index=tree.query(pos[:,(0,2)],k=2,workers=1)
        nn=np.min(np.where(index!=np.arange(5000)[:,None],distance,np.inf),axis=1)/old.DP
        pair=tree.query_pairs(.7*old.DP,output_type='ndarray');pairs=int(np.count_nonzero(np.linalg.norm(pos[pair[:,0]]-pos[pair[:,1]],axis=1)<.7*old.DP)) if len(pair) else 0
        ratio,tri,mixed,bow,_=topology.material.measures(pos[:,(0,2)],cells,a0);J=x['PoroVolumeRatio'][2060:,0]
        rows.append(dict(part=part,time_s=history[part]['time_s'],completed_step=history[part]['completed_step'],
            NN_min_over_dp=float(nn.min()),NN_q05_over_dp=float(np.quantile(nn,.05)),NN_median_over_dp=float(np.median(nn)),pairs_r_lt_0p7dp=pairs,
            soil_x_below0=int(np.count_nonzero(pos[:,0]<0)),soil_z_below0=int(np.count_nonzero(pos[:,2]<0)),min_soil_x_m=float(pos[:,0].min()),min_soil_z_m=float(pos[:,2].min()),
            min_material_chord_area_ratio=float(ratio.min()),max_material_chord_area_ratio=float(ratio.max()),nonpositive_area_cells=int((ratio<=0).sum()),
            chosen_diagonal_triangle_reversals=int(tri.sum()),mixed_turn_cells=int(mixed.sum()),self_cross_cells=int(bow.sum()),
            material_chord_area_minus_mean_nativeJ_RMS=float(np.sqrt(np.mean((ratio-J[cells].mean(axis=1))**2)))))
    need(len(rows)==1001,'Every genuine source geometry state required')
    return rows


def geometry_plot(rows):
    fig,axes=old.plt.subplots(2,3,figsize=(13,7),layout='constrained');t=[q['time_s'] for q in rows]
    charts=(('Nearest soil distance / dp',('NN_min_over_dp','NN_q05_over_dp','NN_median_over_dp')),
        ('Close soil pairs [count]',('pairs_r_lt_0p7dp',)),('Saved geometry observations [count]',('soil_x_below0','soil_z_below0','self_cross_cells','nonpositive_area_cells')),
        ('Fixed material chord area ratio',('min_material_chord_area_ratio','max_material_chord_area_ratio')),
        ('Material topology observations [count]',('chosen_diagonal_triangle_reversals','mixed_turn_cells')),
        ('Chord area vs native J [RMS]',('material_chord_area_minus_mean_nativeJ_RMS',)))
    for ax,(title,keys) in zip(axes.flat,charts):
        for key in keys:ax.plot(t,[q[key] for q in rows],label=key)
        ax.set(title=title,xlabel='Actual source time [s]');ax.grid(alpha=.2);ax.legend(fontsize=6)
    fig.suptitle('Wendland psi2p5 source: all1001 actual saves; fixed100x50 material grid\nChord geometry is not native J, exact continuum strain, or an equilibrium certificate')
    dest=Path(str(PREFIX)+'_geometry.png');fig.savefig(dest,dpi=170);old.plt.close(fig);return dest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Separate root offline authorization required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'_*')),'Existing completed/partial source review protected')
    consumed=[stat(q) for q in (Path(__file__),NOTE,Path(previous.__file__),Path(old.__file__),Path(plastic.__file__),Path(topology.__file__),Path(topology.material.__file__))]
    result=dict(stage=TAG,analysis_complete=False,physical_acceptance=False,source_equilibrium_accepted=False,solver_invocations=0,reader_invocations=0,VTK_invocations=0,GPU_actions=0,SHA_scans=0,automatic_next_job=False)
    try:
        n,manifest=inputs(consumed);proofs=[];load,focus=loader(proofs);bundle=load(manifest,consumed)
        analysis=old.analyze_case(bundle);history=analysis['history'];spatial=geometry(bundle,history);tails,changes=previous.tails(bundle,analysis)
        need(len(history)==1001 and len(analysis['layers'])==50050 and all(q['group']==GROUP and q['source']==SOURCE for q in history),'All1001 actual source histories/50 fixed layers/group labels required')
        need(history[-1]['FS23_soil']>0 and history[-1]['saved_FS23_positive']==0,'Original nonempty final FS certificate observation differs')
        files=[]
        for name,rows in [(key,analysis[key]) for key in ('history','extrema','layers','tracks')]+[('geometry',spatial),('tail_metrics',tails),('tail_same_material_changes',changes)]:
            dest=Path(str(PREFIX)+'_'+name+'.csv');old.write_csv(dest,rows);files.append(dest)
        files+=plastic.source_plots([analysis],PREFIX);files+=focus(history,PREFIX);files.append(geometry_plot(spatial))
        need(all(stat(q['path'])==q for q in consumed),'Source/native/helper stat binding changed during offline review')
        result.update(passed=True,analysis_complete=True,group=GROUP,actual_source=SOURCE,unique_native_check=stat(NATIVE),
            source_native_qualified=True,source_run=n['source_run'],source_native_check=stat(NATIVE),source_native_completion=n['completion'],
            original_native_guards_unchanged=True,actual_samples=1001,material_grid=[100,50],fixed_material_quad_cells=4851,
            source_summary=analysis['summary'],tail_same_material_changes=changes,spatial_summary=dict(final=spatial[-1],
                minimum_NN_over_dp=min(q['NN_min_over_dp'] for q in spatial),maximum_close_pairs=max(q['pairs_r_lt_0p7dp'] for q in spatial),
                all_saved_nonpositive_area_cells=sum(q['nonpositive_area_cells'] for q in spatial),all_saved_self_cross_cells=sum(q['self_cross_cells'] for q in spatial)),
            mechanical_adapter_proofs=proofs,old_module_globals_modified=False,old_psi0_payload_read=False,Cubic_comparison=False,
            saved_FS23_positive_history_is_observation=True,full_history_FS23_positive_observations=sum(q['saved_FS23_positive'] for q in history),
            final_FS23_positive0_is_original_certificate=True,source_certificate_is_not_equilibrium=True,source_equilibrium_gate_added=False,
            chord_geometry_is_native_J=False,pressure_storage_or_KE_is_full_coupled_energy=False,new_receiver_continuity_tested=False,
            native_p_minus_P0_is_paper_excess_truth=False,half_or_theory_error_claimed=False,consumed_stats_unchanged=True,
            visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),partial_outputs_preserved=True)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False)
    need(result.get('passed',False),result.get('first_failure','Offline source review failed; preserve partials'))


if __name__=='__main__':main()
