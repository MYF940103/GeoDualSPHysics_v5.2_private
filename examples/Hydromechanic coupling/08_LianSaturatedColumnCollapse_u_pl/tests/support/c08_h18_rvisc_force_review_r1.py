"""Offline fixed-state residual-force review only; no force or time advancement."""
import argparse, math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import c08_h18_wend_matrix_r1 as m
T,L=m.T,m.L
TAG='c08_h18_rvisc_force_review_r1'
SOURCE='c08_h18_rvisc_force_r1'
OUT=T/'figures'/TAG
CHECK=L/(TAG+'.check.json')

def same(x,y,scale,label,n=5000):
    # Separate CSV/accumulation forward arithmetic allowance; never changes a physical gate.
    nu=(16*n+64)*(.5*np.finfo(float).eps)
    budget=nu/(1-nu)*(float(scale)+abs(float(y)))
    m.need(abs(float(x)-float(y))<=budget,label+' algebra differs')
    return budget

def save_csv(frame,path):
    with path.open('x',encoding='utf-8',newline='') as f:frame.to_csv(f,index=False,float_format='%.17g')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true')
    m.need(p.parse_args().execution_authorized,'Root offline admission required')
    m.need(not OUT.exists() and not CHECK.exists(),'Existing complete/failed review is immutable')
    inputs=[m.stat(Path(__file__)),m.stat(T/'notes'/(TAG+'.md'))];files=[]
    try:
        cp=L/(SOURCE+'.check.json');c=m.read(cp);inputs.append(m.stat(cp))
        m.need(c['passed'] and c['consumed_stats_unchanged'] and c['physical_steps']==0,'Sealed passed zero-step component required')
        for key in ('build','actual_call','completion'):
            e=m.bind(c[key]);inputs.append(e)
        b=m.read(c['build']['path']);call=m.read(c['actual_call']['path']);done=m.read(c['completion']['path'])
        m.need(b['passed'] and b['physical_objects_compiled']==0 and b['original_Single_no_hook'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual build and owned component must pass')
        m.need(done['passed'] and done['actual_force_calls']==2 and done['actual_Darcy_calls']==6 and done['extra_Darcy_calls']==4 and done['physical_steps']==done['material_return_calls']==0 and done['baseline_RHS_bit_rows']==done['zero_recompute_rate_bit_rows']==10000 and done['literal_rate_rows']==30000,'Original bounded count/bit/arithmetic gates required')
        m.need(done['max_final_float_budget_ratio']<=1 and done['max_expanded_budget_ratio']<=1,'Original literal budgets failed')
        frames={}
        for name,count in [('metrics',2),('soil',10000),('pairs',4),('manufactured',6)]:
            path=(T/'outputs'/SOURCE/(name+'.csv')).resolve()
            e=next(q for q in c['files'] if Path(q['path']).resolve()==path);inputs.append(m.bind(e))
            d=pd.read_csv(path,float_precision='round_trip');m.need(len(d)==count,name+' count differs')
            num=d.select_dtypes(include=np.number);m.need(np.isfinite(num.to_numpy(dtype=float)).all(),name+' nonfinite')
            frames[name]=d
        metrics,soil,pairs,made=(frames[q] for q in ('metrics','soil','pairs','manufactured'))
        m.need(set(metrics.part)=={38,76} and not metrics.part.duplicated().any(),'Metric states differ')
        rows=[]
        for part,step,idx in [(38,2076001,0),(76,2152001,1)]:
            z=metrics[metrics.part==part].iloc[0];d=soil[soil.part==part].sort_values('native_id')
            q=pairs[pairs.part==part];f=made[made.part==part]
            m.need(len(d)==5000 and np.array_equal(d.native_id.to_numpy(),np.arange(2060,7060)),'Complete fixed material IDs differ')
            m.need(len(q)==2 and set(zip(q.ID_i,q.ID_j))=={(4953,4954),(6767,6865)} and set(f.manufacture)=={'constant','affine','rigid_rotation'} and len(f)==3,'Pair/manufactured identities differ')
            for t in (d,q):m.need((t.completed_step==step).all() and (t.time_s==z.time_s).all() and (t.tau_s==z.tau_s).all(),'Actual time/step differs')
            m.need(z.completed_step==step and z.actual_force_calls_cumulative==idx+1 and z.actual_Darcy_calls_cumulative==3*(idx+1) and z.actual_DtVariable_calls_cumulative==2*(idx+1) and z.baseline_bits==z.zero_recompute_bits==5000,'State gates/counts differ')
            m.need(z.wall_active+z.wall_inactive==z.wall_NpbOk and z.wall_NpbOk+z.wall_ignored==1805,'Effective wall partition differs')
            m.need(z.baseline_DtVariable==z.candidate_DtVariable==5e-6 and z.necessary_bound_s>=5e-6 and z.alpha_dt_dmax<=1,'Original necessary/isolated5us bounds failed')
            m.need(z.work<=z.work_budget and abs(z.work_plus_2form)<=z.work_budget and z.max_normal_budget_fraction<=1 and z.committed_work<=z.committed_work_budget and z.committed_net_force_norm<=z.committed_net_force_budget and abs(z.committed_torque_y)<=z.committed_torque_budget,'Original mechanical budgets failed')
            m.need((f.manufacture_max_residual<=f.manufacture_residual_budget).all() and (f.max_force<=f.manufacture_force_budget).all(),'Original affine/null manufactured budgets failed')
            rate0=d.base_R_Pa_s.to_numpy();rate1=d.candidate_R_Pa_s.to_numpy();dr=rate1-rate0
            m.need(np.array_equal(dr,d.delta_R_Pa_s.to_numpy()) and np.array_equal(5e-6*dr,d.dt_delta_R_Pa.to_numpy()),'Actual deltaR/conditional dt deltaR differs')
            mass=d.V.to_numpy()*d.rho.to_numpy();fx=mass*d.committed_da_x;fz=mass*d.committed_da_z
            power=d.vx*fx+d.vz*fz;torque=d.z_m*fx-d.x_m*fz
            work=math.fsum(power);net=math.hypot(math.fsum(fx),math.fsum(fz));moment=math.fsum(torque)
            wb=same(work,z.committed_work,np.abs(power).sum(),'Committed work')
            nb=same(net,z.committed_net_force_norm,np.hypot(fx,fz).sum(),'Committed net force')
            tb=same(moment,z.committed_torque_y,(np.abs(d.z_m*fx)+np.abs(d.x_m*fz)).sum(),'Committed torque')
            # Original budgets apply to the original accumulation; expose independent arithmetic deltas too.
            pp=d.weight_nV_Kw*d.p_Pa*dr;wp=math.fsum(pp)
            same(wp,z.sum_weighted_p_delta_R,np.abs(pp).sum(),'Conditional pressure term')
            rms0=math.sqrt(math.fsum(rate0*rate0)/5000);rms1=math.sqrt(math.fsum(rate1*rate1)/5000);rmsd=math.sqrt(math.fsum(dr*dr)/5000)
            for value,name in [(rms0,'baseline_R_RMS'),(rms1,'candidate_R_RMS'),(rmsd,'delta_R_RMS')]:same(value,z[name],abs(value),name)
            for value,name in [(np.max(np.abs(rate0)),'baseline_max_abs_R'),(np.max(np.abs(rate1)),'candidate_max_abs_R'),(np.max(np.abs(dr)),'max_abs_delta_R')]:m.need(value==z[name],name+' differs')
            row=z.to_dict();row.update(recomputed_work=work,recomputed_net_force=net,recomputed_torque=moment,CSV_work_arithmetic_budget=wb,CSV_net_force_arithmetic_budget=nb,CSV_torque_arithmetic_budget=tb,recomputed_pressure_term=wp,recomputed_baseline_R_RMS=rms0,recomputed_candidate_R_RMS=rms1,recomputed_delta_R_RMS=rmsd,physical_steps=0);rows.append(row)
        result=pd.DataFrame(rows);m.verify(inputs);OUT.mkdir()
        for frame,name in [(result,'summary'),(pairs,'pairs')]:save_csv(frame,OUT/(name+'.csv'))
        plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.22})
        fig,axs=plt.subplots(2,2,figsize=(13,8.5));x=np.arange(2);labels=['P38, tau=%.6fs'%rows[0]['tau_s'],'P76, tau=%.6fs'%rows[1]['tau_s']]
        for ax,col,title in [(axs[0,0],'R_RMS','Pressure-rate RMS'),(axs[0,1],'max_abs_R','Maximum absolute pressure rate')]:
            ax.bar(x-.18,result['baseline_'+col]/1e6,.36,label='Original');ax.bar(x+.18,result['candidate_'+col]/1e6,.36,label='Residual viscosity alpha=0.1');ax.set_xticks(x,labels);ax.set_ylabel('MPa/s');ax.set_title(title);ax.legend(fontsize=8)
        ax=axs[1,0];other=ax.twinx();ax.bar(x-.17,result.recomputed_work,.32,color='tab:blue',label='Mechanical added power');other.bar(x+.17,result.recomputed_pressure_term,.32,color='tab:orange',label='Conditional sum(w p deltaR)')
        ax.set_xticks(x,labels);ax.set_ylabel('Mechanical power [W/m]',color='tab:blue');other.set_ylabel('Conditional pressure term [W/m]',color='tab:orange');other.grid(False);ax.set_title('Different conditional terms; no total energy claim');ax.legend(loc='upper left',fontsize=8);other.legend(loc='lower right',fontsize=8)
        ax=axs[1,1];q=pairs.sort_values(['part','ID_i']);j=np.arange(4);ax.bar(j-.18,q.base_rddot,.36,label='Original');ax.bar(j+.18,q.candidate_rddot,.36,label='Candidate');ax.set_xticks(j,['P%d\n%d/%d'%(r.part,r.ID_i,r.ID_j) for r in q.itertuples()]);ax.set_ylabel('rddot [m/s2]');ax.set_title('Fixed material pairs; same actual rdot');ax.legend(fontsize=8)
        footer='Frozen states only; no advance or physical acceptance. Max added Ace=%.5g / %.5g m/s2; dt/bound=%.5g / %.5g; alpha*dt*dmax=%.5g / %.5g.'%(result.max_added_accel.iloc[0],result.max_added_accel.iloc[1],5e-6/result.necessary_bound_s.iloc[0],5e-6/result.necessary_bound_s.iloc[1],result.alpha_dt_dmax.iloc[0],result.alpha_dt_dmax.iloc[1])
        fig.suptitle('C08 H1.8 conditional residual-viscosity force/Darcy feasibility');fig.text(.5,.015,footer,ha='center',fontsize=8);fig.tight_layout(rect=(0,.045,1,.95));fig.savefig(OUT/'summary.png',dpi=170);plt.close(fig)
        lo,hi=float(soil.dt_delta_R_Pa.min()),float(soil.dt_delta_R_Pa.max());m.need(hi>lo,'Spatial response has no range')
        fig,axs=plt.subplots(1,2,figsize=(12,4.8),sharex=True,sharey=True);norm=Normalize(lo,hi)
        for ax,part in zip(axs,[38,76]):
            d=soil[soil.part==part];sc=ax.scatter(d.x_m,d.z_m,c=d.dt_delta_R_Pa,cmap='RdBu_r',norm=norm,s=5,linewidths=0);ax.set_title('Part%d, tau=%.6fs'%(part,d.tau_s.iloc[0]));ax.set_aspect('equal');ax.set_xlabel('x [m]');ax.set_ylabel('z [m]')
        fig.colorbar(sc,ax=axs.tolist(),label='5 us * deltaR [Pa]; conditional, not an updated pressure',pad=.02);fig.suptitle('All5000 material IDs; common linear full range [%.6g, %.6g] Pa'%(lo,hi));fig.subplots_adjust(left=.06,right=.83,bottom=.12,top=.86,wspace=.08);fig.savefig(OUT/'space.png',dpi=180);plt.close(fig)
        files=[m.stat(OUT/n) for n in ('summary.csv','pairs.csv','summary.png','space.png')];m.verify(inputs)
        m.save(CHECK,dict(stage=TAG,passed=True,consumed=inputs,consumed_stats_unchanged=True,files=files,source_completion=c['completion'],parts=[38,76],soil_rows=10000,pair_rows=4,metrics_rows=2,manufactured_rows=6,spatial_colorbar_min_Pa=lo,spatial_colorbar_max_Pa=hi,space_no_smoothing_or_clipping=True,actual_force_calls_added=0,actual_Darcy_calls_added=0,physical_steps=0,SHA_scans=0,physical_acceptance=False,mechanical_negative_power_not_coupled_stability=True,visual_review_pending=True))
    except Exception as e:
        if not CHECK.exists():m.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),consumed=inputs,files=files,partial_outputs_preserved=True,physical_steps=0,SHA_scans=0,physical_acceptance=False))
        raise

if __name__=='__main__':main()
