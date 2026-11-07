"""Saved-state NoSlip stress decomposition, not a CUDA substage replay or a new wall law."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import csv,json,math,time,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import upl_c08_wall_geometry_r1 as g

T=Path(__file__).resolve().parents[1];TAG='upl_c08_wall_stress_decompose_r1'
CSV=T/'figures'/(TAG+'.csv');CHECK=T/'logs'/(TAG+'.check.json')
DATA={'OFF':T/'outputs/upl_c08_as_short_r1_off_native','ASon':T/'outputs/upl_c08_as_on_partial_r1'}
WALLS=(783,787);COMPONENTS=('xx','yy','zz','xy','yz','xz')
OFFCHECK=T/'logs/upl_c08_as_short_r1_off.native.check.json';ONCHECK=T/'logs/upl_c08_as_on_partial_r1.check.json'
GEOMETRY=T/'figures/upl_c08_wall_geometry_r1.check.json'
# Six independent affine fields; same observed geometry/volumes, no fitted reference data.
AFFINE_A=np.array([1024.,-2048.,4096.,128.,-256.,512.])
AFFINE_X=np.array([16.,32.,-64.,8.,-4.,2.]);AFFINE_Z=np.array([-32.,16.,128.,-2.,8.,-4.])

def stress(frame):
    # Native double ij is xy,yz,xz (JSphCpu::GetParticlesData), not xy,xz,yz.
    return np.column_stack((frame['SigmaState_kk'],frame['SigmaState_ij']))

def active_at_b(tree,soil,b):
    ix=sorted(tree.query_ball_point(b,g.SEARCH));d=b-soil[ix];rr=np.sum(d*d,axis=1);df=d.astype(np.float32)
    rf=np.float32(df[:,0]*df[:,0]+df[:,1]*df[:,1]);rc=rr.astype(np.float32)
    return bool(np.any(((rr<=g.R2)&(rr>=g.LOWER))|((rf<=g.R2)&(rf>=g.LOWER))|((rc<=g.R2)&(rc>=g.LOWER))))

def fit(tree,soil,js,ids,field,centre,b):
    ix=[i for i in sorted(tree.query_ball_point(centre,g.SEARCH)) if np.float32(np.dot(centre-soil[i],centre-soil[i]))<=g.R2]
    m=np.zeros((3,3));rhs=np.zeros((3,6));affrhs=np.zeros((3,6));sumw=sub=0.;near=None;dist=math.inf;ties=0;positive=0
    for i in ix:
        d=centre-soil[i];rr=float(np.dot(d,d));w0,fac=g.cubic(rr);vol=g.VOL0*float(js[i]);row=vol*np.array([w0,fac*d[0],fac*d[1]])
        m+=np.outer(row,np.r_[1.,d]);rhs+=np.outer(row,field[i]);sumw+=row[0];sub-=vol*float(np.dot(d,fac*d));positive+=w0>0
        affine=AFFINE_A+AFFINE_X*soil[i,0]+AFFINE_Z*soil[i,1];affrhs+=np.outer(row,affine)
        if rr<dist:dist,near,ties=rr,i,1
        elif rr==dist:ties+=1
    det=g.det3(m);scaled=np.diag([1,float(g.H),float(g.H)])@m@np.diag([1,1/float(g.H),1/float(g.H)])
    good=bool(sumw>0 and (sub>0 or sumw>=0) and math.isfinite(det) and abs(det)>=1e-3)
    r=dict(nodes=len(ix),positive_W_nodes=int(positive),det=det,cond_inf=float(np.linalg.cond(m,np.inf)),cond_hscaled_inf=float(np.linalg.cond(scaled,np.inf)),geometry_gate=good,
           nearest_id=int(ids[near]) if near is not None else None,nearest_ties=ties,centre_x=float(centre[0]),centre_z=float(centre[1]),nearest_distance_m=math.sqrt(dist) if near is not None else None)
    if not good:return r,near
    q=np.linalg.solve(m,rhs);gradient=-q[1:];nearfield=field[near];mls_at_b=q[0]+(b-centre)@gradient
    residual=nearfield-(q[0]+(soil[near]-centre)@gradient);distance_term=(b-soil[near])@gradient;anchored=nearfield+distance_term
    qa=np.linalg.solve(m,affrhs);ag=-qa[1:];truth=AFFINE_A+AFFINE_X*b[0]+AFFINE_Z*b[1]
    affine_mls=qa[0]+(b-centre)@ag;affine_anchor=AFFINE_A+AFFINE_X*soil[near,0]+AFFINE_Z*soil[near,1]+(b-soil[near])@ag
    scale=max(1.,float(np.max(np.abs(AFFINE_A+soil[ix,0,None]*AFFINE_X+soil[ix,1,None]*AFFINE_Z))))
    budget=32768*np.finfo(float).eps*max(1.,r['cond_hscaled_inf'])*scale
    r.update(q0=q[0],gradient=gradient,nearest_sigma=nearfield,MLS_at_B=mls_at_b,anchor_residual=residual,gradient_distance=distance_term,anchored_at_B=anchored,
             neighbor_min=field[ix].min(axis=0),neighbor_max=field[ix].max(axis=0),affine_mls_error=np.abs(affine_mls-truth),affine_anchor_error=np.abs(affine_anchor-truth),affine_budget=budget,
             decomposition_error=float(np.max(np.abs(anchored-(mls_at_b+residual)))))
    return r,near

def main():
    g.need(not CSV.exists() and not CHECK.exists(),'Fresh derived output paths required')
    provenance=json.loads(GEOMETRY.read_text(encoding='utf-8'));g.need(provenance['passed'] is True,'Closed geometry analysis required')
    normals=Path(provenance['source_stats'][-1]['path']);xml=normals.parent/'CaseLianSaturatedColumnCollapse_psi0_shared_r3.xml'
    g.need(ET.parse(xml).getroot().find(".//mdbcslip/bound[@mkbound='1']").attrib['slipmode']=='2','Actual bottom must be NoSlip')
    before=[g.stat(__file__),g.stat(T/'support/upl_c08_wall_geometry_r1.py'),g.stat(T/'support/upl_c08_fsmask_r1.py'),g.stat(GEOMETRY),g.stat(OFFCHECK),g.stat(ONCHECK),g.stat(xml)]
    g.need(json.loads(OFFCHECK.read_text(encoding='utf-8'))['passed'] is True and json.loads(ONCHECK.read_text(encoding='utf-8'))['passed'] is True,'Both actual partial native checks required')
    rows=[];summary=[];started=time.perf_counter();clock_reference=None
    for dataset,native in DATA.items():
        raw,clocks,b,normal,mk,bindings=g.load(native,normals);before+=bindings;done=json.loads((native/'completion.json').read_text(encoding='utf-8'));release=done['source_actual_time_s']
        actualtimes=np.array(raw['time']);g.need(clock_reference is None or np.array_equal(actualtimes,clock_reference),'Datasets have different actual saved clocks');clock_reference=actualtimes
        g.need(all(mk[i]==11 and normal[i,0]==0 and normal[i,1]>0 for i in WALLS),'Selected IDs must be actual bottom samples')
        for part,frame in enumerate(raw):
            soil=np.asarray(frame['Posd'][1800:][:,[0,2]]);js=np.asarray(frame['PoroVolumeRatio'][1800:]);ids=np.asarray(frame['Idp'][1800:]);sigma=stress(frame);field=sigma[1800:];tree=cKDTree(soil)
            for wall in WALLS:
                B=b[wall];GP=B+normal[wall];active=active_at_b(tree,soil,B);primary,nearest=fit(tree,soil,js,ids,field,GP,B)
                alternative,unused=fit(tree,soil,js,ids,field,soil[nearest],B) if nearest is not None else (primary,None)
                retried=bool(not primary['geometry_gate'] and nearest is not None and np.any(GP-soil[nearest]!=0))
                current=alternative if retried else primary;path=('retry' if retried else 'primary') if active else 'OFF_not_applied'
                for name,f in (('retained_geometry_rule',current),('nearest_source_center',alternative)):
                    shared=dict(dataset=dataset,part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,wall_id=wall,mk=int(mk[wall]),B_x=float(B[0]),B_z=float(B[1]),GP_x=float(GP[0]),GP_z=float(GP[1]),B_active_proxy=active,production_path_proxy=path,fit=name,
                                primary_nodes=primary['nodes'],primary_det=primary['det'],primary_cond_hscaled=primary['cond_hscaled_inf'])
                    shared.update({k:v for k,v in f.items() if not isinstance(v,np.ndarray) and k not in ('affine_budget','decomposition_error')})
                    for c,component in enumerate(COMPONENTS):
                        r={**shared,'component':component,'saved_sigma_B_Pa':float(sigma[wall,c])}
                        for key in ('q0','nearest_sigma','MLS_at_B','anchor_residual','gradient_distance','anchored_at_B','neighbor_min','neighbor_max','affine_mls_error','affine_anchor_error'):r[key+'_Pa']=float(f[key][c]) if f['geometry_gate'] else None
                        r.update(physical_gradient_x_Pa_m=float(f['gradient'][0,c]) if f['geometry_gate'] else None,physical_gradient_z_Pa_m=float(f['gradient'][1,c]) if f['geometry_gate'] else None,
                                 anchored_minus_saved_Pa=float(f['anchored_at_B'][c]-sigma[wall,c]) if f['geometry_gate'] else None,affine_budget_Pa=f.get('affine_budget'),decomposition_identity_error_Pa=f.get('decomposition_error'))
                        rows.append(r)
                entry=dict(dataset=dataset,part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,wall_id=wall,B_active_proxy=active,production_path_proxy=path,saved_sigma_B_Pa=sigma[wall].tolist())
                for name,f in (('current',current),('nearest_center',alternative)):
                    entry[name]={k:f[k] for k in ('nodes','positive_W_nodes','det','cond_hscaled_inf','geometry_gate','nearest_id','nearest_ties')}
                    if f['geometry_gate']:entry[name].update(MLS_at_B_Pa=f['MLS_at_B'].tolist(),anchor_residual_Pa=f['anchor_residual'].tolist(),gradient_distance_Pa=f['gradient_distance'].tolist(),anchored_at_B_Pa=f['anchored_at_B'].tolist(),max_saved_gap_Pa=float(np.max(np.abs(f['anchored_at_B']-sigma[wall]))),max_affine_error_Pa=float(max(f['affine_mls_error'].max(),f['affine_anchor_error'].max())),affine_budget_Pa=f['affine_budget'])
                summary.append(entry)
    g.need(len(rows)==528 and len(summary)==44,'Incomplete dataset/frame/wall/component coverage')
    with CSV.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    g.need(all(g.stat(e['path'])==e for e in before),'Consumed saved inputs changed')
    selected=[s for s in summary if s['part'] in (4,7)]
    result=dict(stage=TAG,passed=True,rows=len(rows),frames_each=11,wall_ids=list(WALLS),selected_0p05_0p08=selected,all_saved_summaries=summary,consumed=before,outputs=[g.stat(CSV)],elapsed_s=time.perf_counter()-started,
                source_stress_order='xx,yy,zz,xy,yz,xz',kernel_scope='same cubic float32 pattern and float radius as existing geometry audit; double sums in native-ID order',
                current_rule_is_geometry_proxy=True,saved_wall_values_are_actual_native_B=True,reconstructed_from_saved_soil_not_unsaved_substage=True,GPU_cell_order_and_FMA_replayed=False,
                nearest_center_is_counterfactual=True,nearest_stencil_search_count_per_wall_frame=1,original_evaluation_B_and_GP_unchanged=True,affine_checks_are_algebra_not_physical_acceptance=True,
                solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,original_data_modified=False,physical_acceptance=False)
    with CHECK.open('x',encoding='utf-8') as f:json.dump(g.clean(result),f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(g.clean(dict(check=str(CHECK),rows=len(rows),selected_0p05_0p08=selected)),allow_nan=False))

if __name__=='__main__':main()
