#!/usr/bin/env python3
import matplotlib.pyplot as plt
import pandas as pd
import os
import matplotlib.patches as patches
from common import *


def filter_dbms(df, metric_col):
    """Filter out DBMS that have 0 memory safety bugs across the whole dataset."""
    valid_dbs = df.groupby('db')[metric_col].sum()
    valid_dbs = valid_dbs[valid_dbs > 0].index
    return df[df['db'].isin(valid_dbs)].copy()


def plot_combined(output_prefix="bug_"):
    """
    Single figure containing:
      Left (ax1)   – CVE vs Bug memory-safety count (dual y-axis lines)
      Middle (ax2) – stacked bar (per year, per DB) + secondary % line
      Right (ax3 & ax4) – Pie charts for Total Bugs and Total CVEs
    Saved as a single PDF with width figwidth_full and height fig_height.
    """
    bug_csv = os.path.join(result_dir, "bug_results_by_year.csv")
    cve_csv = os.path.join(result_dir, "cve_results_by_year.csv")

    if not os.path.exists(bug_csv) or not os.path.exists(cve_csv):
        print("Missing CSV files.")
        return

    # ── Load & clean bug data ────────────────────────────────────────────────
    df_bug_raw = pd.read_csv(bug_csv)
    df_bug_raw = df_bug_raw[df_bug_raw['year'] != 2026]
    df_bug_raw['memory_safety_bugs'] = df_bug_raw['memory_safety_bugs_llms']
    df_bug_raw['total_bugs'] = df_bug_raw[['total_bugs', 'memory_safety_bugs']].max(axis=1)
    
    df_cve_raw = pd.read_csv(cve_csv)
    df_cve_raw = df_cve_raw[df_cve_raw['year'] != 2026]
    df_cve_raw['total_cves'] = df_cve_raw[['total_bugs', 'memory_safety_bugs_llms']].max(axis=1)

    df_bug = filter_dbms(df_bug_raw, 'memory_safety_bugs')
    df_cve = filter_dbms(df_cve_raw, 'memory_safety_bugs_llms')

    if df_bug.empty:
        print("No memory safety bug data to plot.")
        return

    # ── Bar data (Right) ────────────────────────────────────────────────────
    pivot_df = df_bug.pivot_table(
        index='year', columns='db',
        values='memory_safety_bugs', aggfunc='sum', fill_value=0
    )
    bug_years = pivot_df.index.tolist()
    dbs = pivot_df.columns.tolist()

    yearly = df_bug.groupby('year')[['total_bugs', 'memory_safety_bugs']].sum()
    yearly = yearly.reindex(bug_years, fill_value=0)
    yearly['pct'] = (yearly['memory_safety_bugs'] / yearly['total_bugs'].replace(0, np.nan)) * 100
    pct_values = yearly['pct'].values
    max_pct = float(np.nanmax(pct_values))

    bar_colors = sns.color_palette("tab20", n_colors=len(dbs))

    # ── Line data (Middle) ─────────────────────────────────────────────────────
    cve_yearly = df_cve.groupby('year')['memory_safety_bugs_llms'].sum()
    bug_yearly = df_bug.groupby('year')['memory_safety_bugs'].sum()
    cve_yearly = cve_yearly[cve_yearly > 0]
    bug_yearly = bug_yearly[bug_yearly > 0]
    all_years = sorted(set(cve_yearly.index) | set(bug_yearly.index))

    color_map = dict(zip(dbs, bar_colors))

    # ── Figure ───────────────────────────────────────────────────────────────
    fig, (ax_line, ax_bar) = plt.subplots(
        1, 2, figsize=(figwidth_half, fig_height)
    )

    # ════════════ Top: CVE vs Bug lines ════════════
    #ax_line.set_xlabel('Year', fontsize=FONTSIZE_AXIS_LABEL)
    ax_line.set_ylabel('Memory Safety CVEs', fontsize=FONTSIZE_AXIS_LABEL)
    ax_line.plot(cve_yearly.index, cve_yearly.values,
                 color='black', marker='X', markersize=2, linestyle='--', linewidth=1, label='CVEs')
    if len(cve_yearly) >= 2:
        ax_line.annotate('CVEs', xy=(cve_yearly.index[-3], cve_yearly.iloc[-3]), xytext=(0, -5),
                         textcoords='offset points', ha='center', va='top', fontsize=FONTSIZE_TICK_LABEL)
    ax_line.tick_params(axis='y', color='black', labelsize=FONTSIZE_TICK_LABEL - 1, pad=1, length=2)
    ax_line.set_ylim(bottom=0)

    ax_line_r = ax_line.twinx()
    ax_line_r.plot(bug_yearly.index, bug_yearly.values,
                   color='black', marker='o', markersize=2, linestyle='-', linewidth=1, label='Bugs')
    if len(bug_yearly) >= 2:
        ax_line_r.annotate('Bugs', xy=(bug_yearly.index[3], bug_yearly.iloc[3]), xytext=(0, 8),
                           textcoords='offset points', ha='center', va='bottom', fontsize=FONTSIZE_TICK_LABEL)
    ax_line_r.tick_params(axis='y', color='black', labelsize=FONTSIZE_TICK_LABEL - 1, pad=1, length=2)
    
    # Force perfectly aligned scale for both 'Bugs' axes
    y_max_bugs = bug_yearly.max() * 1.05
    ax_line_r.set_ylim(0, y_max_bugs)

    ax_line.set_xticks(all_years)
    ax_line.set_yticks(np.arange(0, cve_yearly.max() + 1, 10))
    ax_line_r.set_yticks(np.arange(0, bug_yearly.max() + 1, 250))
    if len(all_years) > 5:
        stride = 5
        ax_line.set_xticklabels(
            [str(y) if i % stride == 0 else '' for i, y in enumerate(all_years)],
            fontsize=FONTSIZE_TICK_LABEL
        )
        ax_line.tick_params(axis='x', length=2)
    else:
        ax_line.set_xticklabels([str(y) for y in all_years], fontsize=FONTSIZE_TICK_LABEL, rotation=45)

    ax_line.set_title(r"\textbf{(a) Number of bugs/CVEs over time}", fontsize=FONTSIZE_TITLE, y=-0.35)


    # ════════════ Bottom: Stacked bars ════════════
    bottom = np.zeros(len(bug_years))
    for i, db in enumerate(dbs):
        values = pivot_df[db].values
        ax_bar.bar(bug_years, values, bottom=bottom, label=db,
                   color=bar_colors[i], zorder=2)
        bottom += values

    #ax_bar.set_xlabel('Year', fontsize=FONTSIZE_AXIS_LABEL)
    ax_bar.set_ylabel('Memory Safety Bugs', fontsize=FONTSIZE_AXIS_LABEL)
    ax_bar.set_xticks(bug_years)
    ax_bar.set_yticks(np.arange(0, bug_yearly.max() + 1, 250))
    ax_bar.tick_params(axis='y', labelsize=FONTSIZE_TICK_LABEL - 1, pad=1, length=2)
    ax_bar.set_ylim(0, y_max_bugs)

    if len(bug_years) > 5:
        stride = 5
        ax_bar.set_xticklabels(
            [str(y) if i % stride == 0 else '' for i, y in enumerate(bug_years)],
            fontsize=FONTSIZE_TICK_LABEL
        )
        ax_bar.tick_params(axis='x', length=2)
    else:
        ax_bar.set_xticklabels([str(y) for y in bug_years], fontsize=FONTSIZE_TICK_LABEL, rotation=45)

    ax_bar_r = ax_bar.twinx()
    ax_bar_r.plot(bug_years, pct_values, color="darkgrey", marker='o',
                  markersize=2, linewidth=1, label=r'\% Memory Safety', zorder=3)
    if len(bug_years) >= 2:
        ax_bar_r.annotate('\\% Memory\nSafety', xy=(bug_years[2], pct_values[2]), xytext=(0, 13),
                          textcoords='offset points', ha='center', va='center', fontsize=FONTSIZE_TICK_LABEL, color='darkgrey')
    ax_bar_r.set_ylabel(r'\% of Memory Safety Bugs', fontsize=FONTSIZE_AXIS_LABEL)
    ax_bar_r.set_ylim(0, max_pct * 1.15)

    h1, l1 = ax_bar.get_legend_handles_labels()
    h2, l2 = ax_bar_r.get_legend_handles_labels()
    ax_bar_r.set_yticks([0, 5, 10, 15])
    ax_bar_r.tick_params(axis='y', labelsize=FONTSIZE_TICK_LABEL - 1, pad=1, length=2)

    ax_bar.set_title(r"\textbf{(b) Breakdown per database system}", fontsize=FONTSIZE_TITLE, y=-0.35)


    # ════════════ Global Legend ════════════
    import matplotlib.lines as mlines
    
    db_name_map = {
        'clickhouse': 'ClickHouse',
        'duckdb': 'DuckDB',
        'leveldb': 'LevelDB',
        'mariadb': 'MariaDB',
        'memcached': 'Memcached',
        'mongodb': 'MongoDB',
        'mysql': 'MySQL',
        'postgresql': 'PostgreSQL',
        'redis': 'Redis',
        'redshift': 'Redshift',
        'rocksdb': 'RocksDB',
        'sqlite': 'SQLite'
    }
    
    legend_handles = [patches.Patch(facecolor=color_map[db], edgecolor='black', label=db_name_map.get(db, db)) for db in dbs]

    # Place single global legend stretching above the entire figure
    fig.legend(handles=legend_handles, loc='lower center', bbox_to_anchor=(0.5, 1.0), 
               ncol=7, fontsize=FONTSIZE_LEGEND, columnspacing=0.5,
               handlelength=1.0, handleheight=1.0)

    plt.tight_layout(pad=0.01, w_pad=0.12)
    output_filename = f"{output_prefix}combined.pdf"
    plt.savefig(os.path.join(result_dir, output_filename), format='pdf', bbox_inches='tight', pad_inches=0.01)
    print(f"Generated {output_filename}")


def print_stats_table():
    bug_csv = os.path.join(result_dir, "bug_results_by_year.csv")
    cve_csv = os.path.join(result_dir, "cve_results_by_year.csv")

    if not os.path.exists(bug_csv) or not os.path.exists(cve_csv):
        print("Missing CSV files for stats table.")
        return

    df_bug = pd.read_csv(bug_csv)
    df_cve = pd.read_csv(cve_csv)

    # Exclude incomplete year
    df_bug = df_bug[df_bug['year'] != 2026]
    df_cve = df_cve[df_cve['year'] != 2026]

    # Bug aggregates per year
    df_bug['memory_safety_bugs'] = df_bug['memory_safety_bugs_llms']
    df_bug['total_bugs'] = df_bug[['total_bugs', 'memory_safety_bugs']].max(axis=1)
    bug_yearly = df_bug.groupby('year')[['total_bugs', 'memory_safety_bugs']].sum()
    bug_yearly.columns = ['total_bugs', 'ms_bugs']

    # CVE aggregates per year
    cve_yearly = df_cve.groupby('year')[['total_bugs', 'memory_safety_bugs_llms']].sum()
    cve_yearly.columns = ['total_cves', 'ms_cves']

    # Join on year
    table = bug_yearly.join(cve_yearly, how='outer').fillna(0).astype(int)
    table = table.sort_index()

    # Compute percentages
    table['bug_pct']  = (table['ms_bugs'] / table['total_bugs'].replace(0, pd.NA) * 100).round(1)
    table['cve_pct']  = (table['ms_cves'] / table['total_cves'].replace(0, pd.NA) * 100).round(1)

    # Print
    header = f"{'Year':>6}  {'Bugs':>8}  {'MS Bugs':>8}  {'Bug %':>7}  {'CVEs':>8}  {'MS CVEs':>8}  {'CVE %':>7}"
    sep    = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for year, row in table.iterrows():
        bug_pct_str = f"{row['bug_pct']:.1f}" if pd.notna(row['bug_pct']) else "N/A"
        cve_pct_str = f"{row['cve_pct']:.1f}" if pd.notna(row['cve_pct']) else "N/A"
        print(f"{int(year):>6}  {int(row['total_bugs']):>8}  {int(row['ms_bugs']):>8}  "
              f"{bug_pct_str:>7}  {int(row['total_cves']):>8}  {int(row['ms_cves']):>8}  "
              f"{cve_pct_str:>7}")
    print(sep)


def run_analysis():
    print_stats_table()
    plot_combined()

if __name__ == "__main__":
    run_analysis()