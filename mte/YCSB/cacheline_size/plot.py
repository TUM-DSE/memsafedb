#!/usr/bin/env python

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_throughput(csv_file):
    # Read CSV file
    df = pd.read_csv(csv_file, sep=';')
    
    # Compute mean duration per (len, stride) pair
    grouped = df.groupby(['len', 'stride'])['duration'].mean().reset_index()
    print(grouped)

    grouped['len'] = grouped['len'] * 4
    grouped['throughput'] = (grouped['len'] / grouped['stride']) / grouped['duration']
    print(grouped.loc[grouped['stride'] == 1])

    grouped['stride'] = grouped['stride'].astype(str)

    
    # Plot
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=grouped, x='len', y='throughput', hue='stride', marker='o', palette='viridis')
    plt.xlabel('Array Size (Bytes)')
    plt.ylabel('Throughput (MB/s)')
    plt.title('Memory Throughput vs Array Size')
    plt.legend(title='Stride')
    plt.grid(True)
    plt.savefig('/mnt/c/Users/t-rdichler/Downloads/ba_meeting/cache_size_pixel_tagged_ldg.png')
    plt.show()

plot_throughput('../results/result_tagged_ldg.csv')

