#!/usr/bin/env python3
"""Run an uncoordinated crossing followed by the matched local Rust hybrid trial."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pause-between',type=float,default=5,
                        help='Wall seconds to display the paused baseline result before resetting')
    parser.add_argument('--dashboard-url',default='http://127.0.0.1:3000',
                        help='local read-only dashboard/API origin')
    parser.add_argument('--no-dashboard',action='store_true',help='run both trials without dashboard telemetry')
    args=parser.parse_args()
    if not 0<=args.pause_between<=60:parser.error('--pause-between must be between 0 and 60')
    if not args.no_dashboard:
        with urlopen(args.dashboard_url.rstrip('/')+'/health',timeout=1) as response:
            if response.status!=200:raise RuntimeError('dashboard health check failed')
    folder=ROOT/'runs'/('grid-comparison-'+uuid.uuid4().hex[:10]);folder.mkdir()
    results=[]
    for baseline in (True,False):
        mode='baseline' if baseline else 'hybrid'
        command=[sys.executable,str(ROOT/'scripts/run_grid_hybrid_crossing.py')]
        command.extend(['--dashboard-url',args.dashboard_url])
        if args.no_dashboard:command.append('--no-dashboard')
        if baseline:command.append('--baseline')
        print('TRIAL',len(results)+1,mode,flush=True)
        process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        evidence=None
        with (folder/(mode+'.log')).open('w') as log:
            try:
                for line in process.stdout:
                    print(line,end='',flush=True);log.write(line);log.flush()
                    if line.startswith('EVIDENCE '):evidence=Path(line.partition(' ')[2].strip())
                code=process.wait()
            except BaseException:
                process.terminate();process.wait(timeout=10);raise
        if evidence is None or not (evidence/'summary.json').exists():
            raise RuntimeError(f'{mode} has no trial summary (exit {code})')
        summary=json.loads((evidence/'summary.json').read_text())
        results.append({'mode':mode,'evidence':str(evidence),'summary':summary})
        (folder/'comparison.json').write_text(json.dumps({'trials':results},indent=2)+'\n')
        if code!=0 or summary.get('outcome') in ('setup_failed','guarded_abort'):
            raise RuntimeError(f'{mode} stopped: {summary.get("error")}')
        if baseline:time.sleep(args.pause_between)
    baseline,hybrid=[r['summary'] for r in results]
    comparison={'trials':results,'dashboard_url':None if args.no_dashboard else args.dashboard_url,'baseline_damage_observed':any(d>5 for d in baseline.get('final_damage',{}).values()),
                'hybrid_both_cleared':hybrid['outcome']=='both_cleared',
                'hybrid_zero_damage':all(d==0 for d in hybrid.get('final_damage',{}).values()),
                'hybrid_yielded':hybrid.get('yielded',[]),
                'contact_detector_available':False,
                'limitation':'Damage and crossing telemetry are measured; verified contact attribution and general safety acceptance are unavailable.'}
    (folder/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    print('COMPARISON',folder,json.dumps({k:v for k,v in comparison.items() if k!='trials'}),flush=True)

if __name__=='__main__':main()
