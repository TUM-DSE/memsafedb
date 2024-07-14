#!/usr/bin/env python3
import argparse, json
from src.benchmarks import MBench, YCSB, IBenchmarks

def fetch_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='path to the configuration file.',
                        type=str, default='config.json')
    return parser.parse_args()

def read_config(filename: str) -> dict:
    return json.load(open(filename))

def perform_benchmarks(config: dict):
    for name, bconfig in config['benchmarks'].items():
        bname, btargets = bconfig['benchmark'], bconfig['target']
        benchmark: IBenchmarks = eval(f'{bname}(config={bconfig})')
        for ntarget in btargets:
            benchmark.perform_benchmark(
                libso_path=config['target'][ntarget], output_path=f'./output/{name}/{ntarget}')
            if bconfig['perf']['do_profiling']:
                benchmark.perform_perf(
                    libso_path=config['target'][ntarget], output_path=f'./output/{name}/{ntarget}')

def main():
    args   = fetch_args()
    config = read_config(filename=args.config)
    perform_benchmarks(config=config)

if __name__ == '__main__':
    main()
