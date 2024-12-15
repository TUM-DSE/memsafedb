import argparse
import asyncio

from pathlib import Path
from sys import executable
from typing import Optional
from tempfile import TemporaryDirectory

from analyser import map_analyser


MTE_ROOT_LOCAL = Path(__file__).parent.resolve().parent
MTE_ROOT_REMOTE = Path("~")
MTE_YCSB_REMOTE = MTE_ROOT_REMOTE / Path("mte/YCSB")


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


async def run_analyse_remote(user: str, host: str, datastructure: str):
    analyser = map_analyser(datastructure)
    with TemporaryDirectory() as d:
        info(msg=f"Setup anaylse enviroment for '{datastructure}' in {d}", intend=0)
        executables = analyser.executables
        for executable in executables:
            await run(f"cp {MTE_ROOT_LOCAL}/YCSB/build/{executable} {d}/{executable}")

    info("Anaylsing ...")


async def run_build_remote(user: str, host: str, datastructure: str):
    datastructure = datastructure.upper()
    build_cmd = (
        f"cd {MTE_YCSB_REMOTE} && "
        f"cmake -B build -D{datastructure}=ON . && "
        "cmake --build build"
    )

    await run(f"ssh {user}@{host} -t '{build_cmd}'")


async def run_copy(user: str, host: str):
    cmd = (
        "rsync -avz --exclude '*.o' --exclude '*.out' --exclude '*.a'"
        f' -e "ssh -A" {MTE_ROOT_LOCAL} {user}@{host}:{MTE_ROOT_REMOTE}'
    )
    await run(cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Perform benchmark")
    parser.add_argument("--user", help="The user which is used to logged in")
    parser.add_argument("--host", help="The host to which to connect")

    subparsers = parser.add_subparsers(
        title="subcommands",
        description="valid subcommands",
        help="additional help",
        required=True,
        dest="subcommands",
    )

    copy_parser = subparsers.add_parser(
        "copy", help="Copies the files to the remote machine"
    )
    build_parser = subparsers.add_parser("build", help="Builds YCSB remote")
    build_parser.add_argument("--datastructure", help="The data structure to build")

    analyser_parser = subparsers.add_parser("analyse", help="Builds YCSB remote")
    analyser_parser.add_argument(
        "--datastructure", help="The data structure to analyse"
    )

    args = parser.parse_args()
    user, host = args.user, args.host
    if None in [user, host]:
        parser.print_help()
        exit(1)

    if args.subcommands == "copy":
        asyncio.run(run_copy(user=user, host=host))

    elif args.subcommands == "build":
        datastructure = args.datastructure
        if datastructure is None:
            analyser_parser.print_help()
            exit(1)

        asyncio.run(run_build_remote(user=user, host=host, datastructure=datastructure))

    elif args.subcommands == "analyse":
        datastructure = args.datastructure
        if datastructure is None:
            analyser_parser.print_help()
            exit(1)

        asyncio.run(
            run_analyse_remote(user=user, host=host, datastructure=datastructure)
        )

    else:
        parser.print_help()
        exit(1)
