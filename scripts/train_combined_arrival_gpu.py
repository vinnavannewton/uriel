#!/usr/bin/env python3
"""Audited exploratory GPU ETA training from Small Grid and provisional West Coast data."""
import csv, hashlib, json, math, os, platform, time, uuid
from collections import defaultdict
from pathlib import Path
import numpy as np
import xgboost as xgb
from sklearn.model_selection import GroupShuffleSplit
import train_arrival as base
import collect_west_coast_arrival_trials as west

ROOT=Path(__file__).resolve().parents[1]

def save(path,obj):
    path.write_text(json.dumps(base.json_safe(obj),indent=2,allow_nan=False)+'\n')

def project(point,points):
    best=(float('inf'),0.,np.array([1.,0.]))
    offset=0.
    for a,b in zip(points[:-1],points[1:]):
        delta=b[:2]-a[:2];length=np.linalg.norm(delta)
        if length<1e-8: continue
        t=np.clip(np.dot(np.asarray(point)[:2]-a[:2],delta)/(length*length),0.,1.)
        dist=np.linalg.norm(np.asarray(point)[:2]-(a[:2]+t*delta))
        if dist<best[0]: best=(dist,offset+t*length,delta/length)
        offset+=length
    return best

def west_examples(audit,seen):
    out={t:[] for t in base.TARGETS}
    for path in sorted((ROOT/'runs').glob('west-coast-*/*/telemetry.csv')):
        meta=path.parent/'metadata.json'; summary=path.parent/'summary.json'
        if not meta.exists() or not summary.exists():continue
        try:
            m=json.loads(meta.read_text());s=json.loads(summary.read_text())
            if m.get('level')!='west_coast_usa':continue
            digest=base.sha256_file(path)
            if digest in seen: audit.append({'path':str(path),'reason':'duplicate_content'});continue
            seen.add(digest)
            if s.get('outcome')!='both_cleared' or not m.get('expanded_graph_paths'):
                audit.append({'path':str(path),'reason':'incomplete_or_missing_exact_geometry'});continue
            if any(v>0 for v in s.get('damage_increase',{}).values()):
                audit.append({'path':str(path),'reason':'damage'});continue
            rows=defaultdict(list)
            with path.open() as f:
                for r in csv.DictReader(f):rows[r['vehicle_id']].append(r)
            pair=tuple(m['configuration'][n]['model'] for n in west.IDS)
            group='west_pair:'+','.join(pair)
            accepted=0
            for name,rr in rows.items():
                if name not in west.IDS:continue
                points=np.array(m['expanded_graph_paths'][name]['positions'],dtype=float)
                zone=m.get('zone',west.ZONE);center=zone['center_xyz_m'];radius=zone['radius_m']
                zone_progress=project(center,points)[1]
                events={};occupied=False;history=[];prepared=[];last=-math.inf;deviated=False
                for r in rr:
                    box=json.loads(r['bbox_world_json']);elapsed=float(r['elapsed_s'])
                    hit=west.overlaps_zone(box)
                    if hit and 'entry' not in events:events['entry']=elapsed;occupied=True
                    if occupied and not hit and 'clearance' not in events:events['clearance']=elapsed
                    p=np.array([float(r[k]) for k in ('x_m','y_m','z_m')]);dist,progress,tangent=project(p,points)
                    deviated=deviated or dist>3.5
                    if elapsed-last<.2-1e-6:continue
                    last=elapsed;speed=float(r['forward_speed_mps']);box=np.array(box)
                    rel=(box[:,:2]-p[:2])@tangent
                    side=(box[:,:2]-p[:2])@np.array([-tangent[1],tangent[0]])
                    heights=box[:,2]
                    def lag(seconds):
                        vals=[v for t,v in history if t<=elapsed-seconds+1e-6 and elapsed-t<=seconds+.6]
                        return vals[-1] if vals else math.nan
                    recent=[v for t,v in history if t>=elapsed-1]+[speed]
                    accel=sum(float(r.get(k) or 'nan')*v for k,v in zip(('ax_mps2','ay_mps2'),tangent))
                    record=dict(zip(base.FEATURES,[zone_progress-radius-progress-max(rel),zone_progress+radius-progress-min(rel),speed,accel,lag(.5),lag(1),np.mean(recent),np.std(recent),max(rel)-min(rel),max(side)-min(side),max(heights)-min(heights),float(r['nearest_distance_m']),float(r['nearest_relative_speed_mps'])]))
                    record.update(trial_id=str(path.parent.relative_to(ROOT)),group_id=group,vehicle_id=name,elapsed=elapsed,source='west_coast',label_quality='provisional_radius_spawn_OOBB',deviated=deviated)
                    prepared.append(record);history.append((elapsed,speed))
                for target,event in events.items():
                    for r in prepared:
                        if r['elapsed']<event and not r['deviated']:
                            out[target].append(dict(r,target=target,target_seconds=event-r['elapsed']));accepted+=1
            audit.append({'path':str(path),'sha256':digest,'group':group,'rows':accepted,'status':'exploratory_provisional'})
        except Exception as exc:audit.append({'path':str(path),'reason':repr(exc)})
    return out

def main():
    start=time.monotonic();out=ROOT/'runs/ml-arrival'/('combined-gpu-'+uuid.uuid4().hex[:10]);out.mkdir(parents=True)
    print('OUTPUT',out,flush=True)
    audit=[];seen=set();trials=[]
    for label,root in [('local',ROOT/'uriel_experiment'),('teammate',Path('/home/vinnavan/Downloads/uriel_experiment')),('teammate_lidar_telemetry',Path('/home/vinnavan/Downloads/uriel_lidar_experiment'))]:
        print('LOADING',label,root,flush=True)
        loaded=base.load_trial_folders(root)
        for t in loaded:
            t.trial_id=label+'/'+t.trial_id
            for v in t.vehicle_runs:v.trial_id=t.trial_id
            if t.digest in seen and t.reason is None:t.reason='duplicate_content_across_sources'
            elif t.reason is None:seen.add(t.digest)
        trials.extend(loaded)
    base.group_and_sample_duplicate_configs(trials)
    examples,labels=base.build_examples(trials)
    for target in examples:
        for r in examples[target]:r['source']='smallgrid';r['label_quality']='virtual_square_spawn_OOBB'
    audit.extend({'path':str(t.folder),'status':'accepted' if not t.reason else 'excluded','reason':t.reason,'group':t.group_id,'sha256':t.digest} for t in trials)
    w=west_examples(audit,seen)
    for target in examples:examples[target].extend(w[target])
    groups={}
    for source in ('smallgrid','west_coast'):
        gg=sorted({r['group_id'] for rows in examples.values() for r in rows if r['source']==source})
        if len(gg)<8:raise RuntimeError(f'{source} only {len(gg)} groups; need 8')
        indexes=np.arange(len(gg));train,tmp=next(GroupShuffleSplit(n_splits=1,test_size=.4,random_state=42).split(indexes,groups=gg))
        val,test=next(GroupShuffleSplit(n_splits=1,test_size=.5,random_state=42).split(tmp,groups=np.array(gg)[tmp]))
        for split,indices in [('train',train),('validation',tmp[val]),('test',tmp[test])]:
            for i in indices:groups[gg[i]]=split
    save(out/'data_audit.json',{'sources':audit,'smallgrid_label_audit':labels})
    save(out/'split_manifest.json',groups)
    save(out/'feature_schema.json',{'features':base.FEATURES,'units':'metres, seconds, metres/second','labels':'time remaining to source-specific proxy zone entry/rear clearance','provisional':True})
    report={'status':'exploratory','device_requested':'cuda','production_ready':False,'limitation':'West Coast labels remain provisional; source zones differ; no automatic deployment or worker compatibility claimed','targets':{}}
    (out/'models').mkdir()
    for target,records in examples.items():
        print('TRAIN',target,'rows',len(records),'groups',len({r['group_id'] for r in records}),flush=True)
        subsets={split:[r for r in records if groups[r['group_id']]==split] for split in ('train','validation','test')}
        best=None;candidates=[]
        for depth in (3,5):
            model=xgb.XGBRegressor(tree_method='hist',device='cuda',n_estimators=250,max_depth=depth,learning_rate=.05,n_jobs=4,random_state=42)
            model.fit(base.fit_features(subsets['train']),[r['target_seconds'] for r in subsets['train']],sample_weight=base.balance_weights(subsets['train']))
            metrics=base.run_balanced_metrics(subsets['validation'],model.predict(base.fit_features(subsets['validation'])))
            candidates.append({'depth':depth,'validation':metrics})
            if best is None or metrics['mae_seconds']<best[0]:best=(metrics['mae_seconds'],depth)
        final=xgb.XGBRegressor(tree_method='hist',device='cuda',n_estimators=250,max_depth=best[1],learning_rate=.05,n_jobs=4,random_state=42)
        fit=subsets['train']+subsets['validation'];final.fit(base.fit_features(fit),[r['target_seconds'] for r in fit],sample_weight=base.balance_weights(fit))
        preds=np.maximum(0,final.predict(base.fit_features(subsets['test'])))
        final.save_model(out/'models'/f'{target}.ubj')
        # Verify the portable serialized model produces the same predictions.
        restored=xgb.XGBRegressor();restored.load_model(out/'models'/f'{target}.ubj')
        restored.set_params(device='cpu');np.testing.assert_allclose(preds,np.maximum(0,restored.predict(base.fit_features(subsets['test']))),rtol=1e-5,atol=1e-5)
        config=json.loads(final.get_booster().save_config())
        result={'selected_depth':best[1],'gpu_config':{k:v for k,v in config['learner']['generic_param'].items() if k != 'rng_state'},'candidates':candidates,'split_counts':base.split_counts(records,groups),'test':base.metrics_for_predictions(subsets['test'],preds),'by_source':{}}
        for source in ('smallgrid','west_coast'):
            idx=[i for i,r in enumerate(subsets['test']) if r['source']==source]
            result['by_source'][source]=base.metrics_for_predictions([subsets['test'][i] for i in idx],preds[idx])
        report['targets'][target]=result
        save(out/f'{target}_test_predictions.json',[{'trial_id':r['trial_id'],'group_id':r['group_id'],'source':r['source'],'elapsed_s':r['elapsed'],'truth_seconds':r['target_seconds'],'prediction_seconds':float(p)} for r,p in zip(subsets['test'],preds)])
        print('RESULT',target,json.dumps(result['test']['all']),flush=True)
    report['elapsed_wall_seconds']=time.monotonic()-start;report['xgboost_version']=xgb.__version__;report['status']='evaluated_exploratory'
    save(out/'evaluation_report.json',report)
    (out/'trainer_source.py').write_bytes(Path(__file__).read_bytes())
    print('COMPLETE',out,'SECONDS',report['elapsed_wall_seconds'],flush=True)
if __name__=='__main__':main()
