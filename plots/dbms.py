#!/usr/bin/env python3
"""DBMS benchmark plotting script."""
from common import *

BASELINE_COLOR = 'tab:blue'
MTE_COLOR = 'tab:orange'
BASELINE_HATCH = ''
MTE_HATCH = '///'

def add_two_item_legend(fig, left_label: str, right_label: str, loc: str = 'upper left', bbox_to_anchor: tuple = (0.03, 0.97)):
    handles = [
        mpl.patches.Patch(facecolor=BASELINE_COLOR, edgecolor='black', label=left_label),
        mpl.patches.Patch(facecolor=MTE_COLOR, edgecolor='black', hatch=MTE_HATCH, label=right_label),
    ]
    fig.legend(
        handles=handles,
        fontsize=FONTSIZE - 2,
        loc=loc,
        ncol=2,
        bbox_to_anchor=bbox_to_anchor,
    )


def spaced_positions(count: int, spacing: float = 1.2) -> np.ndarray:
    return np.arange(count) * spacing


def load_dbms_data() -> pd.DataFrame:
    """Load DBMS benchmark results from CSV."""
    csv_path = os.path.join(result_dir, 'dbms_results.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Results file not found: {csv_path}")
    return pd.read_csv(csv_path)


def plot_grouped_bars(
    df: pd.DataFrame,
    database: str,
    benchmark: str,
    metric: str,
    ylabel: str,
    filename: str,
    figsize: tuple = None,
    higher_is_better: bool = False,
):
    """Generic grouped bar plot for baseline vs MTE."""
    data = df[
        (df['database'] == database) &
        (df['benchmark'] == benchmark) &
        (df['metric_name'] == metric)
    ]

    if data.empty:
        print(f"No data for {database}/{benchmark}/{metric}")
        return

    if figsize is None:
        figsize = (figwidth_half, fig_height * 1.3)

    fig, ax = plt.subplots(figsize=figsize)

    # Pivot to get release vs release-mte side by side
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )

    # Sort workloads naturally (q1, q2, ... q10, q11, etc.)
    pivot = pivot.reindex(natsorted(pivot.index, alg=ns.NUMAFTER))

    x = spaced_positions(len(pivot))
    width = 0.5

    # Get column names dynamically
    variants = pivot.columns.tolist()

    # Determine baseline and MTE variants based on available options
    # Priority: release/release-mte > release-dynamic/release-mte > first/last
    if 'release' in variants and 'release-mte' in variants:
        baseline_var = 'release'
        mte_var = 'release-mte'
    elif 'release-dynamic' in variants and 'release-mte' in variants:
        baseline_var = 'release-dynamic'
        mte_var = 'release-mte'
    else:
        # Fallback to first and last (but this may not be correct)
        baseline_var = variants[0]
        mte_var = variants[-1]

    bars1 = ax.bar(
        x - width / 2,
        pivot[baseline_var],
        width,
        label='Baseline',
        color=BASELINE_COLOR,
        edgecolor='black',
        hatch=BASELINE_HATCH,
    )
    bars2 = ax.bar(
        x + width / 2,
        pivot[mte_var],
        width,
        label='MTE',
        color=MTE_COLOR,
        edgecolor='black',
        hatch=MTE_HATCH,
    )

    ax.set_ylabel(ylabel, fontsize=FONTSIZE, labelpad=1)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)

    # Rotate labels if many workloads
    if len(pivot) > 10:
        ax.tick_params(axis='x', labelrotation=45)
    elif len(pivot) > 6:
        ax.tick_params(axis='x', labelrotation=30)

    add_two_item_legend(fig, 'Baseline', 'MTE')

    # Add better/worse indicator
    indicator = higher_better_str if higher_is_better else lower_better_str
    ax.text(
        0.5,
        0.94,
        indicator,
        color='blue',
        ha='center',
        va='top',
        transform=ax.transAxes,
        fontsize=FONTSIZE - 1,
    )

    # Format y-axis for large numbers
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))

    plt.tight_layout()
    plt.savefig(
        os.path.join(result_dir, filename),
        format='pdf',
        bbox_inches='tight',
    )
    plt.close()
    print(f"Generated {filename}")


def plot_duckdb_tpch(df: pd.DataFrame):
    """Plot DuckDB TPC-H query times (warm cache)."""
    # Filter to only warm cache variants (release and release-mte)
    data = df[
        (df['database'] == 'duckdb') &
        (df['benchmark'] == 'tpch') &
        (df['metric_name'] == 'query_time') &
        (df['variant'].isin(['release', 'release-mte']))
    ]

    if data.empty:
        print("No data for duckdb/tpch/query_time (warm cache)")
        return

    figsize = (figwidth_full, fig_height * 1.5)
    fig, ax = plt.subplots(figsize=figsize)

    # Pivot to get release vs release-mte side by side
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )

    # Sort workloads naturally (q1, q2, ... q10, q11, etc.)
    pivot = pivot.reindex(natsorted(pivot.index, alg=ns.NUMAFTER))

    x = np.arange(len(pivot))
    width = 0.35

    # Get column names dynamically
    variants = pivot.columns.tolist()

    # Determine baseline and MTE variants based on available options
    # Priority: release/release-mte > release-dynamic/release-mte > first/last
    if 'release' in variants and 'release-mte' in variants:
        baseline_var = 'release'
        mte_var = 'release-mte'
    elif 'release-dynamic' in variants and 'release-mte' in variants:
        baseline_var = 'release-dynamic'
        mte_var = 'release-mte'
    else:
        # Fallback to first and last (but this may not be correct)
        baseline_var = variants[0]
        mte_var = variants[-1]

    bars1 = ax.bar(
        x - width / 2,
        pivot[baseline_var],
        width,
        label='Baseline',
        color=baseline_color,
        edgecolor='black',
        hatch=baseline_hatch,
    )
    bars2 = ax.bar(
        x + width / 2,
        pivot[mte_var],
        width,
        label='MTE',
        color=sys_color,
        edgecolor='black',
        hatch=sys_hatch,
    )

    ax.set_ylabel('Query Time (s)', fontsize=FONTSIZE)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)
    ax.tick_params(axis='x', labelrotation=45)

    ax.legend(fontsize=FONTSIZE - 1, loc='upper right')

    # Add better/worse indicator
    ax.annotate(
        lower_better_str,
        color='blue',
        xy=(0.02, 0.92),
        xycoords='axes fraction',
        fontsize=FONTSIZE - 1,
    )

    # Format y-axis for large numbers
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))

    plt.tight_layout()
    plt.savefig(
        os.path.join(result_dir, 'dbms_duckdb_tpch.pdf'),
        format='pdf',
        bbox_inches='tight',
    )
    plt.close()
    print("Generated dbms_duckdb_tpch.pdf")


def plot_duckdb_tpch_cold(df: pd.DataFrame):
    """Plot DuckDB TPC-H query times (cold cache)."""
    # Filter to only cold cache variants (release-cold and release-mte-cold)
    data = df[
        (df['database'] == 'duckdb') &
        (df['benchmark'] == 'tpch') &
        (df['metric_name'] == 'query_time') &
        (df['variant'].isin(['release-cold', 'release-mte-cold']))
    ]

    if data.empty:
        print("No data for duckdb/tpch/query_time (cold cache)")
        return

    figsize = (figwidth_full, fig_height * 1.5)
    fig, ax = plt.subplots(figsize=figsize)

    # Pivot to get release-cold vs release-mte-cold side by side
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )

    # Sort workloads naturally (q1, q2, ... q10, q11, etc.)
    pivot = pivot.reindex(natsorted(pivot.index, alg=ns.NUMAFTER))

    x = np.arange(len(pivot))
    width = 0.35

    # Get column names dynamically
    variants = pivot.columns.tolist()
    baseline_var = 'release-cold' if 'release-cold' in variants else variants[0]
    mte_var = 'release-mte-cold' if 'release-mte-cold' in variants else variants[-1]

    bars1 = ax.bar(
        x - width / 2,
        pivot[baseline_var],
        width,
        label='Baseline (Cold)',
        color=baseline_color,
        edgecolor='black',
        hatch=baseline_hatch,
    )
    bars2 = ax.bar(
        x + width / 2,
        pivot[mte_var],
        width,
        label='MTE (Cold)',
        color=sys_color,
        edgecolor='black',
        hatch=sys_hatch,
    )

    ax.set_ylabel('Query Time (s)', fontsize=FONTSIZE)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)
    ax.tick_params(axis='x', labelrotation=45)

    ax.legend(fontsize=FONTSIZE - 1, loc='upper right')

    # Add better/worse indicator
    ax.annotate(
        lower_better_str,
        color='blue',
        xy=(0.02, 0.92),
        xycoords='axes fraction',
        fontsize=FONTSIZE - 1,
    )

    # Format y-axis for large numbers
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))

    plt.tight_layout()
    plt.savefig(
        os.path.join(result_dir, 'dbms_duckdb_tpch_cold.pdf'),
        format='pdf',
        bbox_inches='tight',
    )
    plt.close()
    print("Generated dbms_duckdb_tpch_cold.pdf")


def plot_leveldb_ycsb(df: pd.DataFrame):
    """Plot LevelDB YCSB throughput: Dynamic vs MTE and Static vs CHERI as separate PDFs."""
    data = df[
        (df['database'] == 'leveldb') &
        (df['benchmark'] == 'ycsb') &
        (df['metric_name'] == 'throughput')
    ]

    if data.empty:
        print("No data for leveldb/ycsb/throughput")
        return

    # Pivot to get all variants
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )

    # Sort workloads naturally
    pivot = pivot.reindex(natsorted(pivot.index, alg=ns.NUMAFTER))

    # Check which naming scheme is used
    variant_order = ['release-dynamic', 'release-mte', 'release-static', 'release-cheri']
    variant_order_old = ['dynamic', 'mte', 'static', 'cheri']

    if any(v in pivot.columns for v in variant_order):
        dynamic_var, mte_var, static_var, cheri_var = variant_order
    else:
        dynamic_var, mte_var, static_var, cheri_var = variant_order_old

    x = np.arange(len(pivot))
    width = 0.35

    # Plot 1: Dynamic vs MTE
    if dynamic_var in pivot.columns and mte_var in pivot.columns:
        fig, ax = plt.subplots(figsize=(figwidth_half, fig_height * 1.3))

        ax.bar(
            x - width / 2,
            pivot[dynamic_var],
            width,
            label='Dynamic',
            color=baseline_color,
            edgecolor='black',
            hatch='',
        )
        ax.bar(
            x + width / 2,
            pivot[mte_var],
            width,
            label='MTE',
            color=sys_color,
            edgecolor='black',
            hatch='///',
        )
        ax.set_ylabel('Throughput (ops/sec)', fontsize=FONTSIZE)
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)
        ax.tick_params(axis='x', labelrotation=30)
        ax.legend(fontsize=FONTSIZE - 1, loc='upper right')
        ax.annotate(
            higher_better_str,
            color='blue',
            xy=(0.02, 0.92),
            xycoords='axes fraction',
            fontsize=FONTSIZE - 1,
        )
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))

        plt.tight_layout()
        plt.savefig(
            os.path.join(result_dir, 'dbms_leveldb_ycsb_dynamic_mte.pdf'),
            format='pdf',
            bbox_inches='tight',
        )
        plt.close()
        print("Generated dbms_leveldb_ycsb_dynamic_mte.pdf")

    # Plot 2: Static vs CHERI
    if static_var in pivot.columns and cheri_var in pivot.columns:
        fig, ax = plt.subplots(figsize=(figwidth_half, fig_height * 1.3))

        ax.bar(
            x - width / 2,
            pivot[static_var],
            width,
            label='Static',
            color='#90EE90',
            edgecolor='black',
            hatch='\\\\\\',
        )
        ax.bar(
            x + width / 2,
            pivot[cheri_var],
            width,
            label='CHERI',
            color='#FFB6C1',
            edgecolor='black',
            hatch='|||',
        )
        ax.set_ylabel('Throughput (ops/sec)', fontsize=FONTSIZE)
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)
        ax.tick_params(axis='x', labelrotation=30)
        ax.legend(fontsize=FONTSIZE - 1, loc='upper right')
        ax.annotate(
            higher_better_str,
            color='blue',
            xy=(0.02, 0.92),
            xycoords='axes fraction',
            fontsize=FONTSIZE - 1,
        )
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))

        plt.tight_layout()
        plt.savefig(
            os.path.join(result_dir, 'dbms_leveldb_ycsb_static_cheri.pdf'),
            format='pdf',
            bbox_inches='tight',
        )
        plt.close()
        print("Generated dbms_leveldb_ycsb_static_cheri.pdf")


def plot_redis_ycsb(df: pd.DataFrame):
    """Plot Redis YCSB throughput: Dynamic vs MTE and Static vs CHERI as separate PDFs."""
    data = df[
        (df['database'] == 'redis') &
        (df['benchmark'] == 'ycsb') &
        (df['metric_name'] == 'throughput')
    ]

    if data.empty:
        print("No data for redis/ycsb/throughput")
        return

    # Pivot to get all variants
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )

    # Sort workloads naturally
    pivot = pivot.reindex(natsorted(pivot.index, alg=ns.NUMAFTER))

    # Check which naming scheme is used
    variant_order = ['release-dynamic', 'release-mte', 'release-static', 'release-cheri']
    variant_order_old = ['dynamic', 'mte', 'static', 'cheri']

    if any(v in pivot.columns for v in variant_order):
        dynamic_var, mte_var, static_var, cheri_var = variant_order
    else:
        dynamic_var, mte_var, static_var, cheri_var = variant_order_old

    x = spaced_positions(len(pivot))
    width = 0.5

    # Plot 1: Dynamic vs MTE
    if dynamic_var in pivot.columns and mte_var in pivot.columns:
        fig, ax = plt.subplots(figsize=(figwidth_half, fig_height * 1.3))

        bars_baseline = ax.bar(
            x - width / 2,
            pivot[dynamic_var],
            width,
            label='Dynamic',
            color=BASELINE_COLOR,
            edgecolor='black',
            hatch=BASELINE_HATCH,
        )
        bars_mte = ax.bar(
            x + width / 2,
            pivot[mte_var],
            width,
            label='MTE',
            color=MTE_COLOR,
            edgecolor='black',
            hatch=MTE_HATCH,
        )
        ax.set_ylabel('Throughput (ops/sec)', fontsize=FONTSIZE, labelpad=1)
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)
        ax.tick_params(axis='x', labelrotation=30)
        ax.set_title('YCSB (Non-MTE vs MTE)', fontsize=FONTSIZE, pad=10)
        ax.text(
            0.5,
            1.12,
            higher_better_str,
            color='blue',
            ha='center',
            va='top',
            transform=ax.transAxes,
            fontsize=FONTSIZE - 1,
        )
        add_two_item_legend(fig, 'Dynamic', 'MTE')
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
        for base_val, mte_val, bar in zip(pivot[dynamic_var], pivot[mte_var], bars_mte):
            if base_val > 0 and mte_val > 0:
                pct = (mte_val / base_val - 1.0) * 100.0
                sign = '+' if pct >= 0 else '-'
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"${sign}{abs(pct):.0f}\\%$",
                    ha='center',
                    va='bottom',
                    fontsize=FONTSIZE - 2,
                )
        ymax = max(pivot[dynamic_var].max(), pivot[mte_var].max())
        ax.set_ylim(0, ymax * 1.2)

        plt.tight_layout()
        plt.savefig(
            os.path.join(result_dir, 'dbms_redis_ycsb_dynamic_mte.pdf'),
            format='pdf',
            bbox_inches='tight',
        )
        plt.close()
        print("Generated dbms_redis_ycsb_dynamic_mte.pdf")

    # Plot 2: Static vs CHERI
    if static_var in pivot.columns and cheri_var in pivot.columns:
        fig, ax = plt.subplots(figsize=(figwidth_half, fig_height * 1.3))

        bars_baseline = ax.bar(
            x - width / 2,
            pivot[static_var],
            width,
            label='Static',
            color=BASELINE_COLOR,
            edgecolor='black',
            hatch=BASELINE_HATCH,
        )
        bars_mte = ax.bar(
            x + width / 2,
            pivot[cheri_var],
            width,
            label='CHERI',
            color=MTE_COLOR,
            edgecolor='black',
            hatch=MTE_HATCH,
        )
        ax.set_ylabel('Throughput (ops/sec)', fontsize=FONTSIZE, labelpad=1)
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)
        ax.tick_params(axis='x', labelrotation=30)
        ax.set_title('YCSB (Static vs CHERI)', fontsize=FONTSIZE, pad=10)
        ax.text(
            0.5,
            1.12,
            higher_better_str,
            color='blue',
            ha='center',
            va='top',
            transform=ax.transAxes,
            fontsize=FONTSIZE - 1,
        )
        add_two_item_legend(fig, 'Static', 'CHERI')
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
        for base_val, mte_val, bar in zip(pivot[static_var], pivot[cheri_var], bars_mte):
            if base_val > 0 and mte_val > 0:
                pct = (mte_val / base_val - 1.0) * 100.0
                sign = '+' if pct >= 0 else '-'
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"${sign}{abs(pct):.0f}\\%$",
                    ha='center',
                    va='bottom',
                    fontsize=FONTSIZE - 2,
                )
        ymax = max(pivot[static_var].max(), pivot[cheri_var].max())
        ax.set_ylim(0, ymax * 1.2)

        plt.tight_layout()
        plt.savefig(
            os.path.join(result_dir, 'dbms_redis_ycsb_static_cheri.pdf'),
            format='pdf',
            bbox_inches='tight',
        )
        plt.close()
        print("Generated dbms_redis_ycsb_static_cheri.pdf")


def plot_sqlite_tpcc(df: pd.DataFrame):
    """Plot SQLite TPC-C TPS."""
    data = df[
        (df['database'] == 'sqlite') &
        (df['benchmark'] == 'tpcc') &
        (df['metric_name'] == 'tps')
    ]

    if data.empty:
        print("No data for sqlite/tpcc/tps")
        return

    fig, ax = plt.subplots(figsize=(figwidth_half * 0.6, fig_height * 1.3))

    # Group by variant
    grouped = data.groupby('variant')['metric_value'].agg(['mean', 'std']).reset_index()
    grouped = grouped.sort_values('variant')

    variants = grouped['variant'].tolist()
    x = np.arange(len(variants))

    colors = [baseline_color if 'mte' not in v else sys_color for v in variants]
    hatches = [baseline_hatch if 'mte' not in v else sys_hatch for v in variants]
    labels = ['Baseline' if 'mte' not in v else 'MTE' for v in variants]

    bars = ax.bar(
        x,
        grouped['mean'],
        yerr=grouped['std'],
        color=colors,
        edgecolor='black',
        capsize=3,
    )
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    ax.set_ylabel('TPS', fontsize=FONTSIZE)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=FONTSIZE - 1)
    ax.annotate(
        higher_better_str,
        color='blue',
        xy=(0.02, 0.92),
        xycoords='axes fraction',
        fontsize=FONTSIZE - 1,
    )

    plt.tight_layout()
    plt.savefig(
        os.path.join(result_dir, 'dbms_sqlite_tpcc.pdf'),
        format='pdf',
        bbox_inches='tight',
    )
    plt.close()
    print("Generated dbms_sqlite_tpcc.pdf")


def plot_mysql_sysbench(df: pd.DataFrame):
    """Plot MySQL sysbench TPS and latency."""
    tps_data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'tps')
    ]

    if tps_data.empty:
        print("No data for mysql/sysbench/tps")
        return

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(figwidth_half, fig_height),
        gridspec_kw={"width_ratios": [1, 2]},
    )

    def resolve_variants(available):
        if 'release' in available and 'release-mte' in available:
            return 'release', 'release-mte'
        if 'release-dynamic' in available and 'release-mte' in available:
            return 'release-dynamic', 'release-mte'
        return available[0], available[-1]

    def annotate_pct(ax, bar, baseline, mte):
        if baseline <= 0 or mte <= 0:
            return
        pct = (mte / baseline - 1.0) * 100.0
        sign = '+' if pct >= 0 else '-'
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"${sign}{abs(pct):.0f}\\%$",
            ha='center',
            va='bottom',
            fontsize=FONTSIZE - 1,
        )

    # Throughput subplot
    ax = axes[0]
    grouped = tps_data.groupby('variant')['metric_value'].agg(['mean', 'std']).reset_index()
    grouped = grouped.sort_values('variant')
    variants = grouped['variant'].tolist()
    baseline_var, mte_var = resolve_variants(variants)

    baseline_mean = grouped.loc[grouped['variant'] == baseline_var, 'mean'].values[0]
    baseline_std = grouped.loc[grouped['variant'] == baseline_var, 'std'].values[0]
    mte_mean = grouped.loc[grouped['variant'] == mte_var, 'mean'].values[0]
    mte_std = grouped.loc[grouped['variant'] == mte_var, 'std'].values[0]

    width = 0.5
    x = np.array([0.0])

    bars_baseline = ax.bar(
        x - width / 2,
        [baseline_mean],
        width,
        yerr=[baseline_std],
        color=BASELINE_COLOR,
        edgecolor='black',
        capsize=3,
    )
    bars_mte = ax.bar(
        x + width / 2,
        [mte_mean],
        width,
        yerr=[mte_std],
        color=MTE_COLOR,
        edgecolor='black',
        capsize=3,
        hatch=MTE_HATCH,
    )

    annotate_pct(ax, bars_mte[0], baseline_mean, mte_mean)

    ymax = max(baseline_mean + baseline_std, mte_mean + mte_std)
    ax.set_ylim(0, ymax * 1.15)

    ax.set_ylabel('TPS', fontsize=FONTSIZE, labelpad=1)
    ax.set_xticks(x)
    ax.set_xticklabels(["Throughput"], fontsize=FONTSIZE - 1)
    ax.set_title('Throughput', fontsize=FONTSIZE, pad=10)
    ax.text(
        0.5,
        1.16,
        higher_better_str,
        color='blue',
        ha='center',
        va='top',
        transform=ax.transAxes,
        fontsize=FONTSIZE - 1,
    )

    # Latency subplot (avg + p95)
    ax = axes[1]
    lat_avg_data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'latency_avg')
    ]
    lat_p95_data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'latency_p95')
    ]

    if not lat_avg_data.empty or not lat_p95_data.empty:
        grouped_avg = lat_avg_data.groupby('variant')['metric_value'].agg(['mean', 'std']).reset_index()
        grouped_p95 = lat_p95_data.groupby('variant')['metric_value'].agg(['mean', 'std']).reset_index()

        avg_vars = grouped_avg['variant'].tolist()
        p95_vars = grouped_p95['variant'].tolist()
        variants = sorted(set(avg_vars + p95_vars))
        baseline_var, mte_var = resolve_variants(variants)

        avg_baseline = grouped_avg.loc[grouped_avg['variant'] == baseline_var, 'mean'].values[0]
        avg_baseline_std = grouped_avg.loc[grouped_avg['variant'] == baseline_var, 'std'].values[0]
        avg_mte = grouped_avg.loc[grouped_avg['variant'] == mte_var, 'mean'].values[0]
        avg_mte_std = grouped_avg.loc[grouped_avg['variant'] == mte_var, 'std'].values[0]

        p95_baseline = grouped_p95.loc[grouped_p95['variant'] == baseline_var, 'mean'].values[0]
        p95_baseline_std = grouped_p95.loc[grouped_p95['variant'] == baseline_var, 'std'].values[0]
        p95_mte = grouped_p95.loc[grouped_p95['variant'] == mte_var, 'mean'].values[0]
        p95_mte_std = grouped_p95.loc[grouped_p95['variant'] == mte_var, 'std'].values[0]

        x = np.array([0.0, 1.2])

        bars_baseline = ax.bar(
            x - width / 2,
            [avg_baseline, p95_baseline],
            width,
            yerr=[avg_baseline_std, p95_baseline_std],
            color=BASELINE_COLOR,
            edgecolor='black',
            capsize=3,
        )
        bars_mte = ax.bar(
            x + width / 2,
            [avg_mte, p95_mte],
            width,
            yerr=[avg_mte_std, p95_mte_std],
            color=MTE_COLOR,
            edgecolor='black',
            capsize=3,
            hatch=MTE_HATCH,
        )

        annotate_pct(ax, bars_mte[0], avg_baseline, avg_mte)
        annotate_pct(ax, bars_mte[1], p95_baseline, p95_mte)

        ymax = max(
            avg_baseline + avg_baseline_std,
            avg_mte + avg_mte_std,
            p95_baseline + p95_baseline_std,
            p95_mte + p95_mte_std,
        )
        ax.set_ylim(0, ymax * 1.15)

        ax.set_ylabel('Latency (ms)', fontsize=FONTSIZE, labelpad=1)
        ax.set_xticks(x)
        ax.set_xticklabels(['Avg', 'P95'], fontsize=FONTSIZE - 1)
        ax.set_title('Latency', fontsize=FONTSIZE, pad=10)
        ax.text(
            0.5,
            1.16,
            lower_better_str,
            color='blue',
            ha='center',
            va='top',
            transform=ax.transAxes,
            fontsize=FONTSIZE - 1,
        )


    plt.tight_layout()
    fig.subplots_adjust(wspace=0.5)
    add_two_item_legend(fig, 'Baseline', 'MTE', loc='upper center', bbox_to_anchor=(0.53, 0.98))
    plt.savefig(
        os.path.join(result_dir, 'dbms_mysql_sysbench.pdf'),
        format='pdf',
        bbox_inches='tight',
    )
    plt.close()
    print("Generated dbms_mysql_sysbench.pdf")


def plot_ladybug_lsqb(df: pd.DataFrame):
    """Plot Ladybug LSQB query times: Dynamic vs MTE and Static vs CHERI as separate PDFs."""
    data = df[
        (df['database'] == 'ladybug') &
        (df['benchmark'] == 'lsqb') &
        (df['metric_name'] == 'query_time')
    ]

    if data.empty:
        print("No data for ladybug/lsqb/query_time")
        return

    # Pivot to get all variants
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )

    # Sort workloads naturally
    pivot = pivot.reindex(natsorted(pivot.index, alg=ns.NUMAFTER))

    # Check which naming scheme is used
    variant_order = ['release-dynamic', 'release-mte', 'release-static', 'release-cheri']
    variant_order_old = ['dynamic', 'mte', 'static', 'cheri']

    if any(v in pivot.columns for v in variant_order):
        dynamic_var, mte_var, static_var, cheri_var = variant_order
    else:
        dynamic_var, mte_var, static_var, cheri_var = variant_order_old

    x = np.arange(len(pivot))
    width = 0.35

    # Plot 1: Dynamic vs MTE
    if dynamic_var in pivot.columns and mte_var in pivot.columns:
        fig, ax = plt.subplots(figsize=(figwidth_half, fig_height * 1.3))

        ax.bar(
            x - width / 2,
            pivot[dynamic_var],
            width,
            label='Dynamic',
            color=baseline_color,
            edgecolor='black',
            hatch='',
        )
        ax.bar(
            x + width / 2,
            pivot[mte_var],
            width,
            label='MTE',
            color=sys_color,
            edgecolor='black',
            hatch='///',
        )
        ax.set_ylabel('Query Time (s)', fontsize=FONTSIZE)
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)
        ax.tick_params(axis='x', labelrotation=30)
        ax.legend(fontsize=FONTSIZE - 1, loc='upper right')
        ax.annotate(
            lower_better_str,
            color='blue',
            xy=(0.02, 0.92),
            xycoords='axes fraction',
            fontsize=FONTSIZE - 1,
        )
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))

        plt.tight_layout()
        plt.savefig(
            os.path.join(result_dir, 'dbms_ladybug_lsqb_dynamic_mte.pdf'),
            format='pdf',
            bbox_inches='tight',
        )
        plt.close()
        print("Generated dbms_ladybug_lsqb_dynamic_mte.pdf")

    # Plot 2: Static vs CHERI
    if static_var in pivot.columns and cheri_var in pivot.columns:
        fig, ax = plt.subplots(figsize=(figwidth_half, fig_height * 1.3))

        ax.bar(
            x - width / 2,
            pivot[static_var],
            width,
            label='Static',
            color='#90EE90',
            edgecolor='black',
            hatch='\\\\\\',
        )
        ax.bar(
            x + width / 2,
            pivot[cheri_var],
            width,
            label='CHERI',
            color='#FFB6C1',
            edgecolor='black',
            hatch='|||',
        )
        ax.set_ylabel('Query Time (s)', fontsize=FONTSIZE)
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)
        ax.tick_params(axis='x', labelrotation=30)
        ax.legend(fontsize=FONTSIZE - 1, loc='upper right')
        ax.annotate(
            lower_better_str,
            color='blue',
            xy=(0.02, 0.92),
            xycoords='axes fraction',
            fontsize=FONTSIZE - 1,
        )
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))

        plt.tight_layout()
        plt.savefig(
            os.path.join(result_dir, 'dbms_ladybug_lsqb_static_cheri.pdf'),
            format='pdf',
            bbox_inches='tight',
        )
        plt.close()
        print("Generated dbms_ladybug_lsqb_static_cheri.pdf")


def plot_overhead_summary(df: pd.DataFrame):
    """Summary plot of MTE overhead across all databases (warm cache only)."""
    # Filter to only warm cache variants (exclude -cold variants)
    df_warm = df[~df['variant'].str.contains('-cold', na=False)]

    # Compute overhead for each database/benchmark
    overheads = []

    for (database, benchmark, workload), group in df_warm.groupby(['database', 'benchmark', 'workload']):
        # Try different variant naming schemes
        if 'release' in group['variant'].values:
            baseline = group[group['variant'] == 'release']['metric_value'].mean()
        elif 'release-dynamic' in group['variant'].values:
            baseline = group[group['variant'] == 'release-dynamic']['metric_value'].mean()
        else:
            baseline = 0

        mte = group[group['variant'] == 'release-mte']['metric_value'].mean()

        if baseline > 0 and mte > 0 and not (pd.isna(baseline) or pd.isna(mte)):
            # Get the primary metric for this benchmark
            metric = group['metric_name'].iloc[0]

            # Determine if higher is better for this metric
            higher_is_better = metric in ['throughput', 'tps', 'qps']

            if higher_is_better:
                # For throughput metrics, overhead = baseline / mte
                overhead = baseline / mte
            else:
                # For latency/time metrics, overhead = mte / baseline
                overhead = mte / baseline

            overheads.append({
                'database': database,
                'benchmark': benchmark,
                'workload': workload,
                'overhead': overhead,
            })

    if not overheads:
        print("No overhead data to plot")
        return

    overhead_df = pd.DataFrame(overheads)

    # Compute mean overhead per database
    db_overhead = overhead_df.groupby('database')['overhead'].agg(['mean', 'std']).reset_index()
    db_overhead = db_overhead.sort_values('mean')

    fig, ax = plt.subplots(figsize=(figwidth_half, fig_height * 1.3))

    x = np.arange(len(db_overhead))
    bars = ax.bar(
        x,
        db_overhead['mean'],
        yerr=db_overhead['std'],
        color=sys_color,
        edgecolor='black',
        hatch=sys_hatch,
        capsize=3,
    )

    # Add 1.0 reference line
    ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1, label='No overhead')

    ax.set_ylabel('Normalized Overhead', fontsize=FONTSIZE)
    ax.set_xticks(x)
    ax.set_xticklabels(db_overhead['database'], fontsize=FONTSIZE - 1)
    ax.tick_params(axis='x', labelrotation=30)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f'{height:.2f}x',
            ha='center',
            va='bottom',
            fontsize=FONTSIZE - 2,
        )

    ax.set_ylim(0, max(db_overhead['mean'].max() * 1.3, 1.5))
    ax.annotate(
        lower_better_str,
        color='blue',
        xy=(0.02, 0.92),
        xycoords='axes fraction',
        fontsize=FONTSIZE - 1,
    )

    plt.tight_layout()
    plt.savefig(
        os.path.join(result_dir, 'dbms_overhead_summary.pdf'),
        format='pdf',
        bbox_inches='tight',
    )
    plt.close()
    print("Generated dbms_overhead_summary.pdf")


def main():
    try:
        df = load_dbms_data()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run 'just dbms benchmark' first to generate results.")
        return

    print(f"Loaded {len(df)} records from results")
    print(f"Databases: {df['database'].unique().tolist()}")
    print(f"Benchmarks: {df['benchmark'].unique().tolist()}")

    # Generate individual plots
    plot_duckdb_tpch(df)
    plot_duckdb_tpch_cold(df)
    plot_leveldb_ycsb(df)
    plot_redis_ycsb(df)
    plot_sqlite_tpcc(df)
    plot_mysql_sysbench(df)
    plot_ladybug_lsqb(df)

    # Generate summary plot
    plot_overhead_summary(df)

    print("\nAll plots generated successfully.")


if __name__ == '__main__':
    main()
