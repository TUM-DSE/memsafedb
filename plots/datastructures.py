#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from common import *

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
    df_tmp = pd.read_csv(result_dir+'/datastructures_{}.csv'.format(host))
    # TODO: this selects only 1, 16 and 192 threads for MTE and 1, 4 for CHERI
    df_tmp = df_tmp[(df_tmp['host'] == 'ace') & ((df_tmp['nthreads'] == 1) | (df_tmp['nthreads'] == 4)) |
                    (df_tmp['host'] == 'eliza') & ((df_tmp['nthreads'] == 1) | (df_tmp['nthreads'] == 16) | (df_tmp['nthreads'] == 192))]
    df_tmp = df_tmp[(df_tmp['name'] != 'readmodifywrite') & (df_tmp['name'] != 'YCSB-A') & (df_tmp['name'] != 'YCSB-B') & (df_tmp['name'] != 'YCSB-C') & (df_tmp['name'] != 'YCSB-D') & (df_tmp['name'] != 'YCSB-E') & (df_tmp['name'] != 'YCSB-F')]
    df_tmp['memsafe'] = df_tmp['arch'].map({'aarch64': 'unsafe', 'mte': 'safe', 'cheri': 'safe'})
    df_tmp = df_tmp[[x for x in df_tmp.columns if x != 'nb_ops']]
    df = df_tmp.copy()
    df['fkey'] = df[[x for x in df.columns if x not in ['latency', 'arch', 'memsafe']]].apply(lambda x: '-'.join(x.astype(str).values), axis=1)
    df['expe'] = df['host'].map({'eliza': 'MTE', 'ace': 'CHERI'})
    df = df[[ x for x in df.columns if x not in ['arch']]]
    agg = df.pivot(index='fkey', columns='memsafe', values='latency')
    agg['overhead'] = agg['safe'] / agg['unsafe']
    agg = agg.reset_index()
    df = df[[ x for x in df.columns if x not in ['mean', 'memsafe']]].drop_duplicates()
    joined = pd.merge(agg, df, on='fkey', how='inner')
    joined['name'] = joined['name'].replace({"readmodifywrite": "rmw", "queue_bench": "queue"})
    #joined['nthreads'] = joined['nthreads'].replace({1: '', 4: '4T', 8: '8T', 16: '16T', 32: '32T', 64: '64T', 96: '96T'})
    joined = joined[joined['nthreads'] != 16]
    joined['nthreads'] = joined['nthreads'].replace({1: '', 4: 'SMT', 192: 'SMT'})
    joined['bench'] = joined['name'] + ' ' + joined['nthreads'].astype(str)
    joined = joined[[x for x in joined.columns if x not in ['fkey', 'name', 'nthreads', 'latency']]]
    """all_res = df_tmp
    all_res['name'] = all_res['name'].replace({"readmodifywrite": "rmw", "queue_bench": "queue"})
    all_res['nthreads'] = all_res['nthreads'].replace({1: '', 4: '4', 8: '8', 16: '16', 32: '32', 64: '64', 96: '96'})
    all_res['bench'] = all_res['name'] + ' ' + all_res['nthreads'].astype(str)
    all_res = all_res[[x for x in all_res.columns if x not in ['name', 'nthreads', 'host', 'arch']]]"""
    return joined

def compute_std(overhead):
    std_overhead = overhead.groupby([ x for x in overhead.columns if x not in ['repetition', 'safe', 'unsafe', 'overhead']])['overhead'].agg(['mean', 'std']).reset_index()
    std_overhead['max'] = std_overhead['mean'] + std_overhead['std']
    std_overhead['min'] = std_overhead['mean'] - std_overhead['std']
    return std_overhead

def main():
    expes = ['MTE', 'CHERI']
    colors = ["tab:green", "tab:blue"]
    
    for cid, xp in zip(range(len(expes)), expes):
        overhead = load_data(xp.lower())
        fig, ax = plt.subplots(3, 2, figsize=(figwidth_full, fig_height*3))
        systems = overhead['system'].unique()
        std_overhead = compute_std(overhead)
        grouped_overhead = std_overhead.groupby([x for x in std_overhead.columns if x not in ['bench', 'mean', 'std', 'max', 'min']])['mean'].agg('mean').reset_index()
        for i, sys in zip(range(len(systems)), systems):
            cur_ax = ax[int(i/2)][i%2]
            cur_ax.axhline(y=1, color='red', zorder=0)
            sorted_confs = sorted(overhead[overhead['system'] == sys]['bench'].unique(), key = sort_workload)
            sns.barplot(ax=cur_ax, data=overhead[overhead['system'] == sys], x = "bench", y = "overhead", order=sorted_confs, edgecolor="black", errorbar=("sd"), color=colors[cid])
           
            for p in cur_ax.patches:
                height = p.get_height()
                y_pos = height
                if xp == "MTE":
                    if sys == "queue":
                        y_pos = 1.15  
                cur_ax.text(x=p.get_x() + p.get_width() / 2,
                        y = y_pos, s=f'{height:.2f}',
                        ha='center', va='bottom',
                        fontsize=FONTSIZE-2)
            cur_ax.set_xlabel("")
            rotation = 0
            if len(overhead[overhead['system'] == sys]['bench'].unique()) > 6:
                if len(overhead[overhead['system'] == sys]['bench'].unique()) > 15:
                    cur_ax.tick_params(axis='x', labelrotation=90)
                    rotation = 90
                else:
                    cur_ax.tick_params(axis='x', labelrotation=45)
                    rotation = 45
            else:
                cur_ax.tick_params(axis='x', pad=5)
            cur_ax.set_ylabel("Normalized\nlatency", fontsize=FONTSIZE)
            max_val = std_overhead[(std_overhead.system == sys)]['max'].max()
            cur_ax.set_ylim(0.8, max_val*1.2)
            cur_ax.set_xticklabels(cur_ax.get_xticklabels(), size=FONTSIZE-1)
            cur_ax.set_yticklabels(cur_ax.get_yticklabels(), size=FONTSIZE)
            baseline_agg = overhead[overhead['system'] == sys].groupby([ x for x in overhead.columns if x not in ['repetition', 'safe', 'unsafe', 'overhead']])['unsafe'].agg(['mean', 'std']).reset_index()
            baseline_val = baseline_agg[baseline_agg['system'] == sys].sort_values(by="bench", key=lambda x: natsorted(baseline_agg[baseline_agg['system'] == sys]['bench'], alg=ns.NUMAFTER))['mean']
            for i, tick in enumerate(cur_ax.get_xticklabels()):
                if i == 0:
                    cur_ax.text(x=i-0.5, y=-0.08, s="Baseline:", ha='right', va='top', transform=cur_ax.get_xaxis_transform(), fontsize=FONTSIZE-1, color='gray')
                if baseline_val[i] > 1_000_000:
                    val = "{:.2f}ms".format(baseline_val[i]/1_000_000)
                elif baseline_val[i] > 10_000:
                    val = "{}µs".format(int(baseline_val[i]/1000))
                elif baseline_val[i] > 1_000:
                    val = "{:.2f}µs".format(baseline_val[i]/1000)
                else:
                    val = "{}ns".format(int(baseline_val[i]))
                pos_y = -0.1
                cur_ax.text(x=i, y=pos_y, s=val,
                            ha='center', va='top', transform=cur_ax.get_xaxis_transform(),
                            color='gray', fontsize=FONTSIZE-2)
            #ax[int(i/2)][i%2].get_legend().remove()
            cur_ax.set_title(sys+" (mean: x{:.2f})".format(grouped_overhead[grouped_overhead['system'] == sys]['mean'].to_list()[0]))

        plt.tight_layout()
        plt.suptitle(lower_better_str, color='blue')
        plt.subplots_adjust(wspace=0.25)
        plt.savefig(os.path.join(result_dir, "datastructures_{}.pdf".format(xp)), format="pdf", pad_inches=0, bbox_inches="tight")

    # Per-system plot
    overhead = pd.concat([load_data("mte"), load_data("cheri")])
    systems = overhead['system'].unique()
    std_overhead = compute_std(overhead)
    grouped_overhead = std_overhead.groupby([x for x in std_overhead.columns if x not in ['bench', 'mean', 'std', 'max', 'min']])['mean'].agg('mean').reset_index()
    for sys in systems:
        fig, ax = plt.subplots(1, 1, figsize=(figwidth_half, fig_height))
        cur_ax = ax
        cur_ax.axhline(y=1, color='red', zorder=0)
        sorted_confs = sorted(overhead[overhead['system'] == sys]['bench'].unique(), key = sort_workload)
        sns.barplot(ax=cur_ax, data=overhead[overhead['system'] == sys], x = "bench", y = "overhead", order=sorted_confs, hue="expe", palette = colors, edgecolor="black", errorbar=("sd"))
        for i, p in zip(range(len(cur_ax.patches)), cur_ax.patches):
            if p.get_x() == 0 and p.get_y() == 0:
               continue
            hatch = hatch_def[0] if i < len(cur_ax.patches)/2-1 else hatch_def[1]
            height = p.get_height()
            cur_ax.text(x=p.get_x() + p.get_width() / 2,
                            y = p.get_height(), s=f'{height:.2f}',
                            ha='center', va='bottom',
                            fontsize=FONTSIZE-2)
            p.set_hatch(hatch)
        cur_ax.set_xlabel("")
        rotation = 0
        if len(overhead[overhead['system'] == sys]['bench'].unique()) > 6:
            if len(overhead[overhead['system'] == sys]['bench'].unique()) > 15:
                cur_ax.tick_params(axis='x', labelrotation=90)
                rotation = 90
            else:
                cur_ax.tick_params(axis='x', labelrotation=45)
                rotation = 45
        else:
            cur_ax.tick_params(axis='x', pad=5)
        baseline_agg = overhead[overhead['system'] == sys].groupby([ x for x in overhead.columns if x not in ['repetition', 'safe', 'unsafe', 'overhead', 'expe']])['unsafe'].agg(['mean', 'std']).reset_index()
        baseline_val = baseline_agg[baseline_agg['system'] == sys].sort_values(by='bench', key=lambda x: natsorted(baseline_agg[baseline_agg['system'] == sys]['bench'], alg=ns.NUMAFTER))['mean']
        shift = 1/4
        for i, tick in enumerate(cur_ax.get_xticklabels()):
            cur_ax.text(x=i-shift, y=-0.1, s=format_val_time(baseline_val[i]),
                        ha='center', va='top', transform=cur_ax.get_xaxis_transform(),
                        color='gray', fontsize=FONTSIZE-2)
            cur_ax.text(x=i+shift, y=-0.1, s=format_val_time(baseline_val[i+len(baseline_val)/2]),
                        ha='center', va='top', transform=cur_ax.get_xaxis_transform(),
                        color='gray', fontsize=FONTSIZE-2)
        cur_ax.text(x=-0.5, y=-0.08, s="Baseline:", ha='right', va='top', transform=cur_ax.get_xaxis_transform(), fontsize=FONTSIZE-1, color='gray') 
        cur_ax.set_ylabel("Normalized\nlatency", fontsize=FONTSIZE)
        cur_ax.set_xticklabels(cur_ax.get_xticklabels(), size=FONTSIZE-1)
        cur_ax.set_yticklabels(cur_ax.get_yticklabels(), size=FONTSIZE)
        max_val = std_overhead[(std_overhead.system == sys)]['max'].max()
        cur_ax.set_ylim(0.8, max_val*1.4)
        handles, labels = cur_ax.get_legend_handles_labels()
        leg = [
            mpl.patches.Patch(facecolor=colors[0], hatch=hatch_def[0], edgecolor="black"),
            mpl.patches.Patch(facecolor=colors[1], hatch=hatch_def[1], edgecolor="black")
        ]
        cur_ax.legend(leg, labels, loc="upper right", title=None, fontsize=FONTSIZE-2,
            #bbox_to_anchor=(0.5, 0.07),
            ncol=2,
        )
        #cur_ax.legend_ = None
        #cur_ax.set_title(sys+" (mean: x{:.2f})".format(grouped_overhead[grouped_overhead['system'] == sys]['mean'].to_list()[0]))
        cur_ax.set_title(sys, color='black')
        cur_ax.annotate(lower_better_str, color='blue', xy=(0.05, 0.75), xycoords='figure fraction', annotation_clip=False, fontsize=FONTSIZE)

        plt.tight_layout()
        #plt.suptitle(lower_better_str, color='blue')
        #plt.subplots_adjust(wspace=0.25)
        plt.savefig(os.path.join(result_dir, "datastructures_{}.pdf".format(sys)), format="pdf", pad_inches=0, bbox_inches="tight")

if __name__ == "__main__":
    main()



"""
            labels = cur_ax.bar_label(cur_ax.containers[0], fontsize=FONTSIZE-2, labels=[f"x{a:.2f}" for a in std_overhead[std_overhead['system']==sys]['mean']], padding=1)
            for label in labels:
                bar_height = label.xy[1]
                if bar_height < clamp_y:
                    label.set_textcoords('data')
                    label.set_position((label.xy[0], clamp_y))
"""
