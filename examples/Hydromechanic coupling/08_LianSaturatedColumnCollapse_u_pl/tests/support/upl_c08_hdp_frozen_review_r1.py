"""Frozen n3 soil-only support counts and Cubic AS distance multipliers; no physical acceptance."""
import argparse,csv,json,os
from pathlib import Path
import xml.etree.ElementTree as ET
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
from scipy.spatial import cKDTree

T=Path(__file__).resolve().parents[1];C=T.parent;TAG='upl_c08_hdp_frozen_review_r1'
DATA=T/'figures/upl_c08_n3_full_compare_r1_spatial.csv';DEF=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_Def.xml'
NEIGH=T/'figures'/(TAG+'_neighbors.csv');WEIGHTS=T/'figures'/(TAG+'_weights.csv');CHECK=T/'logs'/(TAG+'.check.json')
EXPECTED=['group','requested_tau_s','time_s','tau_s','completed_step','native_id','x_m','z_m','p_Pa','kappa','rNN_over_dp','FSType']

def need(value,message):
    if not value:raise ValueError(message)
def stat(path):
    p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def write_csv(path,keys,rows):
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def shape(q):return 1.-1.5*q*q+.75*q*q*q if q<1. else .25*(2.-q)**3 if q<2. else 0.

def main():
    need(not any(p.exists() for p in (NEIGH,WEIGHTS,CHECK)),'Existing complete/partial review protected; never overwrite')
    inputs=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),DATA,DEF)]
    root=ET.parse(DEF).getroot();geom=root.find('casedef/geometry');variables=geom.findall('predefinition/newvarcte[@Dp]')
    need(len(variables)==1 and geom.find('definition').get('dp')=='#Dp','Expected explicit Dp variable binding required');dp=float(variables[0].get('Dp'));need(dp==.04,'Frozen C08 dp must be .04 m')
    need(float(root.find('casedef/constantsdef/hdp').get('value'))==1.2,'Retained r6 hdp1.2 context required')
    snapshots={}
    with DATA.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);need(reader.fieldnames==EXPECTED,'Retained spatial CSV schema differs')
        for row in reader:
            if row['group']=='n3':snapshots.setdefault(float(row['requested_tau_s']),[]).append(row)
    need(set(snapshots)=={.3,.6,1.2,2.,3.},'Exactly the five retained n3 snapshots required');rows=[]
    for requested,items in sorted(snapshots.items()):
        items.sort(key=lambda r:int(r['native_id']));need([int(r['native_id']) for r in items]==list(range(2060,7060)),'Every snapshot must have exactly5000 unique original soil IDs')
        identity={(r['time_s'],r['tau_s'],r['completed_step']) for r in items};need(len(identity)==1,'Actual snapshot time/step is not unique');time,tau,step=next(iter(identity))
        x=np.array([(float(r['x_m']),float(r['z_m'])) for r in items]);need(np.isfinite(x).all(),'Nonfinite frozen soil coordinates');tree=cKDTree(x)
        for hdp in (1.2,1.5):
            h=dp*hdp;pairs=tree.query_pairs(2.*h,output_type='ndarray');d=x[pairs[:,0]]-x[pairs[:,1]];pairs=pairs[np.einsum('ij,ij->i',d,d)<(2.*h)**2]
            counts=np.bincount(pairs.reshape(-1),minlength=5000);p05,median,p95=np.percentile(counts,[5,50,95])
            rows.append(dict(group='n3',requested_tau_s=requested,time_s=time,tau_s=tau,completed_step=step,soil_IDs=5000,hdp=hdp,h_m=h,support_radius_m=2.*h,mean_neighbors=float(counts.mean()),median_neighbors=float(median),p05_neighbors=float(p05),p95_neighbors=float(p95),min_neighbors=int(counts.min()),max_neighbors=int(counts.max())))
    weights=[]
    for hdp in (1.2,1.5):
        for s in (.32,.425,.5,.7,1.,1.5,2.):
            ratio=shape(s/hdp)/shape(1./hdp);weights.append(dict(hdp=hdp,r_over_dp=s,q=s/hdp,W_over_Wdp=ratio,epsilon=.2,exponent=3.,epsilon_times_ratio_power=.2*ratio**3))
    need(inputs==[stat(e['path']) for e in inputs],'Source changed during offline review')
    write_csv(NEIGH,list(rows[0]),rows);write_csv(WEIGHTS,list(weights[0]),weights)
    need(inputs==[stat(e['path']) for e in inputs],'Source changed while writing derived CSVs')
    result=dict(stage=TAG,passed=True,analysis_completed=True,physical_acceptance=False,inputs=inputs,outputs=[stat(NEIGH),stat(WEIGHTS)],consumed_stats_unchanged=True,dp_m=dp,snapshots=5,neighbor_summary_rows=len(rows),weight_rows=len(weights),scope='Frozen n3 XZ soil only; no fixed walls, ghost images or actual force-neighbor claim',neighbor_definition='distinct unordered soil pairs, strict r<2h; each contributes one neighbor to each end',arithmetic='Nominal h=hdp*dp and normalized Cubic shape in float64; not GPU float-bit replay',weight_formula='epsilon*[W(r;h)/W(dp;h)]^3 with epsilon=.2; not actual pair acceleration',kernel_shape='q<1:1-1.5q^2+.75q^3; 1<=q<2:.25(2-q)^3; otherwise0',solver_invocations=0,decoder_invocations=0,SHA_scans=0)
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(passed=True,check=str(CHECK),neighbor_rows=len(rows),weight_rows=len(weights))),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read and one explicit offline invocation required');main()
