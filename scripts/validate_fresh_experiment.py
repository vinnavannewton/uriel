"""Revalidate saved fresh telemetry allowing documented 0.5ms physics quantization."""
import csv
import hashlib
import json
import math
from pathlib import Path
import runpy
import shutil
import sys


def main():
    root=Path(sys.argv[1]).resolve()
    module=runpy.run_path(str(root/'collector_source.py'))
    experiment=json.loads((root/'experiment.json').read_text())
    assert hashlib.sha256((root/'collector_source.py').read_bytes()).hexdigest()==experiment['collector_sha256']
    results=[];dim_reference=None
    for folder in sorted(root.glob('fresh_*')):
        metadata=json.loads((folder/'metadata.json').read_text())
        if 'outcomes' not in metadata:
            results.append(metadata);continue
        with (folder/'telemetry.csv').open() as f: rows=list(csv.DictReader(f))
        texts={'run_id','vehicle_id','vehicle_role','ai_mode','route_id','nearest_vehicle_id','lane_state','conflict_zone_state','bbox_json'}
        booleans={'route_deviation'}
        for r in rows:
            for k,v in r.items():
                if v=='':r[k]=None
                elif k in booleans:r[k]=v=='True'
                elif k not in texts:r[k]=float(v)
        events,outcomes=module['derive_events'](rows,metadata['configuration'])
        original=module['validate'](rows,metadata['configuration'],outcomes)
        # Retain all checks except the known incorrect strict interval check.
        issues=[i for i in original['issues'] if not i.startswith('timestamp gap ')]
        timing={}
        for c in metadata['configuration']:
            name=c['vehicle_id'];rr=[r for r in rows if r['vehicle_id']==name]
            times=[r['sim_time'] for r in rr];dt=[b-a for a,b in zip(times,times[1:])]
            duration=times[-1]-times[0]
            timing[name]={'min_dt':min(dt),'max_dt':max(dt),'duration':duration,
                          'effective_hz':(len(rr)-1)/duration}
            if any(d<=0 or abs(d-1/30)>.00051 for d in dt):issues.append('sampling gap '+name)
            if abs(duration-25)>.00051:issues.append('observation horizon '+name)
            if any(abs((t-times[0])-i/30)>.00051 for i,t in enumerate(times)):issues.append('frame drift '+name)
            if [r['frame_id'] for r in rr]!=list(range(751)):issues.append('frame ID continuity '+name)
            for r in rr:
                box=json.loads(r['bbox_json']);front,rear,overlap=module['box_metrics'](box,c)
                if abs(front-r['front_progress'])>1e-7 or abs(rear-r['rear_progress'])>1e-7:issues.append('bbox projection mismatch '+name);break
                if overlap!=(r['conflict_zone_state']=='overlap'):issues.append('zone mismatch '+name);break
            if metadata['outcomes'][name]!=outcomes[name]:issues.append('metadata label mismatch '+name)
        if dim_reference is None:dim_reference=metadata['vehicle_dimensions']
        for name,d in metadata['vehicle_dimensions'].items():
            if any(abs(d[k]-dim_reference[name][k])>.05 for k in d):issues.append('dimension drift '+name)
        for frame in range(751):
            rr=[r for r in rows if r['frame_id']==frame]
            if len(rr)!=6 or max(r['sim_time'] for r in rr)-min(r['sim_time'] for r in rr)>.00051:
                issues.append('inconsistent frame '+str(frame));break
        stored_events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
        for event in events:
            if event not in stored_events:issues.append('event not preserved '+event['event']);break
        report=original
        report.update(status='PASS_WITH_LIMITATIONS' if not issues else 'FAIL',issues=issues,
            measured_sampling=timing,validation_revision=2,
            revision_reason='Allow up to 0.51ms sample-interval/phase variation for observed 0.5ms physics quantization. Verify 25s total horizon and actual timestamps; raw recordings unchanged.')
        prior=folder/'validation_report_initial.json'
        if not prior.exists():shutil.copyfile(folder/'validation_report.json',prior)
        (folder/'validation_report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
        metadata.setdefault('initial_validation_status',metadata['status'])
        metadata.update(status='complete' if not issues else 'failed_validation',quality=report['status'],validation_revision=2)
        (folder/'metadata.json').write_text(json.dumps(metadata,indent=2,allow_nan=False))
        results.append(metadata)
        print(folder.name,report['status'],len(rows),'rows',issues)
    module['write_summary'](root,results)
    experiment.update(status='complete' if len(results)==3 and all(r['status']=='complete' for r in results) else 'completed_with_failures',validation_revision=2,
        original_strict_validation_reports_preserved=True)
    (root/'experiment.json').write_text(json.dumps(experiment,indent=2))
    shutil.copyfile(__file__,root/'validator_source.py')
    lines=['# Fresh randomized Small Grid pilots','',
        'Two matching ETK subjects and four background vehicles. Three independent seeded runs; 25 simulator seconds at measured average 30 Hz. No Uriel coordinator or ML training.',
        '', '| Run | Seed | Red entry / clearance (s) | Blue entry / clearance (s) | Subject damage increase |',
        '|---|---:|---|---|---|']
    for m in results:
        o=m.get('outcomes',{});a=o.get('uriel_red',{});b=o.get('uriel_blue',{})
        def fmt(o):return ' / '.join('unobserved' if o.get(k) is None else f'{o[k]:.3f}' for k in ['entry_seconds','clearance_seconds'])
        lines.append(f"| {m['run_id']} | {m['seed']} | {fmt(a)} | {fmt(b)} | red {a.get('damage_increase')}, blue {b.get('damage_increase')} |")
    lines+=['','Each run contains telemetry.csv, events.jsonl, metadata.json, geometry.json and validation_report.json. trial_summary.csv includes randomized settings.',
        '', 'Entry and clearance use sampled world spawn bounding boxes against a virtual 6x6m zone; deformation/contact geometry is uncalibrated. Damage can make labels ambiguous. Verified contact is unavailable, not zero.',
        'Missing values: first-frame acceleration and all verified_contact fields. Orientations are radians; lengths metres; time seconds; speeds m/s; acceleration m/s². Relative distance is nearest vehicle reference-point distance, not body clearance; relative speed is radial separation rate.',
        'AI mode records commanded state, not independently acknowledged internal AI state. Delayed vehicles are initially braked; stopped-before-entry may reflect that scheduled hold.',
        'The original interval validator expected mathematically exact 1/30s. Observed 33.0/33.5ms steps represent 0.5ms physics quantization and average 30 Hz. Revision 2 checks quantization, phase, duration, counts, stable IDs, bbox labels and event evidence. Original validation reports preserved as validation_report_initial.json; telemetry/events unchanged.',
        'Initial failed setup batch experiment_a972954ae237434f8d60ee1900441d55 is retained separately. The successful retry changed shift initialization to prevent backward roll. Seeds and exact executed source are archived; replay is not guaranteed bitwise deterministic.']
    (root/'README.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
