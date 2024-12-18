import argparse
import asyncio

from pathlib import Path
from typing import Optional, List

MTE_ROOT_LOCAL = Path(__file__).parent.resolve().parent
MTE_ROOT_REMOTE = Path("~")
MTE_YCSB_REMOTE = MTE_ROOT_REMOTE / Path("mte/YCSB")


def map_analyser(datastructure: str) -> List[str]:
    datastructure = datastructure.lower()

    return {"exampledb": ["ycsb_exampledb_O0", "ycsb_exampledb_O3"]}[datastructure]


def log(prefix: str, msg: str, intend: int = 0):
    intend_offset = "\t" * intend
    for line in msg.split("\n"):
        if len(line) == 0:
            continue
        line = prefix + intend_offset + msg
        print(line, flush=True)


def info(msg, intend=1):
    intend = intend + 1
    GREEN = "\033[32m"
    RESET = "\033[0m\033[39m"
    log(prefix=GREEN + "stdout>" + RESET, msg=msg, intend=intend)


def error(msg):
    RED = "\033[31m"
    RESET = "\033[0m\033[39m"
    log(prefix=RED + "stderr>" + RESET, msg=msg, intend=1)


async def run(command: str, cwd: Optional[str] = None):
    assert isinstance(command, str)

    info(command)
    cp = await asyncio.create_subprocess_shell(
        cmd=command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    async def read_stream(stream, logger):
        while True:
            line = await stream.readline()
            if not line:
                break
            logger(line.decode().strip())

    await asyncio.gather(
        read_stream(cp.stdout, info),
        read_stream(cp.stderr, error),
    )

    _ = await cp.wait()
    if cp.returncode == 1:
        error("Failed.")
        exit(1)


async def run_ssh_command(user: str, host: str, port: int, cmd: str) -> None:
    await run(f"ssh -p {port} {user}@{host} '{cmd}'")


async def run_analyse_remote(user: str, host: str, port: int, datastructure: str):
    cmd = (
        f"cd {MTE_ROOT_REMOTE} && "
        f"./mte/scripts/setup_benchmark_environment.sh "
        f"{MTE_ROOT_REMOTE}/mte/YCSB/workloads "
        f"{MTE_ROOT_REMOTE}/mte/YCSB/build/ "
        f"{MTE_ROOT_REMOTE}/mte/YCSB/{datastructure}/benchmark.sh "
    )
    await run_ssh_command(user, host, port, cmd)

    cmd = (
        f'rsync -avz -e "ssh -A -p {port}" '
        f"{user}@{host}:{MTE_ROOT_REMOTE}/mte/YCSB/results "
        f"{MTE_ROOT_LOCAL}/result.txt "
    )
    await run(cmd)


async def run_build_remote(user: str, host: str, datastructure: str, port: int):
    datastructure = datastructure.upper()
    build_cmd = (
        f"cd {MTE_YCSB_REMOTE} && "
        f"rm -rf build && "
        f"cmake -B build -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -D{datastructure}=ON . && "
        "cmake --build build --clean-first"
    )
    await run(f"ssh -p {port} {user}@{host} '{build_cmd}'")


async def run_copy(user: str, host: str, port: int):
    cmd = (
        "rsync -avz --exclude '*.o' --exclude '*.out' --exclude '*.a'"
        f' -e "ssh -A -p {port}" {MTE_ROOT_LOCAL} {user}@{host}:{MTE_ROOT_REMOTE}'
    )
    await run(cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="benchmark-tool",
        description="A tool for performing benchmarks on remote machines.",
    )
    parser.add_argument(
        "--user",
        type=str,
        required=True,
        help="The username to use for logging into the remote machine.",
    )
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="The hostname or IP address of the remote machine to connect to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=22,
        help="The port number to connect to on the remote machine (default: 22).",
    )

    subparsers = parser.add_subparsers(
        title="Available subcommands",
        description="These are the available subcommands for different operations.",
        help="Use one of the subcommands below. For more details, use '<subcommand> -h'.",
        required=True,
        dest="subcommands",
    )

    copy_parser = subparsers.add_parser(
        "copy", help="Copy files to the remote machine."
    )

    build_parser = subparsers.add_parser(
        "build", help="Build the YCSB data structure on the remote machine."
    )
    build_parser.add_argument(
        "--datastructure",
        type=str,
        required=True,
        help="Specify the data structure to build on the remote machine.",
    )

    analyse_parser = subparsers.add_parser(
        "analyse", help="Analyse the YCSB data structure on the remote machine."
    )
    analyse_parser.add_argument(
        "--datastructure",
        type=str,
        required=True,
        help="Specify the data structure to analyse on the remote machine.",
    )

    args = parser.parse_args()
    user, host, port = args.user, args.host, args.port

    if args.subcommands == "copy":
        info("Copy files to the remote machine.", intend=0)
        asyncio.run(run_copy(user=user, host=host, port=port))

    elif args.subcommands == "build":
        info("Build the YCSB data structure on the remote machine.", intend=0)
        asyncio.run(
            run_build_remote(
                user=user, host=host, port=port, datastructure=args.datastructure
            )
        )

    elif args.subcommands == "analyse":
        info("Analyse the YCSB data structure on the remote machine.", intend=0)
        asyncio.run(
            run_analyse_remote(
                user=user, host=host, port=port, datastructure=args.datastructure
            )
        )

    else:
        parser.print_help()
        exit(1)
