"""Review the returned 1 Tv run against its package and independent dense peak qualification."""
import argparse
from pathlib import Path
import zipfile

from cryer_p3_peak_qualify_r1 import DT, PACKAGE, REVIEW, bind, need, read, review_run, sha, write


def check_peak(receipt, peak_output, manifest):
    need(receipt.name==REVIEW, 'Use the peak qualification issued by the local reviewer')
    peak=read(receipt)
    need(peak['peak_qualified'] is True and peak['scheme']=='B' and peak['rounds']==3
         and peak['nu']==.30 and peak['dt_s']==float(DT) and peak['peak_steps']==36864
         and all(peak[key]==manifest[key] for key in ('package_id','program_sha256','peak_input_sha256')),
         'Peak qualification for a different run, program, or package')
    need(peak['native']['frames']==577 and peak['native']['post_open_frames']==512
         and peak['native']['end_s']==.0703125 and peak['native']['drained_receivers_checked']>0
         and peak['sidecar']==dict(pressure_rounds=3,dt_phases=5,rows=577*18*3)
         and all(peak['physics'][k] is True for k in ('amplitude','amplitude_vs_A','sampling','phase')),
         'Incomplete dense peak qualification')
    for group,base,names in (
        ('peak_server_files',peak_output,('Run.csv','server_run.json')),
        ('local_evidence',receipt.parent,('sidecar_review.json','physical/physical_review.json','physical/native_and_theory.csv'))):
        entries=peak[group]
        need(sorted(e['name'] for e in entries)==sorted(names),'Incomplete peak evidence: '+group)
        for entry in entries:
            need(sha((base/entry['name']).read_bytes())==entry['sha256'],'Changed peak evidence: '+entry['name'])
    peak_run=read(peak_output/'server_run.json')
    need(peak_run['profile']=='peak' and peak_run['solver_exit']==0 and
         all(peak_run[k]==manifest[k] for k in ('package_id','program_sha256','peak_input_sha256','selectors')),
         'Peak output does not match the qualified run')
    physical=read(receipt.parent/'physical/physical_review.json')
    need(physical['stage']=='peak' and physical['peak_physical_criteria_met'] is True
         and all(physical['criteria'][k] is True for k in ('sampling','peak_within_one_percent','no_worse_than_A_plus_0p10pp','peak_time'))
         and physical['amplitude_error_pct']==peak['physics']['amplitude_error_pct']
         and physical['phase_error_s']==peak['physics']['phase_error_s'], 'Inconsistent dense peak result')
    return peak


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output',type=Path)
    ap.add_argument('destination',type=Path)
    ap.add_argument('--peak-review',type=Path,required=True)
    ap.add_argument('--peak-output',type=Path,required=True)
    ap.add_argument('--package',type=Path,default=PACKAGE)
    args=ap.parse_args()
    folder=args.output.resolve()
    dest=args.destination.resolve()
    with zipfile.ZipFile(args.package) as z:
        manifest,plan=bind(z,folder,'full')
    peak=check_peak(args.peak_review,args.peak_output,manifest)
    physical,native,side,steps=review_run(folder,plan,dest,'full')
    need(physical['tail_frames']==101 and physical['peak_assessment']=='separate dense peak receipt',
         'Unexpected tail review scope')
    result=dict(stage='full',package_id=manifest['package_id'],program_sha256=manifest['program_sha256'],
        full_definition_sha256=next(e['sha256'] for e in manifest['files'] if e['name']=='CaseCryer_TPI_P3_nu030_full_r1_Def.xml'),
        full_solver_and_native_checks_passed=True,completed_steps=steps[-1],frames=len(native),end_s=float(native[-1]['time_s']),
        soil_ids=37173,fixed_ids=8,post_open_frames=side['actual_post_open_frames'],
        drained_receivers_checked=sum(int(r['active_drain_count']) for r in native),
        pressure_rows=side['inspected_pressure_rows'],dt_phases=side['dt_phases'],
        dense_peak_receipt_sha256=sha(args.peak_review.read_bytes()),dense_peak_physics=peak['physics'],
        decay={key:val for key,val in physical.items() if key.startswith(('tail_','endpoint_'))},
        assessment='Native and method checks complete; physical review of the full decay remains pending.')
    write(dest/'full_review.json',result)
    print(dest/'full_review.json')


if __name__=='__main__':
    main()
