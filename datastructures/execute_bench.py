#!/usr/bin/env python3
import yaml
import execo
from execo_engine import Engine
from functools import reduce
from itertools import product
import pathlib
import os
import socket
import sys
from time import time, sleep
import random
import tqdm
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait
import pandas as pd
import getpass
import re

base_dir = pathlib.Path().resolve()
RESULT_DIR = os.path.join(base_dir, "../results")
min_target_time = 10
max_time = 600
nbops_dataframe = pd.DataFrame()
debug_mode = False

commands = {
        "ycsb": "/scratch/{}/memsafedb_bin/ycsb".format(getpass.getuser()),
        "queue_bench": "/scratch/{}/memsafedb_bin/queue_bench".format(getpass.getuser()),
}

def calculate_weighted_average_latency(log_text):
    lines = log_text.strip().split('\n')
    target_line = None
    run_summary_index = -1
    for i, line in enumerate(lines):
        if "Run runtime" in line or "Run operations" in line:
            run_summary_index = i
            break
    start_search = run_summary_index - 1 if run_summary_index != -1 else len(lines) - 1
    for i in range(start_search, -1, -1):
        if "operations;" in lines[i] and "[" in lines[i] and "Avg=" in lines[i]:
            target_line = lines[i]
            break
    op_pattern = re.compile(r'\[([a-zA-Z0-9_-]+):.*?Count=(\d+).*?Avg=(\d+(?:\.\d+)?)\]')
    matches = op_pattern.findall(target_line)
    total_ops_count = 0
    weighted_latency_sum = 0.0
    for op_name, count_str, avg_str in matches:
        count = int(count_str)
        avg = float(avg_str)
        total_ops_count += count
        weighted_latency_sum += (count * avg)
        
    if total_ops_count == 0:
        return 0.0
    overall_avg_latency = weighted_latency_sum / total_ops_count
    return overall_avg_latency

def get_taskset(nthreads):
    if nthreads == '1':
        return "taskset -c 0"
    return "taskset -c 0-{} ".format(int(nthreads)-1)

def run_process(host, cmd):
    if debug_mode:
        print("Executing: {}\non host: {}".format(cmd, host))
        return execo.Process(cmd="sleep 0")
    else:
        if host == socket.gethostname():
            process = execo.Process(cmd, shell=True, timeout=max_time, nolog_timeout=True)
        else:
            process = execo.SshProcess(cmd, host, shell=True, timeout=max_time, nolog_timeout=True)
        process.run()
        sleep(1) # for stability
        return process

def start_process(host, cmd):
    if host == socket.gethostname():
        process = execo.Process(cmd)
    else:
        process = execo.SshProcess(cmd, host)
    process.start()
    return process

def get_host(arch):
    if arch == "mte":
        return "eliza"
    if arch == "cheri":
        return "ace"

def build_benchmarks(host: str, arch: str):
    if host == "eliza":
        cmd = "nix develop {}#{} --command just build_structs {}".format(os.path.join(base_dir, ".."), host, arch)
    else:
        cmd = "nix develop {}#{}-{} --command just -f {} build_structs {}".format(os.path.join(base_dir, "../"), host, arch, os.path.join(base_dir, "../justfile"), arch)
    process = run_process(host, cmd)

class Configuration:
    system: str
    name: str
    host: str
    arch: str
    type_bench: str
    nthreads: int
    args: str
    nb_ops: int

    def __init__(self, system, name, type_bench, host, arch, nthreads, args):
        self.system = system
        self.name = name
        self.host = host
        self.arch = arch
        self.nthreads = nthreads
        self.type_bench = type_bench
        self.args = args
        self.nb_ops = 0

    def get_conf(self):
        return nbops_dataframe[
                (nbops_dataframe['host'] == self.host) &
                (nbops_dataframe['system'] == self.system) &
                (nbops_dataframe['name'] == self.name) &
                (nbops_dataframe['nthreads'] == int(self.nthreads))
                ]['nb_ops']
    
    def get_command(self, nb_ops):
        cmd = ""
        match(self.type_bench):
            case "ycsb":
                taskset_str = get_taskset(self.nthreads)
                args = reduce(lambda x, y: x+y, map(lambda x: (' ' if 'load' in x or 'run' in x else ' -p ')+x, self.args))
                args += ' -p recordcount={} -p operationcount={} '.format(nb_ops, nb_ops)
                if 'load' not in args and 'run' not in args:
                    args += ' -load -run'
                cmd = " {} {}_{} -db {} -s -p threadcount={} -p workload=com.yahoo.ycsb.workloads.CoreWorkload {}".format(taskset_str, commands['ycsb'], self.arch, self.system, self.nthreads, args)
            case "queue_bench":
                nthreads = self.nthreads
                if self.nthreads == "1":
                    nthreads = "2"
                taskset_str = get_taskset(nthreads)
                cmd = " {} {}_{} {} {}".format(taskset_str, commands['queue_bench'], self.arch, nb_ops, int(int(nthreads)/2))
        if self.arch == "mte":
            cmd = "GLIBC_TUNABLES='glibc.mem.tagging=3'" + cmd
        return cmd

    def format_output(self, stdout ,rep):
        out = ""
        if not debug_mode:
            match(self.type_bench):
                case "ycsb":
                    latency = calculate_weighted_average_latency(stdout)
                    out += "{},{},{},{},{},{},{},{}\n".format(rep, self.host, self.arch, self.system, self.name, self.nthreads, self.nb_ops, latency)
                case "queue_bench":
                    time = float(stdout.split(" ")[7]) * 10**9
                    thrpt = self.nb_ops / time
                    lat = 1/thrpt
                    out += "{},{},{},{},{},{},{},{:.3f}\n".format(rep, self.host, self.arch, self.system, self.name, self.nthreads, self.nb_ops, lat)
        return out

    def execute(self, starting_nb_ops, rep, extension) -> str:
        conf = self.get_conf()
        self.nb_ops = conf.tolist()[0]
        cmd = self.get_command(self.nb_ops)
        process = run_process(self.host, cmd)
        out = "{} - {} - {} - {} - {} - {} - {}\n".format(rep, self.host, self.arch, self.system, self.name, self.nthreads, self.nb_ops)
        out += process.stdout 
        with open(os.path.join(RESULT_DIR, "raw_{}.txt".format(extension)), "a") as raw_file:
            raw_file.write(out)
            raw_file.write("\n")
        return self.format_output(process.stdout, rep)

class ExpeEngine(Engine):
    confs: list

    def __init__(self):
        super(ExpeEngine, self).__init__()
        self.args_parser.add_argument("--nbops", type=int, help="Default number of operations", default=1000)
        self.args_parser.add_argument("--threads", type=str, help="Comma separated list of number of threads (1,4 or 1 etc..)", default="1,4")
        self.args_parser.add_argument("--extensions", type=str, help="Comma separated list of the extensions to evaluate (mte and/or cheri)", default="mte,cheri")
        self.args_parser.add_argument("--systems", type=str, help="Comma separated list of the systems to evaluate", default="all")
        self.args_parser.add_argument("--workloads", type=str, help="Comma separated list of the workloads to evaluate", default="all")
        self.args_parser.add_argument("--repetitions", type=int, help="Number of repetitions", default=5)
        self.args_parser.add_argument("--debug", type=bool, help="Debug mode", default=False)

    def make_confs(self):
        with open("benchmarks.yaml", 'r') as f:
            data = yaml.safe_load(f)

        ds_list = data['definitions']['systems']
        wl_list = data['definitions']['workloads']
        extensions_list = data['definitions']['extensions']

        self.confs = []

        for ds in ds_list:
            ds_caps = set(ds['capabilities'])
            parallelizable = False
            if 'can_multithread' in ds_caps:
                parallelizable = True
            if 'extra_args' in ds.keys():
                extra_args = ds['extra_args']
            else:
                extra_args= []

            for wl in wl_list:
                if wl['type'] in ds['to_evaluate']:
                    if set(wl['requires']).issubset(ds_caps):
                        args = wl['args'] + extra_args
                        if "all" in self.args.systems or ds['name'] in self.args.systems:
                            if "all" in self.args.workloads or wl['name'] in self.args.workloads:
                                for ext in extensions_list:
                                    if "all" in self.args.extensions or ext['name'] in self.args.extensions:
                                        for arch in ext['archs']:
                                            for t in self.args.threads:
                                                if int(t) == 1 or (parallelizable and int(t) <= ext['max_threads']):
                                                    self.confs.append(Configuration(ds['name'], wl['name'], wl['type'], ext['host'], arch, t, args))
        return self.confs

    def prepare(self):
        global debug_mode, nbops_dataframe
        self.args = self.args_parser.parse_args()
        self.args.threads = self.args.threads.split(",")
        self.args.extensions = self.args.extensions.split(",")
        self.args.systems = self.args.systems.split(',')
        self.args.workloads = self.args.workloads.split(',')
        if self.args.debug:
            debug_mode = True
        pathlib.Path(RESULT_DIR).mkdir(parents=True, exist_ok=True)
        if os.path.exists("nb_ops.csv"):
            nbops_dataframe = pd.read_csv("nb_ops.csv")
        archs = []
        for ext in self.args.extensions:
            host = get_host(ext)
            #build_benchmarks(host, ext)
            #build_benchmarks(host, "aarch64") 
            archs.append((host, ext))
            archs.append((host, "aarch64"))
        self.make_confs()

    def run(self):
        cross = list(product(self.confs, [x for x in range(self.args.repetitions)]))
        random.shuffle(cross)
        out_file = open(os.path.join(RESULT_DIR, "datastructures_{}.csv".format(self.args.extensions[0])), "w")
        out_file.write("repetition,host,arch,system,name,nthreads,nb_ops,latency\n")
        for conf, r in tqdm.tqdm(cross, total=len(cross)):
            stdout = conf.execute(self.args.nbops, r, self.args.extensions[0])
            if len(stdout) != 0:
                out_file.write(stdout) 
        out_file.close()

def main():
    engine = ExpeEngine()
    engine.prepare()
    engine.run()

if __name__ == "__main__":
    main()
