"""Old AS03/Lstar fixed-material local geometry only; no decoder or physical update."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import c08_h18_storage_review_r2 as core
T,L=core.T,core.L
need,read,stat,bind=core.need,core.read,core.stat,core.bind
TAG='c08_h18_material_geometry_r1';SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md');GATE=L/'c08_h18_lstar_window_review_r1.check.json'
FIG=T/'figures';OUT=[FIG/(TAG+s)for s in('_triangles.csv','_local_fit.csv','.png')];CHECK=L/(TAG+'.check.json');DP=.04;TARGET=(6817,6866)
CONSUMED=[]
def save(value):
    with CHECK.open('x',encoding='utf-8')as f:json.dump(value,f,indent=2,allow_nan=False)
def write(path,rows):
    with path.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def load(consumed):
    gate=read(GATE);need(gate['passed']and gate['analysis_complete']and gate['consumed_stats_unchanged'],'Passed old-only review required');consumed.append(stat(GATE))
    def seal(path):
        matches=[q for q in gate['files']+gate['consumed']if Path(q['path']).resolve()==Path(path).resolve()];need(matches and all(q==matches[0]for q in matches),'Existing matching seal required: '+str(path));consumed.append(bind(matches[0]))
    cp=FIG/'c08_h18_lstar_window_review_r1_cohorts.csv';seal(cp);rows=core.table(cp);need(len(rows)==5000,'All sealed material cohorts required')
    ids=np.array([int(q['native_id'])for q in rows]);need(np.array_equal(ids,np.arange(2060,7060)),'Cohort order/IDs differ')
    x0=np.array([[float(q['initial_x_m']),float(q['initial_z_m'])]for q in rows]);pre=np.array([[float(q['PRE_x_m']),float(q['PRE_z_m'])]for q in rows]);xs,zs=np.unique(x0[:,0]),np.unique(x0[:,1]);need(len(xs)==100 and len(zs)==50 and np.isfinite(pre).all(),'Actual source50x100 grid required')
    grid=np.full((50,100),-1,int)
    for k,q in enumerate(rows):
        iz,ix=np.searchsorted(zs,x0[k,1]),np.searchsorted(xs,x0[k,0]);need(grid[iz,ix]<0 and int(q['initial_layer'])==iz and float(q['initial_y_m'])==float(q['PRE_y_m'])==0,'Actual one-to-one planar material grid differs');grid[iz,ix]=k
    need((grid>=0).all(),'Incomplete material topology')
    bundles=[]
    for name in('c08_h18_as03_n255_r1','c08_h18_lstar_window_GPU_r1','c08_h18_wend_psi0_pre_r2'):
        root=T/'outputs'/name/'native_r1'
        for leaf in('typed22.bin','typed22_layout.csv','clocks.csv'):seal(root/leaf)
        source=name.endswith('pre_r2');bundles.append(core.typed(root,7060 if source else 6805,1001 if source else 91,consumed))
    src=core.core.read22(bundles[2],1000);soil=src['Idp'][:,0]>=2060;need(np.array_equal(src['Idp'][soil,0],ids)and np.array_equal(src['Posd'][soil][:,(0,2)],pre),'Sealed PRE cohort/native positions differ')
    jp=np.array(src['PoroVolumeRatio'][soil,0]);need(np.isfinite(jp).all()and(jp>0).all(),'Positive actual PRE J required')
    for a,b in zip(bundles[0]['clocks'],bundles[1]['clocks']):
        need(a['completed_step']==b['completed_step']and a['saved_step']==b['saved_step']and core.bits(a['time_s'])==core.bits(b['time_s'])and float(a['signed_dterror_s'])<=1e-14 and float(b['signed_dterror_s'])<=1e-14,'Actual91 same-time/signed join differs')
    return ids,pre,jp,grid,bundles[:2],float(src['time'])
def patches(ids,grid):
    centers=[tuple(np.argwhere(grid==int(np.flatnonzero(ids==i)[0]))[0])for i in TARGET]
    def patch(c):return set(int(grid[z,x])for z in range(max(0,c[0]-1),min(50,c[0]+2))for x in range(max(0,c[1]-1),min(100,c[1]+2)))
    focal=patch(centers[0])|patch(centers[1]);adj=None
    for dz,dx in((0,-3),(0,3),(-3,0),(3,0)):
        c=(centers[0][0]+dz,centers[0][1]+dx)
        if 1<=c[0]<49 and 1<=c[1]<99 and not(patch(c)&focal):adj=c;break
    need(adj is not None,'No prescribed adjacent patch; do not select by outcome');groups={'focal_union':focal,'adjacent_descriptive':patch(adj)};anchors=[(str(i),int(np.flatnonzero(ids==i)[0]),patch(c))for i,c in zip(TARGET,centers)];anchors.append(('adjacent_descriptive',int(grid[adj]),patch(adj)))
    cells=[]
    for label,nodes in groups.items():
        for z in range(49):
            for x in range(99):
                q=tuple(int(grid[a,b])for a,b in((z,x),(z,x+1),(z+1,x+1),(z+1,x)))
                if set(q)<=nodes:cells.append((label,z,x,q))
    need(cells and len(anchors)==3,'Fixed local cells missing');return groups,anchors,cells
def matrix(X,Y):
    rank=int(np.linalg.matrix_rank(X));F=None if rank<2 else Y@np.linalg.inv(X);s=None if F is None else np.linalg.svd(F,compute_uv=False);return rank,F,s
def main():
    need(not CHECK.exists()and all(not q.exists()for q in OUT),'Protect old/partial derived outputs');consumed=CONSUMED;consumed.extend(stat(q)for q in(SCRIPT,NOTE,Path(core.__file__),Path(core.core.__file__)));ids,pre,jp,grid,bundles,tpre=load(consumed);groups,anchors,cells=patches(ids,grid);tri=[];fit=[];labels=('Original pair-C/Eta','Private receiver-C/bare');pair=np.array([np.flatnonzero(ids==i)[0]for i in TARGET]);dpre=pre[pair[1]]-pre[pair[0]]
    for label,bundle in zip(labels,bundles):
        for part in range(91):
            a=core.core.read22(bundle,part);soil=a['Idp'][:,0]>=2060;need(np.array_equal(a['Idp'][soil,0],ids),'All5000 material IDs required');pos=np.array(a['Posd'][soil][:,(0,2)]);jr=np.array(a['PoroVolumeRatio'][soil,0])/jp;need(np.isfinite(jr).all()and(jr>0).all(),'Original positive J remains required');clock=bundle['clocks'][part];base=dict(case=label,part=part,completed_step=int(clock['completed_step']),actual_time_s=float(a['time']),tau_s=float(a['time'])-tpre,signed_dterror_s=float(clock['signed_dterror_s']))
            for anchor,k,nodes in anchors:
                nn=np.array(sorted(nodes-{k}));X=(pre[nn]-pre[k]).T;Y=(pos[nn]-pos[k]).T;coef,_,rank,_=np.linalg.lstsq(X.T,Y.T,rcond=None);rank=int(rank);F=None if rank<2 else coef.T;res=None if F is None else float(np.sum((Y-F@X)**2)/(len(nn)*DP**2));s=None if F is None else np.linalg.svd(F,compute_uv=False);pred=None if F is None or anchor=='adjacent_descriptive'else float(np.linalg.norm(F@dpre)/DP)
                r=dict(base,anchor=anchor,native_id=int(ids[k]),neighbors=len(nn),reference_rank=rank,Dmin2_over_dp2=res,fit_det=None if F is None else float(np.linalg.det(F)),fit_smin=None if s is None else float(s[-1]),fit_smax=None if s is None else float(s[0]),fit_condition=None if s is None or s[-1]==0 else float(s[0]/s[-1]),fit_singular=s is None or s[-1]==0,J_over_Jpre=float(jr[k]),pair_actual_over_dp=float(np.linalg.norm(pos[pair[1]]-pos[pair[0]])/DP),pair_fit_prediction_over_dp=pred,pair_vector_residual_over_dp=None if pred is None else float(np.linalg.norm(pos[pair[1]]-pos[pair[0]]-F@dpre)/DP))
                fit.append(r)
            for group,z,x,q in cells:
                js=jr[list(q)];records=[]
                for diagonal,local in(('primary',(0,1,2)),('primary',(0,2,3)),('opposite',(0,1,3)),('opposite',(1,2,3))):
                    v=np.array([q[i]for i in local]);X=(pre[v[1:]]-pre[v[0]]).T;Y=(pos[v[1:]]-pos[v[0]]).T;rank,F,s=matrix(X,Y);det=None if F is None else float(np.linalg.det(F));records.append(dict(base,group=group,grid_z=z,grid_x=x,diagonal=diagonal,ids=':'.join(str(int(ids[i]))for i in v),reference_rank=rank,reference_signed_double_area=float(np.linalg.det(X)),current_signed_double_area=float(np.linalg.det(Y)),detF=det,smin=None if s is None else float(s[-1]),smax=None if s is None else float(s[0]),condition=None if s is None or s[-1]==0 else float(s[0]/s[-1]),singular=s is None or s[-1]==0,Jratio_vertex_min=float(js.min()),Jratio_vertex_median=float(np.median(js)),Jratio_vertex_max=float(js.max())))
                signs=[None if r['detF']is None else int(np.sign(r['detF']))for r in records];flag=None if None in signs else len(set(signs))>1
                for r in records:r['quad_triangle_sign_disagreement']=flag;tri.append(r)
    write(OUT[0],tri);write(OUT[1],fit);fig,axs=plt.subplots(3,2,figsize=(16,11));styles=('-', '--', ':');signax=axs[2,1].twinx();signax.set_ylabel('Focal quads: sign disagreement',fontsize=8);signax.yaxis.set_major_locator(MaxNLocator(4,integer=True))
    for label,color in zip(labels,('tab:blue','tab:orange')):
        fs=[q for q in fit if q['case']==label];ts=[q for q in tri if q['case']==label and q['diagonal']=='primary'];time=[q['tau_s']for q in fs if q['anchor']==str(TARGET[0])]
        for j,anchor in enumerate((str(TARGET[0]),str(TARGET[1]),'adjacent_descriptive')):
            a=[q for q in fs if q['anchor']==anchor];axs[0,1].plot(time,[q['Dmin2_over_dp2']for q in a],styles[j],color=color,label=label+' '+anchor)
            if j<2:axs[0,0].plot(time,[q['pair_fit_prediction_over_dp']for q in a],styles[j+1],color=color,label=label+' fit '+anchor)
        axs[0,0].plot(time,[q['pair_actual_over_dp']for q in fs if q['anchor']==str(TARGET[0])],color=color,label=label+' actual')
        for group,ls in(('focal_union','-'),('adjacent_descriptive',':')):
            by=[[q for q in ts if q['part']==i and q['group']==group]for i in range(91)]
            for ax,key,fun in((axs[1,0],'detF',min),(axs[1,1],'smin',min),(axs[2,0],'smax',max),(axs[2,1],'condition',max)):
                val=[fun(q[key]for q in a if q[key]is not None)if any(q[key]is not None for q in a)else None for a in by];ax.plot(time,val,ls,color=color,label=label+' '+group)
            if group=='focal_union':
                axs[1,0].plot(time,[np.median([q['Jratio_vertex_median']for q in a])for a in by],'--',color=color,label=label+' vertex J/PRE median');signax.plot(time,[sum(q['quad_triangle_sign_disagreement']is True for q in a)/2 for a in by],':',color=color,label=label+' sign disagreement')
    titles=('Fixed pair6817/6866 distance / dp','Local nonaffine Dmin² / dp²','Primary-triangle minimum detF and vertex J ratio','Primary-triangle minimum singular value','Primary-triangle maximum singular value','Max condition (left); dotted sign-disagreement count (right)')
    for ax,title in zip(axs.flat,titles):ax.set_title(title,fontsize=10);ax.set_xlabel('Actual time since PRE [s]');ax.grid(alpha=.25);ax.xaxis.set_major_locator(MaxNLocator(5));ax.yaxis.set_major_locator(MaxNLocator(5));ax.legend(fontsize=6)
    axs[1,0].axhline(0,color='k',linewidth=.6);fig.suptitle('Fixed-material local geometry: old AS03 / Lstar only',fontsize=14);fig.text(.5,.012,'Post-built material triangles are not solver cells. Negative area is not stored J<0; no physical threshold or repair claim.',ha='center',fontsize=9);fig.tight_layout(rect=(.01,.035,.99,.96));fig.savefig(OUT[2],dpi=160);plt.close(fig)
    need(all(stat(q['path'])==q for q in consumed),'Consumed old inputs changed');save(dict(stage=TAG,passed=True,consumed_stats_unchanged=True,analysis_complete=True,physical_acceptance=False,visual_QA_pending=True,frames_per_case=91,soil_IDs=5000,focus_IDs=list(TARGET),patches={k:[int(ids[i])for i in sorted(v)]for k,v in groups.items()},triangle_rows=len(tri),local_fit_rows=len(fit),source_frame_reads=[1000],new_pair_body_read=False,new_native_invocations=0,new_solver_invocations=0,consumed=consumed,files=[stat(q)for q in OUT]))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Independent root offline authorization required')
    try:main()
    except Exception as e:
        if not CHECK.exists():save(dict(stage=TAG,passed=False,first_failure=str(e),partial_outputs_preserved=True,consumed=CONSUMED,new_native_invocations=0,new_solver_invocations=0,physical_acceptance=False))
        raise
