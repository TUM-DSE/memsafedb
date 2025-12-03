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

def load_data() -> pd.DataFrame:
    df_tmp = pd.read_csv(result_dir+'/datastructures.csv')
    df_tmp['memsafe'] = df_tmp['arch'].map({'aarch64': 'unsafe', 'mte': 'safe', 'cheri': 'safe'})
    df_tmp = df_tmp[[x for x in df_tmp.columns if x != 'nb_ops']]
    df = df_tmp.copy()
    df['fkey'] = df[[x for x in df.columns if x not in ['throughput', 'arch', 'memsafe']]].apply(lambda x: '-'.join(x.astype(str).values), axis=1) 
    df = df[[ x for x in df.columns if x not in ['arch']]]
    agg = df.pivot(index='fkey', columns='memsafe', values='throughput')
    #for host, arch in zip(['eliza', 'ace'], ['mte', 'cheri']):
    agg['overhead'] = agg['unsafe'] / agg['safe']
    agg = agg.reset_index()
    df = df[[ x for x in df.columns if x not in ['mean', 'memsafe']]].drop_duplicates()
    joined = pd.merge(agg, df, on='fkey', how='inner')
    joined['name'] = joined['name'].replace({"readmodifywrite": "rmw", "queue_bench": "queue"})
    joined['nthreads'] = joined['nthreads'].replace({1: '', 4: '4', 8: '8', 16: '16', 32: '32', 64: '64', 96: '96'})
    joined['bench'] = joined['name'] + ' ' + joined['nthreads'].astype(str)
    joined = joined[[x for x in joined.columns if x not in ['fkey', 'name', 'nthreads', 'throughput']]]
    all_res = df_tmp
    all_res['name'] = all_res['name'].replace({"readmodifywrite": "rmw", "queue_bench": "queue"})
    all_res['nthreads'] = all_res['nthreads'].replace({1: '', 4: '4', 8: '8', 16: '16', 32: '32', 64: '64', 96: '96'})
    all_res['bench'] = all_res['name'] + ' ' + all_res['nthreads'].astype(str)
    all_res = all_res[[x for x in all_res.columns if x not in ['name', 'nthreads', 'host', 'arch']]]
    return all_res, joined

def analyze_results(df):
    df_avg = df.groupby([ x for x in df.columns if x not in ['throughput', 'repetition']])['throughput'].agg(['mean', 'std']).reset_index()
    df_avg['max'] = df_avg['mean'] + df_avg['std']
    df_avg['min'] = df_avg['mean'] - df_avg['std']
    df_avg['fkey'] = df_avg['system'] + df_avg['bench']
    piv = df_avg.pivot_table(index=['system', 'bench'], columns='memsafe', values=['mean', 'std', 'max', 'min'])
    print(piv)
    with open(os.path.join(result_dir, "datastructures_comparison.txt"), 'a') as f:
        f.write(piv.to_string(header=True, index=True))

def main():
    data, overhead = load_data()
    analyze_results(data)
    return
    std_overhead = overhead.groupby([ x for x in overhead.columns if x not in ['rep', 'safe', 'unsafe', 'overhead']])['overhead'].agg(['mean', 'std']).reset_index()
    std_overhead['max'] = std_overhead['mean'] + std_overhead['std']
    std_overhead['min'] = std_overhead['mean'] - std_overhead['std']
    systems = data['system'].unique() 
    
    fig, ax = plt.subplots(3, 2, figsize=(figwidth_full, fig_height*3))
    for i, sys in zip(range(len(systems)), systems):
        ax[int(i/2)][i%2].axhline(y=1, color='red', zorder=0)
        sorted_confs = sorted(overhead[overhead.system == sys]['bench'].unique(), key = sort_workload)
        sns.barplot(ax=ax[int(i/2)][i%2], data=overhead[overhead.system == sys], x = "bench", y = "overhead", order=sorted_confs, edgecolor="black", errorbar=("sd"))
        #hue = "memsafe", hue_order = ['unsafe', 'safe'], palette=[palette[0], palette[1]],
        ax[int(i/2)][i%2].set_xlabel("")
        if len(overhead[overhead.system == sys]['bench'].unique()) > 6:
            if len(overhead[overhead.system == sys]['bench'].unique()) > 15:
                ax[int(i/2)][i%2].tick_params(axis='x', labelrotation=90)
            else:
                ax[int(i/2)][i%2].tick_params(axis='x', labelrotation=45)
        ax[int(i/2)][i%2].set_ylabel("Relative throughput", fontsize=FONTSIZE)
        ax[int(i/2)][i%2].set_xticklabels(ax[int(i/2)][i%2].get_xticklabels(), size=FONTSIZE)
        #ax[i].yaxis.set_major_formatter(ticker.FuncFormatter(format_big_numbers))
        #ax[i].set_yticklabels(ax[i].get_yticklabels(), size=FONTSIZE)
        #ax[i].get_legend().remove()
        max_val = std_overhead[std_overhead.system == sys]['max'].max()
        min_val = std_overhead[std_overhead.system == sys]['min'].min()
        biggest = max(max_val - 1, 1 - min_val)*1
        ax[int(i/2)][i%2].set_ylim(1-biggest, 1+biggest)
        #ax[i].bar_label(ax[i].containers[1], fontsize=FONTSIZE-2, labels=[f"{100*a - 100:.0f}%" for a in overhead[overhead.system==sys]['overhead']])
        ax[int(i/2)][i%2].set_title(sys)

    """handles, labels = ax[0].get_legend_handles_labels()
    leg = [
        mpl.patches.Patch(facecolor=palette[0], hatch=hatch_def[0], edgecolor="black"),
        mpl.patches.Patch(facecolor=palette[1], hatch=hatch_def[1], edgecolor="black")
    ]
    fig.legend(leg, labels, loc="upper center", title=None, fontsize=FONTSIZE-1,
        bbox_to_anchor=(0.5, 0.07),
        ncol=4,
    )"""
    plt.tight_layout()
    plt.subplots_adjust(wspace=0.4)
    plt.savefig(os.path.join(result_dir, "datastructures.pdf"), format="pdf", pad_inches=0, bbox_inches="tight")


"""
        size = int(len(ax[0].patches)/2)
        hatches = [hatch_def[0]] * size + [hatch_def[1]] * size
        for bar,hat in zip(ax[0].patches, hatches):
            bar.set_hatch(hat)
    ax.set_yscale("log")
    ax[0].set_yticks([100_000, 1_000_000])
    ax[0].get_yaxis().set_major_formatter(mpl.ticker.LogFormatterMathtext())
    ax[0].tick_params(axis='y', which='both', labelsize=FONTSIZE)
    ax[0].set_ylabel("Insertions/s", fontsize=FONTSIZE)
    ax[0].set_xlabel("# of threads", fontsize=FONTSIZE, labelpad=2)
    box = ax[0].get_position()
    ax[0].set_xticklabels([1, 16, 32, 64], size=FONTSIZE)
    ax[0].set_position([box.x0, box.y0+box.height*0.1, box.width, box.height*0.9])
    ax[0].set_title("4KiB pages", fontsize=FONTSIZE, color="black")
    
    ax[1].set_yscale("log")
    ax[1].set_yticks([100_000, 1_000_000])
    ax[1].get_yaxis().set_major_formatter(mpl.ticker.LogFormatterMathtext())
    ax[1].tick_params(axis='y', which='both', labelsize=FONTSIZE)
    ax[1].set_xticklabels([f'{x/1024:.0f}' for x in sorted(data_bp['pageSize'].unique())], size=FONTSIZE)
    #ax[1].set_yticks([0, 200_000, 400_000, 600_000, 800_000, 1_000_000])
    #ax[1].set_yticklabels([0, 0.2, 0.4, 0.6, 0.8, 1], size=FONTSIZE)
    #ax[1].set_ylabel("test", fontsize=FONTSIZE)
    ax[1].set_xlabel("Buffer size (KiB)", fontsize=FONTSIZE, labelpad=2)
    ax[1].set_title("64 threads", fontsize=FONTSIZE, color="black")
    
    ax2.set_ylabel("Throughput (GiB/s)", fontsize=FONTSIZE)
    #ax2.set_yscale("log")
    #ax2.get_yaxis().set_major_formatter(mpl.ticker.LogFormatterMathtext())
    ax2.tick_params(axis='y', which='both', labelsize=FONTSIZE)
    ax2.set_ylim(0, 13)

    handles, labels = ax[0].get_legend_handles_labels()
    leg = [
        mpl.patches.Patch(facecolor=get_palette("micro")[0], hatch=hatch_def[0], edgecolor="black"),
        mpl.patches.Patch(facecolor=get_palette("micro")[1], hatch=hatch_def[1], edgecolor="black")
    ]
    fig.legend(leg, labels, loc="upper center", title=None, fontsize=FONTSIZE-1,
        bbox_to_anchor=(0.5, 0.07),
        ncol=4,
    )
    ax[0].get_legend().remove()
    """


if __name__ == "__main__":
    main()
