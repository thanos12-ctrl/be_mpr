import numpy as np
import pandas as pd

# Load the data
file_path = 'processed_ednet_sequences.npy'

print(f"--- Loading {file_path} ---")
try:
    data = np.load(file_path)
    print("✅ File loaded successfully.")
except FileNotFoundError:
    print("❌ Error: File not found. Make sure you ran the previous script.")
    exit()

# 1. CHECK SHAPE
# Expected: (Num_Sequences, 100, 5)
print(f"\n--- 1. Dimensions Check ---")
print(f"Shape: {data.shape}")
if len(data.shape) == 3 and data.shape[1] == 100 and data.shape[2] == 5:
    print("✅ Shape looks correct.")
else:
    print(f"⚠️ WARNING: Unexpected shape. Expected (N, 100, 5).")

# 2. CHECK FOR NANs / INFs (Corruption)
print(f"\n--- 2. Integrity Check ---")
if np.isnan(data).any():
    print(f"❌ DATA CORRUPTION: Found {np.isnan(data).sum()} NaN values.")
else:
    print("✅ No NaNs found.")

if np.isinf(data).any():
    print(f"❌ DATA CORRUPTION: Found {np.isinf(data).sum()} Infinite values.")
else:
    print("✅ No Infinite values found.")

# 3. FEATURE STATISTICS
# Features: [is_correct, difficulty, elapsed_time, lag_time, part]
feature_names = ['is_correct', 'difficulty', 'elapsed_time', 'lag_time', 'part']

print(f"\n--- 3. Feature Distribution (Sanity Check) ---")
# Flatten the batch and time dimensions to calculate stats for each feature
flat_data = data.reshape(-1, 5)

df_stats = pd.DataFrame(flat_data, columns=feature_names)
print(df_stats.describe().T[['mean', 'std', 'min', 'max']])

# 4. LOGIC CHECKS
print(f"\n--- 4. Logic Validation ---")
# Check: is_correct should be binary (0 or 1)
unique_correct = np.unique(df_stats['is_correct'])
if np.all(np.isin(unique_correct, [0, 1])):
    print("✅ 'is_correct' contains only binary values (0, 1).")
else:
    print(f"⚠️ WARNING: 'is_correct' has weird values: {unique_correct[:5]}")

# Check: difficulty should be 0.0 to 1.0
if df_stats['difficulty'].max() <= 1.0 and df_stats['difficulty'].min() >= 0.0:
    print("✅ 'difficulty' is within range [0, 1].")
else:
    print(f"⚠️ WARNING: 'difficulty' out of bounds! Max: {df_stats['difficulty'].max()}")

# Check: part should be integers (usually 1-7 for EdNet)
print(f"Unique 'part' values found: {np.unique(df_stats['part']).astype(int)}")

# 5. VISUAL SAMPLE
print(f"\n--- 5. Visual Sample (First 5 steps of Sequence 0) ---")
sample_seq = data[0, :5, :]
df_sample = pd.DataFrame(sample_seq, columns=feature_names)
print(df_sample)