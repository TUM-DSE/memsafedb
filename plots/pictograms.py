"""Sweep pictograms shared by every row of the combined DBMS figure.


Stacked disks  = working set / scale factor, 1-3 = position in that system's sweep.
Wavy strands   = client threads,             1-3 = position in that system's sweep.
Both are drawn in *figure* coordinates with separate x/y scaling so they keep
their shape whatever the panel aspect ratio is.
"""
import math
import numpy as np
from matplotlib.patches import Rectangle, Ellipse, Arc
from matplotlib.lines import Line2D

DISK_BAND, DISK_W, DISK_RY = 0.030, 0.095, 0.016   # inches: band height, width, ellipse rise
THR_H, THR_PITCH, THR_AMP = 0.090, 0.022, 0.008
COL, LID = '#262626', '#5A5A5A'
DISK_LW = 0.75


def disk_glyph(fig, xc, yc, n, col=COL, scale=1.0):
    """The classic database cylinder, outlined and divided into n bands."""
    W, H = fig.get_size_inches()
    hw = DISK_W*scale/2/W
    ry = DISK_RY*scale/H
    band = DISK_BAND*scale/H
    y0 = yc - (n*band)/2                  # bottom rim centre
    ytop = y0 + n*band                    # top rim centre
    T, kw = fig.transFigure, dict(transform=fig.transFigure, clip_on=False)

    # white body first, so the fill hides nothing but the page behind it
    fig.patches.append(Ellipse((xc, y0), 2*hw, 2*ry, fc='white', ec='none',
                               zorder=9, **kw))
    fig.patches.append(Rectangle((xc-hw, y0), 2*hw, n*band, fc='white', ec='none',
                                 zorder=9, **kw))
    # bottom rim and the band separators: only the front (lower) half is visible
    for i in range(n):
        fig.patches.append(Arc((xc, y0 + i*band), 2*hw, 2*ry, theta1=180, theta2=360,
                               ec=col, lw=DISK_LW, zorder=10, **kw))
    for sx in (-hw, hw):                  # the cylinder's sides
        fig.lines.append(Line2D([xc+sx, xc+sx], [y0, ytop], color=col, lw=DISK_LW,
                                solid_capstyle='butt', zorder=10, **kw))
    # the lid is a full ellipse -- its far edge is what makes it read as 3D
    fig.patches.append(Ellipse((xc, ytop), 2*hw, 2*ry, fc='white', ec=col,
                               lw=DISK_LW, zorder=11, **kw))
    return hw


def thread_glyph(fig, xc, yc, n, col=COL, scale=1.0):
    W, H = fig.get_size_inches()
    hh, amp, pitch = THR_H*scale/2/H, THR_AMP*scale/W, THR_PITCH*scale/W
    t = np.linspace(0, 1, 80)
    ys = yc - hh + 2*hh*t
    x0 = xc - pitch*(n-1)/2
    for k in range(n):
        fig.lines.append(Line2D(x0 + k*pitch + amp*np.sin(2*np.pi*2.5*t), ys,
                                transform=fig.transFigure, color=col, lw=0.5,
                                solid_capstyle='round', zorder=11, clip_on=False))
    return pitch*(n-1)/2 + amp


def glyph(fig, xc, yc, kind, n, **kw):
    return (disk_glyph if kind == 'disk' else thread_glyph)(fig, xc, yc, n, **kw)


def at_axes(fig, ax, x_data, y_axes):
    """(data x, axes-fraction y) -> figure coordinates, for placing glyphs near an axis."""
    disp = ax.get_xaxis_transform().transform((x_data, y_axes))
    return tuple(fig.transFigure.inverted().transform(disp))


def labelled(fig, xc, yc, text, kind, n, fontsize, weight='bold', gap=0.004, scale=1.0):
    """value text, then its pictogram, as one centred unit."""
    hw = glyph(fig, xc, yc, kind, n, scale=scale)
    fig.text(xc - hw - gap, yc, text, ha='right', va='center',
             fontsize=fontsize, fontweight=weight)


def labelled_row(fig, xc, yc, items, fontsize, gap=0.014, scale=1.0, weight='bold'):
    """[(label, kind, n), ...] laid out on ONE line, the whole group centred on xc."""
    W = fig.get_figwidth()
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    def tw(s):
        t = fig.text(0, 0, s, fontsize=fontsize, fontweight=weight)
        w = t.get_window_extent(rend).width / (W*fig.dpi)
        t.remove()
        return w
    def hw(kind, n):
        return (DISK_W*scale/2/W if kind == 'disk'
                else (THR_PITCH*scale*(n-1)/2 + THR_AMP*scale)/W)
    widths = [tw(lab) + 0.004 + 2*hw(k, n) for lab, k, n in items]
    x = xc - (sum(widths) + gap*(len(items)-1))/2
    for (lab, k, n), wd in zip(items, widths):
        fig.text(x, yc, lab, ha='left', va='center', fontsize=fontsize, fontweight=weight)
        glyph(fig, x + wd - hw(k, n), yc, k, n, scale=scale)
        x += wd + gap


def key(fig, xc, yc, fontsize=5.0, labels=None, scale=1.0):
    """Horizontal key: disks 1-3 then strands 1-3, centred on xc."""
    W = fig.get_figwidth()
    hw_d = DISK_W*scale/2/W
    def hw_t(n): return (THR_PITCH*scale*(n-1)/2 + THR_AMP*scale)/W
    lab = labels or {'disk': 'working set', 'thread': 'threads',
                     'vals': ['small', 'mid', 'large']}
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    def tw(s, fs):
        t = fig.text(0, 0, s, fontsize=fs)
        w = t.get_window_extent(rend).width / (W*fig.dpi)
        t.remove()
        return w
    items = [('label', lab['disk'], None)] + [('disk', v, i+1) for i, v in enumerate(lab['vals'])]
    items += [('label', lab['thread'], None)] + [('thread', v, i+1) for i, v in enumerate(lab['vals'])]
    def w_of(kind, s, n):
        if kind == 'label':
            return tw(s, fontsize) + 0.016
        return 2*(hw_d if kind == 'disk' else hw_t(n)) + 0.005 + tw(s, fontsize-0.3) + 0.016
    x = xc - sum(w_of(*it) for it in items)/2
    for kind, s, n in items:
        if kind == 'label':
            fig.text(x, yc, s, ha='left', va='center', fontsize=fontsize)
        else:
            hw = hw_d if kind == 'disk' else hw_t(n)
            glyph(fig, x + hw, yc, kind, n, scale=scale)
            fig.text(x + 2*hw + 0.005, yc, s, ha='left', va='center',
                     fontsize=fontsize-0.3, color='#444444')
        x += w_of(kind, s, n)


def emit_glyph_pdfs(out_dir):
    """Render every glyph to its own PDF, all on one canvas size so a single
    \\includegraphics scale keeps three disks taller than one disk."""
    import os
    import matplotlib.pyplot as plt
    os.makedirs(out_dir, exist_ok=True)
    for kind in ('disk', 'thread'):
        for n in (1, 2, 3):
            fig = plt.figure(figsize=(0.30, 0.16))
            glyph(fig, 0.5, 0.5, kind, n)
            fig.savefig(os.path.join(out_dir, f'{kind}{n}.pdf'), transparent=True)
            plt.close(fig)
    return out_dir
