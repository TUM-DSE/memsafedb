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

SYSTEM_ORDER = ["Redis", "LevelDB", "MySQL", "SQLite", "DuckDB", "LadyBugDB"]


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


def annotate_bar(ax: Any, x_pos: float, y_pos: float, label: str, y_offset: float = 2.0) -> None:
    ax.annotate(
        label,
        xy=(x_pos, y_pos),
        xytext=(0, y_offset),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=FONTSIZE_ANNOTATION - 1,
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

    cheri_df = cast(pd.DataFrame, df[df["mechanism"] == "cheri"].set_index("system"))
    mte_df = cast(pd.DataFrame, df[df["mechanism"] == "mte"].set_index("system"))
    systems = [name for name in SYSTEM_ORDER if name in df["system"].unique() or name in DISPLAY_NAMES.values()]

    fig, ax_cheri = plt.subplots(figsize=(7 / 3, 1.2 * 1.1))
    ax_mte = ax_cheri.twinx()

    x = np.arange(len(systems))
    width = 0.34
    x_cheri = x - width / 2
    x_mte = x + width / 2

    cheri_operand = []
    cheri_manip = []
    cheri_labels = []
    cheri_missing = []
    mte_app = []
    mte_glibc = []
    mte_labels = []

    for system in systems:
        cheri_row = row_for_system(cheri_df, system)
        if cheri_row is None or cheri_row.get("status", "ok") != "ok":
            cheri_operand.append(0.0)
            cheri_manip.append(0.0)
            cheri_labels.append("")
            cheri_missing.append(True)
        else:
            operand_pct = float(cheri_row["cap_operand_instruction_pct"])
            manip_pct = float(cheri_row["cap_manip_instruction_pct"])
            operand_count = float(cheri_row["cap_operand_instruction_count"])
            manip_count = float(cheri_row["cap_manip_instruction_count"])
            cheri_operand.append(operand_pct)
            cheri_manip.append(manip_pct)
            cheri_labels.append(human_count(operand_count + manip_count))
            cheri_missing.append(False)

        mte_row = row_for_system(mte_df, system)
        if mte_row is None or mte_row.get("status", "ok") != "ok":
            mte_app.append(0.0)
            mte_glibc.append(0.0)
            mte_labels.append("")
        else:
            app_pct = float(mte_row["new_instruction_pct"])
            glibc_pct = float(mte_row["glibc_instruction_pct"])
            app_count = float(mte_row["new_instruction_count"])
            glibc_count = float(mte_row["glibc_instruction_count"])
            mte_app.append(app_pct)
            mte_glibc.append(glibc_pct)
            mte_labels.append(human_count(app_count + glibc_count))

    cheri_bars = ax_cheri.bar(
        x_cheri,
        cheri_operand,
        width=width,
        color=BASELINE_CHERI_COLOR,
        edgecolor="black",
        zorder=3,
    )
    ax_cheri.bar(
        x_cheri,
        cheri_manip,
        width=width,
        bottom=cheri_operand,
        color=CHERI_COLOR,
        edgecolor="black",
        hatch=CHERI_HATCH,
        zorder=3,
    )

    for idx, bar in enumerate(cheri_bars):
        if cheri_missing[idx]:
            ax_cheri.text(
                x_cheri[idx],
                max(0.01, ax_cheri.get_ylim()[1] * 0.02 if ax_cheri.get_ylim()[1] > 0 else 0.01),
                "$\\times$",
                color="red",
                fontsize=FONTSIZE_AXIS_LABEL,
                ha="center",
                va="bottom",
                fontweight="bold",
                zorder=5,
            )
            continue
        total = cheri_operand[idx] + cheri_manip[idx]
        annotate_bar(ax_cheri, bar.get_x() + bar.get_width() / 2, total, cheri_labels[idx])

    mte_bars = ax_mte.bar(
        x_mte,
        mte_app,
        width=width,
        color=MTE_COLOR,
        edgecolor="black",
        zorder=3,
    )
    ax_mte.bar(
        x_mte,
        mte_glibc,
        width=width,
        bottom=mte_app,
        color=BASELINE_MTE_COLOR,
        edgecolor="black",
        hatch=MTE_HATCH,
        zorder=3,
    )
    for idx, bar in enumerate(mte_bars):
        total = mte_app[idx] + mte_glibc[idx]
        if total <= 0:
            continue
        annotate_bar(ax_mte, bar.get_x() + bar.get_width() / 2, total, mte_labels[idx])

    cheri_max = max([a + b for a, b in zip(cheri_operand, cheri_manip)], default=0.1)
    mte_max = max([a + b for a, b in zip(mte_app, mte_glibc)], default=0.1)
    ax_cheri.set_ylim(0, cheri_max * 1.35)
    ax_mte.set_ylim(0, mte_max * 1.35)

    ax_cheri.set_ylabel("Changed instructions (\\%)", fontsize=FONTSIZE_AXIS_LABEL - 1)

    ax_cheri.set_xticks(x)
    ax_cheri.set_xticklabels(systems, fontsize=FONTSIZE_TICK_LABEL - 3)

    ax_cheri.tick_params(axis="y", labelsize=FONTSIZE_TICK_LABEL - 1)
    ax_mte.tick_params(axis="y", labelsize=FONTSIZE_TICK_LABEL - 1)
    ax_cheri.tick_params(axis="x")

    ax_cheri.set_axisbelow(True)

    ax_cheri.tick_params(axis="y", colors=CHERI_COLOR)
    #ax_cheri.spines["right"].set_color(CHERI_COLOR)
    ax_mte.tick_params(axis="y", colors=MTE_COLOR)
    #ax_mte.spines["right"].set_color(MTE_COLOR)

    ax_cheri.text(
        -0.09, 0.9,
        "CHERI",
        transform=ax_cheri.transAxes,
        ha="center",
        va="bottom",
        fontsize=FONTSIZE_AXIS_LABEL - 1,
        color=CHERI_COLOR,
    )

    ax_mte.text(
        1.08, 0.9,
        "MTE",
        transform=ax_mte.transAxes,
        ha="center",
        va="bottom",
        fontsize=FONTSIZE_AXIS_LABEL - 1,
        color=MTE_COLOR,
    )
    from matplotlib.ticker import FixedLocator
    ax_cheri.yaxis.set_major_locator(FixedLocator([0, 20, 40, 60]))
    ax_mte.yaxis.set_major_locator(FixedLocator([0.00, 0.05, 0.10]))

    from matplotlib.patches import Patch

    fig.legend(
        handles=[
            Patch(facecolor=BASELINE_CHERI_COLOR, edgecolor="black", label="CHERI operand"),
            Patch(facecolor=CHERI_COLOR, hatch=CHERI_HATCH, edgecolor="black", label="CHERI new"),
            Patch(facecolor=MTE_COLOR, edgecolor="black", label="MTE"),
            Patch(facecolor=BASELINE_MTE_COLOR, hatch=MTE_HATCH, edgecolor="black", label="MTE glibc"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.52, 0.92),
        ncol=4,
        frameon=True,
        fontsize=FONTSIZE_LEGEND - 2,
        handlelength=0.8,
        handleheight=0.8,
        handletextpad=0.4,
        columnspacing=0.8,
    )

    fig.tight_layout()
    plt.savefig(OUTPUT_PATH, format="pdf")
    plt.close(fig)
    print(f"Plot saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
