#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Datastructure memory-safety overhead.

Multi-threaded structures (B+Tree, CLHT, Queue) are shown as a split pair of
panels: an MTE panel sweeping eliza's 1/8/64 threads and a CHERI panel sweeping
ace's 1/2/4 threads. Single-threaded structures (ART, Skiplist, Linked list)
keep one MTE-vs-CHERI panel. Bars are normalised runtime (protected / baseline).
Workload names sit inside the plot at the top of each dashed-separated group;
thread counts sit on the bars; baseline latencies run along the bottom. Bars
whose baseline and protected mean 95% CIs overlap are not statistically
significant and are marked with an asterisk. The CHERI multi-threaded B+Tree is
unobtainable (Morello purecap cannot unwind the OLC restart exception), so that
panel collapses to its single 1-thread bar."""
import os
import csv
import collections
import statistics

from common import (result_dir, dir_path, figwidth_full, fig_height,
                    MTE_COLOR, CHERI_COLOR, MTE_HATCH, CHERI_HATCH, darken,
                    lower_better_str)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import numpy as np
from scipy import stats as _sstats
import shutil

# On-page point sizes (the figure prints at ~\textwidth, ~1:1), kept clearly
# larger than common's defaults so the figure is legible at column size.
FS_TITLE, FS_AXIS, FS_TICK = 9.0, 8.5, 7.0
FS_OP, FS_THR, FS_PCT, FS_BASE = 8.0, 6.5, 7.0, 6.5
FS_PCT_ST = 6.0    # row-2 overheads a touch smaller than row-1's
FS_SUB, FS_LEG, FS_NOTE = 7.5, 8.0, 6.5

BASE_Y = -0.04    # baseline-latency row (rotated), just under the axis

FILES = ['datastructures_mte', 'datastructures_cheri',
         'datastructures_cheri_mt', 'clht_cheri_check']
IGNORED = {'YCSB-A', 'YCSB-B', 'YCSB-C', 'YCSB-D', 'YCSB-E', 'YCSB-F',
           'readmodifywrite'}
OP_ORDER = ['read', 'insert', 'update', 'scan', 'queue_bench']
OP_LABEL = {'read': 'read', 'insert': 'insert', 'update': 'update',
            'scan': 'scan', 'queue_bench': 'queue'}

MT_SYS = ['btree', 'CLHT', 'queue']
ST_SYS = ['ART', 'skiplist', 'linklist']
MTE_THR = [1, 8, 64]
CHERI_THR = [1, 2, 4]
NAME = {'btree': 'B+Tree', 'CLHT': 'CLHT', 'queue': 'Queue',
        'ART': 'ART', 'skiplist': 'Skiplist', 'linklist': 'Linked list'}


def format_val_time(val):
    if val > 1_000_000:
        return '{:.1f}ms'.format(val / 1_000_000)
    elif val > 10_000:
        return '{}us'.format(int(val / 1000))
    elif val > 1_000:
        return '{:.1f}us'.format(val / 1000)
    return '{}ns'.format(int(val))


def load():
    """(system, op, ext, thr, safe) -> [latencies] unioned across FILES."""
    lat = collections.defaultdict(list)
    seen = set()   # dedup identical rows appearing in more than one file
    for f in FILES:
        path = os.path.join(result_dir, f + '.csv')
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path)):
            if r['name'] in IGNORED:
                continue
            ext = {'eliza': 'MTE', 'ace': 'CHERI'}[r['host']]
            safe = {'aarch64': 'base', 'mte': 'prot', 'cheri': 'prot'}[r['arch']]
            key = (r['host'], r['arch'], r['system'], r['name'],
                   r['nthreads'], r['repetition'], r['latency'])
            if key in seen:
                continue
            seen.add(key)
            lat[(r['system'], r['name'], ext, int(r['nthreads']), safe)].append(
                float(r['latency']))
    return lat


def _mean_ci(vals):
    n = len(vals)
    m = statistics.mean(vals)
    if n < 2:
        return m, 0.0
    return m, _sstats.t.ppf(0.975, n - 1) * statistics.stdev(vals) / (n ** 0.5)


def overhead(lat, system, op, ext, thr):
    """{'m','s','sig'} or None. sig=False when the baseline and protected mean
    CIs overlap (the overhead is not statistically significant)."""
    b = lat.get((system, op, ext, thr, 'base'))
    p = lat.get((system, op, ext, thr, 'prot'))
    if not b or not p:
        return None
    mb, hb = _mean_ci(b)
    mp, hp = _mean_ci(p)
    s = statistics.pstdev([mp / bb for bb in b]) if len(b) > 1 else 0.0
    sig = (mb + hb < mp - hp) or (mp + hp < mb - hb)
    return {'m': mp / mb, 's': s, 'sig': sig}


def ops_of(lat, system):
    return [o for o in OP_ORDER
            if any(overhead(lat, system, o, e, t)
                   for e in ('MTE', 'CHERI') for t in MTE_THR + CHERI_THR)]


def _box(ax):
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_linewidth(0.5)


def _pct(ax, x, top, r, rot, fs=FS_PCT):
    txt = r'$%+.0f\%%$' % ((r['m'] - 1) * 100)
    if not r['sig']:
        txt += r'*'
    # never below the 1.0 line: sub-unity bars get their label above the line
    ax.text(x, max(top, 1.0) + 0.01, txt, ha='center', va='bottom', rotation=rot,
            fontsize=fs, color='black' if r['sig'] else '0.4')


def _baseline(ax, x, val):
    ax.text(x, BASE_Y, format_val_time(val), ha='center', va='top', rotation=90,
            transform=ax.get_xaxis_transform(), color='gray', fontsize=FS_BASE)


def _thread_inside(ax, x, thr, ybot, yr):
    ax.text(x, ybot + 0.03 * yr, str(thr), ha='center', va='bottom',
            fontsize=FS_THR, zorder=6,
            bbox=dict(fc='white', ec='none', alpha=0.6, pad=0.4))


def _groups(ax, ops, ybot, ytop):
    """Dashed separators between op groups + workload name in the top whitespace."""
    yr = ytop - ybot
    for i in range(len(ops) - 1):
        ax.axvline(i + 0.5, color='0.7', ls=(0, (3, 3)), lw=0.5, zorder=0)
    fig = ax.get_figure()
    per_in = ax.get_position().width * fig.get_size_inches()[0] / max(len(ops), 1)
    need_in = max(len(OP_LABEL[o]) for o in ops) * FS_OP * 0.62 / 72.0
    tilt = per_in < need_in
    for gi, op in enumerate(ops):
        if op == 'queue_bench':      # the panel title already says "Queue"
            continue
        if tilt:
            ax.text(gi, ytop - 0.02 * yr, OP_LABEL[op], ha='center', va='top',
                    rotation=90, fontsize=FS_OP)
        else:
            ax.text(gi, ytop - 0.03 * yr, OP_LABEL[op], ha='center', va='top',
                    fontsize=FS_OP)


def mt_panel(lat, ax, system, ext, threads, color, hatch):
    ops = ops_of(lat, system)
    threads = [t for t in threads
               if any(overhead(lat, system, o, ext, t) for o in ops)]
    if not threads:
        threads = [1]
    n = len(threads)
    w = 0.86 / n
    placed, tops, mins = [], [], []
    for gi, op in enumerate(ops):
        for ti, thr in enumerate(threads):
            xc = gi + (ti - n / 2 + 0.5) * w
            r = overhead(lat, system, op, ext, thr)
            if r is None:
                continue
            ax.bar(xc, r['m'], w * 0.92, color=color, edgecolor='black',
                   linewidth=0.3, hatch=hatch, yerr=r['s'], capsize=1,
                   error_kw=dict(lw=0.4, capthick=0.4))
            _pct(ax, xc, r['m'] + r['s'], r, 90)
            _baseline(ax, xc, statistics.mean(lat[(system, op, ext, thr, 'base')]))
            placed.append((xc, thr))
            tops.append(r['m'] + r['s'])
            mins.append(r['m'])
    ax.axhline(1.0, color='red', ls='--', lw=0.7, alpha=0.7, zorder=1)
    ybot = min(0.9, min(mins + [1.0]) - 0.03)
    ytop = max(tops + [1.1]) * 1.55
    ax.set_xlim(-0.5, len(ops) - 0.5)
    ax.set_ylim(ybot, ytop)
    ax.set_xticks([])
    ax.tick_params(axis='y', labelsize=FS_TICK, length=1.5, pad=1)
    for xc, thr in placed:
        _thread_inside(ax, xc, thr, ybot, ytop - ybot)
    _groups(ax, ops, ybot, ytop)
    _box(ax)


def st_panel(lat, ax, system):
    ops = ops_of(lat, system)
    x = np.arange(len(ops))
    w = 0.38
    tops, mins = [], []
    for ext, col, hatch, dx in [('MTE', MTE_COLOR, MTE_HATCH, -w / 2),
                                ('CHERI', CHERI_COLOR, CHERI_HATCH, w / 2)]:
        for xi, op in enumerate(ops):
            r = overhead(lat, system, op, ext, 1)
            if r is None:
                continue
            ax.bar(x[xi] + dx, r['m'], w, color=col, edgecolor='black',
                   linewidth=0.3, hatch=hatch, yerr=r['s'], capsize=1,
                   error_kw=dict(lw=0.4, capthick=0.4))
            # nudge the label a few px outwards (away from the group centre)
            _pct(ax, x[xi] + dx + (0.07 if dx > 0 else -0.07),
                 r['m'] + r['s'], r, 0, FS_PCT_ST)   # horizontal % (row 2)
            _baseline(ax, x[xi] + dx, statistics.mean(lat[(system, op, ext, 1, 'base')]))
            tops.append(r['m'] + r['s'])
            mins.append(r['m'])
    ax.axhline(1.0, color='red', ls='--', lw=0.7, alpha=0.7, zorder=1)
    ybot = min(0.9, min(mins + [1.0]) - 0.03)
    ytop = max(tops + [1.1]) * 1.30
    ax.set_xlim(-0.5, len(ops) - 0.5)
    ax.set_ylim(ybot, ytop)
    ax.set_xticks([])
    ax.tick_params(axis='y', labelsize=FS_TICK, length=1.5, pad=1)
    _groups(ax, ops, ybot, ytop)
    _box(ax)


def plot_datastructures(lat):
    fig = plt.figure(figsize=(figwidth_full, 2.0 * fig_height))
    outer = gridspec.GridSpec(2, 1, figure=fig, height_ratios=[1, 0.82], hspace=0.52,
                              left=0.10, right=0.995, top=0.88, bottom=0.07)
    top = gridspec.GridSpecFromSubplotSpec(
        1, 6, subplot_spec=outer[0], wspace=0.30,
        width_ratios=[2.05, 1.05, 1.15, 0.95, 0.62, 0.58])
    bot = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[1], wspace=0.14)

    first_mt = None
    for si, system in enumerate(MT_SYS):
        axm = fig.add_subplot(top[0, si * 2])
        axc = fig.add_subplot(top[0, si * 2 + 1])
        mt_panel(lat, axm, system, 'MTE', MTE_THR, MTE_COLOR, MTE_HATCH)
        mt_panel(lat, axc, system, 'CHERI', CHERI_THR, CHERI_COLOR, CHERI_HATCH)
        if si == 0:
            axm.set_ylabel('Runtime (norm.)', fontsize=FS_AXIS)
            first_mt = axm
        bbm, bbc = axm.get_position(), axc.get_position()
        fig.text((bbm.x0 + bbc.x1) / 2, bbm.y1 + 0.045,
                 r'\textbf{(%s) %s}' % (chr(97 + si), NAME[system]),
                 ha='center', fontsize=FS_TITLE)
        fig.text((bbm.x0 + bbm.x1) / 2, bbm.y1 + 0.012, 'MTE', ha='center',
                 fontsize=FS_SUB, color=darken(MTE_COLOR))
        fig.text((bbc.x0 + bbc.x1) / 2, bbc.y1 + 0.012, 'CHERI', ha='center',
                 fontsize=FS_SUB, color=darken(CHERI_COLOR))

    first_st = None
    for si, system in enumerate(ST_SYS):
        ax = fig.add_subplot(bot[0, si])
        st_panel(lat, ax, system)
        if si == 0:
            ax.set_ylabel('Runtime (norm.)', fontsize=FS_AXIS)
            first_st = ax
        bb = ax.get_position()
        fig.text((bb.x0 + bb.x1) / 2, bb.y1 + 0.028,
                 r'\textbf{(%s) %s}' % (chr(97 + len(MT_SYS) + si), NAME[system]),
                 ha='center', fontsize=FS_TITLE)

    # left-hand row tags: "# threads:" (MT only) sits just above "Baseline:".
    for ax, thr_tag in ((first_mt, True), (first_st, False)):
        if ax is None:
            continue
        bb = ax.get_position()
        x = bb.x0 - 0.006
        fig.text(x, bb.y0 + BASE_Y * bb.height, 'Baseline:', ha='right', va='top',
                 color='gray', fontsize=FS_BASE)
        if thr_tag:
            fig.text(x, bb.y0 + 0.03 * bb.height, r'\# threads:', ha='right',
                     va='bottom', color='0.4', fontsize=FS_BASE)

    legend = [mpatches.Patch(fc=MTE_COLOR, ec='black', lw=0.5, hatch=MTE_HATCH,
                             label='MTE'),
              mpatches.Patch(fc=CHERI_COLOR, ec='black', lw=0.5, hatch=CHERI_HATCH,
                             label='CHERI')]
    fig.legend(handles=legend, loc='upper center', ncol=2, fontsize=FS_LEG,
               frameon=True, bbox_to_anchor=(0.5, 1.01), handlelength=1.3,
               handleheight=0.9, columnspacing=1.2, handletextpad=0.4)
    fig.text(0.02, 0.995, lower_better_str, ha='left', va='top', color='blue',
             fontsize=FS_NOTE + 1)
    fig.text(0.02, 0.953, '* not significant (overlapping CIs)', ha='left',
             va='top', color='0.4', fontsize=FS_NOTE)

    out = os.path.join(result_dir, 'datastructures_all.pdf')
    plt.savefig(out, bbox_inches='tight', pad_inches=0.02)
    plt.close()
    paper_plots = os.path.join(dir_path, '..', 'paper_draft', 'plots')
    if os.path.isdir(paper_plots):
        shutil.copy2(out, os.path.join(paper_plots, os.path.basename(out)))
    print('Generated datastructures_all.pdf')


def main():
    lat = load()
    if not lat:
        print('No data found.')
        return
    plot_datastructures(lat)


if __name__ == '__main__':
    main()
