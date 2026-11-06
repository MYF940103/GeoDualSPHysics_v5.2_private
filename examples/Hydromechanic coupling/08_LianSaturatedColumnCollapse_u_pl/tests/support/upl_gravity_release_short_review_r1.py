"""Closed OFF/ON actual native records only: byte regression and same-dt backend checks."""
import argparse,json,struct
from pathlib import Path
from upl_plastic_periodic_pair_r1 import np,plt,SCHEMA,TYPES,need,js,stat,table,write,frob,bound
T=Path(__file__).resolve().parents[1];CORE=['part','file','time_s','completed_step','saved_step','dt_s','signed_dterror_s','dterror_interval_empty']
FLOAT_CORE={'time_s','dt_s','signed_dterror_s'};inputs=[stat(Path(__file__))]
def bits(x):return struct.pack('<d',float(x))
def clockcore(c):return tuple(bits(c[k]) if k in FLOAT_CORE else c[k].encode('utf-8') if k=='file' else struct.pack('<I',int(c[k])) for k in CORE)
def key(r):return (r['completed'],r['raw'][:8].tobytes())
def load(tag,new):
    d=T/'outputs'/(tag+'_native_r1');cp=T/'logs'/(tag+'_native_r1.check.json');c=js(cp)
    need(c['passed'] and c['original_native_guards_passed'] and c['consumed_stats_unchanged'],'All original native guards must be closed: '+tag)
    inputs.append(stat(cp));inputs.extend(bound(c[k]) for k in ('source_run','reader_call','reader_build','native_completion'))
    if new:
        inputs.extend(bound(c[k]) for k in ('source_run_call','source_build'));inputs.extend(bound(e) for e in c['files'])
    run=js(c['source_run']['path']);need(run['passed'] and run['actual_exit']==0 and run['consumed_stats_unchanged'],'Original run not closed: '+tag)
    done=js(d/'completion.json');samples=done['samples'];need(done['passed'] and samples==run['saved_frames'] and done['completed_steps']==run['actual_steps'] and done['typed_arrays']==22,'Native frame/count identity differs')
    if new:
        on='_on_' in tag;need(done['stage']=='upl_gravity_release_native_r1' and done['input_run_tag']==tag and done['completed_steps']==(800 if on else 400),'New release profile scope differs')
        counts=done['phase_saved_frames'];need(sum(counts)==samples and counts[0]>0 and (counts[1]>0 if on else counts[1]==0),'Actual phase frame counts differ')
        for flag in ('all22_arrays_finite_and_original_ID_aligned','actual_scalar_clock_verified','actual_metadata_counted_before_export_headers','original_case_registry_unchanged','only_declared_fixed_ID_retirement_allowed','saved_FS23_soil_pressure_nonpositive'):need(done[flag],'Missing original phase/native guard: '+flag)
        need(done['soil_ledger_checks']==5000*samples and done['soil_cache_float_bits_checks']==5000*samples and done['soil_noninitial_kappa_monotonic_checks']==5000*(samples-1) and done['noninitial_signed_intervals']==samples-1,'Incomplete original native counters')
    else:
        need(done['stage']=='upl_prestress_native_r1' and done['completed_steps']==400 and done['total_native_IDs']==7060 and done['all22_arrays_finite_and_ID_aligned'] and done['actual_scalar_clock_verified'],'Retained Release control profile differs');counts=[samples,0]
    layout=table(d/'typed22_layout.csv');need(len(layout)==22,'Actual22 layout records required')
    for row,(name,kind,nc) in zip(layout,SCHEMA):need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,nc,TYPES[kind].itemsize*nc),'Actual native typed layout differs')
    clocks=table(d/'clocks.csv');need(len(clocks)==samples and list(clocks[0])[:8]==CORE,'Complete original eight core clock fields required')
    ids=table(d/'native_ids.csv');need(len(ids)==7060 and all(int(r['id'])==i for i,r in enumerate(ids)),'Original7060-ID coordinate ledger differs');x0=np.array([[float(r[k]) for k in ('x0','y0','z0')] for r in ids])
    byphase={};blobs={}
    for phase,count in enumerate(counts):
        if not count:continue
        p=d/(('phase'+str(phase)+'_typed22.bin') if new else 'typed22.bin');blob=p.read_bytes();n=7060 if phase==0 else 6800;size=8+n*212
        need(len(blob)==12+count*size and struct.unpack('<III',blob[:12])==(n,22,count),'Genuine actualN/22/phase-count raw header/file size differs');blobs[phase]=blob;records=[]
        wanted=np.arange(7060) if phase==0 else np.concatenate((np.arange(1800),np.arange(2060,7060)))
        for local in range(count):
            start=12+local*size;off=start+8;a={}
            for name,kind,nc in SCHEMA:
                v=np.frombuffer(blob,dtype=TYPES[kind],count=n*nc,offset=off);need(np.isfinite(v).all(),'Nonfinite native array');a[name]=v.reshape(n,nc) if nc>1 else v;off+=n*TYPES[kind].itemsize*nc
            need(off==start+size and np.array_equal(a['Idp'],wanted),'Actual original IDs/current phase membership differs');records.append(dict(a=a,raw=memoryview(blob)[start:start+size],time=struct.unpack('<d',blob[start:start+8])[0],phase=phase,local=local,n=n))
        byphase[phase]=records;inputs.append(stat(p))
    frames=[];localcounts=[0,0];scalar=0.;previous=0
    for part,c in enumerate(clocks):
        phase=int(c['phase']) if new else 0;local=int(c['phase_local_index']) if new else part;need(phase in byphase and local==localcounts[phase] and int(c['part'])==part,'Actual phase/local/part clock order differs');localcounts[phase]+=1;r=byphase[phase][local]
        completed=int(c['completed_step']);need((completed==0 and int(c['saved_step'])==0) if part==0 else completed>previous and int(c['saved_step'])==completed-1,'Native zero-based Step sequence differs')
        for _ in range(previous,completed):scalar+=2.5e-6
        previous=completed;need(bits(r['time'])==bits(c['time_s']) and abs(r['time']-scalar)<=1e-14 and float(c['dt_s'])==2.5e-6,'Actual scalar clock/raw clock differs')
        if part:need(int(c['dterror_interval_empty'])==0 and np.isfinite(float(c['signed_dterror_s'])) and float(c['signed_dterror_s'])<=1e-14,'Original signed/nonempty interval guard differs')
        if new:need(int(c['actual_native_IDs'])==r['n'],'Actual phase clock currentN differs')
        r.update(part=part,completed=completed,clock=c);frames.append(r)
    need(localcounts==counts and previous==done['completed_steps'] and bits(frames[-1]['time'])==bits(done['actual_end_s']),'Incomplete actual frame coverage')
    inputs.extend(stat(d/name) for name in ('completion.json','typed22_layout.csv','native_ids.csv','clocks.csv','history.csv'))
    return dict(tag=tag,frames=frames,blobs=blobs,done=done,x0=x0)

def bitrow(name,backend,a,b):
    return dict(comparison=name,backend=backend,left_part=a['part'],right_part=b['part'],completed_step=a['completed'],actual_time_s=a['time'],actual_time_bits=key(a)[1].hex(),native_IDs=a['n'],all22_native_record_bytes_equal=a['raw']==b['raw'],eight_core_clock_bits_equal=clockcore(a['clock'])==clockcore(b['clock']),left_signed_dterror_bits=bits(a['clock']['signed_dterror_s']).hex(),right_signed_dterror_bits=bits(b['clock']['signed_dterror_s']).hex())
def physical(r,x0):
    a=r['a'];ids=a['Idp'];soil=np.flatnonzero(ids>=2060);need(np.array_equal(ids[soil],np.arange(2060,7060)),'All5000 soilIDs must be selected from actual Idp, not a phase-dependent slot offset')
    z0=x0[ids[soil],2];u=(a['Posd'][soil]-x0[ids[soil]])*1000.;p=a['PorePress'][soil].astype(float);total=np.column_stack((a['SigmaState_kk'][soil]-p[:,None],a['SigmaState_ij'][soil]));eff=np.column_stack((a['SigmaState_kk'][soil],a['SigmaState_ij'][soil]))
    return dict(ids=ids[soil],soil=soil,u=u,p=p,total=total,eff=eff,top=z0>=z0.max()-2*float(np.float32(.048)),bottom=z0<=z0.min()+2*float(np.float32(.048)))
def run(prefix):
    paths={k:Path(str(prefix)+s) for k,s in dict(bits='_bitwise.csv',pairs='_pairs.csv',history='_history.csv',unmatched='_unmatched.csv',png='.png',check='.check.json').items()};need(not any(p.exists() for p in paths.values()),'Existing review artifacts protected')
    data={(mode,b):load('upl_gravity_release_'+mode+'_'+b+'_r1',True) for mode in ('off','on') for b in ('CPU','GPU')};old={b:load('upl_prestress_check_'+('release_CPU' if b=='CPU' else 'GPU')+'_r1',False) for b in ('CPU','GPU')};rows=[];unmatched=[];fullfiles={}
    for b in ('CPU','GPU'):
        off,on,retained=data['off',b],data['on',b],old[b];need(np.array_equal(off['x0'],on['x0']) and np.array_equal(off['x0'],retained['x0']),'Same-backend original material coordinates differ')
        fullfiles[b]=off['blobs'][0]==retained['blobs'][0];need(len(off['frames'])==len(retained['frames']),'OFF did not retain all control records')
        for a,c in zip(off['frames'],retained['frames']):rows.append(bitrow('OFF_vs_retained_all',b,a,c))
        left={key(r):r for r in on['frames'] if r['phase']==0};right={key(r):r for r in off['frames']};need(len(left)==sum(r['phase']==0 for r in on['frames']) and len(right)==len(off['frames']),'Duplicate actual clock/step key')
        shared=set(left)&set(right);eligible={k for k,r in right.items() if r['completed']<380};need(shared==eligible and shared,'ON must retain every actually shared pre-event control state')
        need([r['completed'] for k,r in left.items() if k not in shared]==[380] and on['done']['event_completed_step']==380,'Only the genuine forced380 phase0 state may be unshared')
        for k in sorted(shared):rows.append(bitrow('ON_vs_OFF_shared_pre380_only',b,left[k],right[k]))
        for side,source in (('ON_phase0',left),('OFF',right)):
            for k,r in source.items():
                if k not in shared:unmatched.append(dict(backend=b,source=side,part=r['part'],completed_step=r['completed'],actual_time_s=r['time'],time_bits=k[1].hex(),shared=False,reason='forced pre-event380' if side=='ON_phase0' else 'control after release threshold; not a shared ON-pre record'))
    cpu,gpu=data['on','CPU'],data['on','GPU'];need(np.array_equal(cpu['x0'],gpu['x0']),'CPU/GPU original coordinates differ');cm={key(r):r for r in cpu['frames']};gm={key(r):r for r in gpu['frames']};need(len(cm)==len(cpu['frames']) and len(gm)==len(gpu['frames']) and set(cm)==set(gm),'ON CPU/GPU actual time/step sets differ; no interpolation')
    pairs=[]
    for k in sorted(cm):
        a,b=cm[k],gm[k];need(a['phase']==b['phase'] and a['n']==b['n'],'Same-time backend release phase/currentN differs');ca,gb=physical(a,cpu['x0']),physical(b,gpu['x0']);dp=gb['p']-ca['p'];du=gb['u']-ca['u'];sa,sb=ca['soil'],gb['soil']
        r=dict(completed_step=a['completed'],actual_time_s=a['time'],phase=a['phase'],CPU_part=a['part'],GPU_part=b['part'],actual_native_IDs=a['n'],soil_IDs=5000,pressure_difference_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),pressure_difference_max_Pa=float(np.abs(dp).max()),material_XYZ_displacement_difference_max_mm=float(np.linalg.norm(du,axis=1).max()),total_stress_difference_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(gb['total']-ca['total'])**2))),effective_stress_difference_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(gb['eff']-ca['eff'])**2))))
        for field,label in (('PoroVolumeRatio','J'),('PoroPorosity','porosity'),('PoroMixtureDensity','density'),('PoroHydraulicConductivity','conductivity'),('Kplastic','kappa')):r[label+'_difference_max']=float(np.abs(b['a'][field][sb]-a['a'][field][sa]).max())
        pairs.append(r)
    history=[]
    for (mode,b),d in data.items():
        for r in d['frames']:
            f=physical(r,d['x0']);q=r['a'];s=f['soil'];history.append(dict(mode=mode,backend=b,part=r['part'],completed_step=r['completed'],actual_time_s=r['time'],phase=r['phase'],soil_IDs=5000,p_mean_Pa=float(f['p'].mean()),p_RMS_Pa=float(np.sqrt(np.mean(f['p']**2))),native_excess_mean_Pa=float(q['ExcessPorePress'][s].mean(dtype=float)),top_2h_settlement_mean_mm=float(-f['u'][f['top'],2].mean()),bottom_2h_settlement_mean_mm=float(-f['u'][f['bottom'],2].mean()),effective_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(f['eff'])**2))),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(f['total'])**2))),J_min=float(q['PoroVolumeRatio'][s].min()),J_max=float(q['PoroVolumeRatio'][s].max()),kappa_max=float(q['Kplastic'][s].max()),FS23_count=int(np.isin(q['FSType'][s],(2,3)).sum())))
    for name,records in (('bits',rows),('pairs',pairs),('history',history),('unmatched',unmatched)):write(paths[name],records)
    fig,axes=plt.subplots(2,2,figsize=(11.5,8.1));colors={'CPU':'#1667a6','GPU':'#d17a12'}
    for b in ('CPU','GPU'):
        for mode in ('off','on'):
            h=[r for r in history if r['backend']==b and r['mode']==mode];x=[r['actual_time_s']*1000 for r in h];style=dict(color=colors[b],label=b+' '+mode.upper(),ls='none' if b=='GPU' else '-' if mode=='on' else '--',marker='o' if b=='GPU' else None,mfc='none',ms=4)
            axes[0,0].plot(x,[r['p_RMS_Pa']*.001 for r in h],**style)
        h=[r for r in history if r['backend']==b and r['mode']=='on'];x=[r['actual_time_s']*1000 for r in h]
        for field,label,ls in (('top_2h_settlement_mean_mm','top_2h','-'),('bottom_2h_settlement_mean_mm','bottom_2h','--')):axes[0,1].plot(x,[r[field] for r in h],color=colors[b],label=b+' '+label,ls='none' if b=='GPU' else ls,marker='o' if b=='GPU' else None,mfc='none',ms=4)
        axes[1,0].plot(x,[r['total_stress_Frobenius_RMS_Pa']*.001 for r in h],color=colors[b],label=b+' ON total stress',ls='none' if b=='GPU' else '-',marker='o' if b=='GPU' else None,mfc='none',ms=4)
        axes[1,1].plot(x,[r['phase'] for r in h],ls='none',marker='o' if b=='GPU' else '.',mfc='none' if b=='GPU' else colors[b],color=colors[b],label=b+' saved phase')
    event=cpu['done']['genuine_pre_event_time_s']*1000
    for ax,title,label in zip(axes.flat,('Actual pore pressure','Fixed initial material settlement / ON','Actual total stress / ON','Phase at actual saved records'),('pressure RMS (kPa)','downward settlement (mm)','Frobenius RMS (kPa)','phase0 preload / phase1 released')):ax.axvline(event,color='#777777',ls=':',lw=1);ax.set(title=title,xlabel='actual saved time (ms)',ylabel=label);ax.grid(alpha=.22);ax.legend(fontsize=7)
    axes[1,1].set_yticks((0,1));fig.suptitle('Case08 short OFF/ON implementation regression; no half-step or physical acceptance',fontsize=12);fig.text(.5,.012,'Vertical line: actual stored release at the genuine phase0 pre-event save. Phase markers show only native saved records.\nFinite-positive surface projection is part of the new boundary law; no native field, header, clock or interval was rewritten.',ha='center',fontsize=8);fig.tight_layout(rect=(0,.06,1,.95));fig.savefig(paths['png'],dpi=180);plt.close(fig)
    passed=all(fullfiles.values()) and all(r['all22_native_record_bytes_equal'] and r['eight_core_clock_bits_equal'] for r in rows) and all(r['pressure_difference_RMS_Pa']<=5 and r['material_XYZ_displacement_difference_max_mm']<=.005 for r in pairs)
    need(all(stat(e['path'])==e for e in inputs),'Consumed closed artifacts changed during review')
    result=dict(stage='upl_gravity_release_short_review_r1',passed=passed,OFF_complete_file_byte_exact_by_backend=fullfiles,bitwise_record_pairs=len(rows),ON_shared_pre_event_pairs_by_backend={b:sum(r['comparison']=='ON_vs_OFF_shared_pre380_only' and r['backend']==b for r in rows) for b in ('CPU','GPU')},unmatched_actual_records=unmatched,ON_CPU_GPU_actual_pairs=len(pairs),maxima={k:max(r[k] for r in pairs) for k in pairs[0] if '_difference_' in k},pressure_RMS_bound_Pa=5,material_XYZ_bound_mm=.005,all22_arrays_compared_in_bitproof=True,signed_clock_dterror_included_without_mask=True,whole_ON_phase0_file_0ULP_claimed=False,half_step_or_theory_or_full_physical_acceptance=False,physical_acceptance=False,figure_visual_QA_pending=True,source_inputs=inputs,outputs=[stat(p) for k,p in paths.items() if k!='check'],SHA_scans=0)
    with paths['check'].open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(passed=passed,maxima=result['maxima'],ON_shared_pairs=result['ON_shared_pre_event_pairs_by_backend'])),flush=True);need(passed,'Keep failed comparisons and plots; no retry, solver or relaxed bounds')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prefix',type=Path,default=T/'figures/upl_gravity_release_short_review_r1');args=ap.parse_args();prefix=args.prefix.resolve();need(prefix.parent==(T/'figures').resolve(),'Use a shallow tests/figures prefix');run(prefix)
