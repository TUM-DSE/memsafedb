#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from common import *
import matplotlib.patches as mpatches

def sort_workload(s):
    parts = s.split(' ')
    name = parts[0]
    threads = 0
    if len(parts) > 1:
        try:
            threads = int(parts[1])
        except ValueError:
            pass
    return (name, threads)

def format_val_time(val):
    if val > 1_000_000:
        return "{:.2f}ms".format(val/1_000_000)
    elif val > 10_000:
        return "{}µs".format(int(val/1000))
    elif val > 1_000:
        return "{:.2f}µs".format(val/1000)
    else:
        return "{}ns".format(int(val))

def load_data(host) -> pd.DataFrame:
    csv_path = os.path.join(result_dir, 'datastructures_{}.csv'.format(host))
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found.")
        return pd.DataFrame()

    df_tmp = pd.read_csv(csv_path)
    # Filter threads
    df_tmp = df_tmp[(df_tmp['host'] == 'ace') & ((df_tmp['nthreads'] == 1) | (df_tmp['nthreads'] == 4)) |
                    (df_tmp['host'] == 'eliza') & ((df_tmp['nthreads'] == 1) | (df_tmp['nthreads'] == 16) | (df_tmp['nthreads'] == 192))]
    
    # Filter ignored benchmarks
    ignored = ['readmodifywrite', 'YCSB-A', 'YCSB-B', 'YCSB-C', 'YCSB-D', 'YCSB-E', 'YCSB-F']
    df_tmp = df_tmp[~df_tmp['name'].isin(ignored)]
    
    df_tmp['memsafe'] = df_tmp['arch'].map({'aarch64': 'unsafe', 'mte': 'safe', 'cheri': 'safe'})
    df_tmp = df_tmp[[x for x in df_tmp.columns if x != 'nb_ops']]
    
    df = df_tmp.copy()
    # Create key for pivoting
    df['fkey'] = df[[x for x in df.columns if x not in ['latency', 'arch', 'memsafe']]].apply(lambda x: '-'.join(x.astype(str).values), axis=1)
    df['expe'] = df['host'].map({'eliza': 'MTE', 'ace': 'CHERI'})
    
    # Calculate overhead
    agg = df.pivot(index='fkey', columns='memsafe', values='latency')
    if 'safe' not in agg.columns or 'unsafe' not in agg.columns:
        return pd.DataFrame()
        
    agg['overhead'] = agg['safe'] / agg['unsafe']
    agg = agg.reset_index()
    
    # Merge back to get metadata
    meta = df[[x for x in df.columns if x not in ['latency', 'memsafe', 'arch']]].drop_duplicates()
    joined = pd.merge(agg[['fkey', 'overhead', 'safe', 'unsafe']], meta, on='fkey', how='inner')
    
    # Renaming
    joined['name'] = joined['name'].replace({"readmodifywrite": "rmw", "queue_bench": "queue"})
    joined = joined[joined['nthreads'] != 16] # Filter out 16T explicitly as in original
    joined['nthreads_str'] = joined['nthreads'].replace({1: '', 4: 'SMT', 192: 'SMT'}).astype(str)
    
    # Create display bench name (e.g. "bst SMT")
    joined['bench'] = joined.apply(lambda row: f"{row['name']} {row['nthreads_str']}".strip(), axis=1)
    
    return joined

def compute_std(overhead):
    std_overhead = overhead.groupby(['system', 'bench', 'expe'])['overhead'].agg(['mean', 'std', 'max', 'min']).reset_index()
    std_overhead['err_max'] = std_overhead['mean'] + std_overhead['std']
    std_overhead['err_min'] = std_overhead['mean'] - std_overhead['std']
    return std_overhead

def plot_datastructures(df):
    if df.empty:
        print("No data loaded.")
        return

    systems = sorted(df['system'].unique())
    # Reorder to put 'art' and 'queue' in the first column (indices 0 and 3)
    # Remaining systems fill indices 1, 2, 4, 5
    priority = ['art', 'queue']
    others = [s for s in systems if s not in priority]
    
    ordered_systems = []
    # Index 0: art
    ordered_systems.append('art' if 'art' in systems else (others.pop(0) if others else ''))
    # Index 1: other
    ordered_systems.append(others.pop(0) if others else '')
    # Index 2: other
    ordered_systems.append(others.pop(0) if others else '')
    # Index 3: queue
    ordered_systems.append('queue' if 'queue' in systems else (others.pop(0) if others else ''))
    # Index 4: other
    ordered_systems.append(others.pop(0) if others else '')
    # Index 5: other
    ordered_systems.append(others.pop(0) if others else '')
    
    # Clean empty placeholders if less than 6 systems
    ordered_systems = [s for s in ordered_systems if s]
    
    n_systems = len(ordered_systems)
    if n_systems > 6:
        print(f"Warning: {n_systems} systems found, but grid is 2x3. Some might be cut off or squeezed.")
    
    fig = plt.figure(figsize=(figwidth_full, 2* fig_height))
    # Adjust width ratios: first column narrower, others wider
    gs = fig.add_gridspec(2, 3, hspace=0.6, wspace=0.3, width_ratios=[0.85, 1.1, 1.1])
    
    axes = []
    for i in range(2):
        for j in range(3):
            axes.append(fig.add_subplot(gs[i, j]))

    palette_map = {'MTE': MTE_COLOR, 'CHERI': CHERI_COLOR}
    hatch_map = {'MTE': MTE_HATCH, 'CHERI': CHERI_HATCH}



    for i, sys in enumerate(ordered_systems):
        if i >= 6: break
        ax = axes[i]
        
        sys_data = df[df['system'] == sys].copy()
        
        bench_order = sorted(sys_data['bench'].unique(), key=sort_workload)
        
        sns.barplot(
            ax=ax,
            data=sys_data,
            x='bench',
            y='overhead',
            hue='expe',
            order=bench_order,
            hue_order=['MTE', 'CHERI'],
            palette=palette_map,
            edgecolor='black',
            errorbar='sd',
            width=0.8
        )
        
        if len(ax.containers) == 2:
            for bar in ax.containers[0]:
                bar.set_hatch(MTE_HATCH)
                bar.set_edgecolor('black')
            for bar in ax.containers[1]:
                bar.set_hatch(CHERI_HATCH)
                bar.set_edgecolor('black')
        else:
            pass

        # Calculate stats for annotations and ylim
        stats = sys_data.groupby(['bench', 'expe'])['overhead'].agg(['mean', 'std']).reset_index()
        stats['std'] = stats['std'].fillna(0)
        
        annot_max_y = 0

        hues = ['MTE', 'CHERI']
        for container_idx, container in enumerate(ax.containers):
            if container_idx >= len(hues): break
            expe = hues[container_idx]
            for j, bar in enumerate(container):
                if j >= len(bench_order): break
                bench = bench_order[j]
                
                row = stats[(stats['bench'] == bench) & (stats['expe'] == expe)]
                if row.empty: continue
                
                mean = row['mean'].values[0]
                std = row['std'].values[0]
                
                if pd.isna(mean) or mean == 0: continue
                
                # Position above bar or error bar
                y_pos = mean + std
                annot_max_y = max(annot_max_y, y_pos)
                
                pct = (mean - 1) * 100
                if abs(pct) < 1: # Show 0% if very small
                    txt = f"${pct:+.0f}\\%$"
                else:
                    txt = f"${pct:+.0f}\\%$"

                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    y_pos + 0.01, # Padding
                    txt,
                    ha='center', va='bottom',
                    fontsize=FONTSIZE_ANNOTATION
                )

        ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1, alpha=0.7, zorder=0)
        
        # ax.set_title(sys, fontsize=FONTSIZE_TITLE, fontweight='bold', pad=15)
        caption = f"({chr(97+i)}) {sys}."
        # Use simple heuristic for capitalization if mostly lowercase
        if sys.islower():
            caption = f"({chr(97+i)}) {sys.title()}."
        if sys == 'art': caption = f"({chr(97+i)}) ART."
        
        ax.text(0.5, -0.35, caption, transform=ax.transAxes, ha='center', va='top', fontsize=FONTSIZE_TITLE+2, fontweight='bold')
        
        ax.set_xlabel('')
        ax.set_ylabel('Normalized Runtime' if i % 3 == 0 else '', fontsize=FONTSIZE_AXIS_LABEL)
        
        ax.tick_params(axis='x', labelsize=FONTSIZE_TICK_LABEL)
        ax.tick_params(axis='y', labelsize=FONTSIZE_TICK_LABEL)
        
        # Adjust Y limits based on max annotation height
        ax.set_ylim(0.95, max(1.1, annot_max_y * 1.15))
        
        if ax.get_legend():
            ax.get_legend().remove()

        baseline_agg = sys_data.groupby(['bench', 'expe'])['unsafe'].mean()
        
        y_txt = -0.03
        width = 0.8
        n_hues = 2
        
        bar_width = width / n_hues
        offsets = {'MTE': -bar_width*2/3, 'CHERI': bar_width*2/3}
        
        for idx, bench in enumerate(bench_order):
            for expe in ['MTE', 'CHERI']:
                if (bench, expe) in baseline_agg.index:
                    val = baseline_agg[(bench, expe)]
                    txt = format_val_time(val)
                    
                    x_pos = idx + offsets[expe]
                    
                    ax.text(
                        x_pos, y_txt, 
                        txt, 
                        ha='center', va='top', 
                        transform=ax.get_xaxis_transform(),
                        color='gray', 
                        fontsize=FONTSIZE_TICK_LABEL-2 # Slightly smaller to fit
                    )
        
        # "Baseline:" label
        if i % 3 == 0:
            ax.text(
                -0.6, y_txt, 
                "Baseline:", 
                ha='right', va='top', 
                transform=ax.get_xaxis_transform(), 
                color='gray', 
                fontsize=FONTSIZE_TICK_LABEL-1
            )

    # Clean empty axes
    for k in range(len(systems), 6):
        axes[k].set_visible(False)

    # Global Legend
    legend_patches = [
        mpatches.Patch(facecolor=MTE_COLOR, hatch=MTE_HATCH, label='MTE', edgecolor='black'),
        mpatches.Patch(facecolor=CHERI_COLOR, hatch=CHERI_HATCH, label='CHERI', edgecolor='black')
    ]
    
    fig.legend(
        handles=legend_patches,
        loc='upper center',
        bbox_to_anchor=(0.5, 0.98),
        ncol=2,
        fontsize=FONTSIZE_LEGEND,
        frameon=True
    )
    
    fig.text(0.5, 0.915, lower_better_str, ha='center', va='top', color='blue', fontsize=FONTSIZE_TITLE)
    
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    output_path = os.path.join(result_dir, "datastructures_all.pdf")
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    plt.close()
    print("Generated datastructures_all.pdf")

def main():
    mte_df = load_data('mte')
    cheri_df = load_data('cheri')
    
    if mte_df.empty and cheri_df.empty:
        print("No data found.")
        return
        
    full_df = pd.concat([mte_df, cheri_df], ignore_index=True)
    plot_datastructures(full_df)

if __name__ == "__main__":
    main()
