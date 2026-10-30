"""Offline small-strain stress/kinematic decomposition; no new physical gate or solver."""
import argparse
import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import sw_mode3_longwin_review_r1 as prior

w=prior.worker; TESTS=w.TESTS; TAG='sw_surface_strain_r1'; NOTE=TESTS/'notes'/(TAG+'.json'); PARTS=[256,512,768,1024]


def integrals(e,z,H):
    """Initial-coordinate quadratures, all anchored at u(0)=0; left/right are sensitivities, not rigorous bounds."""
    dz=np.diff(z); first=e[:,:1]*z[0]
    trap=np.concatenate([first,first+np.cumsum((e[:,:-1]+e[:,1:])*.5*dz,axis=1)],axis=1)
    edges=np.r_[0.,(z[:-1]+z[1:])*.5,H]; widths=np.diff(edges)
    cell=np.cumsum(e*widths,axis=1)-e*(edges[1:]-z)
    left=np.concatenate([first,first+np.cumsum(e[:,:-1]*dz,axis=1)],axis=1)
    right=np.concatenate([first,first+np.cumsum(e[:,1:]*dz,axis=1)],axis=1)
    return trap,cell,left,right


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); z=np.arange(4)*.01+.005; e=np.full((2,4),-.001)
    for x in integrals(e,z,.04):np.testing.assert_allclose(x,e*z,rtol=0,atol=1e-20)
    e=np.array([[1.,2.,-3.,4.]])*1e-5; a,b,lo,hi=integrals(e,z,.04)
    np.testing.assert_allclose(a,b,rtol=0,atol=1e-21); np.testing.assert_allclose(a,(lo+hi)/2,rtol=0,atol=1e-21)
    actual=np.array([[.01,.02,.03,.04]]); ref=np.zeros_like(actual); predicted=-1000*a
    np.testing.assert_allclose(actual-ref,(actual-predicted)+(predicted-ref),rtol=0,atol=1e-17)
    return dict(passed=True,files_written=False,native_reader_started=False,solver_started=False,live_data_read=False)


def figures(data,histories,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
    for label,color in [('coarse','tab:blue'),('half','tab:orange')]:
        a=data[(data.job==label)&(data.part==1024)]; h=histories[label]
        for key,style in [('actual_s_mm','-'),('stress_s_mm','--'),('H1_reference_s_mm',':')]:axes[0,0].plot(a[key],a.z0_m,style,color=color,label=label+' '+key)
        for key,style in [('actual_minus_ref_mm','-'),('actual_minus_stress_mm','--'),('stress_minus_ref_mm',':')]:axes[0,1].plot(a[key],a.z0_m,style,color=color,label=label+' '+key)
        for key,style in [('eps_xx','-'),('eps_yy','--'),('eps_zz',':')]:axes[1,0].plot(a[key]*1e6,a.z0_m,style,color=color,label=label+' '+key)
        for key,style in [('top_actual_minus_ref_mm','-'),('top_actual_minus_stress_mm','--'),('top_stress_minus_ref_mm',':'),('bottom_anchor_offset_mm','-.')]:axes[1,1].plot(h.time_s*1000,h[key],style,color=color,label=label+' '+key)
    for ax,title in zip(axes.flat,['Final actual / stress-integrated / reference increment','Final additive decomposition','Final stress-inferred normal strain [microstrain]','All saved times: top decomposition / bottom anchor offset']):ax.set_title(title);ax.grid(alpha=.25);ax.legend(fontsize=6)
    for ax in axes.flat[:3]:ax.set(ylabel='Initial material z [m]',xlabel='Settlement increment / decomposition [mm]' if ax!=axes[1,0] else 'Stress-inferred microstrain')
    axes[1,1].set(xlabel='Actual saved time [ms]',ylabel='Increment / difference [mm]')
    fig.suptitle('Offline small-strain compatibility diagnostic; fixed bottom anchor, no fitted shift or physical acceptance')
    with path.open('xb') as stream:fig.savefig(stream,format='png',dpi=180)
    plt.close(fig)


def review(tag):
    paths={k:TESTS/folder/(tag+suffix) for k,folder,suffix in [('check','logs','.check.json'),('csv','figures','.csv'),('png','figures','.png')]}
    assert not any(p.exists() for p in paths.values()),'Fresh analysis only; retained evidence is immutable'
    analysis_path=TESTS/'logs'/('sw_mode3_longwin_review_r1.check.json'); analysis=w.read(analysis_path); check=w.read(w.CHECK); run=w.read(check['run']['path']); prepared=w.read(run['prepared']['path'])
    assert analysis['analysis_checks_passed'] and check['passed'] and not check['held_jobs'] and run['jobs']==check['jobs'] and len(prepared['jobs'])==2
    records=[w.bound(p) for p in [__file__,NOTE,prior.__file__,w.__file__,w.old.__file__,w.CHECK,analysis_path]]+[check['run'],run['prepared']]+check['jobs']
    tables=[]; summaries={}; histories={}
    for job,rr in zip(prepared['jobs'],check['jobs']):
        r=w.read(rr['path']); done=w.read(r['sealed_completion']['path']); assert r['passed'] and not r['errors'] and done['solver_finished'] and done['exit_code']==0 and done['owned_exited'] and not done['surviving_owned']
        source=next(x for x in r['artifacts'] if Path(x['path']).name==job['name']+'_numeric_profiles.csv'); records += [r['sealed_completion'],job['config'],source]
        history_source=next(x for x in analysis['artifacts'] if Path(x['path']).name.endswith('_history.csv')); selected_source=next(x for x in analysis['artifacts'] if Path(x['path']).name.endswith('_selected_profiles.csv')); records += [history_source,selected_source]
        w.verify(records); raw=pd.read_csv(source['path'],float_precision='round_trip').sort_values(['part','layer']); assert len(raw)==102500 and not raw.duplicated(['part','layer']).any() and np.isfinite(raw.to_numpy(dtype='<f8')).all()
        z=raw.z0_m.iloc[:100].to_numpy(); t=np.array([x['time_s'] for x in r['rows']]); p=job['parameters']; shape=(1025,100); array=lambda k:raw[k].to_numpy().reshape(shape)
        assert np.array_equal(raw.part,np.repeat(np.arange(1025),100)) and np.array_equal(raw.layer,np.tile(np.arange(100),1025)) and np.array_equal(array('z0_m'),np.tile(z,(1025,1))) and np.array_equal(array('time_s'),np.repeat(t[:,None],100,axis=1))
        assert p==w.old.parameters(Path(job['config']['path']).read_text(encoding='utf8')); root=ET.parse(job['config']['path']); E=float(np.float32(root.find('.//ModulusE').get('value'))); nu=float(np.float32(root.find('.//PRvs').get('value')))
        stress={k:array('sigma_'+k) for k in ['xx','yy','zz']}; delta={k:v-v[:1] for k,v in stress.items()}; eps={k:(delta[k]-nu*sum(delta[j] for j in delta if j!=k))/E for k in delta}
        trap,cell,left,right=integrals(eps['zz'],z,p['H']); predicted=-1000*trap; actual=array('settlement_mm'); ref=prior.series(z,t,p,p['H']); reference=ref['settlement_increment_mm']
        eref=(ref['q_pa']-ref['q_pa'][:1])/p['M']; ref_integral=-1000*integrals(eref,z,p['H'])[0]; residual=actual-predicted; stress_bias=predicted-reference
        previous=pd.read_csv(history_source['path'],float_precision='round_trip'); previous=previous[previous.job.eq(job['name'])]; assert len(previous)==1025 and np.array_equal(previous.time_s,t) and np.array_equal(previous.top_settlement_mm,actual[:,-1]); np.testing.assert_allclose(previous.H1_finite_top_settlement_increment_mm,reference[:,-1],rtol=0,atol=1e-12)
        selected=pd.read_csv(selected_source['path'],float_precision='round_trip'); selected=selected[selected.job.eq(job['name'])&selected.part.isin(PARTS)]; assert np.array_equal(selected.settlement_mm,raw[raw.part.isin(PARTS)].settlement_mm)
        history=pd.DataFrame(dict(time_s=t,top_actual_minus_ref_mm=(actual-reference)[:,-1],top_actual_minus_stress_mm=residual[:,-1],top_stress_minus_ref_mm=stress_bias[:,-1],bottom_anchor_offset_mm=residual[:,0])); histories[job['suffix']]=history
        np.testing.assert_allclose(actual-reference,residual+stress_bias,rtol=0,atol=1e-12)
        data=dict(job=job['suffix'],part=np.repeat(np.arange(1025),100),time_s=np.repeat(t,100),layer=np.tile(np.arange(100),1025),z0_m=np.tile(z,1025))
        values=dict(actual_s_mm=actual,stress_s_mm=predicted,H1_reference_s_mm=reference,actual_minus_ref_mm=actual-reference,actual_minus_stress_mm=residual,stress_minus_ref_mm=stress_bias,
            stress_cell_s_mm=-1000*cell,stress_left_s_mm=-1000*left,stress_right_s_mm=-1000*right,bottom_anchor_offset_mm=np.repeat(residual[:,:1],100,axis=1),
            relative_actual_minus_stress_mm=residual-residual[:,:1],reference_quadrature_error_mm=ref_integral-reference,eps_xx=eps['xx'],eps_yy=eps['yy'],eps_zz=eps['zz'],H1_reference_eps_zz=eref)
        data.update({k:v.ravel() for k,v in values.items()}); table=pd.DataFrame(data); tables.append(table[table.part.isin(PARTS)].copy())
        weights=integrals(np.eye(100),z,p['H'])[0]; rel_weights=weights[:,-1]-weights[:,0]; edge_kin=-np.diff(actual,axis=1)/(1000*np.diff(z)); edge_sigma=(eps['zz'][:,1:]+eps['zz'][:,:-1])*.5
        snaps=[]
        for part in PARTS:
            contributions=-1000*(eps['zz'][part]-eref[part])*rel_weights
            snaps.append(dict(part=part,time_s=float(t[part]),top_actual_minus_ref_mm=float((actual-reference)[part,-1]),top_actual_minus_stress_mm=float(residual[part,-1]),top_stress_minus_ref_mm=float(stress_bias[part,-1]),
                bottom_anchor_offset_mm=float(residual[part,0]),relative_actual_minus_stress_mm=float(residual[part,-1]-residual[part,0]),relative_reference_quadrature_error_mm=float((ref_integral-reference)[part,-1]-(ref_integral-reference)[part,0]),
                strain_bias_relative_contributions_mm={label:float(contributions[mask].sum()) for label,mask in [('top1',np.arange(100)>=99),('top3',np.arange(100)>=97),('top10',np.arange(100)>=90),('bulk90',np.arange(100)<90)]},
                inferred_lateral_strain_rms={key:float(np.sqrt(np.mean(eps[key][part]**2))) for key in ['xx','yy']},edge_stress_vs_kinematic_strain_rms=float(np.sqrt(np.mean((edge_sigma[part]-edge_kin[part])**2)))))
        late=history[history.time_s>.0703125]; summaries[job['suffix']]=dict(E_float_pa=E,nu_float=nu,production_M_pa=p['M'],M_from_E_nu_pa=E*(1-nu)/((1+nu)*(1-2*nu)),snapshots=snaps,
            last_quarter_actual_start_s=float(late.time_s.iloc[0]),last_quarter_actual_end_s=float(late.time_s.iloc[-1]),last_quarter_samples=len(late),last_quarter_change_mm={k:float(late[k].iloc[-1]-late[k].iloc[0]) for k in late if k!='time_s'},
            trapezoid_vs_cell_max_mm=float(abs(predicted+1000*cell).max()),observed_spin_bound=r['hg']['spinbound'],adopted_native_checks=1025)
    records=w.unique(records); w.verify(records); data=pd.concat(tables,ignore_index=True); assert len(data)==800
    with paths['csv'].open('x',encoding='utf8',newline='') as stream:data.to_csv(stream,index=False,float_format='%.17g')
    figures(data,histories,paths['png']); w.verify(records)
    w.seal(paths['check'],dict(analysis_checks_passed=True,inputs=records,jobs=summaries,selected_parts=PARTS,profile_rows_used=205000,native_frames_redecoded=0,adopted_sealed_native_frames=2050,
        definition='Stress-inferred small-strain increments from initial material stress; fixed initial-coordinate integration anchored u(0)=0. actual-ref=(actual-stress_integral)+(stress_integral-ref). Bottom offset remains explicit,not fitted away.',
        quadrature='Constant eps0 over [0,z0],then trapezoid at material centers. Fixed-cell constant integration uses edges0,midpoints,H;uniform cell-centered weights coincide. Left/right center-step alternatives are sensitivity,not rigorous continuum bounds.',
        regional_scope='Top1/top3/top10 overlap;only top10+bulk90 form a partition. Contributions refer to top-minus-bottom stress-strain bias;analytic-reference quadrature error and kinematic residual are separate.',
        limitations='Layer means and linear elastic compliance,not actual production SPH gradient replay. Small strain/material coordinates;Jaumann rotation is not inverted,reported tiny spin only. Stress-inferred lateral strain is diagnostic,not direct particle-x strain. H1 quasi-static reference is not dynamic truth;no baseline/height/time change.',
        physical_acceptance=False,new_physical_gate=False,automatic_full_run_admitted=False,solver_started=False,native_reader_started=False,figures_require_visual_review=True,artifacts=[w.bound(paths[k]) for k in ['csv','png']]))
    return dict(analysis_checks_passed=True,check=str(paths['check']),physical_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(); modes.add_argument('--selftest',action='store_true'); modes.add_argument('--review',action='store_true'); parser.add_argument('--tag',default=TAG)
    args=parser.parse_args(); assert args.tag and Path(args.tag).name==args.tag and args.tag.replace('_','').isalnum()
    if args.selftest:print(json.dumps(selftest()))
    elif args.review:print(json.dumps(review(args.tag)))
    else:parser.print_help()
