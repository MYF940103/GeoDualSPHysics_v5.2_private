"""Offline principal-total-stress observations for the retained, interrupted C08 PRE."""
import argparse,json
from pathlib import Path
import c08_h18_loss_review_r1 as loss

old=loss.old
np,need,path,stat,read,bind=old.np,old.need,old.path,old.stat,old.read,old.bind
T=old.T
TAG='c08_h18_loss_spectrum_r1'
EVENTS=('kappa_gt0','z_lt0','NN_lt0p7dp','lambda_max_gt0Pa','lambda_max_gt100Pa')
OBSERVATION_PA=100.


def clock_row(part,time,step,saved,dt,signed,complete):
    return dict(part=part,time_s=float(time),completed_step=int(step),saved_step=int(saved),dt_s=float(dt),signed_dterror_s=float(signed),complete_original_ID_set=bool(complete))


def total_spectrum(state):
    """Full 3x3 double eigensystem: kk=(xx,yy,zz), ij=(xy,yz,xz)."""
    kk=state['SigmaState_kk']
    ij=state['SigmaState_ij']
    need(kk.dtype==ij.dtype==np.dtype('<f8'),'Full double six-component stress state required')
    tensor=np.empty((len(kk),3,3),dtype=np.float64)
    tensor[:,0,0]=kk[:,0]-state['PorePress'][:,0]
    tensor[:,1,1]=kk[:,1]-state['PorePress'][:,0]
    tensor[:,2,2]=kk[:,2]-state['PorePress'][:,0]
    tensor[:,0,1]=tensor[:,1,0]=ij[:,0]
    tensor[:,1,2]=tensor[:,2,1]=ij[:,1]
    tensor[:,0,2]=tensor[:,2,0]=ij[:,2]
    need(np.isfinite(tensor).all(),'Nonfinite total stress is not an observation')
    values=np.linalg.eigvalsh(tensor,UPLO='L')
    need(values.shape==(len(kk),3) and np.isfinite(values).all(),'Principal-stress calculation failed')
    return values


def population_row(clock,state,ids,eigen,mask,name,original_count):
    values=eigen[mask]
    largest=values[:,-1]
    positive=np.maximum(values,0.)
    posmax=np.maximum(largest,0.)
    selected=ids[mask]
    where=int(np.argmax(largest))
    offplane=state['SigmaState_ij'][mask,:2]
    return dict(**clock,population=name,original_IDs=original_count,present_IDs=int(mask.sum()),missing_original_IDs=original_count-int(mask.sum()),lambda_max_Pa=float(largest.max()),lambda_max_native_ID=int(selected[where]),lambda_max_signed_RMS_present_Pa=float(np.sqrt(np.mean(largest*largest))),positive_lambda_max_RMS_present_Pa=float(np.sqrt(np.mean(posmax*posmax))),positive_spectrum_Frobenius_RMS_present_Pa=float(np.sqrt(np.mean(np.sum(positive*positive,axis=1)))),particles_lambda_max_gt0Pa=int(np.count_nonzero(largest>0.)),particles_lambda_max_gt100Pa=int(np.count_nonzero(largest>OBSERVATION_PA)),positive_eigenvalues_count=int(np.count_nonzero(values>0.)),max_abs_xy_yz_Pa=float(np.max(np.abs(offplane))))


def missing_focus(clock,identity,initial):
    return dict(**clock,native_id=int(identity),present=False,initial_x_m=float(initial[0]),initial_y_m=float(initial[1]),initial_z_m=float(initial[2]),x_m=None,y_m=None,z_m=None,kappa=None,J=None,p_Pa=None,speed_m_s=None,NN_m=None,NN_over_dp=None,lambda_min_Pa=None,lambda_mid_Pa=None,lambda_max_Pa=None,positive_spectrum_Frobenius_Pa=None,max_abs_xy_yz_Pa=None,kappa_gt0=None,z_lt0=None,NN_lt0p7dp=None,lambda_max_gt0Pa=None,lambda_max_gt100Pa=None)


def analyze(bundle,tail,final):
    first=old.read22(bundle,0)
    initial=np.array(first['Posd'],copy=True)
    soil_ids=np.arange(loss.FIXED,loss.NODES,dtype=np.uint32)
    # Select from actual typed0 positions; an ID is never converted into a guessed layer.
    distance=np.linalg.norm(initial[soil_ids][:,(0,2)]-initial[loss.LOST,(0,2)],axis=1)
    near=soil_ids[np.argsort(distance,kind='stable')[:9]]
    need(loss.LOST in near and len(np.unique(near))==9,'Actual lost point plus eight initial soil neighbours required')
    focus_initial=[dict(native_id=int(i),x0_m=float(initial[i,0]),y0_m=float(initial[i,1]),z0_m=float(initial[i,2]),initial_distance_to_lost_m=float(np.linalg.norm(initial[i,(0,2)]-initial[loss.LOST,(0,2)]))) for i in near]
    # -1 is an observation index, never a padded native material value.
    first_events=np.full((loss.SOIL,len(EVENTS)),-1,dtype=np.int32)
    populations=[];focus=[];geometry=[];clocks=[];event_snapshots={}
    for part in range(loss.COUNT+1):
        complete=part<loss.COUNT
        if complete:
            state=first if part==0 else old.read22(bundle,part)
            q=bundle['clocks'][part]
            clock=clock_row(part,q['time_s'],q['completed_step'],q['saved_step'],q['dt_s'],q['signed_dterror_s'],True)
        else:
            state=tail
            clock=clock_row(part,final['time_s'],final['completed_step'],final['saved_step'],final['dt_s'],final['signed_dterror_s'],False)
            need(final['nonfinite_values']==0 and final['fixed_marker_checks']==loss.FIXED and final['ledger_checks']==final['rho_cache_bits_checks']==loss.SOIL-1 and final['P0_bits_checks']==final['kappa_nondecreasing_checks']==loss.NODES-1 and final['max_ledger_relative_error']<=5e-13 and final['scalar_clock_error_s']<=1e-14,'Original incomplete-final receipt budgets differ')
            # Keep final sparse order. No lost ID is appended, sorted in, or set to zero.
            ids=state['Idp'][:,0]
            need(len(ids)==7059 and len(np.unique(ids))==7059 and np.array_equal(np.setdiff1d(np.arange(loss.NODES,dtype=np.uint32),ids),[loss.LOST]),'Final sparse ID domain differs')
            need(all(np.isfinite(state[name]).all() for name,_,_ in old.SCHEMA),'Original final22 finite guard differs')
            need(float(state['time'])==clock['time_s'] and clock['signed_dterror_s']<=1e-14,'Original final scalar/signed clock guard differs')
            need(np.array_equal(state['PorePress0'][:,0].view('<u4'),first['PorePress0'][ids,0].view('<u4')) and np.array_equal(state['ExcessPorePress'][:,0],np.float32(state['PorePress'][:,0]-state['PorePress0'][:,0])),'Actual final P0/excess differs')
            need(np.all(state['Kplastic'][:,0]>=bundle['frames'][loss.COUNT-1]['Kplastic'][ids,0]),'Actual final present-ID kappa decreases')
        ids=state['Idp'][:,0]
        need(np.all(state['Posd'][:,1]==0.),'This native source must remain the actual Y=0 plane')
        spectrum=total_spectrum(state)
        soil=ids>=loss.FIXED;fixed=~soil
        for name,mask,original in [('soil',soil,loss.SOIL),('fixed',fixed,loss.FIXED),('all_present',np.ones(len(ids),dtype=bool),loss.NODES)]:
            populations.append(population_row(clock,state,ids,spectrum,mask,name,original))
        sid=ids[soil].astype(np.int64);pos=state['Posd'][soil]
        tree=old.cKDTree(pos[:,(0,2)])
        nearest,_=tree.query(pos[:,(0,2)],k=2,workers=1)
        nn=nearest[:,1]
        largest=spectrum[soil,-1]
        kap=state['Kplastic'][soil,0]
        flags=np.column_stack((kap>0.,pos[:,2]<0.,nn<.7*old.DP,largest>0.,largest>OBSERVATION_PA))
        offsets=sid-loss.FIXED
        for e,name in enumerate(EVENTS):
            new=flags[:,e]&(first_events[offsets,e]<0)
            first_events[offsets[new],e]=part
            if name not in event_snapshots and flags[:,e].any():
                indexes=np.flatnonzero(flags[:,e])
                event_snapshots[name]=[dict(**clock,native_id=int(sid[i]),initial_x_m=float(initial[sid[i],0]),initial_y_m=float(initial[sid[i],1]),initial_z_m=float(initial[sid[i],2]),x_m=float(pos[i,0]),z_m=float(pos[i,2]),kappa=float(kap[i]),J=float(state['PoroVolumeRatio'][soil,0][i]),NN_over_dp=float(nn[i]/old.DP),lambda_max_Pa=float(largest[i])) for i in indexes]
        geometry.append(dict(**clock,present_soil=int(soil.sum()),soil_below_bed=int(np.count_nonzero(flags[:,1])),minimum_soil_z_m=float(pos[:,2].min()),minimum_soil_z_ID=int(sid[int(np.argmin(pos[:,2]))]),NN_min_over_dp=float(nn.min()/old.DP),soil_NN_lt0p7dp=int(np.count_nonzero(flags[:,2])),maximum_kappa=float(kap.max())))
        index={int(i):at for at,i in enumerate(ids)}
        soil_index={int(i):at for at,i in enumerate(sid)}
        for identity in near:
            row=missing_focus(clock,identity,initial[identity])
            if int(identity) in index:
                at=index[int(identity)];s=soil_index[int(identity)];v=spectrum[at];xyz=state['Posd'][at];vel=state['Vel'][at]
                row.update(present=True,x_m=float(xyz[0]),y_m=float(xyz[1]),z_m=float(xyz[2]),kappa=float(kap[s]),J=float(state['PoroVolumeRatio'][at,0]),p_Pa=float(state['PorePress'][at,0]),speed_m_s=float(np.linalg.norm(vel.astype(np.float64))),NN_m=float(nn[s]),NN_over_dp=float(nn[s]/old.DP),lambda_min_Pa=float(v[0]),lambda_mid_Pa=float(v[1]),lambda_max_Pa=float(v[2]),positive_spectrum_Frobenius_Pa=float(np.linalg.norm(np.maximum(v,0.))),max_abs_xy_yz_Pa=float(np.max(np.abs(state['SigmaState_ij'][at,:2]))))
                row.update({name:bool(flags[s,e]) for e,name in enumerate(EVENTS)})
            focus.append(row)
        clocks.append(clock)
    need(len(clocks)==534 and len(populations)==534*3 and len(focus)==534*9,'All actual534 saves and focus rows must be represented')
    need(not [q for q in focus if q['part']==533 and q['native_id']==loss.LOST][0]['present'],'Lost3060 must remain missing from the final material record')
    events=[]
    for at,identity in enumerate(soil_ids):
        row=dict(native_id=int(identity),initial_x_m=float(initial[identity,0]),initial_y_m=float(initial[identity,1]),initial_z_m=float(initial[identity,2]),present_saved_states=533 if identity==loss.LOST else 534,final_native_present=bool(identity!=loss.LOST))
        for e,name in enumerate(EVENTS):
            p=int(first_events[at,e]);row[name+'_first_saved_part']=None if p<0 else p
            row[name+'_first_saved_time_s']=None if p<0 else clocks[p]['time_s']
            row[name+'_previous_saved_time_s']=None if p<=0 else clocks[p-1]['time_s']
        events.append(row)
    global_first={name:dict(first_saved_part=None if name not in event_snapshots else event_snapshots[name][0]['part'],first_saved_time_s=None if name not in event_snapshots else event_snapshots[name][0]['time_s'],first_IDs=[] if name not in event_snapshots else [q['native_id'] for q in event_snapshots[name]],first_observed_ID_count=0 if name not in event_snapshots else len(event_snapshots[name])) for name in EVENTS}
    snapshot_rows=[row|dict(observation_event=name) for name,rows in event_snapshots.items() for row in rows]
    return dict(populations=populations,focus=focus,geometry=geometry,clocks=clocks,events=events,initial_focus=focus_initial,global_first=global_first,first_snapshots=snapshot_rows,lost_first_events=events[loss.LOST-loss.FIXED])


def plot(result,prefix):
    soil=[q for q in result['populations'] if q['population']=='soil'];g=result['geometry'];files=[]
    fig,axes=old.plt.subplots(2,3,figsize=(14,8),layout='constrained')
    for key,label in [('lambda_max_Pa','Maximum principal total stress'),('positive_lambda_max_RMS_present_Pa','Positive maximum-principal RMS'),('positive_spectrum_Frobenius_RMS_present_Pa','Positive spectrum Frobenius RMS')]:
        axes.flat[0].plot([q['time_s'] for q in soil],[q[key]*.001 for q in soil],label=label)
    axes.flat[0].set_ylabel('kPa');axes.flat[0].legend(fontsize=7)
    for key,label in [('particles_lambda_max_gt0Pa','lambda_max > 0 Pa'),('particles_lambda_max_gt100Pa','lambda_max > 100 Pa')]:axes.flat[1].plot([q['time_s'] for q in soil],[q[key] for q in soil],label=label)
    axes.flat[1].set_ylabel('Present original soil IDs');axes.flat[1].legend(fontsize=7)
    for ax,key,title in [(axes.flat[2],'soil_below_bed','Soil z < 0'),(axes.flat[3],'NN_min_over_dp','Minimum soil NN / dp'),(axes.flat[4],'maximum_kappa','Maximum kappa')]:ax.plot([q['time_s'] for q in g],[q[key] for q in g]);ax.set_title(title)
    for identity in [q['native_id'] for q in result['initial_focus']]:
        rr=[q for q in result['focus'] if q['native_id']==identity and q['present']]
        axes.flat[5].plot([q['time_s'] for q in rr],[q['lambda_max_Pa']*.001 for q in rr],label=str(identity),lw=1.7 if identity==loss.LOST else .7)
    axes.flat[5].set_title('Lost3060 and its eight initial neighbours');axes.flat[5].set_ylabel('Maximum principal total stress [kPa]');axes.flat[5].legend(fontsize=6,ncol=3)
    for ax in axes.flat:ax.set_xlabel('Actual source time [s]');ax.grid(alpha=.2)
    fig.suptitle('Interrupted PRE: all534 actual saves; final population has4999 soil IDs\n0/100Pa are observation levels, not acceptance limits; no AS feedback was active')
    dest=Path(str(prefix)+'_history.png');fig.savefig(dest,dpi=170);old.plt.close(fig);files.append(dest)
    fig,axes=old.plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for ax,(key,title,scale) in zip(axes.flat,[('z_m','Material z [m]',1.),('NN_over_dp','Nearest soil distance / dp',1.),('kappa','Kappa',1.),('lambda_max_Pa','Maximum principal total stress [kPa]',.001)]):
        for identity in [q['native_id'] for q in result['initial_focus']]:
            rr=[q for q in result['focus'] if q['native_id']==identity and q['present']];ax.plot([q['time_s'] for q in rr],[q[key]*scale for q in rr],label=str(identity),lw=1.7 if identity==loss.LOST else .7)
        ax.set(title=title,xlabel='Actual source time [s]');ax.grid(alpha=.2)
    axes[0,0].axhline(0,color='k',ls='--',lw=.6);axes[0,1].axhline(.7,color='k',ls='--',lw=.6);axes[0,0].legend(fontsize=7,ncol=3)
    fig.suptitle('Fixed initial material neighbourhood; missing final3060 is not padded\nSame-save events have unresolved update-level order; no causal or repair claim')
    dest=Path(str(prefix)+'_focus.png');fig.savefig(dest,dpi=170);old.plt.close(fig);files.append(dest)
    return files


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--execution-authorized',action='store_true');a=parser.parse_args()
    need(a.execution_authorized,'Root full-read before one explicit offline analysis')
    prefix=T/'figures'/TAG;check=T/'logs'/(TAG+'.check.json')
    need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')),'Existing or partial spectrum outputs are protected')
    consumed=[stat(a.manifest),stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(loss.__file__),stat(old.__file__),stat(loss.plastic.__file__)]
    outcome=dict(stage=TAG,analysis_complete=False,whole_run_passed=False,certified_PRE=False,source_equilibrium_accepted=False,physical_acceptance=False,consumed=consumed)
    try:
        bundle,tail,meta,excluded,whole=loss.load(read(a.manifest),consumed)
        result=analyze(bundle,tail,meta);files=[]
        for key in ('populations','focus','geometry','clocks','events','initial_focus','first_snapshots'):
            if key=='first_snapshots' and not result[key]:continue
            dest=Path(str(prefix)+'_'+key+'.csv');old.write_csv(dest,result[key]);files.append(dest)
        files+=plot(result,prefix)
        need(all(stat(q['path'])==q for q in consumed),'Existing native/physical receipts or payload changed')
        outcome.update(analysis_complete=True,actual_saved_frames=534,strict_prefix_frames=533,incomplete_final_present_IDs=7059,incomplete_final_missing_IDs=[loss.LOST],all534_actual_clocks_accounted_for=True,full_double_six_component_eigvalsh=True,stress_definition='sigma_effective - native_pore_pressure * identity; kk(xx,yy,zz), ij(xy,yz,xz)',positive_spectrum_RMS_definition='sqrt(mean_present(sum(max(lambda_k,0)^2))), all three eigenvalues',positive_lambda_RMS_definition='sqrt(mean_present(max(lambda_max,0)^2))',population_denominators_are_present_IDs=True,initial_neighbour_selection='Actual typed0 Posd of3060 plus eight smallest initial x/z soil distances, stable originalID tie order',initial_focus=result['initial_focus'],global_first_saved_events=result['global_first'],lost_first_saved_events=result['lost_first_events'],observation_levels_Pa=[0,OBSERVATION_PA],observation_levels_are_not_acceptance_limits=True,observed_near_distance_dp=.7,no_2D_spectral_shortcut=True,no_sigma_zz_substitution=True,actual_AS_active=False,actual_AS_tensor_or_force_replayed=False,same_saved_time_does_not_establish_event_order=True,unsaved_first_crossing_time_inferred=False,no_interpolation_or_native_rewrite=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed_stats_unchanged=True,files=[stat(q) for q in files])
    except Exception as error:outcome.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(outcome,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
