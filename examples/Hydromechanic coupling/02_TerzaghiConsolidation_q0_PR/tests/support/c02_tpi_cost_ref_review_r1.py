"""Use the independently admitted 1 us finite-Kw solution as the high-k accuracy anchor."""
import argparse

from c02_tpi_cost_r1 import PLAN, PREFIX, REFERENCES, TESTS, need
from c02_tpi_cost_review_r1 import target_budgets, write_report


def against_reference(ref,candidate,anchor):
    need(anchor['lane']==REFERENCES['anchor'] and ref['lane'] in REFERENCES['lanes']
         and ref['model']==anchor['model']==1,'Explicit kw10 anchor and independent reference required')
    need(all(ref[k]==candidate[k]==anchor[k] for k in ('backend','host','hardware','cuda_driver_runtime','program_identity')),
         'Same host, program, backend, device and driver required')
    chosen=target_budgets(anchor,ref)
    direct=target_budgets(anchor,candidate)
    selected=target_budgets(ref,candidate)
    passed=chosen['passed'] and direct['passed'] and selected['passed']
    return dict(independent_anchor=anchor['lane'],explicit_reference=ref['lane'],candidate=candidate['lane'],
                reference_vs_anchor=chosen,candidate_vs_anchor=direct,candidate_vs_reference=selected,
                predeclared_target_noninferiority_pass=passed)


if __name__=='__main__':
    # Reuse numerical results from the original native reviews and their sealed exits.
    from c02_tpi_cost_summary_r1 import single
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('backend',choices=('cpu','gpu'));ap.add_argument('lane',choices=PLAN['lanes'])
    ap.add_argument('--reference',choices=REFERENCES['lanes'],required=True)
    args=ap.parse_args()
    need(args.lane!=args.reference,'Self comparisons have no independent timing meaning')
    results={l:single(l,args.backend)[0] for l in dict.fromkeys((args.lane,args.reference,REFERENCES['anchor']))}
    out=results[args.lane]
    out['comparison']=against_reference(results[args.reference],out,results[REFERENCES['anchor']])
    dest=TESTS/'logs'/(f'{PREFIX}_{args.lane}_{args.backend}_vs_{args.reference}.json')
    write_report(dest,out)
