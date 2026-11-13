"""Offline constants/affine recovery at original mirrors of actual saved wall stencils."""
import argparse,json,struct
from pathlib import Path
import c08_h18_wend_partial_review_r1 as replay

np,T,need,stat,read,table=replay.np,replay.T,replay.need,replay.stat,replay.read,replay.table
TAG='c08_h18_wall_affine_probe_r1'
REVIEW=T/'logs/c08_h18_wend_a03_partial_review_r1.check.json'
NATIVE=T/'outputs/c08_h18_wend_psi0_a03_w09_r1/native_partial_r1'
CSV=T/'figures/c08_h18_wend_a03_partial_review_r1_wall_support_replay.csv'
NAMES=('J','p_normal_head_removed','vx','vy','vz','sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_xz','sigma_yz')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args()
    need(args.execution_authorized,'Root must fully read this offline probe first')
    check=T/'logs'/(TAG+'.check.json');dest=T/'figures'/(TAG+'.csv')
    need(not check.exists() and not dest.exists(),'Prior complete/partial artifacts are protected')
    prior=read(REVIEW);need(prior['analysis_complete'] and prior['saved_prefix_native_qualified'] and not prior['whole_run_passed'] and not prior['unsaved_failure_state_reconstructed'],'Only reviewed failed90 saved prefix admitted')
    consumed=[stat(REVIEW),stat(__file__),stat(T/'notes'/(TAG+'.md'))]
    bound={str(Path(q['path']).resolve()):q for q in prior['consumed']+prior['files']}
    for f in (CSV,Path(replay.__file__),NATIVE/'completion.json',NATIVE/'typed22.bin',NATIVE/'typed22_layout.csv',NATIVE/'clocks.csv'):
        q=stat(f);need(bound.get(str(f.resolve()))==q,'Previously reviewed binding changed: '+str(f));consumed.append(q)
    done=read(NATIVE/'completion.json');need(done['diagnostic_complete'] and done['saved_prefix_native_passed'] and done['samples']==90 and not done['whole_run_native_passed'],'Actual partial completion scope changed')
    layout=table(NATIVE/'typed22_layout.csv');fields=[('time','<f8')]
    need(len(layout)==22,'Literal typed22 layout required')
    for row,(name,kind,width) in zip(layout,replay.old.SCHEMA):
        need((row['array'],row['type'],int(row['components']))==(name,kind,width),'Typed22 schema changed');fields.append((name,replay.old.TYPES[kind],(6805,width)))
    dtype=np.dtype(fields);raw=NATIVE/'typed22.bin'
    with raw.open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,90),'Preserve genuine90 header')
    need(raw.stat().st_size==12+90*dtype.itemsize,'Typed22 payload extent changed')
    frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(90,));clocks=table(NATIVE/'clocks.csv');need(len(clocks)==90,'Original90 clocks required')
    groups={}
    for row in table(CSV):groups.setdefault((int(row['part']),int(row['wall_id'])),[]).append(row)
    eligible=[]
    for key,rows in groups.items():
        primary=next(q for q in rows if q['fit_method']=='original_GP')
        good=any(q['fit_method']!='original_GP' and q['geometry_pass']=='True' for q in rows)
        if primary['geometry_pass']=='False' and int(primary['real_B_double_support'])>0 and good:eligible.append(key)
    chosen=[]
    for identity in (True,False):
        subset=sorted(k for k in eligible if (k[1]==893)==identity);need(subset,'Actual893 and front-wall retry stencils required')
        for i in (0,len(subset)//2,len(subset)-1):
            if subset[i] not in chosen:chosen.append(subset[i])
    need((89,893) in chosen,'Include actual last saved wall893, never reconstruct unsaved stage')
    c0=1+np.arange(11,dtype=float)/7;bx=(np.arange(11,dtype=float)+1)/3;bz=(np.arange(11,dtype=float)+1)*(-1.)**np.arange(11)/5
    rowsout=[];stencils=[];threshold=prior['reported_failure']['MdbcThreshold'];h=float(np.float32(.072))
    for part,identity in chosen:
        x=frames[part];ids=x['Idp'][:,0];expected=np.concatenate((np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)))
        need(np.array_equal(ids,expected) and float(x['time'])==float(clocks[part]['time_s']),'Selected native IDs/actual clock differ')
        soil=ids>=2060;pos=x['Posd'][soil][:,(0,2)];J=x['PoroVolumeRatio'][soil,0]
        need(np.isfinite(J).all() and (J>1-float(np.float32(.35))).all(),'Use original positive admissible native J weights')
        records=groups[(part,identity)];base=next(q for q in records if q['fit_method']=='original_GP');target=np.array([float(base['original_GP_x_m']),float(base['original_GP_z_m'])])
        B=x['Posd'][int(np.flatnonzero(ids==identity)[0])][[0,2]]
        need(np.array_equal(B,np.array([float(base['B_x_m']),float(base['B_z_m'])])),'Actual fixed wall position differs from replay')
        for test in ('constant','affine'):
            fields=np.broadcast_to(c0,(len(pos),11)).copy()
            if test=='affine':fields+=(pos[:,0]-target[0])[:,None]*bx+(pos[:,1]-target[1])[:,None]*bz
            for q in records:
                centre=np.array([float(q['fit_centre_x_m']),float(q['fit_centre_z_m'])]);f=replay.fit(pos,J,fields,centre,target,h,threshold)
                need(f['geometry_pass']==(q['geometry_pass']=='True') and f['determinant']==float(q['determinant']) and f['invalid_source_J']==0,'Geometry-only replay differs from bound saved replay')
                error=None if f['value'] is None else f['value']-c0
                for c,name in enumerate(NAMES):
                    e=None if error is None else float(error[c]);rowsout.append(dict(part=part,time_s=float(x['time']),wall_id=identity,test=test,fit_method=q['fit_method'],field=name,analytic_at_original_GP=float(c0[c]),reconstructed_at_original_GP=None if f['value'] is None else float(f['value'][c]),signed_error=e,absolute_error=None if e is None else abs(e),relative_error=None if e is None else abs(e)/max(1.,abs(float(c0[c]))),geometry_pass=f['geometry_pass'],determinant=f['determinant'],raw_moment_condition2=f['raw_moment_condition2'],positive_weight_sources=f['positive_weight_sources'],fit_centre_x_m=float(centre[0]),fit_centre_z_m=float(centre[1]),original_GP_x_m=float(target[0]),original_GP_z_m=float(target[1])))
        stencils.append(dict(part=part,time_s=float(x['time']),saved_step=int(clocks[part]['saved_step']),wall_id=identity,role=base['wall_role'],native_J_min=float(J.min()),native_J_max=float(J.max())))
    summary={}
    for test in ('constant','affine'):
        rr=[q for q in rowsout if q['test']==test and q['absolute_error'] is not None];ee=np.array([q['signed_error'] for q in rr]);summary[test]=dict(component_evaluations=len(rr),max_absolute_error=float(np.max(np.abs(ee))),RMS_error=float(np.sqrt(np.mean(ee*ee))),max_relative_error=max(q['relative_error'] for q in rr))
        summary[test]['methods']={}
        for method in sorted({q['fit_method'] for q in rr}):
            subset=[q for q in rr if q['fit_method']==method];e=np.array([q['signed_error'] for q in subset]);conditions=[q['raw_moment_condition2'] for q in subset if q['raw_moment_condition2'] is not None]
            summary[test]['methods'][method]=dict(component_evaluations=len(subset),max_absolute_error=float(np.max(np.abs(e))),RMS_error=float(np.sqrt(np.mean(e*e))),raw_condition2_min=min(conditions) if conditions else None,raw_condition2_max=max(conditions) if conditions else None)
    need(all(stat(q['path'])==q for q in consumed),'Consumed offline evidence changed')
    replay.old.write_csv(dest,rowsout)
    result=dict(stage=TAG,analysis_complete=True,physical_acceptance=False,whole_run_passed=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,selected_stencils=stencils,analytic_fields=list(NAMES),summary=summary,original_abs_det_limit=.001,error_or_condition_acceptance_gate_added=False,unsaved_failure_reproduced=False,CUDA_cell_traversal_PosCell_FMA_reproduced=False,formula_reused_from=str(Path(replay.__file__).resolve()),consumed=consumed,consumed_stats_unchanged=True,files=[stat(dest)])
    with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
