#!/usr/bin/env python3
"""Count CHERI/MTE-specific instructions in DBMS binaries."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DBMS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = DBMS_DIR.parent
RESULTS_FILE = PROJECT_ROOT / "results" / "compiler_instruction_counts.csv"

DATABASES = ["duckdb", "leveldb", "redis", "sqlite", "mysql", "ladybug"]

MTE_MNEMONICS = {
    "addg",
    "gmi",
    "irg",
    "ldg",
    "ldgm",
    "st2g",
    "stg",
    "stgm",
    "stz2g",
    "stzg",
    "stzgm",
    "subg",
}

CHERI_PATTERNS = [
    re.compile(r"^(?:gc(?:base|flgs|len|off|perm|tag|type|value)|gctype)$"),
    re.compile(r"^(?:sc(?:addr|bnds|bndse|flgs|off|perm|value)|scvalue)$"),
    re.compile(r"^(?:align[du]|build|cfromptr|chk(?:eq|ss)|clrperm|clrtag|cpy(?:type)?|ctoptr|ldct|seal(?:entry)?|stct|unseal)$"),
]

DISASM_LINE_RE = re.compile(r"^\s*[0-9a-f]+:\s+(?:[0-9a-f]{2,8}\s+)+([.a-zA-Z0-9_+-]+)(?:\s+(.*))?$")
CAPABILITY_OPERAND_RE = re.compile(r"\b(?:c(?:[12]?\d|3[01]|sp|zr))\b")


@dataclass(frozen=True)
class BinaryTarget:
    database: str
    mechanism: str
    variant: str
    path: Path


def candidate_paths() -> dict[str, list[BinaryTarget]]:
    return {
        "duckdb": [
            BinaryTarget("duckdb", "mte", "release-mte", DBMS_DIR / "duckdb" / "build" / "release-mte" / "duckdb"),
            BinaryTarget("duckdb", "cheri", "release-cheri", DBMS_DIR / "duckdb" / "build" / "release-cheri" / "duckdb"),
        ],
        "leveldb": [
            BinaryTarget("leveldb", "mte", "release-mte", DBMS_DIR / "leveldb" / "build" / "release-mte" / "db_bench"),
            BinaryTarget("leveldb", "cheri", "release-cheri", DBMS_DIR / "leveldb" / "build" / "release-cheri" / "db_bench"),
        ],
        "redis": [
            BinaryTarget("redis", "mte", "release-mte", DBMS_DIR / "redis" / "src" / "redis-server-mte"),
            BinaryTarget("redis", "cheri", "release-cheri", DBMS_DIR / "redis" / "src" / "redis-server-cheri"),
        ],
        "sqlite": [
            BinaryTarget("sqlite", "mte", "release-mte", DBMS_DIR / "sqlite" / "build" / "release-mte" / "sqlite3"),
            BinaryTarget("sqlite", "cheri", "release-cheri", DBMS_DIR / "sqlite" / "build" / "release-cheri" / "sqlite3"),
        ],
        "mysql": [
            BinaryTarget("mysql", "mte", "release-mte", DBMS_DIR / "mysql" / "build" / "release-mte" / "bin" / "mysqld"),
        ],
        "ladybug": [
            BinaryTarget("ladybug", "mte", "release-mte", DBMS_DIR / "ladybug" / "build-mte" / "tools" / "benchmark" / "lbug_benchmark"),
            BinaryTarget("ladybug", "cheri", "release-cheri", DBMS_DIR / "ladybug" / "build-cheri" / "tools" / "benchmark" / "lbug_benchmark"),
        ],
    }


def detect_objdump(mechanism: str) -> tuple[list[str], str]:
    if mechanism == "cheri":
        env_candidates = [
            os.environ.get("CHERI_OBJDUMP"),
            os.environ.get("MORELLO_OBJDUMP"),
        ]
        morello_clang_dir = os.environ.get("MORELLO_CLANG_DIR")
        if morello_clang_dir:
            morello_clang = Path(morello_clang_dir) / "bin" / "clang"
            if morello_clang.exists():
                result = subprocess.run(
                    [str(morello_clang), "--print-prog-name=llvm-objdump"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    check=False,
                )
                candidate = result.stdout.strip()
                if candidate:
                    env_candidates.append(candidate)
            env_candidates.extend([
                str(Path(morello_clang_dir) / "bin" / "llvm-objdump"),
                str(Path(morello_clang_dir) / "bin" / "objdump"),
            ])
        env_candidates.extend([
            shutil.which("llvm-objdump"),
            shutil.which("objdump"),
        ])
        for candidate in env_candidates:
            if candidate and Path(candidate).exists():
                args = [candidate, "-d"]
                extra_args = os.environ.get("CHERI_OBJDUMP_ARGS")
                if extra_args:
                    args.extend(extra_args.split())
                return args, candidate
    else:
        for candidate in [os.environ.get("LLVM_OBJDUMP"), shutil.which("llvm-objdump"), shutil.which("objdump")]:
            if candidate and Path(candidate).exists():
                return [candidate, "-d"], candidate

    raise FileNotFoundError(f"No usable objdump found for mechanism '{mechanism}'")


def is_new_mnemonic(mechanism: str, mnemonic: str) -> bool:
    mnemonic = mnemonic.lower()
    if mechanism == "mte":
        return mnemonic in MTE_MNEMONICS
    if mechanism == "cheri":
        return any(pattern.match(mnemonic) for pattern in CHERI_PATTERNS)
    return False


def has_capability_operands(operands: str | None) -> bool:
    if not operands:
        return False
    return CAPABILITY_OPERAND_RE.search(operands) is not None


def disassemble(target: BinaryTarget) -> tuple[str, str]:
    cmd, tool_name = detect_objdump(target.mechanism)
    result = subprocess.run(
        [*cmd, str(target.path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"disassembly failed with exit code {result.returncode}: {result.stdout[:400]}")
    return result.stdout, tool_name


def resolve_glibc_path(binary_path: Path) -> Path | None:
    result = subprocess.run(
        ["ldd", str(binary_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        match = re.search(r"libc\.so\.6 => (\S+)", line)
        if match:
            candidate = Path(match.group(1))
            if candidate.exists():
                return candidate
    return None


def count_mte_in_shared_runtime(binary_path: Path) -> tuple[int, float, str]:
    glibc_path = resolve_glibc_path(binary_path)
    if glibc_path is None:
        return 0, 0.0, ""

    disassembly, _ = disassemble(BinaryTarget("glibc", "mte", "shared", glibc_path))
    total, operand_count, manip_count, _, _, _ = count_instructions(disassembly, "mte")
    del operand_count
    pct = (100.0 * manip_count / total) if total else 0.0
    return manip_count, pct, str(glibc_path)


def count_instructions(disassembly: str, mechanism: str) -> tuple[int, int, int, dict[str, int], dict[str, int], int]:
    total = 0
    operand_count = 0
    manip_count = 0
    operand_mnemonic_counts: dict[str, int] = {}
    manip_mnemonic_counts: dict[str, int] = {}
    unknown_count = 0

    for line in disassembly.splitlines():
        match = DISASM_LINE_RE.match(line)
        if not match:
            continue
        mnemonic = match.group(1).lower()
        operands = match.group(2)
        total += 1
        if mnemonic == ".inst":
            unknown_count += 1
        if is_new_mnemonic(mechanism, mnemonic):
            manip_count += 1
            manip_mnemonic_counts[mnemonic] = manip_mnemonic_counts.get(mnemonic, 0) + 1
        elif mechanism == "cheri" and has_capability_operands(operands):
            operand_count += 1
            operand_mnemonic_counts[mnemonic] = operand_mnemonic_counts.get(mnemonic, 0) + 1

    return total, operand_count, manip_count, operand_mnemonic_counts, manip_mnemonic_counts, unknown_count


def rows_for_database(database: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for target in candidate_paths()[database]:
        row: dict[str, object] = {
            "database": target.database,
            "mechanism": target.mechanism,
            "variant": target.variant,
            "binary_path": str(target.path.relative_to(PROJECT_ROOT)),
        }

        if not target.path.exists():
            row.update(
                {
                    "status": "missing-binary",
                    "disassembler": "",
                    "total_instructions": 0,
                    "new_instruction_count": 0,
                    "new_instruction_pct": "",
                    "cap_operand_instruction_count": 0,
                    "cap_operand_instruction_pct": "",
                    "cap_manip_instruction_count": 0,
                    "cap_manip_instruction_pct": "",
                    "glibc_instruction_count": 0,
                    "glibc_instruction_pct": "",
                    "glibc_path": "",
                    "unknown_instruction_count": 0,
                    "mnemonic_counts": "{}",
                    "operand_mnemonic_counts": "{}",
                    "manip_mnemonic_counts": "{}",
                }
            )
            rows.append(row)
            continue

        try:
            disassembly, tool_name = disassemble(target)
            (
                total,
                operand_count,
                manip_count,
                operand_mnemonic_counts,
                manip_mnemonic_counts,
                unknown_count,
            ) = count_instructions(disassembly, target.mechanism)
            new_count = operand_count + manip_count
            pct = (100.0 * new_count / total) if total else 0.0
            operand_pct = (100.0 * operand_count / total) if total else 0.0
            manip_pct = (100.0 * manip_count / total) if total else 0.0
            glibc_count = 0
            glibc_pct = 0.0
            glibc_path = ""
            if target.mechanism == "mte":
                glibc_count, glibc_pct, glibc_path = count_mte_in_shared_runtime(target.path)
            status = "ok"

            row.update(
                {
                    "status": status,
                    "disassembler": tool_name,
                    "total_instructions": total,
                    "new_instruction_count": new_count,
                    "new_instruction_pct": f"{pct:.6f}",
                    "cap_operand_instruction_count": operand_count,
                    "cap_operand_instruction_pct": f"{operand_pct:.6f}",
                    "cap_manip_instruction_count": manip_count,
                    "cap_manip_instruction_pct": f"{manip_pct:.6f}",
                    "glibc_instruction_count": glibc_count,
                    "glibc_instruction_pct": f"{glibc_pct:.6f}",
                    "glibc_path": glibc_path,
                    "unknown_instruction_count": unknown_count,
                    "mnemonic_counts": json.dumps(dict(sorted((operand_mnemonic_counts | manip_mnemonic_counts).items())), sort_keys=True),
                    "operand_mnemonic_counts": json.dumps(dict(sorted(operand_mnemonic_counts.items())), sort_keys=True),
                    "manip_mnemonic_counts": json.dumps(dict(sorted(manip_mnemonic_counts.items())), sort_keys=True),
                }
            )
        except Exception as exc:  # noqa: BLE001
            row.update(
                {
                    "status": f"error: {exc}",
                    "disassembler": "",
                    "total_instructions": 0,
                    "new_instruction_count": 0,
                    "new_instruction_pct": "",
                    "cap_operand_instruction_count": 0,
                    "cap_operand_instruction_pct": "",
                    "cap_manip_instruction_count": 0,
                    "cap_manip_instruction_pct": "",
                    "glibc_instruction_count": 0,
                    "glibc_instruction_pct": "",
                    "glibc_path": "",
                    "unknown_instruction_count": 0,
                    "mnemonic_counts": "{}",
                    "operand_mnemonic_counts": "{}",
                    "manip_mnemonic_counts": "{}",
                }
            )

        rows.append(row)

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Count CHERI/MTE-specific instructions in DBMS binaries")
    parser.add_argument("--db", default="all", help=f"Database to inspect (all, {', '.join(DATABASES)})")
    parser.add_argument("--output", type=Path, default=RESULTS_FILE, help="Output CSV file")
    args = parser.parse_args()

    if args.db == "all":
        databases = DATABASES
    elif args.db in DATABASES:
        databases = [args.db]
    else:
        print(f"Unknown database: {args.db}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "database",
        "mechanism",
        "variant",
        "binary_path",
        "status",
        "disassembler",
        "total_instructions",
        "new_instruction_count",
        "new_instruction_pct",
        "cap_operand_instruction_count",
        "cap_operand_instruction_pct",
        "cap_manip_instruction_count",
        "cap_manip_instruction_pct",
        "glibc_instruction_count",
        "glibc_instruction_pct",
        "glibc_path",
        "unknown_instruction_count",
        "mnemonic_counts",
        "operand_mnemonic_counts",
        "manip_mnemonic_counts",
    ]

    all_rows: list[dict[str, object]] = []
    for database in databases:
        print(f"Counting instructions for {database}...")
        all_rows.extend(rows_for_database(database))

    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
