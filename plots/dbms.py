#!/usr/bin/env python3
"""DBMS benchmark plotting script."""
from common import *

X_TICKS_TILT_THRESHOLD = 8

def load_dbms_data() -> pd.DataFrame:
    """Load DBMS benchmark results from CSV."""
    csv_path = os.path.join(result_dir, 'dbms_results.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Results file not found: {csv_path}")
    return pd.read_csv(csv_path)

def prep_generic_data(data):
    """Refactored helper: Filter generic benchmark data variants and pivot."""
    # Determine variants
    available_variants = data['variant'].unique().tolist()
    
    # MTE Baseline selection
    mte_baseline = None
    if 'release-dynamic' in available_variants:
        mte_baseline = 'release-dynamic'
    elif 'release' in available_variants:
        mte_baseline = 'release'
        
    mte_variant = 'release-mte'
    cheri_baseline = 'release-static'
    cheri_variant = 'release-cheri'
    
    # Collect variants to plot
    variants_to_plot = []
    baseline_map = {} # Maps variant -> baseline_variant

    if mte_baseline and mte_baseline in available_variants:
        variants_to_plot.append(mte_baseline)
        if mte_variant in available_variants:
            variants_to_plot.append(mte_variant)
            baseline_map[mte_variant] = mte_baseline
            
    if cheri_baseline in available_variants:
        variants_to_plot.append(cheri_baseline)
        if cheri_variant in available_variants:
            variants_to_plot.append(cheri_variant)
            baseline_map[cheri_variant] = cheri_baseline
        
    if not variants_to_plot:
        if mte_variant in available_variants and not mte_baseline:
             variants_to_plot.append(mte_variant)
        
    # Filter data for selected variants
    data = data[data['variant'].isin(variants_to_plot)]
    
    if data.empty:
        return None, None, [], {}

    # Pivot
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )
    pivot_std = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='std'
    ).fillna(0)
    
    # Sort Workloads
    sorted_idx = natsorted(pivot.index, alg=ns.NUMAFTER)
    pivot = pivot.reindex(sorted_idx)
    pivot_std = pivot_std.reindex(sorted_idx)
    
    return pivot, pivot_std, variants_to_plot, baseline_map


def plot_bars_on_ax(ax, pivot, pivot_std, variants_to_plot, baseline_map, y_label, show_x_labels=True, higher_better=True, show_indicator=True):
    """Refactored helper: Plot bars on given axis."""
    x = np.arange(len(pivot))
    total_width = 0.8
    width = total_width / len(variants_to_plot)
    
    order_priority = ['release-dynamic', 'release', 'release-mte', 'release-asan', 'release-static', 'release-cheri']
    variants_to_plot = sorted(variants_to_plot, key=lambda v: order_priority.index(v) if v in order_priority else 999)
    local_style_map = style_map.copy()
    local_style_map['release'] = {
        'color': BASELINE_MTE_COLOR,
        'hatch': BASELINE_MTE_HATCH,
        'label': 'Baseline (MTE)'
    }
    
    for i, var in enumerate(variants_to_plot):
        offset = (i - len(variants_to_plot)/2 + 0.5) * width
        
        style = local_style_map.get(var, {'color': 'gray', 'hatch': '', 'label': var})
        
        bars = ax.bar(
            x + offset,
            pivot[var],
            width,
            label=style['label'],
            color=style['color'],
            edgecolor='black',
            hatch=style['hatch'],
            yerr=pivot_std[var] if var in pivot_std else None,
            capsize=3
        )
        
        # Annotate relative performance if this variant has a baseline
        if var in baseline_map:
            baseline_var = baseline_map[var]
            if baseline_var in pivot.columns:
                for idx, (val, base_val, bar) in enumerate(zip(pivot[var], pivot[baseline_var], bars)):
                    if base_val > 0 and val > 0:
                        pct_diff = (val - base_val) / base_val * 100
                        
                        sign = '+' if pct_diff >= 0 else '-'
                        annotation_text = f"${sign}{abs(pct_diff):.0f}\\%$"
                        
                        # Calculate reference height (tallest of the bar pair)
                        ref_height = max(val, base_val)
                        
                        # Consider error bars if present
                        if var in pivot_std:
                            s_v = pivot_std[var].iloc[idx]
                            if pd.notna(s_v) and s_v > 0:
                                ref_height = max(ref_height, val + s_v)
                        
                        if baseline_var in pivot_std:
                            s_b = pivot_std[baseline_var].iloc[idx]
                            if pd.notna(s_b) and s_b > 0:
                                ref_height = max(ref_height, base_val + s_b)
                        
                        padding = 0.05 * ref_height

                        # Determine X position (midpoint between variant and baseline)
                        text_x = bar.get_x() + bar.get_width() / 2
                        if baseline_var in variants_to_plot:
                            base_idx = variants_to_plot.index(baseline_var)
                            base_offset = (base_idx - len(variants_to_plot)/2 + 0.5) * width
                            # 'offset' is the current variant's offset from the outer loop
                            mid_offset = (offset + base_offset) / 2
                            text_x = x[idx] + mid_offset

                        # Place annotation
                        ax.text(
                            text_x,
                            ref_height + padding, 
                            annotation_text,
                            ha='center',
                            va='bottom',
                            fontsize=FONTSIZE_ANNOTATION,
                            rotation=0
                        )

    ax.set_ylabel(y_label, fontsize=FONTSIZE_AXIS_LABEL)
    
    if show_x_labels:
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, fontsize=FONTSIZE_TICK_LABEL)
        
        # Tilt x labels if too many
        if len(pivot) > X_TICKS_TILT_THRESHOLD:
            ax.tick_params(axis='x', labelrotation=45)
        else:
            ax.tick_params(axis='x', labelrotation=0)
    else:
        # Hide x ticks
        ax.set_xticks([])

    # Indicator
    if show_indicator:
        indicator = higher_better_str if higher_better else lower_better_str
        
        ax.annotate(
            indicator,
            color='blue',
            xy=(0.02, 0.92),
            xycoords='axes fraction',
            fontsize=FONTSIZE_TITLE,
        )
    
    # Format Y axis
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
    
    ymax = pivot.max().max()
    ax.set_ylim(0, ymax * 1.5)

def plot_generic_benchmark(
    data: pd.DataFrame,
    output_filename: str,
    y_label: str = "Metric",
    higher_better=True,
    fig_width=figwidth_full,
    show_x_labels=True,
    show_legend=True
):
    """Generic function to plot baseline vs MTE and baseline vs CHERI with relative performance."""
    
    if data.empty:
        print(f"No data for {output_filename}")
        return


    pivot, pivot_std, variants_to_plot, baseline_map = prep_generic_data(data)
    
    if pivot is None:
        print(f"No valid variant pairs found for {output_filename}")
        return

    # Plot setup
    figsize = (fig_width, fig_height)
    fig, ax = plt.subplots(figsize=figsize)
    
    plot_bars_on_ax(ax, pivot, pivot_std, variants_to_plot, baseline_map, y_label, show_x_labels, higher_better)
    
    if show_legend:
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        
        if fig_width <= figwidth_half:
            legend_ncol = len(variants_to_plot)
                
            ax.legend(
                by_label.values(), 
                by_label.keys(), 
                fontsize=FONTSIZE_LEGEND, 
                loc='lower center', 
                bbox_to_anchor=(0.5, 1.02), 
                ncol=legend_ncol,
                borderaxespad=0.,
                columnspacing=0.5,
                handletextpad=0.5,
                labelspacing=0.5,
            )
        else:
            legend_ncol = len(variants_to_plot)
            ax.legend(
                by_label.values(), 
                by_label.keys(), 
                fontsize=FONTSIZE_LEGEND, 
                loc='upper right', 
                ncol=legend_ncol
            )
    
    plt.tight_layout()
    output_path = os.path.join(result_dir, output_filename)
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    plt.close()
    print(f"Generated {output_filename}")

def plot_combined_mysql_sqlite(mysql_data, sqlite_data, output_filename='dbms_mysql_sqlite.pdf'):
    """Combine MySQL and SQLite into single plot."""
    
    p_mysql, ps_mysql, v_mysql, b_mysql = prep_generic_data(mysql_data)
    p_sqlite, ps_sqlite, v_sqlite, b_sqlite = prep_generic_data(sqlite_data)
    
    if p_mysql is None or p_sqlite is None:
        print("Missing data for combined plot")
        return
    
    figsize = (figwidth_half, fig_height)
    
    fig, axes = plt.subplots(1, 2, figsize=figsize, sharey=False, gridspec_kw={'width_ratios': [1, 2]})
    ax_mysql = axes[0]
    ax_sqlite = axes[1]
    plot_bars_on_ax(ax_mysql, p_mysql, ps_mysql, v_mysql, b_mysql, 'Throughput (TPS)', show_x_labels=False, higher_better=True, show_indicator=False)
    plot_bars_on_ax(ax_sqlite, p_sqlite, ps_sqlite, v_sqlite, b_sqlite, '', show_x_labels=False, higher_better=True, show_indicator=False)
    
    handles, labels = ax_sqlite.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    
    fig.legend(
        by_label.values(),
        by_label.keys(),
        loc='upper center',
        bbox_to_anchor=(0.5, 1.1),
        ncol=4,
        fontsize=FONTSIZE_LEGEND
    )

    fig.text(0.5, 1.12, higher_better_str, ha='center', va='center', color='blue', fontsize=FONTSIZE_TITLE)
    
    plt.tight_layout()
    output_path = os.path.join(result_dir, output_filename)
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    plt.close()
    print(f"Generated {output_filename}")

def calculate_overhead_distribution(df, baseline_var, variant_var, label=""):
    """Calculate overhead distribution (normalized runtime) for matched workloads."""
    
    pivot = df.pivot_table(
        index='workload', 
        columns='variant', 
        values='metric_value', 
        aggfunc='mean'
    )
    
    if baseline_var not in pivot.columns or variant_var not in pivot.columns:
        return []
        
    baseline = pivot[baseline_var]
    variant = pivot[variant_var]
    
    overheads = []
    valid_indices = baseline.notna() & variant.notna()
    baseline = baseline[valid_indices]
    variant = variant[valid_indices]
    
    for workload in baseline.index:
        b = baseline[workload]
        v = variant[workload]
        
        if b <= 0 or v <= 0: continue
        
        # Overhead = Variant / Baseline (Time-based: Higher is Worse)
        overhead = v / b
        overheads.append((overhead, workload))
        
    return overheads

def plot_combined_duckdb_ladybug(duckdb_warm, duckdb_cold, ladybug_data):
    """Combined box plot for DuckDB and Ladybug Overheads."""
    
    duck_data_list = []
    duck_stats_list = []
    duck_labels = []
    duck_colors = []
    duck_hatches = []

    cold_overheads = calculate_overhead_distribution(duckdb_cold, 'release-cold', 'release-mte-cold', label="DuckDB Cold")
    if cold_overheads:
        duck_data_list.append([x[0] for x in cold_overheads])
        duck_stats_list.append(cold_overheads)
        duck_labels.append("MTE Cold")
        duck_colors.append(MTE_COLOR)
        duck_hatches.append(MTE_HATCH)

    warm_overheads = calculate_overhead_distribution(duckdb_warm, 'release', 'release-mte', label="DuckDB Warm")
    if warm_overheads:
        duck_data_list.append([x[0] for x in warm_overheads])
        duck_stats_list.append(warm_overheads)
        duck_labels.append("MTE Warm")
        duck_colors.append(MTE_COLOR)
        duck_hatches.append(MTE_HATCH)

    lady_data_list = []
    lady_stats_list = []
    lady_labels = []
    lady_colors = []
    lady_hatches = []
    
    mte_overheads = calculate_overhead_distribution(ladybug_data, 'release-dynamic', 'release-mte', label="Ladybug MTE")
    if mte_overheads:
        lady_data_list.append([x[0] for x in mte_overheads])
        lady_stats_list.append(mte_overheads)
        lady_labels.append("MTE")
        lady_colors.append(MTE_COLOR)
        lady_hatches.append(MTE_HATCH)
        
    cheri_overheads = calculate_overhead_distribution(ladybug_data, 'release-static', 'release-cheri', label="Ladybug CHERI")
    if cheri_overheads:
        lady_data_list.append([x[0] for x in cheri_overheads])
        lady_stats_list.append(cheri_overheads)
        lady_labels.append("CHERI")
        lady_colors.append(CHERI_COLOR)
        lady_hatches.append(CHERI_HATCH)

    if not duck_data_list and not lady_data_list:
        print("No match pairs for combined box plot")
        return

    # --- Print Stats ---
    def print_stats(data_list, labels, title):
        print(f"\n=== {title} Statistics ===")
        for data, label in zip(data_list, labels):
            if not data: continue
            
            # data is list of (val, name)
            vals = np.array([x[0] for x in data])
            sorted_data = sorted(data, key=lambda x: x[0])
            
            print(f"-- {label} --")
            print(f"  Mean (Arith): {np.mean(vals):.4f}")
            print(f"  Min:          {np.min(vals):.4f}")
            print(f"  Max:          {np.max(vals):.4f}")
            
            # Outliers
            print(f"  Top 3 Lowest (Best):")
            for ov, name in sorted_data[:3]:
                print(f"    {name}: {ov:.4f}")
                
            print(f"  Top 3 Highest (Worst):")
            for ov, name in sorted_data[-3:][::-1]:
                print(f"    {name}: {ov:.4f}")

    print_stats(duck_stats_list, duck_labels, "DuckDB")
    print_stats(lady_stats_list, lady_labels, "Ladybug")

    # --- Plotting ---
    figsize = (figwidth_half, fig_height)
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    ax_duck = axes[0]
    ax_lady = axes[1]
    
def plot_box(ax, data_list, labels, colors, hatches):
    if not data_list: return
    
    # Plot boxplot
    bplot = ax.boxplot(
        data_list,
        patch_artist=True,
        showfliers=True,
        flierprops={'marker': 'd', 'markersize': 2, 'alpha': 0.5},
        widths=0.6,
        medianprops={'color': 'black'}
    )
    
    # Color & Hatch
    for patch, color, hatch in zip(bplot['boxes'], colors, hatches):
        patch.set_facecolor(color)
        patch.set_hatch(hatch)
        patch.set_edgecolor('black')
        
    for whisk in bplot['whiskers']: whisk.set_color('black')
    for cap in bplot['caps']: cap.set_color('black')
    
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, fontsize=FONTSIZE_TICK_LABEL, rotation=0, ha='center')
    
    # Reference line
    ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1, alpha=0.7)
    
    # Formatting
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.1f'))
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
    
    ax.set_ylim(0.7, 1.8)

def plot_all_systems(df: pd.DataFrame):
    
    # Redis
    redis_data = df[
        (df['database'] == 'redis') &
        (df['benchmark'] == 'ycsb') &
        (df['metric_name'] == 'throughput')
    ].copy()
    if not redis_data.empty:
        redis_data['workload'] = redis_data['workload'].str.upper()
    p_redis, ps_redis, v_redis, b_redis = prep_generic_data(redis_data)
    
    # LevelDB
    leveldb_data = df[
        (df['database'] == 'leveldb') &
        (df['benchmark'] == 'ycsb') &
        (df['metric_name'] == 'throughput')
    ].copy()
    if not leveldb_data.empty:
        leveldb_data['workload'] = leveldb_data['workload'].apply(lambda x: x.split('_')[0].upper())
    p_level, ps_level, v_level, b_level = prep_generic_data(leveldb_data)
    
    # MySQL
    mysql_data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'tps')
    ].copy()
    p_mysql, ps_mysql, v_mysql, b_mysql = prep_generic_data(mysql_data)
    
    # SQLite
    sqlite_data = df[
        (df['database'] == 'sqlite') &
        (df['benchmark'] == 'tpcc') &
        (df['metric_name'] == 'tps')
    ].copy()
    p_sqlite, ps_sqlite, v_sqlite, b_sqlite = prep_generic_data(sqlite_data)
    
    # DuckDB Prep
    duckdb_warm = df[
        (df['database'] == 'duckdb') &
        (df['benchmark'] == 'tpch') &
        (df['metric_name'] == 'query_time') &
        (df['variant'].isin(['release', 'release-mte']))
    ].copy()
    duckdb_cold = df[
        (df['database'] == 'duckdb') &
        (df['benchmark'] == 'tpch') &
        (df['metric_name'] == 'query_time') &
        (df['variant'].isin(['release-cold', 'release-mte-cold']))
    ].copy()
    
    duck_data_list = []
    duck_labels = []
    duck_colors = []
    duck_hatches = []
    
    cold_overheads = calculate_overhead_distribution(duckdb_cold, 'release-cold', 'release-mte-cold', label="DuckDB Cold")
    if cold_overheads:
        duck_data_list.append([x[0] for x in cold_overheads])
        duck_labels.append("MTE Cold")
        duck_colors.append(MTE_COLOR)
        duck_hatches.append(MTE_HATCH)

    warm_overheads = calculate_overhead_distribution(duckdb_warm, 'release', 'release-mte', label="DuckDB Warm")
    if warm_overheads:
        duck_data_list.append([x[0] for x in warm_overheads])
        duck_labels.append("MTE Warm")
        duck_colors.append(MTE_COLOR)
        duck_hatches.append(MTE_HATCH)

    # Ladybug Prep
    ladybug_data = df[
        (df['database'] == 'ladybug') &
        (df['benchmark'] == 'ldbc') &
        (df['metric_name'] == 'query_time')
    ].copy()
    
    lady_data_list = []
    lady_labels = []
    lady_colors = []
    lady_hatches = []
    
    mte_overheads = calculate_overhead_distribution(ladybug_data, 'release-dynamic', 'release-mte', label="Ladybug MTE")
    if mte_overheads:
        lady_data_list.append([x[0] for x in mte_overheads])
        lady_labels.append("MTE")
        lady_colors.append(MTE_COLOR)
        lady_hatches.append(MTE_HATCH)
        
    cheri_overheads = calculate_overhead_distribution(ladybug_data, 'release-static', 'release-cheri', label="Ladybug CHERI")
    if cheri_overheads:
        lady_data_list.append([x[0] for x in cheri_overheads])
        lady_labels.append("CHERI")
        lady_colors.append(CHERI_COLOR)
        lady_hatches.append(CHERI_HATCH)

    # --- Plotting ---
    fig = plt.figure(figsize=(figwidth_full, 2 * fig_height))
    gs_main = fig.add_gridspec(2, 1, hspace=0.6)
    
    # Row 1: Redis, LevelDB
    gs_top = gs_main[0].subgridspec(1, 2, wspace=0.2)
    ax_redis = fig.add_subplot(gs_top[0])
    ax_level = fig.add_subplot(gs_top[1])
    
    # Row 2: (MySQL, SQLite) ... (Duck, Lady)
    gs_bot = gs_main[1].subgridspec(1, 2, wspace=0.2)
    
    # Group 1: MySQL, SQLite
    gs_bot_left = gs_bot[0].subgridspec(1, 2, wspace=0.35, width_ratios=[1, 2])
    ax_mysql = fig.add_subplot(gs_bot_left[0])
    ax_sqlite = fig.add_subplot(gs_bot_left[1])
    
    # Group 2: Duck, Lady
    gs_bot_right = gs_bot[1].subgridspec(1, 2, wspace=0.35)
    ax_duck = fig.add_subplot(gs_bot_right[0])
    ax_lady = fig.add_subplot(gs_bot_right[1])
    
    # Plot content
    if p_redis is not None:
        plot_bars_on_ax(ax_redis, p_redis, ps_redis, v_redis, b_redis, 'Throughput (ops/sec)')
    if p_level is not None:
        plot_bars_on_ax(ax_level, p_level, ps_level, v_level, b_level, '') # No Y label
    if p_mysql is not None:
        plot_bars_on_ax(ax_mysql, p_mysql, ps_mysql, v_mysql, b_mysql, 'Throughput (TPS)', show_x_labels=False)
    if p_sqlite is not None:
        plot_bars_on_ax(ax_sqlite, p_sqlite, ps_sqlite, v_sqlite, b_sqlite, '', show_x_labels=False)
    
    plot_box(ax_duck, duck_data_list, duck_labels, duck_colors, duck_hatches)
    plot_box(ax_lady, lady_data_list, lady_labels, lady_colors, lady_hatches)
    ax_duck.set_ylabel('Normalized Runtime', fontsize=FONTSIZE_AXIS_LABEL)

    # Add "Lower is better" indicator for DuckDB and Ladybug
    for ax in [ax_duck, ax_lady]:
        ax.annotate(
            lower_better_str,
            color='blue',
            xy=(0.02, 0.92),
            xycoords='axes fraction',
            fontsize=FONTSIZE_TITLE,
        )

    # Captions
    captions = [
        (ax_redis, "(a) Redis."),
        (ax_level, "(b) LevelDB."),
        (ax_mysql, "(c) MySQL."),
        (ax_sqlite, "(d) SQLite."),
        (ax_duck, "(e) DuckDB."),
        (ax_lady, "(f) LadyBugDB."),
    ]
    
    for ax, txt in captions:
        ax.text(0.5, -0.35, txt, transform=ax.transAxes, ha='center', va='top', fontsize=FONTSIZE_TITLE+2, fontweight='bold')
    
    # We can fake the legend handles to ensure order and completeness
    dummy_handles = []
    dummy_labels = []
    
    legend_items = [
        ('release-dynamic', 'Baseline (MTE)'),
        ('release-mte', 'MTE'),
        ('release-static', 'Baseline (CHERI)'),
        ('release-cheri', 'CHERI')
    ]
    
    for var, label in legend_items:
        style = style_map.get(var)
        if not style and var == 'release-dynamic': style = style_map['release-dynamic'] # or check alias
        
        # Use patches.Rectangle for legend handle
        import matplotlib.patches as patches
        patch = patches.Patch(
            facecolor=style['color'] if style else 'gray', 
            hatch=style['hatch'] if style else '', 
            edgecolor='black', 
            label=label
        )
        dummy_handles.append(patch)
        dummy_labels.append(label)

    fig.legend(
        dummy_handles, dummy_labels,
        loc='upper center', 
        bbox_to_anchor=(0.5, 1.0),
        ncol=4, 
        fontsize=FONTSIZE_LEGEND,
        frameon=True
    )
    
    plt.tight_layout()#rect=[0, 0, 1, 0.93])
    output_path = os.path.join(result_dir, "dbms_all_systems.pdf")
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    plt.close()
    print("Generated dbms_all_systems.pdf")

def plot_combined_duckdb_ladybug(duckdb_warm, duckdb_cold, ladybug_data):
    """Combined box plot for DuckDB and Ladybug Overheads."""
    
    duck_data_list = []
    duck_stats_list = []
    duck_labels = []
    duck_colors = []
    duck_hatches = []

    cold_overheads = calculate_overhead_distribution(duckdb_cold, 'release-cold', 'release-mte-cold', label="DuckDB Cold")
    if cold_overheads:
        duck_data_list.append([x[0] for x in cold_overheads])
        duck_stats_list.append(cold_overheads)
        duck_labels.append("MTE Cold")
        duck_colors.append(MTE_COLOR)
        duck_hatches.append(MTE_HATCH)

    warm_overheads = calculate_overhead_distribution(duckdb_warm, 'release', 'release-mte', label="DuckDB Warm")
    if warm_overheads:
        duck_data_list.append([x[0] for x in warm_overheads])
        duck_stats_list.append(warm_overheads)
        duck_labels.append("MTE Warm")
        duck_colors.append(MTE_COLOR)
        duck_hatches.append(MTE_HATCH)

    lady_data_list = []
    lady_stats_list = []
    lady_labels = []
    lady_colors = []
    lady_hatches = []
    
    mte_overheads = calculate_overhead_distribution(ladybug_data, 'release-dynamic', 'release-mte', label="Ladybug MTE")
    if mte_overheads:
        lady_data_list.append([x[0] for x in mte_overheads])
        lady_stats_list.append(mte_overheads)
        lady_labels.append("MTE")
        lady_colors.append(MTE_COLOR)
        lady_hatches.append(MTE_HATCH)
        
    cheri_overheads = calculate_overhead_distribution(ladybug_data, 'release-static', 'release-cheri', label="Ladybug CHERI")
    if cheri_overheads:
        lady_data_list.append([x[0] for x in cheri_overheads])
        lady_stats_list.append(cheri_overheads)
        lady_labels.append("CHERI")
        lady_colors.append(CHERI_COLOR)
        lady_hatches.append(CHERI_HATCH)

    if not duck_data_list and not lady_data_list:
        print("No match pairs for combined box plot")
        return

    # --- Print Stats ---
    def print_stats(data_list, labels, title):
        print(f"\n=== {title} Statistics ===")
        for data, label in zip(data_list, labels):
            if not data: continue
            
            # data is list of (val, name)
            vals = np.array([x[0] for x in data])
            sorted_data = sorted(data, key=lambda x: x[0])
            
            print(f"-- {label} --")
            print(f"  Mean (Arith): {np.mean(vals):.4f}")
            print(f"  Min:          {np.min(vals):.4f}")
            print(f"  Max:          {np.max(vals):.4f}")
            
            # Outliers
            print(f"  Top 3 Lowest (Best):")
            for ov, name in sorted_data[:3]:
                print(f"    {name}: {ov:.4f}")
                
            print(f"  Top 3 Highest (Worst):")
            for ov, name in sorted_data[-3:][::-1]:
                print(f"    {name}: {ov:.4f}")

    print_stats(duck_stats_list, duck_labels, "DuckDB")
    print_stats(lady_stats_list, lady_labels, "Ladybug")

    # --- Plotting ---
    figsize = (figwidth_half, fig_height)
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    ax_duck = axes[0]
    ax_lady = axes[1]
    
    plot_box(ax_duck, duck_data_list, duck_labels, duck_colors, duck_hatches)
    plot_box(ax_lady, lady_data_list, lady_labels, lady_colors, lady_hatches)
    
    ax_duck.set_ylabel('Normalized Runtime', fontsize=FONTSIZE_AXIS_LABEL)
    
    #sns.despine()

    plt.tight_layout()
    output_path = os.path.join(result_dir, "dbms_duckdb_ladybug.pdf")
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    plt.close()
    print(f"Generated dbms_duckdb_ladybug.pdf")

def plot_leveldb_motivation_slowdown(df: pd.DataFrame):
    data = df[
        (df['database'] == 'leveldb_motiv') &
        (df['benchmark'] == 'db_bench') &
        (df['metric_name'] == 'latency_avg')
    ].copy()
    
    if data.empty:
        print("No data for leveldb_motiv slowdown")
        return

    data['metric_value'] = 1_000_000.0 / data['metric_value']
    
    workload_map = {
        'fillrandom_t1': 'Random inserts',
        'readrandom_t1': 'Random reads'
    }
    data = data[data['workload'].isin(workload_map.keys())]
    data['workload'] = data['workload'].map(workload_map)
    
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )
    
    variants_interest = ['release-dynamic', 'release-asan','release-mte', 'release-static', 'release-cheri']
    baseline_map = {
        'release-dynamic': 'release-dynamic',
        'release-asan': 'release-dynamic',
        'release-mte': 'release-dynamic',
        'release-static': 'release-static',
        'release-cheri': 'release-static'
    }
    
    display_labels = {
        'release-dynamic': 'Base',
        'release-asan': 'ASan',
        'release-mte': 'MTE',
        'release-static': 'Base',
        'release-cheri': 'CHERI'
    }
    
    variant_colors = {
        'release-dynamic': BASELINE_MTE_COLOR,
        'release-asan': ASAN_COLOR,
        'release-mte': MTE_COLOR,
        'release-static': BASELINE_CHERI_COLOR,
        'release-cheri': CHERI_COLOR
    }
    
    variant_hatches = {
        'release-dynamic': BASELINE_MTE_HATCH,
        'release-asan': ASAN_HATCH,
        'release-mte': MTE_HATCH,
        'release-static': BASELINE_CHERI_HATCH,
        'release-cheri': CHERI_HATCH
    }

    figsize = (figwidth_half, fig_height)
    fig, axes = plt.subplots(1, 2, figsize=figsize, sharey=True) 
    
    metrics = ['Random inserts', 'Random reads']
    bar_width = 0.6
    
    for ax, workload in zip(axes, metrics):
        if workload not in pivot.index: 
            ax.set_visible(False)
            continue
        
        counts = np.arange(len(variants_interest))
        
        for i, var in enumerate(variants_interest):
            if var not in pivot.columns: continue
            
            val = pivot.loc[workload, var]
            base_var = baseline_map[var]
            
            if base_var in pivot.columns:
                base_val = pivot.loc[workload, base_var]
            else:
                base_val = val # Fallback
                
            ax.bar(
                i, 
                val, 
                color=variant_colors[var], 
                edgecolor='black', 
                hatch=variant_hatches[var],
                width=bar_width
            )

            skip_annotation = (workload == 'Random inserts' and var == 'release-mte')
            if base_val > 0 and val < base_val:
                pct_diff = (val - base_val) / base_val * 100
                
                try:
                    base_idx = variants_interest.index(base_var)
                except ValueError:
                    base_idx = i
                
                ax.hlines(y=base_val, xmin=base_idx+bar_width/2, xmax=i+bar_width/2, colors='#404040', linestyles='--', linewidth=0.5, alpha=1)
                if not skip_annotation:
                    ax.annotate(
                        "",
                        xy=(i, val), xycoords='data',
                        xytext=(i, base_val), textcoords='data',
                        arrowprops=dict(arrowstyle="-|>", color='#8B0000', lw=1, shrinkB=0)
                    )
                
                ax.text(
                    i, 
                    base_val + (base_val * 0.05),
                    f"${pct_diff:.0f}\\%$",
                    ha='center', 
                    va='bottom',
                    fontsize=FONTSIZE_ANNOTATION,
                    color='black'
                )

        import matplotlib.patches as patches
        
        title_height = 0.1
        title_rect = patches.Rectangle((0, 1), 1, title_height, transform=ax.transAxes, facecolor='#E0E0E0', edgecolor='none', clip_on=False)
        ax.add_patch(title_rect)
        
        ax.text(0.5, 1 + title_height/2, workload, transform=ax.transAxes, ha='center', va='center', fontsize=FONTSIZE, color='black', fontweight='bold')
        ax.set_xticks(counts)
        ax.set_xticklabels([display_labels[v] for v in variants_interest], fontsize=FONTSIZE_TICK_LABEL, rotation=0)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers_tweaked))
        ax.tick_params(axis='y', labelsize=FONTSIZE_TICK_LABEL)
        
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(0, ymax * 1.24)
        
        ax.axvline(x=2.5, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        
        if workload == metrics[0]:
            # Labels for groups
            ax.text(1.0, ymax * 1.5, "Ampere 1a", ha='center', va='top', fontsize=FONTSIZE_TICK_LABEL-1, fontweight='bold', color='gray')
            ax.text(3.5, ymax * 1.5, "Morello", ha='center', va='top', fontsize=FONTSIZE_TICK_LABEL-1, fontweight='bold', color='gray')

    axes[0].set_ylabel('Throughput (ops/sec)', fontsize=FONTSIZE_AXIS_LABEL)
    
    plt.tight_layout()
    plt.subplots_adjust(wspace=0.1)
    output_path = os.path.join(result_dir, 'dbms_leveldb_motiv.pdf')
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    plt.close()
    
    print("Generated dbms_leveldb_motiv.pdf")

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
    # DuckDB TPC-H (Warm)
    duckdb_warm = df[
        (df['database'] == 'duckdb') &
        (df['benchmark'] == 'tpch') &
        (df['metric_name'] == 'query_time') &
        (df['variant'].isin(['release', 'release-mte']))
    ].copy()

    duckdb_cold = df[
        (df['database'] == 'duckdb') &
        (df['benchmark'] == 'tpch') &
        (df['metric_name'] == 'query_time') &
        (df['variant'].isin(['release-cold', 'release-mte-cold']))
    ].copy()

    # SQLite TPC-C
    sqlite_data = df[
        (df['database'] == 'sqlite') &
        (df['benchmark'] == 'tpcc') &
        (df['metric_name'] == 'tps')
    ].copy()
    # MySQL Sysbench
    mysql_data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'tps')
    ].copy()
    # Combined Plot for All Systems
    plot_all_systems(df)

    # Motivation Plot (Keep separate as it serves a different purpose)
    plot_leveldb_motivation_slowdown(df)

    print("\nAll plots generated successfully.")


if __name__ == '__main__':
    main()