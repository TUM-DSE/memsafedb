#!/usr/bin/env python3
"""DBMS benchmark plotting script."""
from common import *

X_TICKS_TILT_THRESHOLD = 8

def load_dbms_data() -> pd.DataFrame:
    """Load DBMS benchmark results from CSV.

    Prefers the sweep output (what run_benchmarks.py writes) over the older
    dbms_results.csv; override with DBMS_RESULTS_CSV.
    """
    override = os.environ.get('DBMS_RESULTS_CSV')
    candidates = [override] if override else ['dbms_sweep_results.csv', 'dbms_results.csv']
    for name in candidates:
        csv_path = name if os.path.isabs(name) else os.path.join(result_dir, name)
        if os.path.exists(csv_path):
            print(f"Loading results from {csv_path}")
            return pd.read_csv(csv_path)
    raise FileNotFoundError(f"Results file not found: tried {candidates} in {result_dir}")

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


def plot_bars_on_ax(ax, pivot, pivot_std, variants_to_plot, baseline_map, y_label, show_x_labels=True, higher_better=True, show_indicator=True, bar_width_scale=1.0):
    """Refactored helper: Plot bars on given axis."""
    x = np.arange(len(pivot))
    total_width = 0.8 * bar_width_scale
    width = total_width / len(variants_to_plot)

    ax.set_xlim(x[0] - 0.5, x[-1] + 0.5)
    ax.autoscale(enable=False, axis='x')

    order_priority = ['release-dynamic', 'release', 'release-mte', 'release-asan', 'release-rsan', 'release-static', 'release-cheri']
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
            width=width,
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
            xy=(0.02, 0.9),
            xycoords='axes fraction',
            fontsize=FONTSIZE_TITLE,
        )
    
    # Format Y axis
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
    
    ymax = pivot.max().max()
    ax.set_ylim(0, ymax * 1.5)

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
    fig = plt.figure(figsize=(figwidth_full, 1.5 * fig_height))
    gs_main = fig.add_gridspec(2, 1, hspace=0.5)
    
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
        plot_bars_on_ax(ax_mysql, p_mysql, ps_mysql, v_mysql, b_mysql, 'Throughput (TPS)', show_x_labels=False, bar_width_scale=0.5)
    if p_sqlite is not None:
        plot_bars_on_ax(ax_sqlite, p_sqlite, ps_sqlite, v_sqlite, b_sqlite, '', show_x_labels=False, bar_width_scale=0.6)
    
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
        (ax_redis, r"\textbf{(a) Redis.}"),
        (ax_level, r"\textbf{(b) LevelDB.}"),
        (ax_mysql, r"\textbf{(c) MySQL.}"),
        (ax_sqlite, r"\textbf{(d) SQLite.}"),
        (ax_duck, r"\textbf{(e) DuckDB.}"),
        (ax_lady, r"\textbf{(f) LadyBugDB.}"),
    ]
    
    for ax, txt in captions:
        ax.text(0.5, -0.3, txt, transform=ax.transAxes, ha='center', va='top', fontsize=FONTSIZE_TITLE, fontweight='bold')
    
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
    
    variants_interest = ['release-dynamic', 'release-asan', 'release-rsan', 'release-mte',
                         'release-static', 'release-cheri']
    baseline_map = {
        'release-dynamic': 'release-dynamic',
        'release-asan': 'release-dynamic',
        'release-rsan': 'release-dynamic',
        'release-mte': 'release-dynamic',
        'release-static': 'release-static',
        'release-cheri': 'release-static'
    }

    display_labels = {
        'release-dynamic': 'Base',
        'release-asan': 'ASan',
        'release-rsan': 'RSan',
        'release-mte': 'MTE',
        'release-static': 'Base',
        'release-cheri': 'CHERI'
    }

    variant_colors = {
        'release-dynamic': BASELINE_MTE_COLOR,
        'release-asan': ASAN_COLOR,
        'release-rsan': RSAN_COLOR,
        'release-mte': MTE_COLOR,
        'release-static': BASELINE_CHERI_COLOR,
        'release-cheri': CHERI_COLOR
    }

    variant_hatches = {
        'release-dynamic': BASELINE_MTE_HATCH,
        'release-asan': ASAN_HATCH,
        'release-rsan': RSAN_HATCH,
        'release-mte': MTE_HATCH,
        'release-static': BASELINE_CHERI_HATCH,
        'release-cheri': CHERI_HATCH
    }

    # Baselines are shown as a labelled dashed line rather than a bar, which
    # frees horizontal space for the variants that actually carry the message.
    bar_variants = [v for v in variants_interest if baseline_map[v] != v]

    figsize = (figwidth_half, fig_height)
    fig, axes = plt.subplots(1, 2, figsize=figsize, sharey=True)
    
    metrics = ['Random inserts', 'Random reads']
    bar_width = 0.6
    
    for ax, workload in zip(axes, metrics):
        if workload not in pivot.index: 
            ax.set_visible(False)
            continue
        
        # Leave a gap between the two machine groups so each group's dashed
        # baseline has room for its rotated label at the right-hand end.
        group_gap = 0.85
        positions, x, prev_base = [], 0.0, None
        for var in bar_variants:
            b = baseline_map[var]
            if prev_base is not None and b != prev_base:
                x += group_gap
            positions.append(x)
            x += 1.0
            prev_base = b
        counts = np.array(positions)

        for i, var in enumerate(bar_variants):
            if var not in pivot.columns: continue
            ax.bar(
                positions[i],
                pivot.loc[workload, var],
                color=variant_colors[var],
                edgecolor='black',
                hatch=variant_hatches[var],
                width=bar_width
            )

        # One dashed line per baseline group, labelled in place of the old bar.
        groups = {}
        for i, var in enumerate(bar_variants):
            if var in pivot.columns:
                groups.setdefault(baseline_map[var], []).append(positions[i])

        base_top = 0.0
        for base_var, idxs in groups.items():
            if base_var not in pivot.columns: continue
            base_val = pivot.loc[workload, base_var]
            base_top = max(base_top, base_val)
            x0, x1 = min(idxs) - bar_width / 2, max(idxs) + bar_width / 2
            ax.hlines(y=base_val, xmin=x0, xmax=x1, colors='#404040',
                      linestyles='--', linewidth=0.8, alpha=1)
            # Vertical, just left of the group's first bar so it reads before the
            # bars it applies to. va='top' hangs it *below* the line, so the word
            # ends on the dashed line and leaves the headroom to the % labels.
            ax.text(x0 - 0.30, base_val, "Baseline", ha='center', va='top',
                    rotation=90, fontsize=FONTSIZE_ANNOTATION, color='#404040')

        for i, var in enumerate(bar_variants):
            if var not in pivot.columns: continue
            val = pivot.loc[workload, var]
            base_var = baseline_map[var]
            if base_var not in pivot.columns: continue
            base_val = pivot.loc[workload, base_var]
            if not (base_val > 0 and val < base_val): continue

            pct_diff = (val - base_val) / base_val * 100
            skip_annotation = (workload == 'Random inserts'
                               and var in ('release-mte', 'release-rsan'))
            if not skip_annotation:
                ax.annotate(
                    "",
                    xy=(positions[i], val), xycoords='data',
                    xytext=(positions[i], base_val), textcoords='data',
                    arrowprops=dict(arrowstyle="-|>", color='#8B0000', lw=1, shrinkB=0)
                )

            ax.text(
                positions[i],
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
        ax.set_xticklabels([display_labels[v] for v in bar_variants],
                           fontsize=FONTSIZE_TICK_LABEL, rotation=0)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers_tweaked))
        ax.tick_params(axis='y', labelsize=FONTSIZE_TICK_LABEL)

        # The baselines are lines now, not bars, so autoscale may not cover them.
        # Headroom only needs to clear the % labels; the "Baseline" labels hang
        # below their line.
        ymax = max(ax.get_ylim()[1], base_top)
        top = ymax * 1.16
        ax.set_ylim(0, top)
        # Leading space on the left so the first group's rotated "Baseline"
        # label has room; the inter-group gap houses the second one.
        xlo, xhi = positions[0] - 0.5 - 0.45, positions[-1] + 0.5 + bar_width / 4
        ax.set_xlim(xlo, xhi)

        # Divider/labels derive from the laid-out positions, so they stay aligned
        # when variants are added or the group gap changes.
        amp = [p for v, p in zip(bar_variants, positions)
               if baseline_map[v] == 'release-dynamic']
        mor = [p for v, p in zip(bar_variants, positions)
               if baseline_map[v] != 'release-dynamic']
        divider_x = (max(amp) + min(mor)) / 2 if (amp and mor) else None
        if divider_x is not None:
            ax.axvline(x=divider_x, color='gray',
                       linestyle='--', linewidth=0.5, alpha=0.5)

        if workload == metrics[0]:
            # Each label is centred in its own column (the region the divider
            # cuts out), not over the bars, so a single-bar group like Morello
            # still sits mid-column. y is an axes fraction, so the shared-y
            # rescaling can't shift these and 0.97 keeps them near the top.
            trans = ax.get_xaxis_transform()
            spans = []
            if amp:
                spans.append(((xlo, divider_x if divider_x is not None else xhi), "Ampere 1a"))
            if mor:
                spans.append(((divider_x if divider_x is not None else xlo, xhi), "Morello"))
            for (a, b), label in spans:
                ax.text((a + b) / 2, 0.97, label, transform=trans,
                        ha='center', va='top', fontsize=FONTSIZE_TICK_LABEL-1,
                        fontweight='bold', color='gray')

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

    # Combined sweep figure (table + bars + query-time clouds)
    plot_dbms_sweep()

    print("\nAll plots generated successfully.")


if __name__ == '__main__':
    main()

# ---------------------------------------------------------------------------
# Combined sweep figure: YCSB table (Redis/LevelDB), SQLite+MySQL bars,
# DuckDB and LadyBugDB query-time clouds. Rows are emitted separately and
# stacked by dbms_sweep_combined.tex in the paper.
# ---------------------------------------------------------------------------
import csv as _csv
import math as _math
import statistics as _stats
import shutil as _shutil
import matplotlib.gridspec as _gridspec
from matplotlib.ticker import FuncFormatter, NullFormatter, LogLocator
import matplotlib.colors as _mcolors
from pictograms import labelled_row, key as _pictogram_key, emit_glyph_pdfs

SWEEP_WL = ['a', 'b', 'c', 'd', 'e', 'f']
SWEEP_RWS = ['10000', '100000', '1000000']          # Redis working sets
SWEEP_LWS = ['100000', '1000000', '10000000']       # LevelDB working sets
# tabcolsep chosen so the tabular's natural width is 7in at \tiny; re-solve
# (natural width is linear in tabcolsep, ~27.9pt per pt) if columns change.
SWEEP_TABCOLSEP = '5.90pt'
_SWEEP_BASE = plt.get_cmap('RdYlBu_r')
# trim the darkest ends: at full range the extremes are near-black navy and
# maroon, which swallow the black cell text
SWEEP_CMAP = _mcolors.LinearSegmentedColormap.from_list(
    'RdYlBu_r_soft', _SWEEP_BASE(np.linspace(0.18, 0.82, 256)))
SWEEP_NORM = _mcolors.TwoSlopeNorm(vmin=0.80, vcenter=1.0, vmax=2.20)
T_CRIT = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776}
DUCK_COLS = [('#6E6E6E', '#08519C'), ('#A8A8A8', '#3E8FD0')]   # cold dark / warm light
LADY_COLS = [('#6E6E6E', '#1F78B4'), ('#A8A8A8', '#E08214')]   # MTE / CHERI
FS_SYS, FS_CFG, FS_GM, FS_TICK, FS_XL, FS_KEY = 8.4, 6.4, 6.6, 6.2, 5.4, 6.4
FS_AXIS, FS_ANN, FS_LEG = 7.0, 5.6, 6.4


def _sweep_rows():
    override = os.environ.get('DBMS_RESULTS_CSV')
    name = override or 'dbms_sweep_results.csv'
    path = name if os.path.isabs(name) else os.path.join(result_dir, name)
    return list(_csv.DictReader(open(path)))


def _shorten(v):
    if v is None:
        return '--'
    if v >= 1e6:
        return f"{v/1e6:.1f}".rstrip('0').rstrip('.') + 'M'
    if v >= 1e3:
        return f"{v/1e3:.0f}K"
    return f"{v:.0f}"


def _hexcol(slow):
    r, g, b, _ = SWEEP_CMAP(SWEEP_NORM(slow))
    return f"{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"


def _pct(slow):
    return f"{(slow-1)*100:+.0f}\\%"


# ----------------------------- row 1: YCSB table ---------------------------

def emit_sweep_colorbar(out_dir, name='dbms_sweep_colorbar.pdf'):
    """Horizontal colour-scale legend for the table's config header: a thin
    gradient strip with "Overhead" written inside it and ticks below."""
    import matplotlib.patheffects as _pe
    sm = plt.cm.ScalarMappable(cmap=SWEEP_CMAP, norm=SWEEP_NORM)
    fig = plt.figure(figsize=(2.1, 0.20))
    ax = fig.add_axes([0.02, 0.50, 0.96, 0.5])   # strip on top, ticks below
    cb = fig.colorbar(sm, cax=ax, orientation='horizontal', extend='both')
    cb.set_ticks([0.8, 1.0, 1.5, 2.2])
    cb.set_ticklabels([r'$0.8\times$', r'$1\times$', r'$1.5\times$', r'$2.2\times$'])
    cb.ax.tick_params(labelsize=4.2, length=1.2, pad=0.6, width=0.3)
    cb.outline.set_linewidth(0.3)
    cb.ax.text(0.5, 0.5, 'Overhead', transform=cb.ax.transAxes, ha='center',
               va='center', fontsize=4.6, color='black',
               path_effects=[_pe.withStroke(linewidth=0.9, foreground='white')])
    path = os.path.join(out_dir, name)
    fig.savefig(path, bbox_inches='tight', pad_inches=0.008)
    plt.close(fig)
    print(f"Saved {path}")
    return path


def write_ycsb_table(rows, cbar_dir='.', out_name='dbms_sweep_ycsb_table.tex',
                     out_dir=None):
    """Redis/LevelDB YCSB throughput as a LaTeX tabular (no float wrapper),
    with a colour-scale legend to the right."""
    def val(db, var, met, wl, ws, th, pers=None):
        v = [float(r['metric_value']) for r in rows
             if r['database'] == db and r['variant'] == var and r['metric_name'] == met
             and r['workload'] == wl and r['working_set'] == ws and r['threads'] == th
             and (pers is None or r['persistence'] == pers)]
        return _stats.mean(v) if v else None

    def val_avg(db, var, met, wl, ws_list, th, pers=None):
        vs = [v for ws in ws_list if (v := val(db, var, met, wl, ws, th, pers))]
        return _stats.mean(vs) if vs else None

    def sweep_block(ws_list, ws_piv, thr_list, t_piv):
        out, ts = [], sorted(thr_list, key=int)
        for ws in ws_list:
            if ws == ws_piv and len(thr_list) > 1:
                for t in ts:
                    out.append((_shorten(float(ws)), t, [ws], t))
            else:
                out.append((_shorten(float(ws)), t_piv, [ws], t_piv))
        return out

    collapsed = [('all', '1', SWEEP_RWS, '1')]
    # each extension is a list of (store-label, persistence, rows). LevelDB adds
    # a single on-disk pivot row (1M at the pivot thread) after its in-memory
    # sweep, so the table separates in-memory from on-disk overhead. The badge
    # reflects the in-memory (first) segment. Redis is in-memory only.
    systems = [
        ('(a) Redis', 'redis', 'throughput', lambda w, t: w, [
            ('\\ac{MTE}', 'release-dynamic', 'release-mte', [('', None, collapsed)]),
            ('\\cheri', 'release-static', 'release-cheri', [('', None, collapsed)]),
        ]),
        ('(b) LevelDB', 'leveldb', 'throughput', lambda w, t: f'{w}_t{t}', [
            ('\\ac{MTE}', 'release-dynamic', 'release-mte', [
                ('mem', 'memory', sweep_block(SWEEP_LWS, '1000000', ['1', '8', '64'], '64')),
                ('disk', 'disk', [('1M', '64', ['1000000'], '64')])]),
            ('\\cheri', 'release-static', 'release-cheri', [
                ('mem', 'memory', sweep_block(SWEEP_LWS, '1000000', ['1', '2', '4'], '4')),
                ('disk', 'disk', [('1M', '4', ['1000000'], '4')])]),
        ]),
    ]

    def cells_for(db, met, pers, wlk, base_v, test_v, brows):
        emitted, allv = [], []
        for wcell, tcell, ws_list, th in brows:
            cells, ok = [], False
            for w in SWEEP_WL:
                b = val_avg(db, base_v, met, wlk(w, th), ws_list, th, pers)
                t = val_avg(db, test_v, met, wlk(w, th), ws_list, th, pers)
                if b and t:
                    sl = b / t
                    allv.append(sl); ok = True
                    cells.append(f"{_shorten(b)} & \\cellcolor[HTML]{{{_hexcol(sl)}}}{_shorten(t)}")
                else:
                    cells.append('-- & --')
            if ok:
                emitted.append((wcell, tcell, cells))
        return emitted, (_stats.mean(allv) if allv else None)

    ncol = 5 + 2 * len(SWEEP_WL)
    # the colour scale encodes overhead (lower is better) while the cells hold
    # throughput (higher is better), so the note names its metric explicitly.
    # colour scale and the direction note share one cell, so the header stays
    # at two rows; the note names its metric since the scale encodes overhead.
    cbar = (f"\\shortstack{{\\includegraphics[width=0.85in]"
            f"{{{cbar_dir}/dbms_sweep_colorbar.pdf}}\\\\[-2pt]"
            f"\\textcolor{{blue}}{{higher is better $\\uparrow$}}}}")
    tab = ['  \\begin{tabular}{@{}l@{\\hspace{2pt}}l@{\\hspace{2pt}}l@{\\hspace{2pt}}r@{\\hspace{1pt}}r'
           + 'rr'*len(SWEEP_WL) + '@{}}', '    \\toprule']
    hdr = ' & '.join(f"\\multicolumn{{2}}{{c}}{{YCSB-{w.upper()}}}" for w in SWEEP_WL)
    tab.append(f'    \\multicolumn{{5}}{{c}}{{{cbar}}} & {hdr} \\\\')
    tab.append('    \\cmidrule(lr){1-5} ' + ' '.join(
        f"\\cmidrule(lr){{{6+2*i}-{7+2*i}}}" for i in range(len(SWEEP_WL))))
    # "prot." = with the memory-safety extension enabled; the row itself says
    # which one. Avoids the ambiguous "ext".
    tab.append('    System & & Store & Datasize & thr & '
               + ' & '.join('base & prot.' for _ in SWEEP_WL) + ' \\\\')
    tab.append('    \\midrule')

    for si, (syslabel, db, met, wlk, exts) in enumerate(systems):
        ext_blocks = []
        for extname, base_v, test_v, segments in exts:
            seg_rows = []
            for store, pers, brows in segments:
                emitted, blk = cells_for(db, met, pers, wlk, base_v, test_v, brows)
                if emitted:
                    seg_rows.append((store, emitted, blk))
            # a labelled segment (mem/disk) carries its own average; only an
            # unlabelled single segment (Redis) hangs its badge off the extension.
            badge_blk = seg_rows[0][2] if len(seg_rows) == 1 and not seg_rows[0][0] else None
            if seg_rows:
                ext_blocks.append((extname, badge_blk, seg_rows))
        if not ext_blocks:
            continue
        total = sum(len(e) for _, _, segs in ext_blocks for _, e, _ in segs)
        syshead = f"\\multirow{{{total}}}{{*}}{{\\textbf{{{syslabel}}}}}"
        sys_first = True
        for k, (extname, blk, seg_rows) in enumerate(ext_blocks):
            ext_total = sum(len(e) for _, e, _ in seg_rows)
            badge = (f"\\,\\colorbox[HTML]{{{_hexcol(blk)}}}{{\\textbf{{{_pct(blk)}}}}}"
                     if blk is not None else '')
            exthead = f"\\multirow{{{ext_total}}}{{*}}{{\\textbf{{{extname}}}{badge}}}"
            ri = 0
            for store, emitted, sblk in seg_rows:
                sbadge = (f"\\,\\colorbox[HTML]{{{_hexcol(sblk)}}}{{\\textbf{{{_pct(sblk)}}}}}"
                          if store and sblk is not None else '')
                for j2, (wcell, tcell, cs) in enumerate(emitted):
                    c0 = syshead if sys_first else ''
                    c1 = exthead if ri == 0 else ''
                    sc = (f"\\multirow{{{len(emitted)}}}{{*}}{{{store}{sbadge}}}"
                          if store and j2 == 0 else '')
                    tab.append(f"    {c0} & {c1} & {sc} & {wcell} & {tcell} & "
                               + ' & '.join(cs) + ' \\\\')
                    sys_first = False
                    ri += 1
            if k < len(ext_blocks) - 1:
                tab.append(f'    \\cmidrule(l){{2-{ncol}}}')
        if si < len(systems) - 1:
            tab.append('    \\midrule')
    tab += ['    \\bottomrule', '  \\end{tabular}']

    out = ['\\setlength{\\tabcolsep}{0.8pt}\\setlength{\\fboxsep}{1pt}'
           '\\renewcommand{\\arraystretch}{1.05}\\tiny']
    out += tab

    path = os.path.join(out_dir or result_dir, out_name)
    open(path, 'w').write('\n'.join(out))
    print(f"Saved {path}")
    return path


# ----------------------- row 2: SQLite and MySQL bars ----------------------

def plot_sqlite_mysql_bars(rows):
    style = dict(style_map)
    style['release'] = style_map['release-dynamic']   # MySQL calls its MTE baseline 'release'

    def stat(db, var, metric, ws, th):
        v = [float(r['metric_value']) for r in rows
             if r['database'] == db and r['variant'] == var
             and r['metric_name'] == metric and r['working_set'] == ws
             and r['threads'] == th]
        if not v:
            return None, None
        return _stats.mean(v), (_stats.stdev(v) if len(v) > 1 else 0.0)

    def bars(fig, ax, db, metric, cfgs, variants, baseline_map, ylabel):
        x = np.arange(len(cfgs))
        width = 0.8/len(variants)
        vals = {v: [stat(db, v, metric, ws, th)[0] for _, _, _, ws, th in cfgs]
                for v in variants}
        errs = {v: [stat(db, v, metric, ws, th)[1] for _, _, _, ws, th in cfgs]
                for v in variants}
        for i, v in enumerate(variants):
            off = (i - len(variants)/2 + 0.5) * width
            st = style[v]
            ax.bar(x + off, [0 if y is None else y for y in vals[v]], width=width,
                   label=st['label'], color=st['color'], edgecolor='black',
                   linewidth=0.4, hatch=st['hatch'],
                   yerr=[0 if e is None else e for e in errs[v]],
                   capsize=1.5, error_kw=dict(lw=0.5, capthick=0.5))
            b = baseline_map.get(v)
            if not b:
                continue
            boff = (variants.index(b) - len(variants)/2 + 0.5) * width
            for k in range(len(cfgs)):
                t, base = vals[v][k], vals[b][k]
                if not t or not base:
                    continue
                top = max(t + (errs[v][k] or 0), base + (errs[b][k] or 0))
                pct = (t - base)/base*100
                ax.text(x[k] + (off+boff)/2, top*1.03,
                        f"${'+' if pct >= 0 else '-'}{abs(pct):.0f}\\%$",
                        ha='center', va='bottom', fontsize=FS_ANN)

        ax.set_xticks(x); ax.set_xticklabels([])
        ax.set_ylabel(ylabel, fontsize=FS_AXIS)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
        ax.tick_params(axis='y', labelsize=FS_TICK, length=2, pad=1)
        ax.tick_params(axis='x', length=0)
        ax.set_xlim(-0.6, len(cfgs)-0.4)
        ax.set_ylim(0, max(v for vv in vals.values() for v in vv if v)*1.45)
        ax.annotate(higher_better_str, xy=(0.02, 0.91), xycoords='axes fraction',
                    color='blue', fontsize=FS_ANN)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        for s in ax.spines.values():
            s.set_linewidth(0.5)
        # datasize label + thread count as plain text under each group
        for k, (wlab, _wr, _tr, _, th) in enumerate(cfgs):
            ax.text(x[k], -0.12, f"{wlab}, {th}\\,thr",
                    transform=ax.get_xaxis_transform(), ha='center', va='top',
                    fontsize=FS_CFG)

    # (label, working-set rank, thread rank, working set, threads)
    sqlite_cfgs = [('1 WH', 1, 1, '1', '1'), ('10 WH', 2, 1, '10', '1'),
                   ('50 WH', 3, 1, '50', '1')]
    mysql_cfgs = [('10K rows', 1, 3, '10000', '64'),
                  ('1M rows', 2, 1, '1000000', '1'), ('1M rows', 2, 2, '1000000', '8'),
                  ('1M rows', 2, 3, '1000000', '64'),
                  ('10M rows', 3, 3, '10000000', '64')]

    fig = plt.figure(figsize=(figwidth_full, 1.65))
    gs = fig.add_gridspec(1, 2, width_ratios=[3, 5], wspace=0.19,
                          left=0.062, right=0.995, top=0.83, bottom=0.34)
    ax1 = fig.add_subplot(gs[0, 0])
    bars(fig, ax1, 'sqlite', 'tps', sqlite_cfgs,
         ['release-dynamic', 'release-mte', 'release-static', 'release-cheri'],
         {'release-mte': 'release-dynamic', 'release-cheri': 'release-static'},
         'Throughput (tps)')
    ax2 = fig.add_subplot(gs[0, 1])
    bars(fig, ax2, 'mysql', 'tps', mysql_cfgs, ['release', 'release-mte'],
         {'release-mte': 'release'}, 'Throughput (tps)')

    for ax, name in ((ax1, '(c) SQLite (py-tpcc)'), (ax2, '(d) MySQL (sysbench OLTP)')):
        bb = ax.get_position()      # centre on the axes, not on a guessed offset
        fig.text((bb.x0 + bb.x1)/2, 0.885, r'\textbf{%s}' % name,
                 ha='center', fontsize=FS_SYS)

    seen, H, L = set(), [], []
    for h, l in zip(*[a + b for a, b in zip(ax1.get_legend_handles_labels(),
                                            ax2.get_legend_handles_labels())]):
        if l in seen:
            continue
        seen.add(l); H.append(h); L.append(l)
    fig.legend(H, L, loc='upper center', ncol=len(L), fontsize=FS_LEG, frameon=False,
               bbox_to_anchor=(0.5, 0.20), handlelength=1.4, handleheight=0.8,
               columnspacing=1.4, handletextpad=0.4)

    path = os.path.join(result_dir, 'dbms_sweep_bars.pdf')
    plt.savefig(path, bbox_inches='tight', pad_inches=0.012)
    plt.close(fig)
    print(f"Saved {path}")
    return path


# ------------------ rows 3/4: DuckDB and LadyBugDB clouds ------------------

def plot_query_clouds(rows):
    rng = np.random.default_rng(0)

    def series(db, variant, ws, th):
        g = collections.defaultdict(dict) if 'collections' in dir() else {}
        g = {}
        for r in rows:
            if (r['database'] == db and r['variant'] == variant
                    and r['metric_name'] == 'query_time'
                    and r['working_set'] == ws and r['threads'] == th):
                g.setdefault(r['workload'], {})[r['repetition']] = float(r['metric_value'])
        return g

    def gmean_(vals):
        vals = [v for v in vals if v > 0]
        return _math.exp(_stats.mean(_math.log(v) for v in vals)) if vals else None

    def panel(ax, db, pairs, cols, show_ylab, yr):
        ticks, labels = [], []
        for pi, (tag, base_v, test_v, ws, th) in enumerate(pairs):
            x0 = pi*2.4
            B, T = series(db, base_v, ws, th), series(db, test_v, ws, th)
            common = sorted(set(B) & set(T))
            ext = 'CHERI' if tag == 'CHERI' else 'MTE'
            ticks += [x0, x0+1]
            labels += ([f"Base\n({tag})", f"{ext}\n({tag})"] if tag in ('cold', 'warm')
                       else [f"Base\n({tag})", ext])
            if not common:
                continue
            cb, ce = cols[pi % len(cols)]
            cog = {}
            for xp, D, col in ((x0, B, cb), (x0+1, T, ce)):
                xs, ys = [], []
                for q in common:
                    for v in D[q].values():
                        xs.append(xp + rng.uniform(-0.16, 0.16)); ys.append(v)
                ax.scatter(xs, ys, s=1.6, color=col, alpha=0.45, linewidths=0, zorder=3)
                yr[0], yr[1] = min(yr[0], min(ys)), max(yr[1], max(ys))
                cog[xp] = gmean_(ys)
                ax.scatter([xp], [cog[xp]], marker='X', s=13, color=col,
                           edgecolors='black', linewidths=0.35, zorder=6)
            pct = (cog[x0+1]/cog[x0] - 1) * 100
            # the overhead sits over its own pair of clouds, so it needs no tag
            ax.text(x0+0.5, 0.935,
                    f"${'+' if pct >= 0 else '-'}{abs(pct):.0f}\\%$",
                    ha='center', va='top',
                    transform=ax.get_xaxis_transform(), fontsize=FS_GM, color=ce,
                    fontweight='bold', zorder=8,
                    bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.75))

        ax.set_yscale('log')
        ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0,), numticks=20))
        ax.yaxis.set_minor_locator(LogLocator(base=10, subs=tuple(range(2, 10)), numticks=20))
        ax.yaxis.set_major_formatter(FuncFormatter(
            lambda v, _: f"{v/1000:g}K" if v >= 1000 else f"{v:g}"))
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_xlim(-0.75, (len(pairs)-1)*2.4 + 1.75)
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, fontsize=FS_XL, linespacing=0.95)
        ax.tick_params(axis='x', length=1.2, pad=1)
        ax.tick_params(axis='y', which='minor', length=0.8)
        if show_ylab:
            ax.tick_params(axis='y', which='major', labelsize=FS_TICK, length=1.8, pad=1)
        else:
            ax.tick_params(axis='y', which='major', labelleft=False, length=1.2)
        for s in ax.spines.values():
            s.set_linewidth(0.4)

    def dp(ws, th):
        return [('cold', 'release-cold', 'release-mte-cold', ws, th),
                ('warm', 'release', 'release-mte', ws, th)]

    def lp(ws, tm, tc):
        p = [('MTE', 'release-dynamic', 'release-mte', ws, tm)]
        if tc:
            p.append(('CHERI', 'release-static', 'release-cheri', ws, tc))
        return p

    duck = [('SF 1', 1, '64', 3, dp('1', '64')),
            ('SF 10', 2, '1', 1, dp('10', '1')),
            ('SF 10', 2, '8', 2, dp('10', '8')),
            ('SF 10', 2, '64', 3, dp('10', '64')),
            ('SF 100', 3, '64', 3, dp('100', '64'))]
    lady = [('SF 10', 2, '1', 1, lp('10', '1', '1')),
            ('SF 10', 2, '8/2', 2, lp('10', '8', '2')),
            ('SF 10', 2, '64/4', 3, lp('10', '64', '4')),
            ('SF 100', 3, '64', 3, lp('100', '64', None))]

    TOP, BOTTOM, GLYPH_DY, TITLE_Y, KEY_Y = 0.79, 0.27, 0.062, 0.945, 0.035

    def build(db, title, panels, cols, name, height, show_key):
        fig = plt.figure(figsize=(figwidth_full, height))
        gs = _gridspec.GridSpec(1, len(panels), figure=fig, wspace=0.13,
                                left=0.058, right=0.995, top=TOP, bottom=BOTTOM)
        yr, first = [_math.inf, -_math.inf], None
        for i, (sf_lab, sf_n, th_lab, th_n, pairs) in enumerate(panels):
            ax = fig.add_subplot(gs[0, i], sharey=first)   # one y-axis per system
            if first is None:
                first = ax
            panel(ax, db, pairs, cols, show_ylab=(i == 0), yr=yr)
            bb = ax.get_position()
            fig.text((bb.x0 + bb.x1)/2, bb.y1 + GLYPH_DY,
                     f"{sf_lab}, {th_lab}\\,thr", ha='center', va='bottom',
                     fontsize=FS_CFG)
        # whole decades keep every decade labelled; the extra headroom is for
        # the in-panel overhead labels
        first.set_ylim(10**_math.floor(_math.log10(yr[0])),
                       10**_math.ceil(_math.log10(yr[1])) * 10**0.55)
        fig.text(0.004, (TOP+BOTTOM)/2, 'query time (log)', rotation=90,
                 va='center', fontsize=FS_AXIS)
        fig.text(0.5, TITLE_Y, r'\textbf{%s}' % title, ha='center', fontsize=FS_SYS)
        path = os.path.join(result_dir, name)
        fig.savefig(path, bbox_inches='tight', pad_inches=0.012)
        plt.close(fig)
        print(f"Saved {path}")
        return path

    return [build('duckdb', '(e) DuckDB (TPC-H)', duck, DUCK_COLS,
                  'dbms_sweep_duckdb.pdf', 1.30, show_key=False),
            build('ladybug', '(f) LadyBugDB (LDBC)', lady, LADY_COLS,
                  'dbms_sweep_ladybug.pdf', 1.45, show_key=True)]


def plot_dbms_sweep():
    """Build every row of the combined sweep figure and publish it to the paper."""
    rows = _sweep_rows()
    cbar = emit_sweep_colorbar(result_dir)
    produced = [write_ycsb_table(rows), cbar]
    produced.append(plot_sqlite_mysql_bars(rows))
    produced += plot_query_clouds(rows)

    paper_plots = os.path.join(dir_path, '..', 'paper_draft', 'plots')
    if os.path.isdir(paper_plots):
        for src in produced:
            _shutil.copy2(src, os.path.join(paper_plots, os.path.basename(src)))
        # the paper compiles from paper_draft/, so its copy references the
        # colorbar with a plots/-relative path rather than the results/ one
        write_ycsb_table(rows, cbar_dir='plots', out_dir=paper_plots)
        print(f"Published sweep figure to {paper_plots}")
