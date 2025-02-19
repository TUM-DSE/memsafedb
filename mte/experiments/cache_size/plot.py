#!/usr/bin/env python

import pandas as pd
import matplotlib.pyplot as plt

def process_and_plot(csv_file, image_output):
    # Load the CSV file
    df = pd.read_csv(csv_file)
    df = pd.read_csv(csv_file, delimiter=';')

    if 'len' not in df.columns or 'duration' not in df.columns:
        raise ValueError("CSV file must contain 'len' and 'duration' columns.")

    df['duration'] = df['duration'] / 1e6
    df['len_kb'] = (df['len'] * 4) // 1024

    # Group data by len_kb and process each group
    processed_data = []
    for length_kb, group in df.groupby('len_kb'):
        mean_duration = group['duration'].mean()
        std_duration = group['duration'].std()
        processed_data.append({'len_kb': length_kb, 'mean_duration': mean_duration, "std_dev": std_duration})

    # Create a DataFrame for the processed data
    processed_df = pd.DataFrame(processed_data)

    # Sort the DataFrame by len_kb
    processed_df.sort_values(by='len_kb', inplace=True)

    plt.figure(figsize=(10, 6))
    plt.plot(processed_df['len_kb'], processed_df['mean_duration'], marker='o', linestyle='-', color='b')
    plt.errorbar(processed_df['len_kb'], processed_df['mean_duration'], yerr=processed_df['std_dev'])
    plt.xscale('log', base=2)
    plt.title('Cache size')
    plt.xlabel('KB, log scale')
    plt.ylabel('Mean Duration (ms)')
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.savefig(image_output)


process_and_plot('result.csv', '/home/raphael/Pictures/cacheline.png')

