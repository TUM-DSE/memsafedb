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
        color=MTE_COLOR,
        edgecolor='black',
        hatch=MTE_HATCH,
        capsize=3,
    )

    # Add 1.0 reference line
    ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1, label='No overhead')

    ax.set_ylabel('Normalized Overhead', fontsize=FONTSIZE_AXIS_LABEL)
    ax.set_xticks(x)
    ax.set_xticklabels(db_overhead['database'], fontsize=FONTSIZE_TICK_LABEL)
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
            fontsize=FONTSIZE_ANNOTATION,
        )

    ax.set_ylim(0, max(db_overhead['mean'].max() * 1.3, 1.5))
    ax.annotate(
        lower_better_str,
        color='blue',
        xy=(0.02, 0.92),
        xycoords='axes fraction',
        fontsize=FONTSIZE_ANNOTATION,
    )

    plt.tight_layout()
    plt.savefig(
        os.path.join(result_dir, 'dbms_overhead_summary.pdf'),
        format='pdf',
        bbox_inches='tight',
    )
    plt.close()
    print("Generated dbms_overhead_summary.pdf")

def plot_generic_benchmark(
    data: pd.DataFrame,
    output_filename: str,
    y_label: str = "Metric",
    higher_better=True,
    fig_width=figwidth_full
):
    """Generic function to plot baseline vs MTE and baseline vs CHERI with relative performance."""
    
    if data.empty:
        print(f"No data for {output_filename}")
        return


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
        if not variants_to_plot:
            print(f"No valid variant pairs found for {output_filename}")
            return

    # Filter data for selected variants
    data = data[data['variant'].isin(variants_to_plot)]
    
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
    
    # Plot setup
    figsize = (fig_width, fig_height * 1.5)
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(pivot))
    total_width = 0.8
    width = total_width / len(variants_to_plot)
    
    # Local style map with fallback for 'release'
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
                        
                        # Calculate Y position (top of bar or top of error bar)
                        y_pos = bar.get_height()
                        if var in pivot_std:
                            std_val = pivot_std[var].iloc[idx]
                            if not pd.isna(std_val) and std_val > 0:
                                y_pos += std_val
                        
                        # Dynamic padding
                        padding = 0.02 * pivot.values.max()

                        # Place annotation
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            y_pos + padding, 
                            annotation_text,
                            ha='center',
                            va='bottom',
                            fontsize=FONTSIZE_ANNOTATION,
                            rotation=0
                        )

    ax.set_ylabel(y_label, fontsize=FONTSIZE_AXIS_LABEL)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=FONTSIZE_TICK_LABEL)
    
    # Tilt x labels if too many
    if len(pivot) > X_TICKS_TILT_THRESHOLD:
        ax.tick_params(axis='x', labelrotation=45)
    else:
        ax.tick_params(axis='x', labelrotation=0)

    
    # Add Legend with unique labels (handle duplicate labels if any)
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    
    if fig_width <= figwidth_half:
        # Half width: Place legend above the plot to avoid overlap
        if len(variants_to_plot) > 2:
            legend_ncol = 2
        else:
            legend_ncol = len(variants_to_plot)
            
        ax.legend(
            by_label.values(), 
            by_label.keys(), 
            fontsize=FONTSIZE_LEGEND, 
            loc='lower center', 
            bbox_to_anchor=(0.5, 1.02), 
            ncol=legend_ncol,
            borderaxespad=0.
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

    
    # Indicator
    indicator = higher_better_str if higher_better else lower_better_str
    
    ax.annotate(
        indicator,
        color='blue',
        xy=(0.02, 0.92),
        xycoords='axes fraction',
        fontsize=FONTSIZE_ANNOTATION,
    )
    
    # Format Y axis
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
    
    # Adjust y-limit to fit annotations
    # Simple heuristic: add 15% padding on top
    ymax = pivot.max().max()
    ax.set_ylim(0, ymax * 1.2)
    
    plt.tight_layout()
    output_path = os.path.join(result_dir, output_filename)
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    plt.close()
    print(f"Generated {output_filename}")

def plot_leveldb_motivation_slowdown(df: pd.DataFrame):
    data = df[
        (df['database'] == 'leveldb_motiv') &
        (df['benchmark'] == 'db_bench') &
        (df['metric_name'] == 'latency_avg')
    ].copy()
    
    if data.empty:
        print("No data for leveldb_motiv slowdown")
        return

    # Convert Latency to Throughput (ops/sec)
    data['metric_value'] = 1_000_000.0 / data['metric_value']
    
    # Workload mapping
    workload_map = {
        'fillrandom_t1': 'Random inserts',
        'readrandom_t1': 'Random reads'
    }
    data = data[data['workload'].isin(workload_map.keys())]
    data['workload'] = data['workload'].map(workload_map)
    
    # Pivot
    pivot = data.pivot_table(
        index='workload',
        columns='variant',
        values='metric_value',
        aggfunc='mean'
    )
    
    variants_order = ['release-dynamic', 'release-mte', 'release-asan', 'release-static', 'release-cheri']
    labels_map = {
        'release-dynamic': 'Baseline (MTE/ASan)',
        'release-mte': 'MTE',
        'release-asan': 'ASan',
        'release-static': 'Baseline (CHERI)',
        'release-cheri': 'CHERI'
    }
    
    # Check what's available
    variants_present = [v for v in variants_order if v in pivot.columns]
    
    figsize = (figwidth_half, fig_height * 1.8)
    fig, ax = plt.subplots(figsize=figsize)
    
    workloads = ['Random inserts', 'Random reads']
    x = np.arange(len(workloads))
    total_width = 0.85
    bar_width = total_width / len(variants_present)
    
    for i, var in enumerate(variants_present):
        offset = (i - len(variants_present)/2 + 0.5) * bar_width
        
        heights = []
        annotations = []
        
        for wl in workloads:
            if wl not in pivot.index: 
                heights.append(0)
                annotations.append("")
                continue
            
            # Throughput value
            thpt_val = pivot.loc[wl, var]
            heights.append(thpt_val)
            
            # Determine baseline for THIS variant to calc overhead
            if var in ['release-dynamic', 'release-mte', 'release-asan']:
                base_var = 'release-dynamic'
            else:
                base_var = 'release-static'
            
            if base_var not in pivot.columns or thpt_val == 0:
                 annotations.append("N/A")
                 continue
                 
            thpt_base = pivot.loc[wl, base_var]
            
            # Overhead calculation: (Tb / Tv) - 1  == (Lv - Lb) / Lb
            if thpt_val > 0:
                overhead_pct = (thpt_base / thpt_val - 1) * 100
            else:
                overhead_pct = 0
                
            if abs(overhead_pct) < 0.1:
                annotations.append("")
            else:
                sign = '+' if overhead_pct >= 0 else '-'
                annotations.append(f"${sign}{abs(overhead_pct):.0f}\\%$")

        if var == 'release-dynamic':
            color = BASELINE_MTE_COLOR
            hatch = BASELINE_MTE_HATCH
        elif var == 'release-mte':
            color = MTE_COLOR
            hatch = MTE_HATCH
        elif var == 'release-asan':
            color = ASAN_COLOR
            hatch = ASAN_HATCH
        elif var == 'release-static':
            color = BASELINE_CHERI_COLOR
            hatch = BASELINE_CHERI_HATCH
        elif var == 'release-cheri':
            color = CHERI_COLOR
            hatch = CHERI_HATCH
        else:
            color = 'gray'
            hatch = ''
        
        bars = ax.bar(
            x + offset,
            heights,
            bar_width,
            label=labels_map.get(var, var),
            color=color,
            edgecolor='black',
            hatch=hatch
        )
        
        # Annotate
        for bar, text in zip(bars, annotations):
            height = bar.get_height()
            
            y_pos = height
            padding = 0.02 * max(pivot.max()) # Relative to max height
            
            ax.text(
                bar.get_x() + bar.get_width()/2,
                y_pos + padding,
                text,
                ha='center',
                va='bottom',
                rotation=90,
                fontsize=FONTSIZE_ANNOTATION
            )

    ax.set_ylabel('Throughput (ops/sec)', fontsize=FONTSIZE_AXIS_LABEL)
    ax.set_xticks(x)
    ax.set_xticklabels(workloads, fontsize=FONTSIZE_TICK_LABEL)
    
    # Formatter
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
    
    # Add Legend
    ax.legend(fontsize=FONTSIZE_LEGEND, loc='upper center', bbox_to_anchor=(0.5, 1.25), ncol=2) 
    
    # Adjust Y lims
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax * 1.5) # generous space for annotations/legend

    plt.tight_layout()
    output_path = os.path.join(result_dir, 'dbms_leveldb_motiv.pdf')
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    plt.close()

    print("Generated dbms_leveldb_motiv.pdf")

def plot_ladybug_grouped(df_in: pd.DataFrame, output_filename: str = 'dbms_ladybug.pdf'):
    data = df_in.copy()
    
    def get_group(w):
        if w in ['q24', 'q28']: return 'Agg'
        if w in ['q14', 'q15', 'q16', 'q17', 'q18'] or w.startswith('zonemap-'): return 'Filter'
        if w in [f'q{i:02d}' for i in range(7, 14)]: return 'Fixed_sized_expr'
        if w == 'q23': return 'Fixed_size_scan'
        if w in ['q29', 'q30', 'q31', 'selective-join']: return 'Join'
        if w in ['q35', 'q36']: return 'SNB_IC'
        if w in ['q32', 'q33', 'q34']: return 'SNB_IS'
        if 'limit' in w and 'distinct' in w: return 'Limit'
        if w.startswith('multi-rel-'): return 'Multi-rel'
        if w in ['q25', 'q26', 'q27']: return 'Order_by'
        if 'recursive-join' in w: return 'Rec_join'
        if w in ['q01', 'q02']: return 'Filter_scan'
        if w in ['q37', 'q38', 'q39', 'q40']: return 'Shortest_path'
        if w in ['q03', 'q04', 'q05', 'q06']: return 'Var_size_expr'
        if w in ['q19', 'q20', 'q21', 'q22']: return 'Var_size_scan'
        return 'Other'

    data['group'] = data['workload'].apply(get_group)
    
    # Aggregate: Mean of iterations first
    grouped_wl = data.groupby(['group', 'workload', 'variant'])['metric_value'].mean().reset_index()
    
    # Aggregate: GMean per group
    aggregated = grouped_wl.groupby(['group', 'variant'])['metric_value'].apply(gmean).reset_index()
    
    # Separate into Left and Right groups
    right_groups = ['SNB_IC', 'SNB_IS', 'Limit']
    df_right = aggregated[aggregated['group'].isin(right_groups)].copy()
    df_left = aggregated[~aggregated['group'].isin(right_groups)].copy()
    
    fig, axes = plt.subplots(1, 2, figsize=(figwidth_full, fig_height), gridspec_kw={'width_ratios': [3, 1]})
    ax_left = axes[0]
    ax_right = axes[1]
    
    left_groups = natsorted(df_left['group'].unique())
    right_groups_sorted = natsorted(df_right['group'].unique())
    
    variants = aggregated['variant'].unique().tolist()
    
    # Define style map
    local_style_map = style_map.copy()
    local_style_map['release'] = {'color': BASELINE_MTE_COLOR, 'hatch': BASELINE_MTE_HATCH, 'label': 'Baseline (MTE)'}
    local_style_map['release-dynamic'] = {'color': BASELINE_MTE_COLOR, 'hatch': BASELINE_MTE_HATCH, 'label': 'Baseline (MTE)'}
    local_style_map['release-mte'] = {'color': MTE_COLOR, 'hatch': MTE_HATCH, 'label': 'MTE'}
    local_style_map['release-static'] = {'color': BASELINE_CHERI_COLOR, 'hatch': BASELINE_CHERI_HATCH, 'label': 'Baseline (CHERI)'}
    local_style_map['release-cheri'] = {'color': CHERI_COLOR, 'hatch': CHERI_HATCH, 'label': 'CHERI'}
    
    # Ensure specific variant order if possible
    preferred_order = ['release-dynamic', 'release-mte', 'release-static', 'release-cheri']
    variants_to_plot = [v for v in preferred_order if v in variants]
    # Add others if any
    for v in variants:
        if v not in variants_to_plot: variants_to_plot.append(v)
        
    width = 0.8 / len(variants_to_plot)
    
    def plot_on_ax(ax, df, groups):
        x = np.arange(len(groups))
        
        # Pivot for easier access
        piv = df.pivot(index='group', columns='variant', values='metric_value')
        piv = piv.reindex(groups)
        
        for i, var in enumerate(variants_to_plot):
            if var not in piv.columns: continue
            
            offset = (i - len(variants_to_plot)/2 + 0.5) * width
            vals = piv[var].values
            
            style = local_style_map.get(var, {'color': 'gray', 'hatch': '', 'label': var})
            
            bars = ax.bar(
                x + offset,
                vals,
                width,
                label=style['label'],
                color=style['color'],
                edgecolor='black',
                hatch=style['hatch']
            )
            
            # Determine baseline
            base_var = None
            if var == 'release-mte': base_var = 'release-dynamic'
            elif var == 'release-cheri': base_var = 'release-static'
            
            if base_var and base_var in piv.columns:
                base_vals = piv[base_var].values
                for idx, (val, base_val, bar) in enumerate(zip(vals, base_vals, bars)):
                     if pd.isna(val) or pd.isna(base_val) or base_val == 0: continue
                     
                     pct = (val - base_val) / base_val * 100
                     sign = '+' if pct >= 0 else '-'
                     label = f"${sign}{abs(pct):.0f}\\%$"
                     
                     y_pos = bar.get_height()
                     padding = 0.02 * ax.get_ylim()[1]
                     
                     ax.text(
                         bar.get_x() + bar.get_width()/2,
                         y_pos,
                         label,
                         ha='center',
                         va='bottom',
                         fontsize=FONTSIZE_ANNOTATION,
                         rotation=90
                     )

        # Formatting
        # Clean group names
        clean_labels = [g.replace('_', ' ') for g in groups]
        ax.set_xticks(x)
        ax.set_xticklabels(clean_labels, fontsize=FONTSIZE_TICK_LABEL, rotation=45, ha='right')
        
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
        
        # Add grid
        ax.grid(False)
        
        # Set Y limits with padding for annotations
        ax.margins(y=0.2)

    plot_on_ax(ax_left, df_left, left_groups)
    plot_on_ax(ax_right, df_right, right_groups_sorted)
    
    ax_left.set_ylabel('Throughput (QPS)', fontsize=FONTSIZE_AXIS_LABEL)

    handles, labels = ax_left.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax_left.legend(by_label.values(), by_label.keys(), loc='best', fontsize=FONTSIZE_LEGEND, ncol=4)

    sns.despine()
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, output_filename), format='pdf', bbox_inches='tight')
    plt.close()


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
    if not duckdb_warm.empty:
        duckdb_warm['metric_value'] = 1.0 / duckdb_warm['metric_value']
        plot_generic_benchmark(
            duckdb_warm,
            output_filename='dbms_duckdb_warm.pdf',
            y_label='Throughput (QPS)',
            higher_better=True,
            fig_width=figwidth_full
        )

    # DuckDB TPC-H (Cold)
    duckdb_cold = df[
        (df['database'] == 'duckdb') &
        (df['benchmark'] == 'tpch') &
        (df['metric_name'] == 'query_time') &
        (df['variant'].isin(['release-cold', 'release-mte-cold']))
    ].copy()
    if not duckdb_cold.empty:
        # Normalize variants so generic plotter picks them up
        duckdb_cold['variant'] = duckdb_cold['variant'].replace({
            'release-cold': 'release',
            'release-mte-cold': 'release-mte'
        })
        duckdb_cold['metric_value'] = 1.0 / duckdb_cold['metric_value']
        plot_generic_benchmark(
            duckdb_cold,
            output_filename='dbms_duckdb_cold.pdf',
            y_label='Throughput (QPS)',
            higher_better=True,
            fig_width=figwidth_full
        )

    # SQLite TPC-C (Half Width)
    sqlite_data = df[
        (df['database'] == 'sqlite') &
        (df['benchmark'] == 'tpcc') &
        (df['metric_name'] == 'tps')
    ].copy()
    plot_generic_benchmark(
        sqlite_data,
        output_filename='dbms_sqlite.pdf',
        y_label='Throughput (TPS)',
        higher_better=True,
        fig_width=figwidth_half
    )

    # LevelDB YCSB
    leveldb_data = df[
        (df['database'] == 'leveldb') &
        (df['benchmark'] == 'ycsb') &
        (df['metric_name'] == 'throughput')
    ].copy()
    if not leveldb_data.empty:
        # Rename workloads: a_t1 -> A, etc.
        leveldb_data['workload'] = leveldb_data['workload'].apply(
            lambda x: x.split('_')[0].upper()
        )
        plot_generic_benchmark(
            leveldb_data,
            output_filename='dbms_leveldb.pdf',
            y_label='Throughput (ops/sec)',
            higher_better=True,
            fig_width=figwidth_full
        )

    # Redis YCSB
    redis_data = df[
        (df['database'] == 'redis') &
        (df['benchmark'] == 'ycsb') &
        (df['metric_name'] == 'throughput')
    ].copy()
    if not redis_data.empty:
        # Normalize variants
        redis_data['variant'] = redis_data['variant'].replace({
            'dynamic': 'release-dynamic',
            'mte': 'release-mte',
            'static': 'release-static',
            'cheri': 'release-cheri'
        })
        redis_data['workload'] = redis_data['workload'].str.upper()

        plot_generic_benchmark(
            redis_data,
            output_filename='dbms_redis.pdf',
            y_label='Throughput (ops/sec)',
            higher_better=True,
            fig_width=figwidth_full
        )

    # MySQL Sysbench
    mysql_data = df[
        (df['database'] == 'mysql') &
        (df['benchmark'] == 'sysbench') &
        (df['metric_name'] == 'tps')
    ].copy()
    plot_generic_benchmark(
        mysql_data,
        output_filename='dbms_mysql.pdf',
        y_label='Throughput (TPS)',
        higher_better=True,
        fig_width=figwidth_half
    )

    # Ladybug LDBC
    ladybug_data = df[
        (df['database'] == 'ladybug') &
        (df['benchmark'] == 'ldbc') &
        (df['metric_name'] == 'query_time')
    ].copy()
    
    if not ladybug_data.empty:
        # Convert ms to QPS (1000 / ms)
        ladybug_data['metric_value'] = 1000.0 / ladybug_data['metric_value']
        
        plot_ladybug_grouped(
            ladybug_data,
            output_filename='dbms_ladybug.pdf'
        )

    # LevelDB Motivation
    plot_leveldb_motivation_slowdown(df)


    print("\nAll plots generated successfully.")


if __name__ == '__main__':
    main()