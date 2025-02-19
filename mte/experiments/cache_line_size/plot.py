#!/usr/bin/env python

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def plot_throughput(csv_file, output):
    # Read CSV file
    df = pd.read_csv(csv_file, sep=';')

    # Compute mean duration per (len, stride) pair
    grouped = df.groupby(['len', 'stride'])['duration'].mean().reset_index()
    
    grouped['len'] = grouped['len'] * 4  # Convert to bytes
    grouped['stride'] = grouped['stride'] * 4  # Convert to bytes
    grouped['throughput'] = (grouped['len'] / grouped['stride']) / grouped['duration']

    # Convert stride to string for labeling
    grouped['stride'] = grouped['stride'].astype(str) + " bytes"

    # Plot
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=grouped, x='len', y='throughput', hue='stride', marker='o', palette='viridis')

    plt.xlabel('Array Size (Bytes)')
    plt.ylabel('Throughput (MB/s)')
    plt.yscale('log', base=2)
    plt.xscale('log', base=2)  # Set x-axis to powers of 2

    # Adjust x-axis ticks to show as powers of 2
    xticks = np.logspace(np.log2(grouped['len'].min()), np.log2(grouped['len'].max()), 
                         num=int(np.log2(grouped['len'].max()) - np.log2(grouped['len'].min())) + 1, base=2)
    plt.xticks(xticks, [f"$2^{{{int(np.log2(x))}}}$" for x in xticks])

    plt.title('Memory Throughput vs Array Size')
    plt.legend(title='Stride')
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.savefig(output)


def plot_avg_throughput(csv_file, output):
    # Read CSV file (using semicolon as separator)
    df = pd.read_csv(csv_file, sep=';')

    # Compute mean duration per (len, stride) pair
    grouped = df.groupby(['len', 'stride'])['duration'].mean().reset_index()
    
    # Convert to bytes (if each unit represents 4 bytes)
    grouped['len'] = grouped['len'] * 4  
    grouped['stride'] = grouped['stride'] * 4  

    # Calculate throughput for each (len, stride) pair
    # Throughput = (len/stride) / duration
    grouped['throughput'] = (grouped['len'] / grouped['stride']) / grouped['duration']

    #avg_throughput = grouped.groupby('stride')['throughput'].mean().reset_index()
    avg_throughput = grouped.groupby('stride')['throughput'].agg(['mean', 'std']).reset_index()

    # Create a label for strides (in bytes)
    avg_throughput['stride_label'] = avg_throughput['stride'].astype(str) + " bytes"
    avg_throughput['throughput'] =  avg_throughput['mean'] * (avg_throughput['stride'] // 4)

    # Plot the average throughput per stride as a bar graph
    plt.figure(figsize=(10, 6))
    plt.bar(avg_throughput['stride_label'], avg_throughput['throughput'], color='skyblue', yerr=avg_throughput['std'])
    plt.xlabel('Stride (Bytes)')
    plt.ylabel('Average Throughput (MB/s)')
    plt.title('Average Throughput per Stride')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    
    # Save and show the plot
    plt.savefig(output)


if __name__ == '__main__':
    EXPERIMENT_FOLDER = Path(__file__).parent
    RESULTING_PLOTS_ROOT = EXPERIMENT_FOLDER.parent / Path("plots/") / Path(EXPERIMENT_FOLDER.name + "/")
    RESULTING_PLOTS_ROOT.mkdir(parents=True, exist_ok=True)

    plot_avg_throughput('result_load.csv', str(RESULTING_PLOTS_ROOT / Path('cache_line_size_throughput_avg.png')))
    plot_throughput('result_load.csv', str(RESULTING_PLOTS_ROOT / Path('cache_line_size_throughput.png')))

