#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import os
from common import *
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.lines import Line2D

def plot_spider_chart():
    # Data Definition
    # Tuple format: (Performance, Portability, Safety)
    
    # ASan: 9 portability, 2 performance, 2 safety
    asan_data = (2, 9, 2)
    
    # Rust: 0 portability, 9 performance, 8 safety
    rust_data = (9, 0, 8)
    
    # SoftBound: 7 portability, 4 performance, 7 safety
    softbound_data = (4, 7, 6)
    
    # MTE: 5 portability, 9 performance, 5 safety (Based on file: (9, 5, 5) if (Perf, Port, Safe))
    mte_data = (9, 8, 4)
    
    # CHERI: 2 portability, 5 performance, 9 safety (Based on file: (5, 2, 9) if (Perf, Port, Safe))
    cheri_data = (5, 2, 9)
    
    fig = plt.figure(figsize=(figwidth_half, fig_height*2))
    plt.subplots_adjust(top=0.75, bottom=0.15, left=0.05, right=0.95)
    ax = fig.add_subplot(111, projection='3d')
    
    def plot_item(data, label, color, marker):
        perf, port, safe = data
        
        # Plot Point: X=Portability, Y=Safety, Z=Performance
        # We use scatter for the point
        ax.scatter([port], [safe], [perf], color=color, marker=marker, s=25, label=label, depthshade=False)

        ax.plot([port, port], [safe, safe], [perf, 0], color=color, linestyle=':', linewidth=1, alpha=0.6)
        
        ax.plot([port, port], [safe, 0], [perf, perf], color=color, linestyle=':', linewidth=1, alpha=0.6)
        
        ax.plot([port, 0], [safe, safe], [perf, perf], color=color, linestyle=':', linewidth=1, alpha=0.6)
        
        ax.scatter([port], [safe], [0], color=color, marker='+', s=5, alpha=0.6)
        ax.scatter([port], [0], [perf], color=color, marker='+', s=5, alpha=0.6)
        ax.scatter([0], [safe], [perf], color=color, marker='+', s=5, alpha=0.6)

    # Plot Items
    # MTE
    plot_item(mte_data, 'MTE', MTE_COLOR, 'h') # Diamond
    
    # CHERI
    plot_item(cheri_data, 'CHERI', CHERI_COLOR, '*') # Star
    
    # ASan
    plot_item(asan_data, 'Software-based (e.g. ASan)', ASAN_COLOR, 'o') # Circle
    
    # Rust
    plot_item(rust_data, 'New Language (e.g. Rust)', 'green', 'x')
    
    # SoftBound
    #plot_item(softbound_data, 'SoftBound', '#e377c2', 'P') # Plus (filled) or 'P'

    # Axis Limits
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_zlim(0, 10)

    # Remove ticks
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])
    
    ax.quiver(0, 0, 0, 11, 0, 0, arrow_length_ratio=0.1, color='black', alpha=1, linewidth=1)
    ax.quiver(0, 0, 0, 0, 11, 0, arrow_length_ratio=0.1, color='black', alpha=1, linewidth=1)
    ax.quiver(0, 0, 0, 0, 0, 11, arrow_length_ratio=0.1, color='black', alpha=1, linewidth=1)
    
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_zlabel('')
    
    ax.text(14, 1, 0, 'Portability', fontsize=FONTSIZE_AXIS_LABEL, ha='center', va='center')
    ax.text(2, 12.5, 0, 'Safety', fontsize=FONTSIZE_AXIS_LABEL, ha='center', va='center')
    ax.text(0, 0, 12, 'Performance', fontsize=FONTSIZE_AXIS_LABEL, ha='center', va='center')

    
    # Placeholder Annotations with marker points
    # MTE
    fig.text(0.09, 0.72, "MTE:\nGood performance (5-10\\%)\nMinimal changes\nProbabilistic safety", fontsize=FONTSIZE_ANNOTATION+2, ha='left', va='center', color='black')
    fig.add_artist(Line2D([0.075], [0.77], transform=fig.transFigure, figure=fig, marker='h', markersize=5, color=MTE_COLOR, linestyle='None'))
    
    # CHERI
    fig.text(0.7, 0.72, "CHERI:\nAverage performance (20-60\\%)\nDifficult to port\nExcellent safety", fontsize=FONTSIZE_ANNOTATION+2, ha='left', va='center', color='black')
    fig.add_artist(Line2D([0.685], [0.77], transform=fig.transFigure, figure=fig, marker='*', markersize=5, color=CHERI_COLOR, linestyle='None'))
    
    # ASan
    fig.text(0.15, 0.15, "Software-based (e.g. ASan):\nNot for production\nSimple flag\nOnly for debugging", fontsize=FONTSIZE_ANNOTATION+2, ha='left', va='center', color='black')
    fig.add_artist(Line2D([0.135], [0.2], transform=fig.transFigure, figure=fig, marker='o', markersize=5, color=ASAN_COLOR, linestyle='None'))
    
    # Rust
    fig.text(0.7, 0.15, "Memory-safe languages (e.g. Rust):\nExcellent performance\nNeed complete rewrite\nGood safety", fontsize=FONTSIZE_ANNOTATION+2, ha='left', va='center', color='black')
    fig.add_artist(Line2D([0.685], [0.2], transform=fig.transFigure, figure=fig, marker='x', markersize=5, color='green', linestyle='None'))
    
    # View Angle
    ax.view_init(elev=20, azim=45)
    
    # Legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    
    all_labels = ['MTE', 'CHERI', 'Software-based (e.g. ASan)', 'New Language (e.g. Rust)']
    all_handles = [by_label[l] for l in all_labels if l in by_label]
    
    #legend = ax.legend(all_handles, all_labels, loc='lower center', bbox_to_anchor=(0.5, 0.02), 
    #                    fontsize=FONTSIZE_LEGEND, frameon=True, ncol=2, bbox_transform=fig.transFigure)
               
    # Save
    if not os.path.exists(result_dir):
        try:
            os.makedirs(result_dir)
        except OSError:
            pass
    
    output_filename = "spider_chart.pdf"
    output_path = os.path.join(result_dir, output_filename)
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    print(f"Generated {output_filename}")

if __name__ == "__main__":
    plot_spider_chart()
