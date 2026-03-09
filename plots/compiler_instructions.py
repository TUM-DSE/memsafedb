#!/usr/bin/env python3
"""Plot CHERI/MTE instruction-count ratios across DBMS binaries."""

from typing import Any, cast

from common import *


CSV_PATH = os.path.join(result_dir, "compiler_instruction_counts.csv")
OUTPUT_PATH = os.path.join(result_dir, "compiler_instructions.pdf")

DISPLAY_NAMES = {
    "duckdb": "DuckDB",
    "ladybug": "LadyBugDB",
    "leveldb": "LevelDB",
    "mysql": "MySQL",
    "redis": "Redis",
    "sqlite": "SQLite",
}

CHERI_ORDER = ["Redis", "LevelDB", "SQLite"]
MTE_ORDER = ["Redis", "MySQL", "LevelDB", "SQLite", "DuckDB", "LadyBugDB"]


def human_count(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}\\,M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}\\,K"
    return f"{int(value)}"


def load_numeric(df: pd.DataFrame, column: str) -> None:
    df[column] = cast(Any, pd.to_numeric(cast(Any, df[column]), errors="coerce"))


def row_for_system(df: pd.DataFrame, system: str) -> pd.Series | None:
    if system not in df.index:
        return None
    row = df.loc[system]
    if isinstance(row, pd.DataFrame):
        return cast(pd.Series, row.iloc[0])
    return cast(pd.Series, row)


def annotate_bar(
    ax: Any,
    x_pos: float,
    y_pos: float,
    label: str,
    *,
    fontsize: float | None = None,
    y_offset: float = 2,
) -> None:
    ax.annotate(
        label,
        xy=(x_pos, y_pos),
        xytext=(0, y_offset),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=fontsize if fontsize is not None else FONTSIZE_ANNOTATION - 1,
        clip_on=False,
        zorder=5,
    )


def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Results file not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    if df.empty:
        print("No instruction-count data found.")
        return

    df = df[df["status"] == "ok"].copy()
    if df.empty:
        print("No successful instruction-count rows found.")
        return

    database_col = cast(Any, df["database"])
    df["system"] = database_col.apply(lambda value: DISPLAY_NAMES.get(str(value), str(value).title()))
    df_frame = cast(pd.DataFrame, df)
    for column in [
        "new_instruction_pct",
        "new_instruction_count",
        "glibc_instruction_pct",
        "glibc_instruction_count",
        "cap_operand_instruction_pct",
        "cap_operand_instruction_count",
        "cap_manip_instruction_pct",
        "cap_manip_instruction_count",
    ]:
        load_numeric(df_frame, column)
    df = cast(Any, df_frame).dropna(
        subset=[
            "new_instruction_pct",
            "new_instruction_count",
            "glibc_instruction_pct",
            "glibc_instruction_count",
            "cap_operand_instruction_pct",
            "cap_operand_instruction_count",
            "cap_manip_instruction_pct",
            "cap_manip_instruction_count",
        ]
    )

    cheri_df = cast(pd.DataFrame, df[df["mechanism"] == "cheri"].set_index("system"))
    mte_df = cast(pd.DataFrame, df[df["mechanism"] == "mte"].set_index("system"))

    cheri_systems = [name for name in CHERI_ORDER if name in cheri_df.index]
    mte_systems = [name for name in MTE_ORDER if name in mte_df.index]

    fig, (ax_cheri, ax_mte) = plt.subplots(
        1,
        2,
        figsize=(figwidth_half, fig_height),
        gridspec_kw={"width_ratios": [3, 5]},
    )

    cheri_x = np.arange(len(cheri_systems))
    mte_x = np.arange(len(mte_systems))

    cheri_operand_heights = []
    cheri_manip_heights = []
    cheri_labels = []
    for system in cheri_systems:
        row = row_for_system(cheri_df, system)
        if row is None:
            continue
        operand_pct = float(row["cap_operand_instruction_pct"])
        manip_pct = float(row["cap_manip_instruction_pct"])
        operand_count = float(row["cap_operand_instruction_count"])
        manip_count = float(row["cap_manip_instruction_count"])
        cheri_operand_heights.append(operand_pct)
        cheri_manip_heights.append(manip_pct)
        # shorter, two-line label
        cheri_labels.append(f"{human_count(operand_count + manip_count)}")

    if cheri_systems:
        operand_bars = ax_cheri.bar(
            cheri_x,
            cheri_operand_heights,
            color=BASELINE_CHERI_COLOR,
            edgecolor="black",
            width=0.72,
            zorder=3,
        )
        ax_cheri.bar(
            cheri_x,
            cheri_manip_heights,
            bottom=cheri_operand_heights,
            color=CHERI_COLOR,
            edgecolor="black",
            hatch=CHERI_HATCH,
            width=0.72,
            zorder=3,
        )
        for idx, bar in enumerate(operand_bars):
            total_height = cheri_operand_heights[idx] + cheri_manip_heights[idx]
            annotate_bar(
                ax_cheri,
                bar.get_x() + bar.get_width() / 2,
                total_height,
                cheri_labels[idx],
            )

    mte_heights = []
    mte_glibc_heights = []
    mte_labels = []
    for system in mte_systems:
        row = row_for_system(mte_df, system)
        if row is None:
            continue
        height = float(row["new_instruction_pct"])
        glibc_height = float(row["glibc_instruction_pct"])
        count = float(row["new_instruction_count"])
        glibc_count = float(row["glibc_instruction_count"])
        mte_heights.append(height)
        mte_glibc_heights.append(glibc_height)
        mte_labels.append(human_count(count + glibc_count))

    if mte_systems:
        mte_bars = ax_mte.bar(
            mte_x,
            mte_heights,
            color=MTE_COLOR,
            edgecolor="black",
            width=0.72,
            zorder=3,
        )
        ax_mte.bar(
            mte_x,
            mte_glibc_heights,
            bottom=mte_heights,
            color=BASELINE_MTE_COLOR,
            edgecolor="black",
            hatch=MTE_HATCH,
            width=0.72,
            zorder=3,
        )
        for idx, bar in enumerate(mte_bars):
            # put zero labels a bit above baseline so they stay readable
            total_height = mte_heights[idx] + mte_glibc_heights[idx]
            label_y = total_height if total_height > 0 else 0.002
            annotate_bar(
                ax_mte,
                bar.get_x() + bar.get_width() / 2,
                label_y,
                mte_labels[idx],
            )

    ax_cheri.set_ylabel("Changed instructions (\\%)", fontsize=FONTSIZE_AXIS_LABEL)
    ax_cheri.set_xticks(cheri_x)
    ax_cheri.set_xticklabels(cheri_systems, fontsize=FONTSIZE_TICK_LABEL, rotation=20)

    ax_mte.set_xticks(mte_x)
    ax_mte.set_xticklabels(mte_systems, fontsize=FONTSIZE_TICK_LABEL, rotation=20)

    for ax in [ax_cheri, ax_mte]:
        ax.tick_params(axis="y", labelsize=FONTSIZE_TICK_LABEL)
        ax.grid(True, axis="y", linestyle="--", alpha=0.7, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", pad=0)

    cheri_max = max([a + b for a, b in zip(cheri_operand_heights, cheri_manip_heights)], default=0.1)
    mte_max = max([a + b for a, b in zip(mte_heights, mte_glibc_heights)], default=0.1)

    # extra headroom for labels and legends above axes
    ax_cheri.set_ylim(0, cheri_max * 1.15)
    ax_mte.set_ylim(0, mte_max * 1.20)

    from matplotlib.patches import Patch
    
    fig.legend(
        handles=[
            Patch(facecolor=BASELINE_CHERI_COLOR, edgecolor="black", label="CHERI operand"),
            Patch(facecolor=CHERI_COLOR, hatch=CHERI_HATCH, edgecolor="black", label="CHERI new"),
            Patch(facecolor=MTE_COLOR, edgecolor="black", label="MTE"),
            Patch(facecolor=BASELINE_MTE_COLOR, hatch=MTE_HATCH, edgecolor="black", label="MTE glibc"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.05),
        ncol=4,
        frameon=True,
        fontsize=FONTSIZE_LEGEND,
        columnspacing=1.2,
        handletextpad=0.6,
    )

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    plt.savefig(OUTPUT_PATH, format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
