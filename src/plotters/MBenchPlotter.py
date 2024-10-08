#!/usr/bin/env python3
"""
*   @details: Used to generate the corresponding plots.
*   @author: Cristian Sandu <cristian.sandu@tum.de>
"""
from .IPlotter import IPlotter

from collections import defaultdict
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import os

class MBenchPlotter(IPlotter):
    def __init__(self, config: str):
        self.__config = config
    
    def __plot_latency(self, plotconfig: dict, log_latency: dict, fname: str, plotname: str, save_dir: str):
        threadnum      = plotconfig['threadnum']
        granularity    = self.__config['granularity']
        stdavg         = self.__config['stdavg']

        sns.set_theme()
        fig, axs = plt.subplots(1, 1, figsize=(12, 6), sharey=True)
        max_means = []

        for threadval in threadnum:
            dataset = log_latency[f'{threadval}'][fname]

            means, stds = [], []
            interval = len(dataset)//granularity
            for i in range(granularity):
                batch = dataset[i * interval:(i+1) * interval]
                means.append(np.mean(batch))
                stds.append(np.std(batch) / stdavg)

            df = pd.DataFrame({'mean': means, 'std': stds})
            axis = [i * interval for i in range(granularity)]
            max_means.append(max(means))

            axs.plot(axis, df['mean'], label=f"threads={threadval}")
            axs.fill_between(axis, df['mean'] - df['std'], df['mean'] + df['std'],
                             alpha=0.3)

        axs.set_ylim(bottom=0, top=max(max_means))
        axs.set_xlim(left=0, right=len(dataset))

        plt.xlabel('num. op.')
        plt.ylabel('latency (ns)')
        plt.legend()  # Display the legend
        plt.title(f'Performance Evaluation {plotname}') 
        plt.savefig(f'{save_dir}/plot_{fname}.png')
        plt.close(fig)

    def __plot_memoryusage(self, plotconfig: dict, log_memory: dict, save_dir: str):
        granularity    = self.__config['granularity']

        sns.set_theme()
        _, axs = plt.subplots(1, 1, figsize=(12, 6), sharey=True)

        dataset = log_memory['dataset_performfill']
        means = []
        interval = len(dataset)//granularity
        for i in range(granularity):
            batch = dataset[i * interval:(i+1) * interval]
            means.append(np.mean(batch))

        df = pd.DataFrame({'mean': means})
        axis = [i * interval for i in range(granularity)]
        axs.plot(axis, df['mean'], label=f"memory usage")

        plt.xlabel('num. op.')
        plt.ylabel('memory (kb)')
        plt.legend()  # Display the legend
        plt.title(f'Memory Evaluation Insert') 
        plt.savefig(f'{save_dir}/plot_memory.png')

    def __evaluate_utrace(self, config: dict, utrace:dict, dir: str):
        data = defaultdict(lambda: defaultdict(lambda: 0))
        for value in utrace:
            data[value['region']]['instructions']        += value['instructions']
            data[value['region']]['branch-instructions'] += value['branch-instructions']
            data[value['region']]['branch-misses']       += value['branch-misses']
            data[value['region']]['cache-references']    += value['cache-references']
            data[value['region']]['cache-misses']        += value['cache-misses']
        json.dump(data, open(f'{dir}/utrace.json', 'w'))

    def evaluate_statics(self, config: dict, dir: str):
        if os.path.isfile('{dir}/utrace.out'):
            log_utrace = json.load(open(f'{dir}/utrace.out', 'r'))
            self.__evaluate_utrace(config, log_utrace, dir)

    def plot_results(self, config: dict, dir: str):
        log_latency = json.load(open(f'{dir}/latency.out', 'r'))
        log_memory  = json.load(open(f'{dir}/memory.out', 'r'))
        self.__plot_latency(config, log_latency, 'dataset_performfill', 'Insert', dir)
        self.__plot_latency(config, log_latency, 'dataset_performquery', 'Query', dir)
        self.__plot_latency(config, log_latency, 'dataset_performdeletion', 'Deletion', dir)
        self.__plot_memoryusage(config, log_memory, dir)