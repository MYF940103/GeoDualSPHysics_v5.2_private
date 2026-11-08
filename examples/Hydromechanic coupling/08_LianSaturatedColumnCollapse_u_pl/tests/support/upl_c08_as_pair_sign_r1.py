"""Read at most four sealed native records; inspect close soil-pair stress/AS signs only."""
import argparse,csv,json,struct
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_as_pair_sign_r1';PREFIX=T/'figures'/TAG;CHECK=L/(TAG+'.check.json')
N=6805;FRAMES=66;DP=.04;HDP=1.2;EPSILON=.2
SPECS=(('baseline',2.55,'upl_c08_stage_trace_window_GPU_r1','native','upl_c08_clustering_r1_history.csv','epsilon0p2_full_r5'),('n3',3.,'upl_c08_asn3_window_GPU_r1','native_r1','upl_c08_asn3_compare_r1_cohorts.csv','epsilon0p2_exponent3'))
def need(ok,message):
    if not ok:raise ValueError(message)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def table(p):
    with Path(p).open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(e):need(stat(e['path'])==e,'Closed input changed: '+e['path']);return e
def entry(receipt,path):return bind(next(e for e in receipt if Path(e['path']).resolve()==path.resolve()))
def write(path,rows):
    with path.open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def cubic(q):return 1.-1.5*q*q+.75*q*q*q if q<=1. else .25*(2.-q)**3 if q<2. else 0.
def tensor(frame,slots):
    d=frame['SigmaState_kk'][slots];s=frame['SigmaState_ij'][slots];a=np.zeros((len(slots),3,3));a[:,range(3),range(3)]=d-frame['PorePress'][slots]
    a[:,0,1]=a[:,1,0]=s[:,0];a[:,1,2]=a[:,2,1]=s[:,1];a[:,0,2]=a[:,2,0]=s[:,2];return a
def sign(value,resolution):return 'near_zero_unresolved' if abs(value)<=resolution else 'attractive_shadow' if value>0. else 'repulsive_shadow'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline execution required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial derived outputs protected')
    cc=L/'upl_c08_clustering_plot_r2.check.json';ac=L/'upl_c08_asn3_compare_r1.check.json';pc=L/'upl_c08_stage_trace_window_GPU_r1.prefix_r1.check.json';cluster,compare,prefix=read(cc),read(ac),read(pc)
    need(cluster['passed'] and cluster['current_source_bindings_revalidated'] and compare['passed'] and compare['analysis_completed'] and compare['actual_common_frames']==66 and prefix['passed'],'Closed clustering/66-state comparison/retained prefix required')
    before=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),cc,ac,pc)];pairs=[];summaries=[];records_read=0;run_bindings=[]
    for label,exponent,job,folder,csvleaf,group in SPECS:
        native=T/'outputs'/job/folder;npth=L/(job+'.native_r1.json');rp=L/(job+'.run.json');nr,run=read(npth),read(rp)
        need(nr['passed'] and nr['original_native_guards_passed'] and nr['consumed_stats_unchanged'] and run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0,'Original run/native guards required')
        before.extend([stat(npth),stat(rp),bind(nr['completion'])]);need(Path(nr['completion']['path']).resolve()==native/'completion.json','Native completion binding differs');done=read(native/'completion.json')
        need(done['passed'] and done['samples']==FRAMES and done['actual_native_IDs_per_frame']==N and done['typed_arrays']==22 and done['soil_IDs']==5000,'Literal 66/6805/22/5000 scope required')
        run_bindings.append({k:bind(run[k]) for k in ('program','source_pre_file')});before.extend(run_bindings[-1].values())
        cp=T/'figures'/csvleaf;before.append(entry(cluster['files'] if label=='baseline' else compare['files'],cp));rows=[r for r in table(cp) if r['group']==group and r['cohort']=='all_soil' and int(r['part'])<FRAMES]
        need(len(rows)==FRAMES and {int(r['part']) for r in rows}==set(range(FRAMES)) and all(int(r['soil_count'])==5000 for r in rows),'Exact all-soil common window required')
        minimum=min(rows,key=lambda r:(float(r['rNN_over_dp_min']),int(r['part'])));last=max(rows,key=lambda r:float(r['time_s']));need(int(last['part'])==65 and abs(float(last['tau_s'])-.66)<1e-8,'Actual final .66 state differs')
        selected={}
        for reason,r in [('window_min_NN',minimum),('tau_0p66',last)]:selected.setdefault(int(r['part']),dict(row=r,reasons=[]))['reasons'].append(reason)
        for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):before.append(entry(nr['outputs'],native/leaf))
        layout=table(native/'typed22_layout.csv');need(len(layout)==22,'Original 22-array layout required');fields=[('time','<f8')]
        for q in layout:fields.append((q['array'],{'uint32':'<u4','float32':'<f4','float64':'<f8'}[q['type']],(N,int(q['components']))))
        dtype=np.dtype(fields);need(dtype.itemsize==8+212*N,'Literal native frame stride differs');clocks=table(native/'clocks.csv');need(len(clocks)==FRAMES,'Actual66 clocks required')
        with (native/'typed22.bin').open('rb') as f:
            need(struct.unpack('<III',f.read(12))==(N,22,FRAMES),'Actual native header differs; no rewrite')
            for part,selection in sorted(selected.items()):
                f.seek(12+part*dtype.itemsize);a=np.fromfile(f,dtype=dtype,count=1);need(len(a)==1,'Selected native record incomplete');a=a[0];records_read+=1;r=selection['row'];clock=clocks[part]
                need(float(a['time'])==float(r['time_s'])==float(clock['time_s']) and int(r['completed_step'])==int(clock['completed_step']),'Selected actual time/step differs')
                ids=a['Idp'][:,0];slots=np.flatnonzero(ids>=2060);need(np.array_equal(ids[slots],np.arange(2060,7060)),'All original5000 soil IDs required');x=a['Posd'][slots];need(np.all(x[:,1]==0.),'Literal2D geometry required')
                close=cKDTree(x[:,(0,2)]).query_pairs(.7*DP,output_type='ndarray');dist=np.linalg.norm(x[close[:,0]]-x[close[:,1]],axis=1);keep=dist<.7*DP;close,dist=close[keep],dist[keep]
                need(len(close)>0 and np.all(dist>0.),'No close pair or coincident points: line-of-centers diagnosis undefined')
                need(len(close)==int(r['pair_both_in_cohort_lt_0p7dp']) and abs(float(dist.min()/DP)-float(r['rNN_over_dp_min']))<=64*np.finfo(float).eps,'Selected native close pairs do not reproduce retained geometry CSV')
                tensors=tensor(a,slots);need(np.all(np.isfinite(tensors)),'Finite sealed total stress required');eig,Q=np.linalg.eigh(tensors);positive=(Q*np.maximum(eig,0.)[:,None,:])@Q.transpose(0,2,1);frame_rows=[]
                for ij,distance in sorted(zip(close,dist),key=lambda item:(float(item[1]),int(ids[slots[item[0][0]]]),int(ids[slots[item[0][1]]]))):
                    i,j=map(int,ij);si,sj=slots[i],slots[j];direction=(x[i]-x[j])/distance;s=float(distance/DP);ratio=cubic(s/HDP)/cubic(1./HDP);F=EPSILON*ratio**exponent
                    raw=float(direction@(tensors[i]+tensors[j])@direction);pn=float(direction@(positive[i]+positive[j])@direction);art=-F*pn;net=raw+art
                    scale=max(1.,float(np.max(np.abs(eig[i])))+float(np.max(np.abs(eig[j]))));resolution=32*np.finfo(np.float32).eps*(1.+F)*scale
                    row=dict(group=label,AS_epsilon=EPSILON,AS_exponent=exponent,part=part,time_s=float(a['time']),tau_s=float(r['tau_s']),completed_step=int(r['completed_step']),selection=';'.join(selection['reasons']),id_i=int(ids[si]),id_j=int(ids[sj]),r_over_dp=s,nx=float(direction[0]),nz=float(direction[2]),separation_rate_m_s=float((a['Vel'][si].astype(float)-a['Vel'][sj].astype(float))@direction),kernel_ratio=ratio,F_includes_epsilon=F,total_normal_Pa=raw,positive_spectrum_normal_Pa=pn,AS_normal_Pa=art,net_normal_Pa=net,float_scale_screening_Pa=float(resolution),total_sign=sign(raw,resolution),AS_sign=sign(art,resolution),net_sign=sign(net,resolution),min_abs_total_eigenvalue_Pa=float(min(np.min(abs(eig[i])),np.min(abs(eig[j])))),positive_rank_i=int(np.count_nonzero(eig[i]>0)),positive_rank_j=int(np.count_nonzero(eig[j]>0)))
                    for suffix,slot in [('i',si),('j',sj)]:
                        for key,k in [('x',0),('y',1),('z',2)]:row[key+'_'+suffix+'_m']=float(a['Posd'][slot,k])
                        for key,k in [('vx',0),('vy',1),('vz',2)]:row[key+'_'+suffix+'_m_s']=float(a['Vel'][slot,k])
                        for field,key in [('Kplastic','kappa'),('PorePress','p_Pa'),('PoroVolumeRatio','J'),('FSType','FS')]:row[key+'_'+suffix]=float(a[field][slot,0])
                    frame_rows.append(row);pairs.append(row)
                m=frame_rows[0];summaries.append(dict(group=label,part=part,time_s=float(a['time']),tau_s=float(r['tau_s']),selection=';'.join(selection['reasons']),close_pair_count=len(frame_rows),min_pair_ids=[m['id_i'],m['id_j']],min_r_over_dp=m['r_over_dp'],min_pair_total_normal_Pa=m['total_normal_Pa'],min_pair_AS_normal_Pa=m['AS_normal_Pa'],min_pair_net_normal_Pa=m['net_normal_Pa'],min_pair_net_sign=m['net_sign'],net_attractive_pairs=sum(q['net_sign']=='attractive_shadow' for q in frame_rows),net_repulsive_pairs=sum(q['net_sign']=='repulsive_shadow' for q in frame_rows),net_near_zero_pairs=sum(q['net_sign']=='near_zero_unresolved' for q in frame_rows)))
    need(records_read<=4 and run_bindings[0]==run_bindings[1],'At most4 records and same frozen program/PRE required');need(all(stat(e['path'])==e for e in before),'Closed input changed during offline read')
    pp=Path(str(PREFIX)+'_pairs.csv');sp=Path(str(PREFIX)+'_frames.csv');write(pp,pairs);write(sp,[dict(q,min_pair_ids=','.join(map(str,q['min_pair_ids']))) for q in summaries])
    result=dict(stage=TAG,passed=True,analysis_completed=True,selected_native_records_read=records_read,full_native_window_scan=False,common_saved_window_parts=[0,65],frame_summaries=summaries,double_eigen_frozen_shadow=True,GPU_float_bit_replay=False,AS_epsilon_in_F_once=True,positive_net_normal_means_attractive=True,negative_separation_rate_means_closing=True,float_screen_not_certified_GPU_error_bound=True,no_C_correction=True,whole_stencil_or_temporal_causation_claimed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[stat(pp),stat(sp)])
    with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(check=str(CHECK),records_read=records_read,pairs=len(pairs))),flush=True)
if __name__=='__main__':main()
