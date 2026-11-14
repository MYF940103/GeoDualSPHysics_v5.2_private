"""Offline polynomial norms and native-pressure operator shadows, no solver."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm

T=Path(__file__).resolve().parents[1]
TAG='c08_h18_quadratic_review_r1'
OPS=('pairC_Eta2','receiverC_Eta2','receiverC_bare')


def table(q):
    with q.open() as f:return list(csv.DictReader(f))


def stat(q):return dict(path=str(q),bytes=q.stat().st_size,mtime_ns=q.stat().st_mtime_ns)


def write(q,rows):
    with q.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true')
    assert parser.parse_args().execution_authorized
    out=T/'outputs';check=T/'logs'/(TAG+'.check.json');prefix=T/'figures'/TAG
    assert not check.exists() and not list(prefix.parent.glob(TAG+'*'))
    files=[Path(__file__),T/'logs/c08_h18_quadratic_r1.check.json',out/'c08_h18_quadratic_r1/completion.json',
           out/'c08_h18_quadratic_r1/quadratic.csv',out/'c08_h18_quadratic_r1/summary.csv',
           out/'c08_h18_storage_rhs_r2/soil_rhs.csv',out/'c08_h18_storage_rhs_r2/terms.csv',out/'c08_h18_storage_rhs_r2/summary.csv']
    before=[stat(q) for q in files]
    assert json.loads(files[1].read_text())['passed']
    done=json.loads(files[2].read_text());assert done['passed'] and done['physical_steps']==0 and done['quadratic_rows']==40000
    rows=table(files[3]);summary=table(files[4]);native=[q for q in rows if q['basis']=='native_pressure']
    soil={int(q['native_id']):q for q in table(files[5]) if q['part']=='60'}
    terms={int(q['native_id']):q for q in table(files[6]) if q['part']=='60' and q['donor_group']=='all'}
    assert len(native)==len(soil)==len(terms)==5000 and len(rows)==40000 and len(summary)==336
    selected=[q for q in summary if q['basis'] in ('half_x2','xz','half_z2','half_x2_minus_z2') and q['metric'] in tuple(x+'_L' for x in OPS)]
    q=T/'figures'/(TAG+'_errors.csv');write(q,selected);outputs=[q]
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    bases=('half_x2','xz','half_z2','half_x2_minus_z2')
    for ax,region in zip(axes.flat,('all','interior_no_fixed','wall_adjacent','FS')):
        for oi,op in enumerate(OPS):
            y=[float(next(q for q in selected if q['region']==region and q['basis']==b and q['metric']==op+'_L')['rms_error']) for b in bases]
            ax.bar(np.arange(4)+(oi-1)*.25,y,width=.25,label=op)
        ax.set_xticks(np.arange(4),bases,rotation=25);ax.set(title=region,ylabel='Absolute Laplacian RMS error');ax.grid(axis='y',alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Frozen deformed Part60; shared computed Eq22 gradient\nUniversal Taylor shadows at FS are not the actual raw-FS boundary operator')
    q=Path(str(prefix)+'_errors.png');fig.savefig(q,dpi=170);plt.close(fig);outputs.append(q)
    changes={op:dict(all=0.,interior=0.,FS=0.) for op in OPS[1:]};point_changes={op:[] for op in OPS[1:]}
    maxdiff=dict(LP=0.,Lxx=0.,Lxz=0.,gpx=0.,gpz=0.);weight=0.;xy=[]
    for a in native:
        i=int(a['native_id']);s=soil[i];r=terms[i];assert a['FS']==s['fresh_FS'] and float(a['time_s'])==float(s['time_s'])
        sf=int(a['FS']) in (2,3);V=float(s['V_m2']);k=float(s['k_m_s']);weight+=float(s['n'])*V/1e9;xy.append([float(a['x_m']),float(a['z_m'])])
        for name in ('LP','Lxx','Lxz'):maxdiff[name]=max(maxdiff[name],abs(float(a['pairC_Eta2_'+name])-float(r[name])))
        for name in ('gpx','gpz'):maxdiff[name]=max(maxdiff[name],abs(float(a['Eq22_'+name])-float(r[name])))
        for op in OPS[1:]:
            if sf:
                dl=float(a[op+'_LP'])-float(a['pairC_Eta2_LP'])+1000*(float(s['Acex'])*(float(a[op+'_Lxx'])-float(a['pairC_Eta2_Lxx']))+float(s['Acez'])*(float(a[op+'_Lxz'])-float(a['pairC_Eta2_Lxz'])))
            else:dl=float(a[op+'_L'])-float(a['pairC_Eta2_L'])
            dq=V*k/(1000*9.80665)*dl
            changes[op]['all']+=dq;changes[op]['FS' if sf else 'interior']+=dq
            point_changes[op].append(1e9/float(s['n'])*k/(1000*9.80665)*dl/1000)
    source=next(q for q in table(files[7]) if q['part']=='60' and q['donor_group']==q['receiver_group']=='all')
    base=float(source['actual_Q_all_only_m2_s'])/weight/1000
    result=[dict(operator=op,region=g,delta_storage_rate_m2_s=v,delta_weighted_rate_kPa_s=v/weight/1000,
                 baseline_weighted_rate_kPa_s=base,new_all_weighted_rate_kPa_s=base+changes[op]['all']/weight/1000)
            for op,groups in changes.items() for g,v in groups.items()]
    q=Path(str(prefix)+'_rate_changes.csv');write(q,result);outputs.append(q)
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained');xy=np.array(xy)
    extreme=max(max(abs(np.array(v))) for v in point_changes.values());norm=SymLogNorm(linthresh=1,vmin=-extreme,vmax=extreme)
    for ax,op in zip(axes,OPS[1:]):
        im=ax.scatter(xy[:,0],xy[:,1],c=point_changes[op],norm=norm,cmap='coolwarm',s=4);ax.set_aspect('equal');ax.set(title=op,xlabel='x [m]',ylabel='z [m]')
    fig.colorbar(im,ax=list(axes),label='Changed pressure rate [kPa/s]',shrink=.8)
    fig.suptitle('Native pressure shadows on fixed geometry: retain actual raw-FS branch\nOther RHS terms and fields fixed; not a coupled solution or next-step prediction')
    q=Path(str(prefix)+'_native_changes.png');fig.savefig(q,dpi=170);plt.close(fig);outputs.append(q)
    assert all(stat(Path(q['path']))==q for q in before)
    check.write_text(json.dumps(dict(stage=TAG,analysis_complete=True,consumed=before,consumed_stats_unchanged=True,
        outputs=[stat(q) for q in outputs],same_field_reassociation_max_abs_differences=maxdiff,
        total_storage_weight=weight,native_pressure_shadow_changes=result,universal_Taylor_at_FS_not_production=True,
        actual_raw_FS_branch_retained_for_native_rate_changes=True,pressure_gradient_Da_chain_unchanged=True,
        physical_acceptance=False,operator_replaced=False,solver_invocations=0,native_decodes=0,SHA_scans=0),indent=2)+'\n')


if __name__=='__main__':main()
