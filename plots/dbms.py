#!/usr/bin/env python3
"""DBMS benchmark plotting script."""
from common import *


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

    ax.set_ylabel(ylabel, fontsize=FONTSIZE)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=FONTSIZE - 1)

    # Rotate labels if many workloads
    if len(pivot) > 10:
        ax.tick_params(axis='x', labelrotation=45)
    elif len(pivot) > 6:
        ax.tick_params(axis='x', labelrotation=30)

    ax.legend(fontsize=FONTSIZE - 1, loc='upper right')

    # Add better/worse indicator
    indicator = higher_better_str if higher_is_better else lower_better_str
    ax.annotate(
        indicator,
        color='blue',
        xy=(0.02, 0.92),
        xycoords='axes fraction',
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
            os.path.join(result_dir, 'dbms_redis_ycsb_dynamic_mte.pdf'),
            format='pdf',
            bbox_inches='tight',
        )
        plt.close()
        print("Generated dbms_redis_ycsb_dynamic_mte.pdf")

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
    # Plot TPS
    data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'tps')
    ]

    if data.empty:
        print("No data for mysql/sysbench/tps")
        return

    fig, axes = plt.subplots(1, 3, figsize=(figwidth_half * 2.2, fig_height * 1.3))

    # TPS subplot
    ax = axes[0]
    grouped = data.groupby('variant')['metric_value'].agg(['mean', 'std']).reset_index()
    grouped = grouped.sort_values('variant')

    variants = grouped['variant'].tolist()
    x = np.arange(len(variants))

    colors = [baseline_color if 'mte' not in v else sys_color for v in variants]
    hatches = [baseline_hatch if 'mte' not in v else sys_hatch for v in variants]
    labels = ['Baseline' if 'mte' not in v else 'MTE' for v in variants]

    bars = ax.bar(x, grouped['mean'], yerr=grouped['std'], color=colors, edgecolor='black', capsize=3)
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    ax.set_ylabel('TPS', fontsize=FONTSIZE)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=FONTSIZE - 1)
    ax.set_title('Throughput', fontsize=FONTSIZE)
    ax.annotate(
        higher_better_str,
        color='blue',
        xy=(0.02, 0.92),
        xycoords='axes fraction',
        fontsize=FONTSIZE - 1,
    )

    # Average latency subplot
    ax = axes[1]
    lat_avg_data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'latency_avg')
    ]

    if not lat_avg_data.empty:
        grouped = lat_avg_data.groupby('variant')['metric_value'].agg(['mean', 'std']).reset_index()
        grouped = grouped.sort_values('variant')

        variants = grouped['variant'].tolist()
        x = np.arange(len(variants))

        colors = [baseline_color if 'mte' not in v else sys_color for v in variants]
        hatches = [baseline_hatch if 'mte' not in v else sys_hatch for v in variants]
        labels = ['Baseline' if 'mte' not in v else 'MTE' for v in variants]

        bars = ax.bar(x, grouped['mean'], yerr=grouped['std'], color=colors, edgecolor='black', capsize=3)
        for bar, hatch in zip(bars, hatches):
            bar.set_hatch(hatch)

        ax.set_ylabel('Latency (ms)', fontsize=FONTSIZE)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=FONTSIZE - 1)
        ax.set_title('Avg Latency', fontsize=FONTSIZE)
        ax.annotate(
            lower_better_str,
            color='blue',
            xy=(0.02, 0.92),
            xycoords='axes fraction',
            fontsize=FONTSIZE - 1,
        )

    # P95 latency subplot
    ax = axes[2]
    lat_p95_data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'latency_p95')
    ]

    if not lat_p95_data.empty:
        grouped = lat_p95_data.groupby('variant')['metric_value'].agg(['mean', 'std']).reset_index()
        grouped = grouped.sort_values('variant')

        variants = grouped['variant'].tolist()
        x = np.arange(len(variants))

        colors = [baseline_color if 'mte' not in v else sys_color for v in variants]
        hatches = [baseline_hatch if 'mte' not in v else sys_hatch for v in variants]
        labels = ['Baseline' if 'mte' not in v else 'MTE' for v in variants]

        bars = ax.bar(x, grouped['mean'], yerr=grouped['std'], color=colors, edgecolor='black', capsize=3)
        for bar, hatch in zip(bars, hatches):
            bar.set_hatch(hatch)

        ax.set_ylabel('Latency (ms)', fontsize=FONTSIZE)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=FONTSIZE - 1)
        ax.set_title('P95 Latency', fontsize=FONTSIZE)
        ax.annotate(
            lower_better_str,
            color='blue',
            xy=(0.02, 0.92),
            xycoords='axes fraction',
            fontsize=FONTSIZE - 1,
        )

    plt.tight_layout()
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
