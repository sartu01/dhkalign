

import os
print("DEBUG: cwd =", os.getcwd())
print("DEBUG: files =", os.listdir())

import pandas as pd
import glob

# Finds all CSV files in the current directory
csv_files = glob.glob('*.csv')

# If no CSV files found, alert the user
if not csv_files:
    print("🚨 No CSV files found in this directory.")
    exit(1)

# Read each CSV file into a DataFrame and collect
dataframes = []
for file in csv_files:
    print(f"Loading {file}...")
    df = pd.read_csv(file)
    dataframes.append(df)

# Concatenate all DataFrames
merged_df = pd.concat(dataframes, ignore_index=True)

# Remove duplicate rows (optional)
merged_df.drop_duplicates(inplace=True)

# Write out the merged CSV
output_file = 'merged_output.csv'
merged_df.to_csv(output_file, index=False)
print(f"✅ Merged {len(csv_files)} files successfully into '{output_file}'")