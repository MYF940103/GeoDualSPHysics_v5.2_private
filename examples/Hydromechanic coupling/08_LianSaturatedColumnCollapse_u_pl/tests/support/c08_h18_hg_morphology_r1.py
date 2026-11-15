"""One CSV-only PRE-neighborhood affine/nonaffine shape diagnostic; no native/API."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import MaxNLocator

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_hg_morphology_r1'
SCRIPT, NOTE = Path(__file__).resolve(), T/'notes'/(TAG+'.md')
FIG, CHECK = T/'figures', T/'logs'/(TAG+'.check.json')
PHYSICAL = T/'logs/c08_h18_hg_cached_physical_r1.check.json'
SPATIAL = FIG/'c08_h18_hg_cached_physical_r1_spatial.csv'
COHORT = FIG/'c08_h18_hg_cached_physical_r1_cohorts.csv'
CASES, PARTS, DP, H = ('Retained HG0', 'Cached HG xi0.1'), (38, 76, 90), .04, float(np.float32(.072))


def need(ok, message):
    if not ok: raise RuntimeError(message)


def stat(path):
    p = Path(path); s = p.stat(); return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def load(path):
    with Path(path).open(encoding='utf-8-sig') as f: return json.load(f)


def table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))


def write(path, rows):
    need(rows, 'No empty diagnostic table')
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def inputs():
    q = load(PHYSICAL); need(q['passed'] and q['analysis_complete'] and q['consumed_stats_unchanged'], 'Passed original physical analysis required')
    consumed = [stat(p) for p in (SCRIPT, NOTE, PHYSICAL)]
    for p in (SPATIAL, COHORT):
        e = [r for r in q['files'] if Path(r['path']).resolve() == p.resolve()]
        need(len(e) == 1 and stat(p) == e[0], 'Original CSV seal differs: '+p.name); consumed.append(e[0])
    source, body = table(COHORT), table(SPATIAL)
    need(len(source) == 5000 and len(body) == 30000, 'Exactly5000 PRE records/30000 selected material records required')
    source.sort(key=lambda r:int(r['native_id'])); ids = np.array([int(r['native_id']) for r in source])
    need(np.array_equal(ids, np.arange(2060,7060)), 'All original5000 material IDs required')
    X = np.array([[float(r['PRE_x_m']),float(r['PRE_z_m'])] for r in source])
    need(np.isfinite(X).all() and all(float(r['PRE_y_m'])==0 for r in source), 'Finite actual2D PRE reference required')
    frames = {}
    for case in CASES:
        for part in PARTS:
            rows = sorted((r for r in body if r['case']==case and int(r['part'])==part), key=lambda r:int(r['native_id']))
            need(len(rows)==5000 and np.array_equal([int(r['native_id']) for r in rows],ids), 'Every selected case/time must retain all5000 IDs')
            need(len({r['actual_time_s'] for r in rows})==len({r['tau_s'] for r in rows})==1, 'One genuine time per saved frame required')
            frames[(case,part)] = rows
    for part in PARTS:
        a,b = [frames[(case,part)][0] for case in CASES]
        need(a['actual_time_s']==b['actual_time_s'] and a['tau_s']==b['tau_s'], 'Actual matched CSV times differ')
    return consumed, ids, X, frames


def reference(X):
    graph = cKDTree(X).query_ball_point(X, 2*H); result=[]
    for i, raw in enumerate(graph):
        js = np.array(sorted(j for j in raw if j!=i), dtype=int)
        d = X[js]-X[i]; r = np.linalg.norm(d,axis=1); keep=(r>0)&(r<2*H); js,d,r=js[keep],d[keep],r[keep]
        q=r/H; w=(1-.5*q)**4*(1+2*q); M=(d*w[:,None]).T@d
        eig=np.linalg.eigvalsh(M); rankok=bool(np.isfinite(M).all() and len(js)>=2 and eig[0]>0)
        result.append(dict(js=js,d=d,r=r,w=w,M=M,rankok=rankok,cond=float(eig[-1]/eig[0]) if rankok else None))
    return result


def evaluate(case,part,rows,ids,X,graph):
    x=np.array([[float(r['x_m']),float(r['z_m'])] for r in rows]); Fs=np.full((5000,2,2),np.nan); D=np.full(5000,np.nan)
    singular=np.full((5000,2),np.nan); determinants=np.full(5000,np.nan); records=[]
    need(np.isfinite(x).all() and all(float(r['y_m'])==0 for r in rows), 'Finite actual2D current positions required')
    for i,g in enumerate(graph):
        if g['rankok']:
            dx=x[g['js']]-x[i]; N=(dx*g['w'][:,None]).T@g['d']; F=np.linalg.solve(g['M'],N.T).T
            residual=dx-g['d']@F.T; d2=float(np.sum(g['w']*np.sum(residual*residual,axis=1))/np.sum(g['w']))
            need(np.isfinite(F).all() and math.isfinite(d2) and d2>=0,'Finite fit/residual required; no invalid record may be dropped')
            Fs[i]=F; D[i]=math.sqrt(d2)/DP; singular[i]=np.linalg.svd(F,compute_uv=False); determinants[i]=np.linalg.det(F)
    for i,row in enumerate(rows):
        g=graph[i]; j=int(row['nearest_material_id'])-2060; need(0<=j<5000 and j!=i,'Real nonself nearest material ID required')
        dX=X[j]-X[i]; actual=x[j]-x[i]; r0=float(np.linalg.norm(dX)); actualnorm=float(np.linalg.norm(actual)); inref=bool(j in g['js'])
        need(abs(actualnorm/DP-float(row['NN_over_dp']))<=2e-13,'Actual CSV nearest pair distance differs from its original NN')
        valid=bool(g['rankok']); both=bool(valid and graph[j]['rankok'])
        pi=Fs[i]@dX if valid else None; ps=.5*(Fs[i]+Fs[j])@dX if both else None
        out=dict(case=case,part=part,actual_time_s=float(row['actual_time_s']),tau_s=float(row['tau_s']),native_id=int(ids[i]),
            x_m=float(x[i,0]),z_m=float(x[i,1]),reference_neighbor_count=len(g['js']),reference_condition=g['cond'],fit_status='full_rank' if valid else 'invalid_reference_rank',
            Fxx=float(Fs[i,0,0]) if valid else None,Fxz=float(Fs[i,0,1]) if valid else None,Fzx=float(Fs[i,1,0]) if valid else None,Fzz=float(Fs[i,1,1]) if valid else None,
            detF_PRE_to_current=float(determinants[i]) if valid else None,singular_max=float(singular[i,0]) if valid else None,singular_min=float(singular[i,1]) if valid else None,
            weighted_Dmin2_m2=float((D[i]*DP)**2) if valid else None,weighted_Dmin_RMS_over_dp=float(D[i]) if valid else None,
            native_J=float(row['J']),native_J_over_Jpre=None,Jpre_available=False,kappa=float(row['kappa']),p_Pa=float(row['p_Pa']),
            actual_NN_over_dp=actualnorm/DP,nearest_material_id=int(ids[j]),nearest_PRE_distance_over_dp=r0/DP,nearest_is_reference_neighbor=inref,
            nearest_reference_rank_within_2H=int(1+np.count_nonzero(g['r']<r0)) if inref else None,
            nearest_Fi_prediction_over_dp=float(np.linalg.norm(pi)/DP) if valid else None,
            nearest_Favg_prediction_over_dp=float(np.linalg.norm(ps)/DP) if both else None,
            nearest_Fi_vector_residual_over_dp=float(np.linalg.norm(actual-pi)/DP) if valid else None,
            nearest_Favg_vector_residual_over_dp=float(np.linalg.norm(actual-ps)/DP) if both else None)
        need(all(math.isfinite(v) for v in out.values() if isinstance(v,float)), 'No nonfinite geometric output may be removed')
        records.append(out)
    close=cKDTree(x).query_pairs(.5*DP,output_type='ndarray')
    close=close[np.linalg.norm(x[close[:,0]]-x[close[:,1]],axis=1)<.5*DP] if len(close) else close
    closest=min(records,key=lambda r:r['actual_NN_over_dp']); watch={tuple(sorted((int(ids[a]),int(ids[b])))) for a,b in close}
    watch.add(tuple(sorted((closest['native_id'],closest['nearest_material_id'])))); watch.add((6817,6866))
    return records,dict(x=x,F=Fs,D=D,det=determinants,rows=rows,close=close),watch


def summarize(records):
    summary=[]
    for case in CASES:
        for part in PARTS:
            frame=[r for r in records if r['case']==case and r['part']==part]
            for cohort in ('all','actual_NN_lt_0p5dp'):
                selected=frame if cohort=='all' else [r for r in frame if r['actual_NN_over_dp']<.5]
                out=dict(case=case,part=part,actual_time_s=frame[0]['actual_time_s'],tau_s=frame[0]['tau_s'],cohort=cohort,count=len(selected),
                    invalid_reference_rank_nodes=sum(r['fit_status']!='full_rank' for r in selected),
                    nearest_not_reference_neighbors=sum(not r['nearest_is_reference_neighbor'] for r in selected),
                    negative_geometric_detF_nodes=sum(r['detF_PRE_to_current'] is not None and r['detF_PRE_to_current']<0 for r in selected))
                for key in ('actual_NN_over_dp','nearest_PRE_distance_over_dp','weighted_Dmin_RMS_over_dp','detF_PRE_to_current','native_J',
                    'singular_max','singular_min','nearest_Favg_prediction_over_dp','nearest_Favg_vector_residual_over_dp'):
                    a=np.array([r[key] for r in selected if r[key] is not None])
                    for suffix,v in (('min',a.min() if len(a) else None),('q05',np.quantile(a,.05) if len(a) else None),
                        ('q50',np.quantile(a,.5) if len(a) else None),('q95',np.quantile(a,.95) if len(a) else None),('max',a.max() if len(a) else None)):
                        out[key+'_'+suffix]=float(v) if v is not None else None
                summary.append(out)
    return summary


def pair_history(watch,frames,ids,X):
    result=[]
    for a,b in sorted(watch):
        i,j=a-2060,b-2060; dX=X[j]-X[i]
        for case in CASES:
            for part in PARTS:
                d=frames[(case,part)]; actual=d['x'][j]-d['x'][i]; pi=d['F'][i]@dX; pj=d['F'][j]@dX; ps=.5*(pi+pj)
                valid=bool(np.isfinite(ps).all()); actualnorm=float(np.linalg.norm(actual))
                result.append(dict(case=case,part=part,actual_time_s=float(d['rows'][0]['actual_time_s']),tau_s=float(d['rows'][0]['tau_s']),
                    material_i=a,material_j=b,PRE_distance_over_dp=float(np.linalg.norm(dX)/DP),PRE_pair_within_2H=bool(np.linalg.norm(dX)<2*H),
                    actual_distance_over_dp=actualnorm/DP,actual_pair_lt_0p5dp=bool(actualnorm<.5*DP),
                    Fi_predicted_distance_over_dp=float(np.linalg.norm(pi)/DP) if valid else None,
                    Fj_predicted_distance_over_dp=float(np.linalg.norm(pj)/DP) if valid else None,
                    Favg_predicted_distance_over_dp=float(np.linalg.norm(ps)/DP) if valid else None,
                    Favg_vector_residual_over_dp=float(np.linalg.norm(actual-ps)/DP) if valid else None,
                    i_Dmin_RMS_over_dp=float(d['D'][i]) if math.isfinite(d['D'][i]) else None,
                    j_Dmin_RMS_over_dp=float(d['D'][j]) if math.isfinite(d['D'][j]) else None,
                    i_native_J=float(d['rows'][i]['J']),j_native_J=float(d['rows'][j]['J']),
                    i_detF=float(d['det'][i]) if math.isfinite(d['det'][i]) else None,j_detF=float(d['det'][j]) if math.isfinite(d['det'][j]) else None))
    return result


def picture(frames,path):
    values=np.concatenate([d['D'][np.isfinite(d['D'])] for d in frames.values()]); need(len(values)>0,'At least one valid reference fit required')
    transformed=np.log1p(values); norm=Normalize(float(transformed.min()),float(transformed.max()))
    pos=np.concatenate([d['x'] for d in frames.values()]); fig,axes=plt.subplots(2,3,figsize=(17,9),layout='constrained')
    for row,case in enumerate(CASES):
        for col,part in enumerate(PARTS):
            d=frames[(case,part)]; ax=axes[row,col]; valid=np.isfinite(d['D'])
            sc=ax.scatter(d['x'][valid,0],d['x'][valid,1],c=np.log1p(d['D'][valid]),s=4,cmap='viridis',norm=norm,rasterized=True)
            if (~valid).any(): ax.scatter(d['x'][~valid,0],d['x'][~valid,1],c='red',s=10,marker='x')
            for i,j in d['close']: ax.plot(d['x'][[i,j],0],d['x'][[i,j],1],color='red',lw=.7)
            ax.set_aspect('equal'); ax.set_xlim(min(0,float(pos[:,0].min()))-DP,float(pos[:,0].max())+DP); ax.set_ylim(min(0,float(pos[:,1].min()))-DP,float(pos[:,1].max())+DP)
            ax.set_title(case+' / P'+str(part)+'\nactual tau='+format(float(d['rows'][0]['tau_s']),'.9g')+' s'); ax.set_xlabel('x [m]');ax.set_ylabel('z [m]')
            ax.xaxis.set_major_locator(MaxNLocator(nbins=6));ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    fig.colorbar(sc,ax=axes.ravel().tolist(),label='log(1 + fixed-PRE weighted nonaffine RMS / dp)',shrink=.86,pad=.025)
    fig.suptitle('Same fixed PRE2H neighbors, all5000 material points each\nRed links: actual pairs <0.5dp, descriptive; geometric detF is not native J',fontsize=13)
    fig.savefig(path,dpi=160);plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');need(p.parse_args().execution_authorized,'Explicit one-time offline authorization required')
    out=[FIG/(TAG+s) for s in ('_nodes.csv','_pairs.csv','_summary.csv','_nonaffinity.png')]
    need(not CHECK.exists() and all(not q.exists() for q in out),'Existing complete/partial diagnostic is protected')
    consumed=[]
    try:
        consumed,ids,X,source=inputs();graph=reference(X); records=[];frames={};watch=set()
        for case in CASES:
            for part in PARTS:
                r,d,w=evaluate(case,part,source[(case,part)],ids,X,graph);records.extend(r);frames[(case,part)]=d;watch.update(w)
        need(len(records)==30000,'All six5000-point frames must remain');pairs=pair_history(watch,frames,ids,X);summary=summarize(records)
        need(all(stat(q['path'])==q for q in consumed),'Consumed CSV/stat changed')
        for path,rows in zip(out[:3],(records,pairs,summary)):write(path,rows)
        picture(frames,out[3]);need(all(stat(q['path'])==q for q in consumed),'Consumed CSV/stat changed after plotting')
        q=dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,selected_frames=6,material_IDs_each=5000,node_rows=30000,
            watched_unique_pairs=len(watch),pair_rows=len(pairs),summary_rows=len(summary),reference_radius_m=2*H,weight='Wendland (1-q/2)^4*(1+2q)',
            fixed_reference='actual PRE Xz',rank_invalid_nodes=sum(r['fit_status']!='full_rank' for r in records),Jpre_available=False,
            geometric_detF_is_native_J=False,close_pairs_are_physical_failure_gate=False,Dmin_is_causal_tensile_proof=False,
            no_fitted_parameter=True,no_particle_rows_removed=True,CSV_only=True,reader_invocations=0,solver_invocations=0,SHA_scans=0,
            visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(x) for x in out])
        with CHECK.open('x',encoding='utf-8') as f:json.dump(q,f,ensure_ascii=False,indent=2)
    except Exception as e:
        if not CHECK.exists():
            with CHECK.open('x',encoding='utf-8') as f:json.dump(dict(stage=TAG,passed=False,first_failure=str(e),consumed=consumed,partial_outputs_preserved=True,solver_invocations=0,reader_invocations=0),f,indent=2)
        raise


if __name__=='__main__':main()
