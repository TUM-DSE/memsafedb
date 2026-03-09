import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from common import (
    result_dir, figwidth_half, figwidth_full, fig_height, FONTSIZE, 
    MTE_COLOR, MTE_HATCH, CHERI_COLOR, CHERI_HATCH,
    higher_better_str, lower_better_str,
    FONTSIZE_AXIS_LABEL, FONTSIZE_LEGEND, FONTSIZE_TITLE, FONTSIZE_ANNOTATION
)

def main():
    import glob
    dbms_rss_dir = os.path.join(result_dir, "dbms_rss")
    all_files = glob.glob(os.path.join(dbms_rss_dir, "*_mem_footprint.csv"))
    
    systems = []
    mte_data = [] 
    cheri_data = [] 
    
    for f in sorted(all_files):
        sys_name = os.path.basename(f).replace('_mem_footprint.csv', '')
        df = pd.read_csv(f)
        
        rss_col = 'peak_rss_bytes' if 'peak_rss_bytes' in df.columns else 'rss_bytes'
        
        if 'query' in df.columns:
            group_col = 'query'
        else:
            group_col = 'workload'
            
        if 'phase' in df.columns:
            df['group_id'] = df['phase'] + "_" + df['query'].astype(str)
            group_col = 'group_id'
            
        groups = df[group_col].unique()
        
        sys_mte = []
        sys_cheri = []
        for g in groups:
            df_g = df[df[group_col] == g]
            
            try:
                dyn_val = df_g[df_g['variant'] == 'dynamic'][rss_col].values[0]
                mte_val = df_g[df_g['variant'] == 'mte'][rss_col].values[0]
                
                if dyn_val > 0:
                    mte_oh = mte_val / dyn_val
                    if pd.notna(mte_oh):
                        sys_mte.append(mte_oh)
            except IndexError:
                pass
                
            try:
                static_val = df_g[df_g['variant'] == 'static'][rss_col].values[0]
                cheri_val = df_g[df_g['variant'] == 'cheri'][rss_col].values[0]
                if static_val > 0:
                    cheri_oh = cheri_val / static_val
                    if pd.notna(cheri_oh):
                        sys_cheri.append(cheri_oh)
            except IndexError:
                pass
                
        name_map = {
            'duckdb': 'DuckDB',
            'ladybug': 'LadyBugDB',
            'leveldb': 'LevelDB',
            'mysql': 'MySQL',
            'redis': 'Redis',
            'sqlite': 'SQLite'
        }
        systems.append(name_map.get(sys_name.lower(), sys_name.title()))
        mte_data.append(sys_mte if len(sys_mte) > 0 else [np.nan])
        cheri_data.append(sys_cheri if len(sys_cheri) > 0 else [np.nan])
        
    if not systems:
        print("No footprint data found.")
        return

    desired_order = ['Redis', 'LevelDB', 'MySQL', 'SQLite', 'DuckDB', 'LadyBugDB']
    
    ordered_systems = []
    ordered_mte = []
    ordered_cheri = []
    
    for des in desired_order:
        if des in systems:
            idx = systems.index(des)
            ordered_systems.append(systems[idx])
            ordered_mte.append(mte_data[idx])
            ordered_cheri.append(cheri_data[idx])
            
    for idx, sys in enumerate(systems):
        if sys not in ordered_systems:
            ordered_systems.append(sys)
            ordered_mte.append(mte_data[idx])
            ordered_cheri.append(cheri_data[idx])
            
    systems = ordered_systems
    mte_data = ordered_mte
    cheri_data = ordered_cheri

    fig, ax = plt.subplots(figsize=(figwidth_half, fig_height))
    
    x = np.arange(len(systems))
    width = 0.35
    
    mte_plot_data = []
    mte_positions = []
    mte_errors = []
    
    cheri_plot_data = []
    cheri_positions = []
    cheri_errors = []
    
    def compute_ci(data):
        valid_data = [d for d in data if not np.isnan(d)]
        if len(valid_data) > 1:
            return 1.96 * np.nanstd(valid_data, ddof=1) / np.sqrt(len(valid_data))
        return 0
    
    for i in range(len(systems)):
        has_cheri = not (len(cheri_data[i]) == 1 and np.isnan(cheri_data[i][0]))
        has_mte = not (len(mte_data[i]) == 1 and np.isnan(mte_data[i][0]))
        
        c_val = np.nanmean(cheri_data[i]) if has_cheri else 0
        c_err = compute_ci(cheri_data[i]) if has_cheri else 0
        
        m_val = np.nanmean(mte_data[i]) if has_mte else 0
        m_err = compute_ci(mte_data[i]) if has_mte else 0
        
        if has_cheri:
            cheri_plot_data.append(c_val)
            cheri_positions.append(x[i] - width/2)
            cheri_errors.append(c_err)
        else:
            ax.plot(x[i] - width/2, 0.7, clip_on=False, marker='x', color='red', markersize=4, zorder=5)
            
        if has_mte:
            mte_plot_data.append(m_val)
            mte_positions.append(x[i] + width/2)
            mte_errors.append(m_err)
            
    # We want CHERI and MTE side by side bar plots
    rects1 = None
    rects2 = None
    
    if cheri_plot_data:
        rects1 = ax.bar(cheri_positions, cheri_plot_data, width=width*0.8, yerr=cheri_errors, error_kw=dict(lw=1, capsize=3, capthick=1),
                        color=CHERI_COLOR, hatch=CHERI_HATCH, edgecolor='black', zorder=3)
                                 
    if mte_plot_data:
        rects2 = ax.bar(mte_positions, mte_plot_data, width=width*0.8, yerr=mte_errors, error_kw=dict(lw=1, capsize=3, capthick=1),
                        color=MTE_COLOR, hatch=MTE_HATCH, edgecolor='black', zorder=3)
        
    def autolabel(rects, errs):
        if not rects:
            return
        for rect, err in zip(rects, errs):
            height = rect.get_height()
            if height > 0:
                val_str = f'{height:.2f}'.rstrip('0').rstrip('.')
                if not val_str:
                    val_str = '0'
                ax.annotate(f'{val_str}x',
                            xy=(rect.get_x() + rect.get_width() / 2, height + err),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=FONTSIZE_ANNOTATION+1)

    autolabel(rects1, cheri_errors)
    autolabel(rects2, mte_errors)
    
    # Add headroom for labels
    all_ohs = []
    for h, e in zip(cheri_plot_data, cheri_errors):
        all_ohs.append(h + e)
    for h, e in zip(mte_plot_data, mte_errors):
        all_ohs.append(h + e)
        
    ax.set_ylim(0.7, 1.9)
                           
    ax.set_ylabel('Normalized memory footprint', fontsize=FONTSIZE_AXIS_LABEL)
    ax.set_xticks(x)
    ax.set_xticklabels(systems, fontsize=FONTSIZE_AXIS_LABEL)
    
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=CHERI_COLOR, hatch=CHERI_HATCH, edgecolor='black', label='CHERI'),
        Patch(facecolor=MTE_COLOR, hatch=MTE_HATCH, edgecolor='black', label='MTE')
    ]
    ax.legend(handles=legend_elements, loc='upper right', frameon=True, fontsize=FONTSIZE_LEGEND)
    
    fig.text(0.55, 0.99, lower_better_str, ha='center', va='top', color='blue', fontsize=FONTSIZE_TITLE)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7, zorder=0)
    fig.tight_layout()
    
    output_path = os.path.join(result_dir, "memory_overhead.pdf")
    plt.savefig(output_path, bbox_inches='tight')
    plt.close(fig)
    print(f"Plot saved to {output_path}")

if __name__ == "__main__":
    main()
