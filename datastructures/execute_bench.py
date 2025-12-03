#!/usr/bin/env python3
import yaml
import execo
from execo_engine import Engine
from functools import reduce
from itertools import product
import pathlib
import os
import socket
from time import time, sleep
import tqdm
from datetime import datetime

base_dir = pathlib.Path().resolve()
RESULT_DIR = os.path.join(base_dir, "results")
max_time = 60
min_target_time = 20

commands = {
        "ycsb": "/scratch/{}/memsafedb_bin/ycsb".format(os.getlogin()),
        "queue_bench": "/scratch/{}/memsafedb_bin/queue_bench".format(os.getlogin()),
}

def get_taskset(nthreads):
    if nthreads == 0:
        return "taskset -c 0"
    return "taskset -c 0-{} ".format(int(nthreads)-1)

def run_process(host, cmd):
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
        cmd = "nix develop {}#{} --command just -f {} full_build {}".format(os.path.join(base_dir, ".."), host, os.path.join(base_dir, "justfile"), arch)
    else:
        cmd = "nix develop {}#{}-{} --command just -f {} full_build {}".format(os.path.join(base_dir, ".."), host, arch, os.path.join(base_dir, "justfile"), arch)
    process = run_process(host, cmd)

class Configuration:
    system: str
    name: str
    type_bench: str
    is_parallelizable: bool
    args: str
    stdout: dict

    def __init__(self, system, name, type_bench, is_parallelizable, args):
        self.system = system
        self.name = name
        self.is_parallelizable = is_parallelizable
        self.type_bench = type_bench
        self.args = args
        self.stdout = {}
    
    def get_command(self, host, arch, nb_ops, nthreads):
        match(self.type_bench):
            case "ycsb":
                taskset_str = get_taskset(nthreads)
                args = reduce(lambda x, y: x+y, map(lambda x: (' ' if 'load' in x or 'run' in x else ' -p ')+x, self.args))
                if 'recordcount' not in args:
                    args += ' -p recordcount={} -p operationcount={} '.format(nb_ops, nb_ops)
                if 'load' not in args and 'run' not in args:
                    args += ' -load -run'
                return "GLIBC_TUNABLES='glibc.mem.tagging=3' {} {}_{} -db {} -p threadcount={} -p workload=com.yahoo.ycsb.workloads.CoreWorkload -p recordcount={} -p operationcount={} {}".format(taskset_str, commands['ycsb'], arch, self.system, nthreads, nb_ops, nb_ops, args)
            case "queue_bench":
                taskset_str = get_taskset(nthreads*2)
                return "GLIBC_TUNABLES='glibc.mem.tagging=3' {} {}_{} {} {}".format(taskset_str, commands['queue_bench'], arch, nb_ops, nthreads)

    def format_output(self, key, stdout, rep):
        out = ""
        match(self.type_bench):
            case "ycsb":
                load_thrpt = 0.0
                run_thrpt = 0.0
                outlines = stdout.splitlines()
                for l in outlines:
                    if l.startswith("Load throughput"):
                        load_thrpt = float(l.split(" ")[2])
                    if l.startswith("Run throughput"):
                        run_thrpt = float(l.split(" ")[2])
                thrpt = run_thrpt
                if run_thrpt == 0.0:
                    thrpt = load_thrpt
                host = key.split('-')[0]
                arch = key.split('-')[1]
                nb_ops = key.split('-')[2]
                nthreads = key.split('-')[3]
                out += "{},{},{},{},{},{},{},{}\n".format(rep, host, arch, self.system, self.name, nthreads, nb_ops, thrpt)
            case "queue_bench":
                host = key.split('-')[0]
                arch = key.split('-')[1]
                nb_ops = int(key.split('-')[2])
                nthreads = key.split('-')[3]
                time = float(stdout.split(" ")[7])
                thrpt = nb_ops / time
                out += "{},{},{},{},{},{},{},{:.3f}\n".format(rep, host, arch, self.system, self.name, nthreads, str(nb_ops), thrpt)
        return out

    def execute(self, host, arch, nthreads, nb_ops) -> (str, str):
        if int(nthreads) > 1 and not self.is_parallelizable:
            return '', ''
        current_ops = nb_ops
        while True:
            cmd = self.get_command(host, arch, current_ops, nthreads)
            process = run_process(host, cmd)
            if process.timeouted: # too long
                current_ops = int(current_ops / 2)
            elif process.end_date - process.start_date >= min_target_time: # long enough
                key = "{}-{}-{}-{}".format(host, arch, current_ops, nthreads)
                return key, process.stdout
            else: # too short
                current_ops = int(current_ops * 10)
            sleep(1)

class ExpeEngine(Engine):
    confs: list

    def __init__(self):
        super(ExpeEngine, self).__init__()
        self.args_parser.add_argument("--nbops", type=int, help="Default number of operations", default=1000)
        self.args_parser.add_argument("--threads", type=str, help="Comma separated list of number of threads (1,4 or 1 etc..)", default="1,4")
        self.args_parser.add_argument("--extensions", type=str, help="Comma separated list of the extensions to evaluate (mte and/or cheri)", default="mte,cheri")
        self.args_parser.add_argument("--systems", type=str, help="Comma separated list of the systems to evaluate (mte and/or cheri)", default="all")
        self.args_parser.add_argument("--repetitions", type=int, help="Number of repetitions", default=5)
    
    def make_confs(self):
        with open("benchmarks.yaml", 'r') as f:
            data = yaml.safe_load(f)

        ds_list = data['definitions']['systems']
        wl_list = data['definitions']['workloads']

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
                            self.confs.append(Configuration(ds['name'], wl['name'], wl['type'], parallelizable, args))
        return self.confs

    def prepare(self):
        self.args = self.args_parser.parse_args()
        self.args.threads = self.args.threads.split(",")
        self.args.extensions = self.args.extensions.split(",")
        self.args.systems = self.args.systems.split(',')
        pathlib.Path(RESULT_DIR).mkdir(parents=True, exist_ok=True)
        self.make_confs()

    def run(self):
        archs = []
        for ext in self.args.extensions:
            host = get_host(ext)
            build_benchmarks(host, ext)
            build_benchmarks(host, "aarch64") 
            archs.append((host, ext))
            archs.append((host, "aarch64"))
        cross = list(product(archs, self.confs, self.args.threads, [x for x in range(self.args.repetitions)]))
        out_file = open(os.path.join(RESULT_DIR, "datastructures.csv"), "w")
        out_file.write("repetition,host,arch,system,name,nthreads,nb_ops,throughput\n")
        for arch, conf, nthreads, r in tqdm.tqdm(cross, total=len(cross)):
            key, stdout = conf.execute(arch[0], arch[1], nthreads, self.args.nbops)
            if len(key) != 0 and len(stdout) != 0:
                out_file.write(conf.format_output(key, stdout, r)) 
        out_file.close()

    def dump(self):
        out_file = open(os.path.join(RESULT_DIR, "benchmarks.out"), "w")
        out_file.write("Results from {}\n\n".format(execo.format_date(time())))
        for c in self.confs:
            out_file.write("system: {}, name: {}\n".format(c.system, c.name))
            out_file.write("Parameters\n")
            if len(c.args) != 0:
                out_file.write(reduce(lambda x, y: x+' '+y, c.args)+'\n')
            for k, out in c.stdout.items():
                out_file.write(k+"\n")
                out_file.write(out)
                out_file.write("\n")
            out_file.write("-----\n")

def main():
    engine = ExpeEngine()
    engine.prepare()
    engine.run()
    #engine.dump()

if __name__ == "__main__":
    main()
