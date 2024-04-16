#!/usr/bin/env python3
"""
*   @details: Used to generate the corresponding plots.
*   @author: Cristian Sandu <cristian.sandu@tum.de>
"""
from ..plotters import IPlotter

import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json

class MBench_1Plotter(IPlotter):
    def __init__(self, config: str):
        self.__config = config
    
    def __plot_latency(self, plotconfig: dict, log_latency: dict, fname: str, plotname: str, save_dir: str):
        threadnum      = plotconfig['threadnum']
        granularity    = self.__config['granularity']
        stdavg         = self.__config['stdavg']

        sns.set_theme()
        _, axs = plt.subplots(1, 1, figsize=(12, 6), sharey=True)

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
            axs.set_ylim(bottom=0, top=max(means))
            axs.set_xlim(left=0, right=len(dataset))
            axs.plot(axis, df['mean'], label=f"threads={threadval}")
            axs.fill_between(axis, df['mean'] - df['std'], df['mean'] + df['std'],
                             alpha=0.3)

        plt.xlabel('num. op.')
        plt.ylabel('latency (ns)')
        plt.legend()  # Display the legend
        plt.title(f'Performance Evaluation {plotname}') 
        plt.savefig(f'{save_dir}/plot_{fname}.png')
    
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

    def plot_results(self, config: dict, dir: str):
        log_latency = json.load(open(f'{dir}/latency.out', 'r'))
        log_memory  = json.load(open(f'{dir}/memory.out', 'r'))
        self.__plot_latency(config, log_latency, 'dataset_performfill', 'Insert', dir)
        self.__plot_latency(config, log_latency, 'dataset_performquery', 'Query', dir)
        self.__plot_latency(config, log_latency, 'dataset_performdeletion', 'Deletion', dir)
        self.__plot_memoryusage(config, log_memory, dir)

    # def plot_memory_performfill(self):
    #         capacity       = self.__config['capacity']
    #         threadnum      = self.__config['threadnum']
    #         granularity    = self.__config['granularity']
    #         repetitions    = self.__config['repetitions']
    #         filling_factor = self.__config['performfill']['filling_factor']

    #         average_data = defaultdict(lambda: [0] * granularity)
    #         for threadnum, datasets in self.__bresults.items():
    #             for dataset in datasets:
    #                 data = dataset['memory']['dataset_performfill']
    #                 data_index, size_data = [], len(data)
    #                 for i in range(0, granularity): 
    #                     if i == 0:  data_index.append(0)
    #                     else:       data_index.append(100*i/granularity)
    #                     left_range  = int(len(data) * i    /granularity)
    #                     right_range = int(len(data) * (i+1)/granularity)
    #                     average_data[threadnum][i] += sum(data[left_range : right_range]) / len(data[left_range : right_range])
    #             average_data[threadnum] = [x/granularity for x in average_data[threadnum]]
    #             average_data[threadnum] = [x/1024.0 for x in average_data[threadnum]]

    #         for threadnum in self.__bresults:
    #             plt.plot(data_index, average_data[threadnum], label = f'thread no. {threadnum}')
    #         plt.xlabel('percentage of ds. usage %')
    #         plt.ylabel('memory usage (kbytes)')
    #         plt.title(f'[mem_performfill] memory usage ds_insert (no.threads:{threadnum}: {repetitions}, gran.: {granularity}, cap.: {capacity}, fill fact.: {filling_factor})')
    #         plt.grid(True)
    #         plt.legend()

    #         plt.savefig(f'{self.__outputpath}/mem_performfill.png', dpi=300, bbox_inches = "tight")
    #         plt.show()
    #         plt.clf()

    # def plot_dataset_performfill(self):
    #         capacity       = self.__config['capacity']
    #         threadnum      = self.__config['threadnum']
    #         granularity    = self.__config['granularity']
    #         repetitions    = self.__config['repetitions']
    #         filling_factor = self.__config['performfill']['filling_factor']

    #         average_data = defaultdict(lambda: [0] * granularity)
    #         for threadnum, datasets in self.__bresults.items():
    #             for dataset in datasets:
    #                 dataset = dataset['performance']

    #                 data = dataset['dataset_performfill']
    #                 data_index, size_data = [], len(data)
    #                 for i in range(0, granularity): 
    #                     if i == 0:  data_index.append(0)
    #                     else:       data_index.append(100*i/granularity)
    #                     left_range  = int(len(data) * i    /granularity)
    #                     right_range = int(len(data) * (i+1)/granularity)
    #                     average_data[threadnum][i] += sum(data[left_range : right_range]) / len(data[left_range : right_range])
    #             average_data[threadnum] = [x/granularity for x in average_data[threadnum]]

    #         for threadnum in self.__bresults:
    #             plt.plot(data_index, average_data[threadnum], label = f'thread no. {threadnum}')
    #         plt.xlabel('percentage of ds. usage %')
    #         plt.ylabel('latency (ns)')
    #         plt.title(f'[dataset_performfill] latency ds_insert (no.threads:{threadnum}, rep.: {repetitions}, gran.: {granularity}, cap.: {capacity}, fill fact.: {filling_factor})')
    #         plt.grid(True)
    #         plt.legend()

    #         plt.savefig(f'{self.__outputpath}/performfill.png', dpi=300, bbox_inches = "tight")
    #         plt.show()
    #         plt.clf()

    #     def __plot_dataset_performquery(self):
    #         capacity       = self.__config['capacity']
    #         threadnum      = self.__config['threadnum']
    #         granularity    = self.__config['granularity']
    #         repetitions    = self.__config['repetitions']
    #         query_factor   = self.__config['performquery']['query_factor']
    #         success_factor = self.__config['performquery']['success_factor']

    #         average_data = defaultdict(lambda: [0] * granularity)
    #         for threadnum, datasets in self.__bresults.items():
    #             data_index, data_len = [], len(datasets[0]['performance']['dataset_performqueries'])
    #             for i in range(0, granularity): 
    #                 if i == 0:  data_index.append(0)
    #                 else:       data_index.append(data_len * i/granularity)

    #             for dataset in datasets:
    #                 data  = dataset['performance']['dataset_performqueries']
    #                 for i in range(0, granularity): 
    #                     left_range  = int(len(data) * i    /granularity)
    #                     right_range = int(len(data) * (i+1)/granularity)
    #                     if  len(data[left_range : right_range]) == 0: continue
    #                     average_data[threadnum][i] += sum(data[left_range : right_range]) / len(data[left_range : right_range])
    #             average_data[threadnum] = [x/granularity for x in average_data[threadnum]]

    #         for threadnum in self.__bresults:
    #             plt.plot(data_index, average_data[threadnum], label = f'thread no. {threadnum}')
    #         plt.xlabel('number of queries')
    #         plt.ylabel('latency (ns)')
    #         plt.title(f'[dataset_performquery] latency ds_read (no.threads{threadnum}, rep.: {repetitions}, gran.: {granularity}, cap.: {capacity}, rate: {query_factor}, succ.: {success_factor*100}%)')
    #         plt.grid(True)
    #         plt.legend()

    #         plt.savefig(f'{self.__outputpath}/performquery.png', dpi=300, bbox_inches = "tight")
    #         plt.show()
    #         plt.clf()

    #     def __plot_dataset_performdeletion(self):
    #         capacity        = self.__config['capacity']
    #         threadnum       = self.__config['threadnum']
    #         granularity     = self.__config['granularity']
    #         repetitions     = self.__config['repetitions']
    #         deletion_factor = self.__config['performdeletion']['deletion_factor']
    #         success_factor  = self.__config['performdeletion']['success_factor']

    #         average_data = defaultdict(lambda: [0] * granularity)
    #         for threadnum, datasets in self.__bresults.items():
    #             data_index, data_len = [], len(datasets[0]['performance']['dataset_performdeletion'])
    #             for i in range(0, granularity): 
    #                 if i == 0:  data_index.append(0)
    #                 else:       data_index.append(data_len * i/granularity)

    #             for dataset in datasets:
    #                 dataset = dataset['performance']
    #                 data = dataset['dataset_performdeletion']
    #                 for i in range(0, granularity): 
    #                     left_range  = int(len(data) * i    /granularity)
    #                     right_range = int(len(data) * (i+1)/granularity)
    #                     average_data[threadnum][i] += sum(data[left_range : right_range]) / len(data[left_range : right_range])
    #             average_data[threadnum] = [x/granularity for x in average_data[threadnum]]

    #         for threadnum in self.__bresults:
    #             plt.plot(data_index, average_data[threadnum], label = f'thread no. {threadnum}')
    #         plt.xlabel('number of deletions')
    #         plt.ylabel('latency (ns)')
    #         plt.title(f'[dataset_performdeletion] latency ds_remove (no.threads:{threadnum}, rep.: {repetitions}, gran.: {granularity}, cap.: {capacity}, del fact.: {deletion_factor}, succ.: {success_factor})')
    #         plt.grid(True)
    #         plt.legend()

    #         plt.savefig(f'{self.__outputpath}/performdeletion.png', dpi=300, bbox_inches = "tight")
    #         plt.show()
    #         plt.clf()
