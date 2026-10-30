"""Fresh attempt identity only; reuse reviewed physics/guards, never restart the rejected R1 host."""
import argparse
import json
import sw_freshpr_run_r1 as worker

worker.TAG='sw_freshpr_run_r2'
worker.NOTE=worker.TESTS/'notes'/(worker.TAG+'.json')
worker.MONITOR,worker.RUN,worker.CHECK,worker.COMPLETE,worker.RECEIPT=[worker.LOGS/(worker.TAG+s) for s in ['.monitor.inputs.json','.run.json','.check.json','.completion.json','.receipt.json']]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(); modes.add_argument('--selftest',action='store_true'); modes.add_argument('--run',action='store_true'); args=parser.parse_args()
    if args.selftest:print(json.dumps(worker.selftest()))
    elif args.run:raise SystemExit(0 if worker.run() else 1)
    else:parser.print_help()
