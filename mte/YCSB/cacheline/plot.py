#!/usr/bin/env python

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the CSV file with the correct delimiter
df = pd.read_csv('result.csv', delimiter=';')

# Strip any leading/trailing whitespace from column names
df.columns = df.columns.str.strip()

# Convert 'nano' column to numeric, coercing errors to NaN
df['nano'] = pd.to_numeric(df['nano'], errors='coerce')

# Check column names for debugging
print(df.columns)

# Remove rows with NaN in 'nano' (if conversion failed)
df = df.dropna(subset=['nano'])

# Remove outliers based on the Interquartile Range (IQR) method
def remove_outliers(df, column):
    # Calculate Q1 (25th percentile) and Q3 (75th percentile)
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    
    # Define the bounds for outliers
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    # Filter the DataFrame to exclude outliers
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

# Apply outlier removal for 'nano' and 'size' columns
df = remove_outliers(df, 'nano')
df = remove_outliers(df, 'size')

# Create the first plot with scatter points
plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x='size', y='nano', hue='steps', palette='viridis', size='steps', sizes=(50, 200))
plt.title('Time (nano) vs Size and Steps (Points)')
plt.xlabel('Size')
plt.ylabel('Time (nano)')
plt.legend(title='Steps', loc='upper right')
plt.grid(True)
plt.savefig('/mnt/c/Users/t-rdichler/Downloads/cache_points.png')
plt.clf()  # Clear the plot to prepare for the next one

# Create the second plot with trend lines for each step
plt.figure(figsize=(10, 6))
sns.lineplot(data=df, x='size', y='nano', hue='steps', markers=True, palette='viridis', ci=None)
plt.title('Time (nano) vs Size and Steps (Trend)')
plt.xlabel('Size')
plt.ylabel('Time (nano)')
plt.legend(title='Steps', loc='upper right')
plt.grid(True)
plt.savefig('/mnt/c/Users/t-rdichler/Downloads/cache_trend.png')

