#!/usr/bin/env python3
"""
*   @details:
*       1. Generate 64bit keys and 64bit values from an uniform random distribution to be inserted, removed or queried.
*       2. Evaluation of Insertion: from 0% -> 95% of the total capacity.
*       3. Evaluation of Queries: Positive and Negative questions (50/50).
*       4. Evaluation of Deletion: Remove a selections of keys until the usage reaches ~50%.
*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
"""
import matplotlib.pyplot as plt
from collections import defaultdict

import subprocess, json, tempfile, os

class MBench_1:
    NAME_EXECUTABLE  = f'{os.path.dirname(os.path.abspath(__file__))}/mbench_1'
    RESULT_FILE_NAME = 'generic_output'
    PERF_RESULT      = 'perf_data.out'

    def __init__(self, config: dict):
        self.__config     = config
        self.__bresults   = []
    
    def __prepare_dir(self):
        os.makedirs(self.__outputpath, exist_ok=True)

    def __parse_results_performance(self, lines: list[str]) -> dict:
        data = defaultdict(lambda: [])
        for line in lines:
            function_name, thread_id, key_num, key, value, status, start_time, end_time = line.split(' ')
            data[function_name].append(int(int(end_time) - int(start_time)))
        return data

    def __parse_results_memory(self, lines: list[str]) -> dict:
        data = defaultdict(lambda: [])
        for line in lines:
            function_name, thread_id, key_num, memory_usage = line.split(' ')
            data[function_name].append(int(memory_usage))
        return data

    def __perform_bechmark(self, libso_path: str, config_path: str) -> list[str]:
        process = subprocess.Popen([MBench_1.NAME_EXECUTABLE, libso_path, config_path, MBench_1.RESULT_FILE_NAME])
        exit_code = process.wait()
        if exit_code != 0: raise Exception(f'MBench_1 filed during execution, exit-code: {exit_code}')
        
        return {
            'performance': self.__parse_results_performance(
                open(f'{MBench_1.RESULT_FILE_NAME}_performance.out', 'r').readlines()),
            'memory': self.__parse_results_memory(
                open(f'{MBench_1.RESULT_FILE_NAME}_memory.out', 'r').readlines())
        }

    def perform_benchmark(self, libso_path: str):
        self.__bresults = defaultdict(lambda: [])
        for threadnum in self.__config['threadnum']:
            with tempfile.NamedTemporaryFile(mode='w') as temp:
                # rescale for the given threads
                config = self.__config.copy()
                config['threadnum'] = threadnum
                json.dump(config, temp)
                temp.flush()
                for _ in range(self.__config['repetitions']):
                    self.__bresults[threadnum].append(self.__perform_bechmark(libso_path=libso_path, config_path=temp.name))

    def plot_results(self, result_name: str):
        self.__outputpath = f"{self.__config['output_path']}/{result_name}"
        self.__prepare_dir()

        self.__plot_dataset_performfill()
        self.__plot_dataset_performquery()
        self.__plot_dataset_performdeletion()

        self.__plot_memory_performfill()
    
    def __plot_memory_performfill(self):
        capacity       = self.__config['capacity']
        threadnum      = self.__config['threadnum']
        granularity    = self.__config['granularity']
        repetitions    = self.__config['repetitions']
        filling_factor = self.__config['performfill']['filling_factor']

        average_data = defaultdict(lambda: [0] * granularity)
        for threadnum, datasets in self.__bresults.items():
            for dataset in datasets:
                data = dataset['memory']['dataset_performfill']
                data_index, size_data = [], len(data)
                for i in range(0, granularity): 
                    if i == 0:  data_index.append(0)
                    else:       data_index.append(100*i/granularity)
                    left_range  = int(len(data) * i    /granularity)
                    right_range = int(len(data) * (i+1)/granularity)
                    average_data[threadnum][i] += sum(data[left_range : right_range]) / len(data[left_range : right_range])
            average_data[threadnum] = [x/granularity for x in average_data[threadnum]]
            average_data[threadnum] = [x/1024.0 for x in average_data[threadnum]]

        for threadnum in self.__bresults:
            plt.plot(data_index, average_data[threadnum], label = f'thread no. {threadnum}')
        plt.xlabel('percentage of ds. usage %')
        plt.ylabel('memory usage (kbytes)')
        plt.title(f'[mem_performfill] memory usage ds_insert (no.threads:{threadnum}: {repetitions}, gran.: {granularity}, cap.: {capacity}, fill fact.: {filling_factor})')
        plt.grid(True)
        plt.legend()

        plt.savefig(f'{self.__outputpath}/mem_performfill.png', dpi=300, bbox_inches = "tight")
        plt.show()
        plt.clf()

    def __plot_dataset_performfill(self):
        capacity       = self.__config['capacity']
        threadnum      = self.__config['threadnum']
        granularity    = self.__config['granularity']
        repetitions    = self.__config['repetitions']
        filling_factor = self.__config['performfill']['filling_factor']

        average_data = defaultdict(lambda: [0] * granularity)
        for threadnum, datasets in self.__bresults.items():
            for dataset in datasets:
                dataset = dataset['performance']

                data = dataset['dataset_performfill']
                data_index, size_data = [], len(data)
                for i in range(0, granularity): 
                    if i == 0:  data_index.append(0)
                    else:       data_index.append(100*i/granularity)
                    left_range  = int(len(data) * i    /granularity)
                    right_range = int(len(data) * (i+1)/granularity)
                    average_data[threadnum][i] += sum(data[left_range : right_range]) / len(data[left_range : right_range])
            average_data[threadnum] = [x/granularity for x in average_data[threadnum]]

        for threadnum in self.__bresults:
            plt.plot(data_index, average_data[threadnum], label = f'thread no. {threadnum}')
        plt.xlabel('percentage of ds. usage %')
        plt.ylabel('latency (ns)')
        plt.title(f'[dataset_performfill] latency ds_insert (no.threads:{threadnum}, rep.: {repetitions}, gran.: {granularity}, cap.: {capacity}, fill fact.: {filling_factor})')
        plt.grid(True)
        plt.legend()

        plt.savefig(f'{self.__outputpath}/performfill.png', dpi=300, bbox_inches = "tight")
        plt.show()
        plt.clf()

    def __plot_dataset_performquery(self):
        capacity       = self.__config['capacity']
        threadnum      = self.__config['threadnum']
        granularity    = self.__config['granularity']
        repetitions    = self.__config['repetitions']
        query_factor   = self.__config['performquery']['query_factor']
        success_factor = self.__config['performquery']['success_factor']

        average_data = defaultdict(lambda: [0] * granularity)
        for threadnum, datasets in self.__bresults.items():
            data_index, data_len = [], len(datasets[0]['performance']['dataset_performqueries'])
            for i in range(0, granularity): 
                if i == 0:  data_index.append(0)
                else:       data_index.append(data_len * i/granularity)

            for dataset in datasets:
                data  = dataset['performance']['dataset_performqueries']
                for i in range(0, granularity): 
                    left_range  = int(len(data) * i    /granularity)
                    right_range = int(len(data) * (i+1)/granularity)
                    if  len(data[left_range : right_range]) == 0: continue
                    average_data[threadnum][i] += sum(data[left_range : right_range]) / len(data[left_range : right_range])
            average_data[threadnum] = [x/granularity for x in average_data[threadnum]]

        for threadnum in self.__bresults:
            plt.plot(data_index, average_data[threadnum], label = f'thread no. {threadnum}')
        plt.xlabel('number of queries')
        plt.ylabel('latency (ns)')
        plt.title(f'[dataset_performquery] latency ds_read (no.threads{threadnum}, rep.: {repetitions}, gran.: {granularity}, cap.: {capacity}, rate: {query_factor}, succ.: {success_factor*100}%)')
        plt.grid(True)
        plt.legend()

        plt.savefig(f'{self.__outputpath}/performquery.png', dpi=300, bbox_inches = "tight")
        plt.show()
        plt.clf()

    def __plot_dataset_performdeletion(self):
        capacity        = self.__config['capacity']
        threadnum       = self.__config['threadnum']
        granularity     = self.__config['granularity']
        repetitions     = self.__config['repetitions']
        deletion_factor = self.__config['performdeletion']['deletion_factor']
        success_factor  = self.__config['performdeletion']['success_factor']

        average_data = defaultdict(lambda: [0] * granularity)
        for threadnum, datasets in self.__bresults.items():
            data_index, data_len = [], len(datasets[0]['performance']['dataset_performdeletion'])
            for i in range(0, granularity): 
                if i == 0:  data_index.append(0)
                else:       data_index.append(data_len * i/granularity)

            for dataset in datasets:
                dataset = dataset['performance']
                data = dataset['dataset_performdeletion']
                for i in range(0, granularity): 
                    left_range  = int(len(data) * i    /granularity)
                    right_range = int(len(data) * (i+1)/granularity)
                    average_data[threadnum][i] += sum(data[left_range : right_range]) / len(data[left_range : right_range])
            average_data[threadnum] = [x/granularity for x in average_data[threadnum]]

        for threadnum in self.__bresults:
            plt.plot(data_index, average_data[threadnum], label = f'thread no. {threadnum}')
        plt.xlabel('number of deletions')
        plt.ylabel('latency (ns)')
        plt.title(f'[dataset_performdeletion] latency ds_remove (no.threads:{threadnum}, rep.: {repetitions}, gran.: {granularity}, cap.: {capacity}, del fact.: {deletion_factor}, succ.: {success_factor})')
        plt.grid(True)
        plt.legend()

        plt.savefig(f'{self.__outputpath}/performdeletion.png', dpi=300, bbox_inches = "tight")
        plt.show()
        plt.clf()

    def __perform_perf_profilling(self, libso_path: str, config_path: str) -> dict:
        """
            Perform the perf_profilling over self.perform_benchmark. The execution
            is slow
        """
        process = subprocess.Popen(['perf', 'record', '-ag', '-e LLC-stores,LLC-store-misses,LLC-prefetch-misses', 
                                    MBench_1.NAME_EXECUTABLE, libso_path, config_path, MBench_1.RESULT_FILE_NAME])
        exit_code = process.wait()
        if exit_code != 0: raise Exception(f'MBench_1 filed during execution, exit-code: {exit_code}')

        process = subprocess.Popen(['perf', 'data', 'convert','--force', '--to-json', MBench_1.PERF_RESULT])
        exit_code = process.wait()
        if exit_code != 0: raise Exception(f'MBench_1 filed during execution, exit-code: {exit_code}')

        return json.load(open(MBench_1.PERF_RESULT, 'r'))
    
    def perform_perf_profilling(self, libso_path: str):
        with tempfile.NamedTemporaryFile(mode='w') as temp:
            json.dump(self.__config, temp)
            temp.flush()
            
            self.__bresults = []
            for _ in range(self.__config['perf']['repetitions']):
                result = self.__perform_perf_profilling(libso_path=libso_path, config_path=temp.name)
        