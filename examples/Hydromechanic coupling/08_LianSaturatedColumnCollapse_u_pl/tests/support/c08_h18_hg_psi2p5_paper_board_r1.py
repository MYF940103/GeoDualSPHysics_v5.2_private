"""CSV/PNG-only comparison boards from sealed existing paper/native figures; no numerical analysis."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import c08_h18_storage_review_r2 as evidence

T,L=evidence.T,evidence.L
need,read,stat,bind=evidence.need,evidence.read,evidence.stat,evidence.bind
TAG='c08_h18_hg_psi2p5_paper_board_r1';NOTE=T/'notes'/(TAG+'.md')
PHYSICAL=L/'c08_h18_hg_psi2p5_full3_physical_r1.check.json';REF=T/'figures/c08_h18_lian2023_ref-21.png'
MD=T.parents[3]/'src/papers/u-pw/Lian 2023 u-pl.md';PREFIX=T/'figures'/TAG;CHECK=L/(TAG+'.check.json')
# Original1361x1857 page21 pixels. Boxes are [left,top,right,bottom), no pressure/outline sampling.
PANELS=((15,(148,158,1228,858),'Native p - fixed initial material P0 [kPa]; native kappa',
         'Paper Fig15 excess pl +/-10 kPa; paper strain scales0..0.3/1/2. Native definitions are qualified, not identified.'),
        (16,(148,882,1228,1610),'Native total pore-water pressure [kPa]',
         'Paper Fig16: left(a) stabilized, right(b) non-stabilized; rows .01/.5/1.2s. Native times are columns, same display -10..20 kPa.'))


def sealed(check,path,key,consumed):
    refs=[q for q in check[key] if Path(q['path']).resolve()==path.resolve()]
    need(refs and all(q==refs[0] for q in refs),'Missing or ambiguous original figure seal: '+str(path))
    consumed.append(bind(refs[0]))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Root separately reviews and authorizes this display-only entry')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'_*')),'Existing completed/partial boards protected')
    consumed=[stat(q) for q in (Path(__file__),NOTE,PHYSICAL,MD,Path(evidence.__file__))]
    result=dict(stage=TAG,passed=False,physical_acceptance=False,numerical_analysis_invocations=0,native_reader_invocations=0,solver_invocations=0,GPU_actions=0,VTK_invocations=0,SHA_scans=0,automatic_next_job=False)
    try:
        physical=read(PHYSICAL);need(physical['passed'] and physical['analysis_complete'] and physical['group']=='psi2p5' and physical['consumed_stats_unchanged'],'Already completed sealed psi2p5 physical analysis required')
        sealed(physical,REF,'consumed',consumed);reference=plt.imread(REF);need(reference.shape[:2]==(1857,1361),'Original supplied page21 raster extent differs')
        rows=[];files=[]
        for figure,box,field,caption in PANELS:
            native=T/'figures'/f'c08_h18_hg_psi2p5_full3_physical_r1_paper_fig{figure}.png'
            sealed(physical,native,'files',consumed);current=plt.imread(native);left,top,right,bottom=box
            need(0<=left<right<=1361 and 0<=top<bottom<=1857,'Invalid source-pixel display rectangle')
            crop=reference[top:bottom,left:right]
            fig,axes=plt.subplots(1,2,figsize=(28,11),layout='constrained')
            axes[0].imshow(crop,interpolation='none');axes[1].imshow(current,interpolation='none')
            axes[0].set_title(f'Lian et al.2023, original Fig{figure} raster\nNumerical reference, not analytical/experimental truth',fontsize=15)
            axes[1].set_title('Current psi=+2.5 deg completed diagnostic\n'+field,fontsize=15)
            for ax in axes:ax.set_axis_off()
            fig.suptitle(f'C08: supplied paper Fig{figure} beside the existing native-result figure',fontsize=19)
            fig.supxlabel(caption+'\nOriginal figure files unchanged. Visual similarity does not establish mechanism, pressure error or accepted collapse physics.',fontsize=12)
            destination=Path(str(PREFIX)+f'_fig{figure}.png');fig.savefig(destination,dpi=160);plt.close(fig);files.append(destination)
            for role,source,image,rect in (('paper_reference',REF,reference,box),('existing_native_figure',native,current,(0,0,current.shape[1],current.shape[0]))):
                entry=stat(source);rows.append(dict(board_figure=figure,role=role,source_path=entry['path'],source_bytes=entry['bytes'],source_mtime_ns=entry['mtime_ns'],
                    source_width_px=image.shape[1],source_height_px=image.shape[0],left_px=rect[0],top_px=rect[1],right_exclusive_px=rect[2],bottom_exclusive_px=rect[3],
                    original_raw_image_values_passed_to_imshow=True,pressure_or_outline_digitization=False,plot_field_or_reference_label=field if role=='existing_native_figure' else caption))
        table=Path(str(PREFIX)+'_sources.csv')
        with table.open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        files.append(table);need(all(stat(q['path'])==q for q in consumed),'Sealed source figure or helper changed')
        result.update(passed=True,display_completed=True,group='psi2p5',source_rows=4,reference_pixel_extent=[1361,1857],
            crops_are_original_source_pixel_rectangles=True,source_image_files_unchanged=True,board_is_not_pixelwise_identity_with_inputs=True,
            no_pressure_or_shape_values_inferred=True,native_excess_equals_paper_excess_claimed=False,native_result_assigned_to_paper_stabilized_column=False,
            paper_explicitly_calls_Fig16b_frozen=False,qualitative_similarity_is_causal_proof=False,paper_mechanism_MD_lines=[923,930,942,943],
            consumed_stats_unchanged=True,visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),partial_outputs_preserved=True)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False)
    need(result['passed'],result.get('first_failure','Display-only board failed; preserve partials'))


if __name__=='__main__':main()
