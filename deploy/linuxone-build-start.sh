#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PATH="$HOME/.cargo/bin:$PATH"
export CARGO_BUILD_JOBS=2
mkdir -p "$HOME/.local/state/uriel"
exec > >(tee "$HOME/.local/state/uriel/build.log") 2>&1
cargo test --locked
cargo build --locked --release -j 2
systemctl --user daemon-reload
systemctl --user enable --now uriel.service
python3 - <<'PY'
import json,time,urllib.request
for attempt in range(20):
    try:
        with urllib.request.urlopen('http://127.0.0.1:3000/health',timeout=2) as r:
            value=json.load(r)
        assert value['status']=='ok'
        print('LinuxONE Uriel health:',value)
        break
    except Exception:
        if attempt==19: raise
        time.sleep(.5)
PY
systemctl --user status uriel.service --no-pager
