#!/usr/bin/env python

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def remove_outliers(data, column, threshold=1.5):
    """Removes outliers from a pandas Series using the IQR method."""
    Q1 = data[column].quantile(0.25)
    Q3 = data[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - threshold * IQR
    upper_bound = Q3 + threshold * IQR
    return data[(data[column] >= lower_bound) & (data[column] <= upper_bound)]

def process_and_plot(csv_file):
    # Load the CSV file
    df = pd.read_csv(csv_file)
    df = pd.read_csv(csv_file, delimiter=';')

    # Ensure the required columns are present
    if 'len' not in df.columns or 'duration' not in df.columns:
        raise ValueError("CSV file must contain 'len' and 'duration' columns.")

    # Convert durations to milliseconds
    df['duration'] = df['duration'] / 1e6

    # Convert lengths to KB (1 element = 4 bytes)
    df['len_kb'] = (df['len'] * 4) // 1024

    # Group data by len_kb and process each group
    processed_data = []
    for length_kb, group in df.groupby('len_kb'):
        # Remove outliers for the group
        group_cleaned = remove_outliers(group, 'duration')
        # Calculate the mean duration for the len_kb
        mean_duration = group_cleaned['duration'].mean()
        processed_data.append({'len_kb': length_kb, 'mean_duration': mean_duration})

    # Create a DataFrame for the processed data
    processed_df = pd.DataFrame(processed_data)

    # Sort the DataFrame by len_kb
    processed_df.sort_values(by='len_kb', inplace=True)

    plt.figure(figsize=(10, 6))
    for label, position in {'L1':48, 'L2': 512, 'L3': 8 * 1024}.items():
        plt.axvline(x=position, color='r', linestyle='--', linewidth=1)
        plt.text(position, plt.ylim()[1], label, color='g', fontsize=10,
                 verticalalignment='top', horizontalalignment='center', rotation=0)


    plt.plot(processed_df['len_kb'], processed_df['mean_duration'], marker='o', linestyle='-', color='b')
    plt.xscale('log', base=2)
    plt.title('Mean Duration vs. Array Length (in KB)')
    plt.xlabel('Array Length (KB, log scale)')
    plt.ylabel('Mean Duration (ms)')
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.savefig('/mnt/c/Users/t-rdichler/Downloads/simple.png')


process_and_plot('data.csv')

