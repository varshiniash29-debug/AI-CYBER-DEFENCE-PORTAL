import pandas as pd

# Load fraud dataset
df = pd.read_csv("fraud_data.csv")

print("\nFirst 5 rows:\n")
print(df.head())

print("\nColumn names:\n")
print(df.columns)

# Show unique values (important for labels)
for col in df.columns:
    if df[col].dtype == 'object':
        print(f"\nUnique values in {col}:\n")
        print(df[col].unique()[:10])