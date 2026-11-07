"""Offline comparison of two closed real basic cases; actual times, no interpolation or 5Pa gate."""
import argparse,csv,json,os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from basic_material_r1 import context,need,read,stat,save
def table(p):
    with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(p,rows):
    with Path(p).open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def load(t,window,mode):
    tag='basic_material_'+window+'_'+mode+'_CPU_r1';cp=t/'logs'/(tag+'.native_r2.check.json');c=read(cp);need(c['passed'] and c['consumed_stats_unchanged'],'Only closed native output');folder=t/'outputs'/(tag+'_native_r2');b=folder/'states.bin';h=np.fromfile(b,dtype='<u4',count=4);soil,fixed,frames,width=map(int,h);need(width==14,'Native row width changed');dt=np.dtype([('time','<f8'),('state','<f8',(soil,width))]);need(b.stat().st_size==16+frames*dt.itemsize,'Native binary length differs');a=np.fromfile(b,dtype=dt,offset=16);hist=table(folder/'history.csv');clock=table(folder/'clocks.csv');need(len(a)==frames==len(hist)==len(clock) and np.isfinite(a['state']).all(),'Native field coverage invalid');need(np.array_equal(a['time'],[float(r['time_s']) for r in clock]),'Typed/native CSV clocks differ');return dict(mode=mode,a=a,history=hist,clock=clock,soil=soil,fixed=fixed,source=[stat(cp),stat(b),stat(folder/'clocks.csv'),stat(folder/'history.csv')],completion=c['completion'])
def main():
    p=argparse.ArgumentParser();p.add_argument('case',choices=['column','collapse']);p.add_argument('window',choices=['short','full']);args=p.parse_args();c,t,stem,short,full,soil,fixed=context(args.case);prefix='basic_material_'+args.window+'_r1';png=t/'figures'/(prefix+'.png');check=t/'logs'/(prefix+'.review.json');need(not png.exists() and not check.exists(),'Fresh review required');sets=[load(t,args.window,x) for x in ('old','new')];old,new=sets
    need(all(x['soil']==soil and x['fixed']==fixed for x in sets),'Original IDs/count differ');initial_bits=int(np.count_nonzero(old['a']['state'][0].view('<u8')!=new['a']['state'][0].view('<u8')));need(initial_bits==0,'Common native initial fields differ')
    hist=[];final=[];deltas=[];summary={};labels=('x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s','native_rho_kg_m3','kappa','sigma_xx_Pa','sigma_yy_Pa','sigma_zz_Pa','sigma_xy_Pa','sigma_yz_Pa','sigma_xz_Pa')
    for d in sets:
        for row in d['history']:hist.append(dict(mode=d['mode'],**row))
        x0=d['a']['state'][0];v=d['a']['state'][-1]
        for i,row in enumerate(v):final.append(dict(mode=d['mode'],id=fixed+i,x0_m=x0[i,0],z0_m=x0[i,2],**dict(zip(labels,map(float,row))),settlement_m=float(x0[i,2]-row[2])))
        s=dict(end_actual_s=float(d['a']['time'][-1]),samples=len(d['a']),kappa_max=float(np.max(v[:,7])),kappa_nonzero=int(np.count_nonzero(v[:,7])),max_velocity_m_s=float(np.max(np.linalg.norm(v[:,3:6],axis=1))),position_storage='float64' if d['completion']['float64_position_frames']==len(d['a']) else 'native float32 expanded exactly to float64',stress_storage='native float64' if d['completion']['float64_stress_frames']==len(d['a']) else 'native float32 display expanded to float64')
        if args.case=='column':
            exact=1.-v[:,2];observed=-v[:,10]/(2100.*9.81);error=observed-exact;s.update(relative_L2_sigma_zz_vs_H1_current_z=float(np.linalg.norm(error)/np.linalg.norm(exact)),normalized_sigma_zz_RMSE=float(np.sqrt(np.mean(error**2))),normalized_sigma_zz_max_abs=float(np.max(np.abs(error))))
        summary[d['mode']]=s
    for part,(time,v) in enumerate(zip(old['a']['time'],old['a']['state'])):
        j=int(np.argmin(np.abs(new['a']['time']-time)));dt=float(new['a']['time'][j]-time);e=new['a']['state'][j]-v;ds=e[:,8:14];frob=np.sum(ds[:,:3]**2,axis=1)+2*np.sum(ds[:,3:]**2,axis=1)
        deltas.append(dict(old_part=part,new_nearest_part=j,old_actual_time_s=float(time),new_actual_time_s=float(new['a']['time'][j]),time_gap_s=dt,within_1e_14_s=abs(dt)<=1e-14,comparison='matched_actual_time' if abs(dt)<=1e-14 else 'nearest_actual_time_descriptive_only',position_XYZ_RMS_m=float(np.sqrt(np.mean(np.sum(e[:,:3]**2,axis=1)))),velocity_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(e[:,3:6]**2,axis=1)))),rho_RMS_kg_m3=float(np.sqrt(np.mean(e[:,6]**2))),kappa_RMS=float(np.sqrt(np.mean(e[:,7]**2))),sigma_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob))),sigma_component_max_abs_Pa=float(np.max(np.abs(ds)))))
    outputs=[t/'figures'/(prefix+s) for s in ('_history.csv','_final.csv','_differences.csv')]
    for path,rows in zip(outputs,(hist,final,deltas)):need(not path.exists(),'Retained CSV protected');write(path,rows)
    fig,ax=plt.subplots(2,2,figsize=(11,8),layout='constrained');colors={'old':'tab:blue','new':'tab:orange'}
    for d in sets:
        mode=d['mode'];color=colors[mode];tm=d['a']['time'];v=d['a']['state'][-1];hh=d['history'];line=lambda key:np.array([float(r[key]) for r in hh]);label=mode+' @ '+format(tm[-1],'.9g')+' s'
        if args.case=='column':
            ax[0,0].scatter(-v[:,10]/(2100*9.81),v[:,2],s=7,alpha=.5,label=label,color=color);ax[0,0].set(xlabel='-sigma_zz / (rho0 g H)',ylabel='current z (m)',title='Static H=1 reference (short window is transient)');ax[0,1].plot(tm,line('top_material_settlement_m')*1000,color=color,label=mode+' top');ax[0,1].plot(tm,line('bottom_material_settlement_m')*1000,'--',color=color,label=mode+' bottom');ax[0,1].set(xlabel='actual time (s)',ylabel='fixed-material settlement (mm)')
        else:
            ax[0,0].scatter(v[:,0],v[:,2],s=4,alpha=.45,label=label,color=color);ax[0,0].set(xlabel='x (m)',ylabel='z (m)',title='All native soil positions; no fitted boundary');ax[0,0].set_aspect('equal',adjustable='datalim');ax[0,1].plot(tm,line('sigma_Frobenius_RMS_Pa'),color=color,label=mode);ax[0,1].set(xlabel='actual time (s)',ylabel='effective/total dry stress Frobenius RMS (Pa)')
        ax[1,0].plot(tm,line('kappa_max'),color=color,label=mode);ax[1,1].plot(tm,line('velocity_RMS_m_s'),color=color,label=mode)
    if args.case=='column':ax[0,0].plot([1,0],[0,1],'k:',label='H=1 hydrostatic reference')
    ax[1,0].set(xlabel='actual time (s)',ylabel='maximum saved kappa');ax[1,1].set(xlabel='actual time (s)',ylabel='velocity XYZ RMS (m/s)')
    for a in ax.flat:a.grid(alpha=.25);a.legend(fontsize=8)
    fig.suptitle(('Feng static dry column' if args.case=='column' else 'Granular column a=1')+' | old basic fast vs unified return | CPU1\nSame input, adaptive dt; differences at unequal saved times are descriptive',fontsize=11);fig.savefig(png,dpi=160);plt.close(fig)
    consumed=[v for d in sets for v in d['source']];need(all(stat(v['path'])==v for v in consumed),'Consumed closed export changed');result=dict(stage=prefix+'.review',passed=True,case=args.case,window=args.window,initial_common_14_field_different_scalar_bits=initial_bits,summary=summary,maximum_nearest_actual_time_gap_s=max(abs(v['time_gap_s']) for v in deltas),maximum_descriptive_sigma_Frobenius_RMS_gap_Pa=max(v['sigma_Frobenius_RMS_Pa'] for v in deltas),maximum_descriptive_position_XYZ_RMS_gap_m=max(v['position_XYZ_RMS_m'] for v in deltas),interpolation=False,new_5Pa_or_half_gate=False,physical_acceptance=False,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(png),*[stat(x) for x in outputs]],SHA_scans=0);save(check,result);print(json.dumps({k:v for k,v in result.items() if k not in ('consumed','files')},indent=2))
if __name__=='__main__':main()
