#!/usr/bin/env python3
import argparse, os, json
from src.benchmarks import *

def fetch_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='the configuration used for plots.',
                        type=str, default='configplot.json')
    parser.add_argument('-d', '--dir', help='the directory containing the dumbed data from the evaluator.',
                        type=str, default='./output')
    return parser.parse_args()

def read_config(filename: str) -> dict:
    return json.load(open(filename))

def plot_results(dir: str, config: dict):
    for root, dirs, _ in os.walk(dir):
        for d in dirs:
            if not os.path.exists(f'{root}/{d}/config.json'):
                plot_results(f'{root}/{d}', config)
                continue

            cdir   = f'{root}/{d}'
            plotconfig = json.load(open(f'{cdir}/config.json', 'r'))
            plotter: IPlotter = eval(f'{plotconfig["benchmark"]}Plotter(config=config["{plotconfig["benchmark"]}"])')
            plotter.plot_results(config=plotconfig, dir=cdir)
            plotter.evaluate_statics(config=plotconfig, dir=cdir)

def main():
    args   = fetch_args()
    config = read_config(filename=args.config)
    plot_results(dir=args.dir, config=config)

if __name__ == '__main__':
    main()
