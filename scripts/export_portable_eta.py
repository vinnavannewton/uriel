#!/usr/bin/env python3
"""Export native XGBoost regression trees and verify portable inference parity."""
import argparse, hashlib, json, re
from pathlib import Path
import numpy as np
import xgboost as xgb
from portable_eta import PortableRegressor

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);args=parser.parse_args();p=args.directory
    data={};fixtures={};rng=np.random.default_rng(42)
    features=rng.normal(size=(500,13))*10;features[rng.random(features.shape)<.15]=np.nan
    fixtures['features']=[[None if np.isnan(v) else float(v) for v in row] for row in features]
    for name in ('entry','clearance'):
        m=xgb.XGBRegressor();m.load_model(p/'models'/f'{name}.ubj');m.set_params(device='cpu',n_jobs=2)
        config=json.loads(m.get_booster().save_config())
        # Native dumps use non-JSON -inf thresholds for missing-value splits.
        trees=[json.loads(re.sub(r': (-?inf)(?=\s*[,}])',r': "\1"',t)) for t in m.get_booster().get_dump(dump_format='json')]
        data[name]={'base_score':json.loads(config['learner']['learner_model_param']['base_score'])[0],'trees':trees}
        native=m.predict(features);portable=PortableRegressor(data[name]).predict(features)
        np.testing.assert_allclose(native,portable,atol=1e-4,rtol=1e-5)
        fixtures[name]=native.tolist();print(name,'max conversion difference',max(abs(native-portable)),flush=True)
    path=p/'models/portable.json';path.write_text(json.dumps(data,separators=(',',':')))
    (p/'portable_fixtures.json').write_text(json.dumps(fixtures))
    (p/'portable_manifest.json').write_text(json.dumps({'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'native_parity_verified':True,'fixtures':500,'tolerance_absolute':1e-4}))
if __name__=='__main__':main()
