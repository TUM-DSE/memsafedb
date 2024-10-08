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
from collections import defaultdict

import subprocess, json, tempfile, os

from ..benchmarks import IBenchmarks
from ..utils import do_average

class MBench(IBenchmarks):
    NAME_EXECUTABLE_LAT  = f'{os.path.dirname(os.path.abspath(__file__))}/mlatency'
    NAME_EXECUTABLE_MEM  = f'{os.path.dirname(os.path.abspath(__file__))}/mmemory'
    RESULT_FILE_NAME = 'generic_output'
    NULL_PATH        = '/dev/null'
    PERFORATOR_PATH  = 'src/perf/perforator/perforator'

    def __init__(self, config: dict):
        self.__config     = config
    
    def __parse_results_performance(self, lines: list[str]) -> dict:
        data = defaultdict(lambda: {})
        for line in lines:
            function_name, key_num, duration = line.split(' ')
            data[function_name][int(key_num)] = int(duration)
        
        rdata = {}
        for function, fdata in data.items():
            rdata[function] = [fdata[x] for x in sorted(fdata.keys())]
        return rdata

    def __parse_results_memory(self, lines: list[str]) -> dict:
        data = defaultdict(lambda: [])
        for line in lines:
            function_name, _, memory_usage = line.split(' ')
            data[function_name].append(int(memory_usage))
        return data 

    def __perform_bechmark(self, libso_path: str, config_path: str):
        process = subprocess.Popen([MBench.NAME_EXECUTABLE_LAT, libso_path, config_path, MBench.RESULT_FILE_NAME], stdout=subprocess.PIPE)
        print(' '.join([MBench.NAME_EXECUTABLE_LAT, libso_path, config_path, MBench.RESULT_FILE_NAME]))
        stdout, _ = process.communicate()
        data = stdout.decode()
        if data: print(data)    # debugging functionality
        import time
        if process.returncode != 0:
            time.sleep(1000)
            raise Exception(f'MBench failed during execution, exit-code: {process.returncode}')
        
        return self.__parse_results_performance(open(f'{MBench.RESULT_FILE_NAME}_performance.out', 'r').readlines())

    def __perform_memoryusage(self, libso_path: str, config_path: str):
        process = subprocess.Popen([MBench.NAME_EXECUTABLE_MEM, libso_path, config_path, MBench.RESULT_FILE_NAME])
        exit_code = process.wait()
        if exit_code != 0: raise Exception(f'MBench filed during execution, exit-code: {exit_code}')
        return self.__parse_results_memory(open(f'{MBench.RESULT_FILE_NAME}_memory.out', 'r').readlines())
    
    def perform_benchmark(self, libso_path: str, output_path: str):
        os.makedirs(output_path, exist_ok=True)
        json.dump(self.__config, open(f'{output_path}/config.json', 'w'))

        tlatency = {}
        for threadnum in self.__config['threadnum']:
            temp = tempfile.NamedTemporaryFile(mode='w')
            config = self.__config.copy()
            config.update({
                'threadnum': threadnum
            })
            json.dump(config, temp)
            temp.flush()

            presults, mresults = [], []
            for _ in range(self.__config['repetitions']):
                performance = self.__perform_bechmark(libso_path=libso_path, config_path=temp.name)
                presults.append(performance)

            function_names = presults[0].keys()
            pfresults = {}
            for function_name in function_names:
                pfresults[function_name] = do_average([presult[function_name] for presult in presults])
            tlatency[threadnum] = pfresults
        json.dump(tlatency, open(f'{output_path}/latency.out', 'w'))

        temp = tempfile.NamedTemporaryFile(mode='w')
        config = self.__config.copy()
        json.dump(config, temp)
        temp.flush()
        tmemory = self.__perform_memoryusage(libso_path=libso_path, config_path=temp.name)
        json.dump(tmemory, open(f'{output_path}/memory.out', 'w'))
    
    def __parse_utrace(self, output: str):
        data = []
        for line in output.split('\n')[3:]:
            if '|' not in line: continue
            functname, instr, branchinstr, branchmiss, cacheref, cachemiss, timeelapsed = line[1:-1].split('|')
            data.append({
                'region':               functname.strip(),
                'instructions':         int(instr.strip()),
                'branch-instructions':  int(branchinstr.strip()),
                'branch-misses':        int(branchmiss.strip()),
                'cache-references':     int(cacheref.strip()),
                'cache-misses':         int(cachemiss.strip())
            })
        return data

    def __perform_utrace(self, libso_path: str, config_path: str) -> dict:
        """
            Perform the perf_profilling over self.perform_benchmark. The execution
            is slow
        """
        process = subprocess.run(
            [MBench_1.PERFORATOR_PATH, '--summary', '-r', '_ds_insert', '-r', '_ds_read', '-r', '_ds_remove',
                MBench_1.NAME_EXECUTABLE_LAT, libso_path, config_path, MBench_1.RESULT_FILE_NAME], stdout=subprocess.PIPE)
        if process.returncode != 0:
            # TODO: possible error, check it
            # raise Exception(f'{MBench_1.PERFORATOR_PATH} filed during execution, exit-code: {process.returncode}')
            return None
        result = self.__parse_utrace(process.stdout.decode())
        return result

    def __parse_perf(self, output: str):
        data = {}
        for line in output.split('\n'):
            for keyword in ['instructions', 'branches', 'branch-misses', 'cache-misses', 'cache-references']:
                if keyword not in line: continue
                line = line.strip()
                value, keyword = line.split('      ')[:2]
                value = int(value.strip().replace(',', ''))
                data[keyword] = value
        return data

    def __perform_perf(self, libso_path: str, config_path: str) -> dict:
        process = subprocess.run(['perf', 'stat', '-a', '-e', 'instructions,branches,branch-misses,cache-misses,cache-references',
                                  '-o', MBench_1.RESULT_FILE_NAME, MBench_1.NAME_EXECUTABLE_LAT, libso_path, config_path,
                                  MBench_1.NULL_PATH], stdout=subprocess.PIPE)
        result = self.__parse_perf(open(MBench_1.RESULT_FILE_NAME).read())
        if process.returncode != 0: raise Exception(f'MBench_1 filed during execution, exit-code: {process.returncode}')
        return result

    def perform_perf(self, libso_path: str, output_path: str):
        """
            this function should be called after perform_benchmark, to prepare the output
            directory.
        """
        temp = tempfile.NamedTemporaryFile(mode='w')
        config = self.__config.copy()
        config.update({
            'threadnum': 1
        })
        json.dump(config, temp)
        temp.flush()
        
        utrace = self.__perform_utrace(libso_path=libso_path, config_path=temp.name)
        json.dump(utrace, open(f'{output_path}/utrace.out', 'w'))

        tperf = {}
        for threadnum in self.__config['threadnum']:
            temp = tempfile.NamedTemporaryFile(mode='w')
            config.update({
                'threadnum': threadnum
            })
            json.dump(config, temp)
            temp.flush()
            tperf[threadnum] = self.__perform_perf(libso_path=libso_path, config_path=temp.name)
        json.dump(tperf, open(f'{output_path}/perf.out', 'w'))
