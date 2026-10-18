#!/usr/bin/env python3
"""Run the local ETA worker and Rust hybrid algorithm; Ctrl+C stops both."""
import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--scenario', type=Path, default=ROOT / 'scenarios/crossing-v1.json')
    parser.add_argument('--bind', default='127.0.0.1:3000')
    parser.add_argument('--worker-port', type=int, default=3100)
    args = parser.parse_args()
    # Refuse to take over existing listeners.
    for host, port in [args.bind.rsplit(':', 1), ('127.0.0.1', args.worker_port)]:
        with socket.socket() as check:
            check.bind((host, int(port)))
    binary = ROOT / 'target/debug/arc-angel'
    if not binary.is_file():
        parser.error('Build the Rust binary first: cargo build --offline')
    processes = []
    def stop(_sig, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        environment = dict(os.environ, OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
        worker = subprocess.Popen([sys.executable, str(ROOT / 'scripts/ml_worker.py'),
            '--models', str(args.models.resolve()), '--bind', f'127.0.0.1:{args.worker_port}'],
            cwd=ROOT, env=environment)
        processes.append(worker)
        for _ in range(150):
            if worker.poll() is not None:
                raise RuntimeError('ML worker failed to start')
            try:
                with socket.create_connection(('127.0.0.1', args.worker_port), timeout=.1):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('ML worker startup timed out')
        rust = subprocess.Popen([str(binary)], cwd=ROOT, env=dict(environment,
            ARC_SCENARIO=str(args.scenario.resolve()), ARC_BIND=args.bind,
            ARC_ML_ADDR=f'127.0.0.1:{args.worker_port}', ARC_ML_MODE='hybrid'))
        processes.append(rust)
        print(f'Hybrid algorithm running at {args.bind}; model={args.models.name}', flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(.2)
        raise RuntimeError('A hybrid service exited; stopping the other process')
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

if __name__ == '__main__':
    main()
