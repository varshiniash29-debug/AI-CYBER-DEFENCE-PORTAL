import pandas as pd

# Load new dataset
df = pd.read_csv("new_data.csv")

print("\nFirst 5 rows:\n")
print(df.head())

print("\nColumn names:\n")
print(df.columns)

# Try to detect label column automatically
for col in df.columns:
    if df[col].dtype == 'object':
        print(f"\nUnique values in {col}:\n")
        print(df[col].unique())