#!/usr/bin/env python3
import argparse, json
from src.services import Benchmark

def fetch_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='path to the configuration file.',
                        required=True, type=str)
    return parser.parse_args()

def read_config(filename: str) -> dict:
    return json.load(open(filename))

def __perform_mbench_1(config: dict):
    from src.benchmarks.microbenchmarks import MBench_1
    mbench1 = MBench_1(config=config['mbench_1'])
    for ds, path in config['target'].items():
        if ds.startswith('__'): continue
        mbench1.perform_benchmark(libso_path=path)
        mbench1.plot_results(result_name=ds)

        #if config['mbench_1']['perf']['do_profiling']:
        #    mbench1.perform_perf_profilling(libso_path=path)

def perform_benchmarks(config: dict):
    if 'mbench_1' in config:
        if isinstance(config['mbench_1'], list):
            for sconfig in config['mbench_1']:
                __perform_mbench_1(config=sconfig)
        else: __perform_mbench_1(config=config)

def __perform_ycsb(config: dict):
    from src.benchmarks.workloads import YCSB
    ycsb = YCSB(config['ycsb'])
    for ds, path in config['target'].items():
        if ds.startswith('__'): continue
        ycsb.perform_workload(libso_path=path)
        ycsb.save_results()

def perform_workloads(config: dict):
    if 'ycsb' in config:
        if isinstance(config['ycsb'], list):
            for sconfig in config['ycsb']:
                __perform_ycsb(config=sconfig)
        else: __perform_ycsb(config=config)

def main():
    args   = fetch_args()
    config = read_config(filename=args.config)
    # perform_benchmarks(config=config)
    perform_workloads(config=config)

if __name__ == '__main__':
    main()