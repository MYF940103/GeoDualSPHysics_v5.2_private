"""Saved-geometry fluid-only pressure coefficients; not a GPU rate replay or spectral proof."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import upl_c08_plane_window_review_r1 as w
import upl_c08_wall_geometry_r1 as g
T=Path(__file__).resolve().parents[1];TAG='upl_c08_pressure_coeff_r1';PREFIX=T/'figures'/TAG
NATIVE=T/'outputs/upl_c08_plane_partial_r1';CHECK=T/'logs/upl_c08_plane_partial_r1.check.json'
PARTS=(0,47,48,49,53);IDS=(4808,4859,5809,5556)
H=np.float32(.048);R=float(np.float32(np.float32(2)*H));R2=float(np.float32(np.float32(R)*np.float32(R)))
LOWER=float(np.float32(1e-18));V0=float(np.float32(3.316))/2072.5
ETA2=float(np.float32((float(H)*.1)*(float(H)*.1)))
SOLID0=1-float(np.float32(.35));CK=2.;KW=1e9;GAMMA=1000.*9.80665
# Broad phase covers rounding into the unchanged float(rr2)<=R2 moment predicate.
SEARCH=math.nextafter(math.sqrt(float(np.nextafter(np.float32(R2),np.float32(np.inf)))),math.inf)
need,read,stat=w.need,w.read,w.stat

class WallStencil(Exception):pass

def write(path,rows):
    need(rows,'Empty observation table')
    with path.open('x',encoding='utf-8',newline='') as f:
        out=csv.DictWriter(f,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)

class Cloud:
    def __init__(self,frame):
        self.ids=frame['Idp'][:,0];self.x=frame['Posd'][:,[0,2]].copy()
        self.J=frame['PoroVolumeRatio'][:,0];self.V=V0*self.J
        self.p=frame['PorePress'][:,0].astype(float);self.n=frame['PoroPorosity'][:,0]
        self.k=frame['PoroHydraulicConductivity'][:,0];self.fs=frame['FSType'][:,0]
        self.tree=cKDTree(self.x);self.walltree=cKDTree(self.x[self.ids<2060]);self.edges_cache={};self.c_cache={}
        soil=self.ids>=2060
        need(np.array_equal(self.V[soil],frame['PoroCurrentVolume'][soil,0]),'Original soil V0*J ledger differs')

    def edges(self,i,moment):
        key=(i,moment)
        if key not in self.edges_cache:
            rows=[]
            for j in sorted(self.tree.query_ball_point(self.x[i],SEARCH)):
                d=self.x[i]-self.x[j];rr2=float(d[0]*d[0]+d[1]*d[1])
                test=float(np.float32(rr2)) if moment else rr2
                if test>R2 or test<LOWER:continue
                if self.ids[j]<2060:raise WallStencil('fixed_native_ID_'+str(int(self.ids[j]))+'_in_'+('C' if moment else 'Darcy')+'_stencil_of_'+str(int(self.ids[i])))
                # Audited float GetKernelCubic_Fac pattern, with the same nonzero cutoff.
                fac=g.cubic(rr2)[1];rows.append((j,d,rr2,fac*d))
            self.edges_cache[key]=rows
        return self.edges_cache[key]

    def correction(self,i):
        if i not in self.c_cache:
            M=np.zeros((2,2))
            for j,d,rr2,grad in self.edges(i,True):M-=self.V[j]*np.outer(d,grad)
            det=float(M[0,0]*M[1,1]-M[0,1]*M[1,0])
            # Match KerFsCorrMatInverse: exact nonzero determinant, identity only at zero.
            C=np.array([[M[1,1],-M[0,1]],[-M[1,0],M[0,0]]])/det if det else np.eye(2)
            need(np.isfinite(M).all() and np.isfinite(C).all(),'Nonfinite reconstructed fluid C')
            condition=float(np.linalg.cond(M));mineig=float(np.linalg.eigvalsh((M+M.T)*.5).min())
            self.c_cache[i]=(C,det,condition,mineig)
        return self.c_cache[i]

    def coefficients(self,i):
        if float(self.walltree.query(self.x[i])[0])<2*R:raise WallStencil('receiver_not_at_least_2R_from_all_saved_fixed_B')
        ci,det,cond,mineig=self.correction(i);edges=self.edges(i,False)
        need(edges,'No nonself Darcy fluid neighbors')
        jj=[];ww=[];gg=[];cc=[]
        for j,d,rr2,raw in edges:
            cj=self.correction(j)[0]  # Every j uses its COMPLETE own moment stencil, never a truncated receiver cloud.
            gi=ci@raw;gj=cj@raw
            jj.append(j);gg.append(gi);ww.append(self.V[j]*float(d@(gi+gj))/(rr2+ETA2));cc.append(d)
        jj=np.asarray(jj);gi=np.asarray(gg);weights=np.asarray(ww);d=np.asarray(cc)
        lx=np.sum(d*weights[:,None],axis=0)
        gradJ=np.sum(self.V[jj,None]*(self.J[jj]-self.J[i])[:,None]*gi,axis=0)
        pref=KW/(float(self.n[i])*GAMMA);ki=float(self.k[i]);kp=ki/(SOLID0*CK)
        raw=-pref*ki*weights
        taylor=-pref*ki*self.V[jj]*(gi@lx)
        chain=pref*kp*self.V[jj]*(gi@gradJ)
        current=raw+chain+(0 if int(self.fs[i]) in (2,3) else taylor)
        need(all(np.isfinite(q).all() for q in (raw,taylor,chain,current)),'Nonfinite pressure coefficient')
        dp=self.p[jj]-self.p[i];gp=np.sum(self.V[jj,None]*dp[:,None]*gi,axis=0);lp=-float(weights@dp)
        direct=pref*(ki*(lp if int(self.fs[i]) in (2,3) else lp-float(gp@lx))+kp*float(gradJ@gp))
        data=dict(neighbors=len(jj),C_moment_det=det,C_moment_condition=cond if math.isfinite(cond) else None,C_moment_min_symmetric_eigenvalue=mineig,C_exact_zero_identity_fallback=(det==0),C11=float(ci[0,0]),C13=float(ci[0,1]),C31=float(ci[1,0]),C33=float(ci[1,1]),lx_x=float(lx[0]),lx_z=float(lx[1]),reconstructed_gradJ_x=float(gradJ[0]),reconstructed_gradJ_z=float(gradJ[1]),coefficient_expansion_roundoff_Pa_s=float(current@dp-direct),nearest_fixed_B_m=float(self.walltree.query(self.x[i])[0]))
        return jj,raw,taylor,chain,current,data

def local_plots(data,done,rows,pairs):
    """Direct native point pressure/FS; each panel has its own labelled raw-data scale."""
    from matplotlib.colors import Normalize
    files=[];points=[]
    for leaf,selections in (('local4808',((47,4808),(48,4808),(49,4808))),('local5809',((53,5809),))):
        fig,axs=w.plt.subplots(1,len(selections),figsize=(4.8*len(selections),4.5),squeeze=False,layout='constrained')
        for ax,(part,identity) in zip(axs.ravel(),selections):
            frame=data[part];ids=frame['Idp'][:,0];i=int(np.flatnonzero(ids==identity)[0]);xy=frame['Posd'][:,[0,2]];dist2=np.sum((xy-xy[i])**2,axis=1);at=np.flatnonzero(dist2<=(2*R)**2)
            pressure=frame['PorePress'][at,0].astype(float)/1000;fstype=frame['FSType'][at,0];norm=Normalize(float(pressure.min()),float(pressure.max()))
            for surface,marker,label in ((False,'o','FS0/other'),(True,'^','FS2/3')):
                pick=np.isin(fstype,(2,3))==surface
                ax.scatter(xy[at[pick],0],xy[at[pick],1],c=pressure[pick],cmap='RdBu_r',norm=norm,marker=marker,s=26,edgecolors='black',linewidths=.3,label=label)
            for p in pairs:
                if p['part']==part and p['native_ID']==identity:
                    j=int(np.searchsorted(ids,p['neighbor_native_ID']));negative=p['a_actual_saved_FS_choice_per_s']<0
                    ax.plot([xy[i,0],xy[j,0]],[xy[i,1],xy[j,1]],color='red' if negative else '0.5',alpha=.65 if negative else .2,lw=1.2 if negative else .5,zorder=0)
            ax.scatter([xy[i,0]],[xy[i,1]],marker='*',c='gold',edgecolors='black',s=140,label='receiver '+str(identity));desc=next(q for q in rows if q['part']==part and q['native_ID']==identity)
            if desc['status']=='evaluated_fluid_only_proxy':
                ax.text(.02,.02,'C=[[%g,%g],[%g,%g]]\ncond(M)=%s; red: a<0'%(desc['C11'],desc['C13'],desc['C31'],desc['C33'],desc['C_moment_condition']),fontsize=7,transform=ax.transAxes,bbox=dict(facecolor='white',alpha=.85,edgecolor='none'))
            else:ax.text(.02,.02,'Coefficients not evaluated: fixed-wall scope',fontsize=7,transform=ax.transAxes)
            tau=float(frame['time'])-done['source_actual_time_s'];ax.set(title='Part%d tau=%.6f; own color scale'%(part,tau),xlabel='Native x [m]',ylabel='Native z [m]',aspect='equal');ax.legend(fontsize=6,loc='upper right');ax.grid(alpha=.2)
            fig.colorbar(w.plt.cm.ScalarMappable(norm=norm,cmap='RdBu_r'),ax=ax,label='Unsmoothed native p [kPa]',shrink=.75)
            points.extend(dict(part=part,time_s=float(frame['time']),tau_s=tau,receiver_native_ID=identity,native_ID=int(ids[j]),x_m=float(xy[j,0]),z_m=float(xy[j,1]),p_Pa=float(frame['PorePress'][j,0]),FSType=int(frame['FSType'][j,0]),distance_from_receiver_m=float(math.sqrt(dist2[j]))) for j in at)
        fig.suptitle('Saved full-stage geometry; reconstructed C/coefficients, not GPU rate replay');path=Path(str(PREFIX)+'_'+leaf+'.png');fig.savefig(path,dpi=180);w.plt.close(fig);files.append(path)
    path=Path(str(PREFIX)+'_local_points.csv');write(path,points);files.append(path)
    return files

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root review before the one offline observation')
    need(not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial observations protected')
    nativecheck=read(CHECK);need(nativecheck['passed'] and nativecheck['original_saved_native_guards_passed'] and nativecheck['consumed_stats_unchanged'] and not nativecheck['runtime_success_claimed'],'Closed original54 native prefix required')
    files=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(w.__file__),Path(g.__file__),T/'support/upl_c08_fsmask_r1.py',CHECK)]
    for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):
        path=NATIVE/leaf;entry=next(e for e in nativecheck['files'] if Path(e['path']).samefile(path));need(stat(path)==entry,'Closed native file stat changed');files.append(entry)
    reader=read(Path(nativecheck['reader_call']['path']));need(reader['actual_Popen_wait_exit']==reader['actual_Win32_exit']==0 and reader['ownership_failure'] is None,'Closed actual native reader exit differs')
    files.append(nativecheck['reader_call']);data,done,clocks,history=w.load(NATIVE,54,4216000)
    need(done['diagnostic_partial'] and not done['runtime_success_claimed'] and done['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly','Actual source is a failed-runtime saved prefix, not completed0.6s')
    need(float(g.H)==float(H) and g.R2==R2 and g.LOWER==LOWER and g.VOL0==V0,'Audited Cubic helper constants differ')
    rows=[];pairs=[];evaluated=0
    for part in PARTS:
        frame=data[part];cloud=Cloud(frame)
        for identity in IDS:
            hits=np.flatnonzero(cloud.ids==identity);need(len(hits)==1,'Selected native ID missing');i=int(hits[0])
            base=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-done['source_actual_time_s'],completed_step=int(clocks[part]['completed_step']),native_ID=identity,FSType=int(cloud.fs[i]),x_m=float(cloud.x[i,0]),z_m=float(cloud.x[i,1]),p_Pa=float(cloud.p[i]),J=float(cloud.J[i]))
            try:
                jj,raw,taylor,chain,current,desc=cloud.coefficients(i);evaluated+=1
            except WallStencil as e:
                rows.append(dict(**base,status='not_evaluated_fixed_wall_scope',reason=str(e),variant='',neighbors=None,C_moment_det=None,C_moment_condition=None,C_moment_min_symmetric_eigenvalue=None,C_exact_zero_identity_fallback=None,C11=None,C13=None,C31=None,C33=None,lx_x=None,lx_z=None,reconstructed_gradJ_x=None,reconstructed_gradJ_z=None,coefficient_expansion_roundoff_Pa_s=None,nearest_fixed_B_m=float(cloud.walltree.query(cloud.x[i])[0]),negative_offdiag_count=None,negative_offdiag_abs_sum_per_s=None,negative_abs_fraction=None,min_offdiag_per_s=None,min_offdiag_neighbor_ID=None,max_offdiag_per_s=None,row_diagonal_per_s=None,current_p_pressure_only_Pa_s=None,worst_unit_minimum_rate_Pa_s=None));continue
            variants={'raw_LP':raw,'Lstar':raw+taylor,'chain_increment':chain,'raw_LP_plus_chain':raw+chain,'actual_saved_FS_choice':current}
            for label,coeff in variants.items():
                bad=coeff<0;neg=float(-np.sum(coeff[bad]));total=float(np.sum(np.abs(coeff)));minimum=int(np.argmin(coeff))
                # With p_i=0, neighbors with a<0 set to1Pa and all others0, this is the exact bounded local minimum counterexample for this frozen row.
                rows.append(dict(**base,status='evaluated_fluid_only_proxy',reason='',variant=label,**desc,negative_offdiag_count=int(bad.sum()),negative_offdiag_abs_sum_per_s=neg,negative_abs_fraction=neg/total if total else 0.,min_offdiag_per_s=float(coeff[minimum]),min_offdiag_neighbor_ID=int(cloud.ids[jj[minimum]]),max_offdiag_per_s=float(coeff.max()),row_diagonal_per_s=float(-coeff.sum()),current_p_pressure_only_Pa_s=float(coeff@(cloud.p[jj]-cloud.p[i])),worst_unit_minimum_rate_Pa_s=-neg))
            for index,j in enumerate(jj):pairs.append(dict(**base,neighbor_native_ID=int(cloud.ids[j]),distance_m=float(np.linalg.norm(cloud.x[i]-cloud.x[j])),neighbor_FSType=int(cloud.fs[j]),neighbor_p_Pa=float(cloud.p[j]),a_raw_LP_per_s=float(raw[index]),a_Taylor_increment_per_s=float(taylor[index]),a_chain_increment_per_s=float(chain[index]),a_Lstar_per_s=float(raw[index]+taylor[index]),a_actual_saved_FS_choice_per_s=float(current[index])))
    paths=[Path(str(PREFIX)+'_rows.csv'),Path(str(PREFIX)+'_pairs.csv')];write(paths[0],rows)
    if pairs:write(paths[1],pairs)
    paths+=local_plots(data,done,rows,pairs)
    need(all(stat(Path(e['path']))==e for e in files),'Sealed source/data changed during offline observation')
    actual=[r for r in rows if r['variant']=='actual_saved_FS_choice'];worst=min(actual,key=lambda r:r['worst_unit_minimum_rate_Pa_s']) if actual else None
    result=dict(stage=TAG,passed=True,analysis_completed=True,selected_parts=list(PARTS),selected_native_IDs=list(IDS),part0_is_first_saved_post_not_PRE=True,evaluated_receivers=evaluated,not_evaluated_receivers=20-evaluated,largest_local_1Pa_minimum_counterexample=worst,pressure_rate_sign_convention='rate_i_pressure=sum_j a_ij*(p_j-p_i); a_ij<0 violates local minimum preservation',C_source='inverse(-sum Vj d_ij tensor grad_iW_ij); native-double/float-rr2 CPU-style reconstruction proxy',volume_source='V0*savedJ, V0=float(massfluid)/rho0',C_native_or_GPU_bit_replay=False,packed_float_positions_recovered=False,saved_full_stage_only=True,wall_ghosts_omitted_or_fabricated=False,wall_or_neighbor_C_wall_support_is_not_evaluated=True,actual_Ace_theta_or_rate_replayed=False,global_matrix_or_eigenvalues_computed=False,negative_coefficient_is_not_proof_of_positive_global_eigenvalue=True,physical_acceptance=False,dt_changed=False,thresholds_relaxed=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=files,files=[stat(p) for p in paths if p.exists()])
    with Path(str(PREFIX)+'.check.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('PRESSURE_COEFFICIENT_OBSERVATION_READY',str(PREFIX)+'.check.json',flush=True)

if __name__=='__main__':main()
